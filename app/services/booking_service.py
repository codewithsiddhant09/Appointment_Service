"""
Booking service — orchestrates locking, confirmation, cancellation,
and rescheduling with full concurrency safety.
"""

import uuid
from datetime import datetime
from typing import Optional

from pymongo.errors import DuplicateKeyError

from app.core.database import get_db
from app.core.config import get_settings
from app.core.exceptions import (
    SlotNotAvailableError,
    SlotAlreadyLockedError,
    LockExpiredError,
    BookingNotFoundError,
    DoubleBookingError,
    ConcurrencyError,
    InvalidInputError,
    UnauthorizedError,
)
from app.core.logging import logger
from app.models.booking import BookingStatus
from app.models.slot import SlotStatus
from app.services import lock_service, slot_service


# ---------------------------------------------------------------------------
# Customer upsert (find-or-create by phone)
# ---------------------------------------------------------------------------

async def _get_or_create_customer(name: str, phone: str) -> str:
    """Return customer _id, creating the document if needed."""
    db = get_db()
    existing = await db.customers.find_one({"phone": phone})
    if existing:
        return str(existing["_id"])

    customer_id = uuid.uuid4().hex
    try:
        await db.customers.insert_one({"_id": customer_id, "name": name, "phone": phone})
    except DuplicateKeyError:
        # Race condition — another request created it first
        existing = await db.customers.find_one({"phone": phone})
        return str(existing["_id"])
    return customer_id


# ---------------------------------------------------------------------------
# Lock a slot
# ---------------------------------------------------------------------------

async def lock_slot(
    provider_id: str, date: str, time: str, customer_phone: str
) -> dict:
    """
    1. Acquire a distributed Redis lock on the slot.
    2. Mark the slot as LOCKED in MongoDB.

    Returns lock metadata on success.
    """
    # Step 1: distributed lock via Redis
    lock_id, expires_at = await lock_service.acquire_slot_lock(
        provider_id, date, time, customer_phone
    )
    if lock_id is None:
        raise SlotAlreadyLockedError()

    # Step 2: transition slot in Mongo
    locked = await slot_service.mark_slot_locked(
        provider_id, date, time, customer_phone, expires_at
    )
    if not locked:
        # Slot was not available — release the Redis lock we just acquired
        await lock_service.release_slot_lock(provider_id, date, time, lock_id)
        raise SlotNotAvailableError()

    logger.info(
        "Slot locked: provider=%s date=%s time=%s lock_id=%s",
        provider_id, date, time, lock_id,
    )
    return {
        "lock_id": lock_id,
        "provider_id": provider_id,
        "date": date,
        "time": time,
        "expires_at": expires_at.isoformat() + "Z",
    }


# ---------------------------------------------------------------------------
# Confirm booking
# ---------------------------------------------------------------------------

async def confirm_booking(
    customer_id: str,            # customer phone — the unique identifier used during locking
    customer_name: str,
    provider_id: str,
    date: str,
    time: str,
    lock_id: Optional[str] = None,   # Redis lock — validated if supplied (voice/chat path)
    slot_id: Optional[str] = None,   # MongoDB slot _id — used for logging
) -> dict:
    """
    1. Fetch the slot from MongoDB; validate status (locked) and ownership (locked_by).
    2. Optionally validate the Redis lock when lock_id is supplied.
    3. Transition slot LOCKED → BOOKED.
    4. Upsert customer, insert booking document.
    5. Force-release Redis lock.
    """
    settings = get_settings()
    db = get_db()

    logger.debug(
        "Confirm booking hit: slot_id=%s customer_id=%s provider=%s %s %s lock_id=%s",
        slot_id, customer_id, provider_id, date, time, lock_id,
    )

    # Step 1 — Fetch slot from MongoDB
    slot = await db.slots.find_one(
        {"provider_id": provider_id, "date": date, "time": time}
    )
    logger.debug("Slot state: %s", slot)

    # Step 2a — Slot must be in LOCKED status
    if slot is None or slot.get("status") != SlotStatus.LOCKED:
        logger.warning(
            "Confirm rejected: slot not locked — provider=%s %s %s status=%s",
            provider_id, date, time,
            slot.get("status") if slot else "NOT_FOUND",
        )
        raise LockExpiredError("Slot is not reserved or has expired")

    # Step 2b — Caller must be the one who locked the slot
    if slot.get("locked_by") != customer_id:
        logger.warning(
            "Confirm rejected: locked_by=%s != caller=%s",
            slot.get("locked_by"), customer_id,
        )
        raise UnauthorizedError()

    # Step 2c — Belt-and-suspenders: also validate Redis lock when provided
    if lock_id is not None:
        valid = await lock_service.validate_lock(provider_id, date, time, lock_id)
        if not valid:
            logger.warning("Confirm rejected: Redis lock invalid/expired for lock_id=%s", lock_id)
            raise LockExpiredError()

    # Step 3 — Transition slot LOCKED → BOOKED
    booked = await slot_service.mark_slot_booked(provider_id, date, time)
    if not booked:
        raise SlotNotAvailableError("Slot could not be transitioned to booked state")

    # Step 4 — Upsert customer record
    customer_db_id = await _get_or_create_customer(customer_name or customer_id, customer_id)

    # Step 4b — Create booking document
    booking_id = uuid.uuid4().hex
    now = datetime.utcnow()
    booking_doc = {
        "_id": booking_id,
        "customer_id": customer_db_id,
        "provider_id": provider_id,
        "date": date,
        "time": time,
        "status": BookingStatus.CONFIRMED,
        "created_at": now,
        "updated_at": now,
    }

    for attempt in range(1, settings.MAX_BOOKING_RETRIES + 1):
        try:
            await db.bookings.insert_one(booking_doc)
            logger.debug("Booking document inserted: id=%s attempt=%d", booking_id, attempt)
            break
        except DuplicateKeyError:
            # Unique index caught a true double-booking — roll back slot
            await slot_service.release_slot(provider_id, date, time)
            raise DoubleBookingError()
        except Exception as exc:
            logger.warning("Booking insert attempt %d failed: %s", attempt, exc)
            if attempt == settings.MAX_BOOKING_RETRIES:
                await slot_service.release_slot(provider_id, date, time)
                raise ConcurrencyError()

    # Step 5 — Release Redis lock (force, ownership already verified via MongoDB)
    await lock_service.force_release_slot_lock(provider_id, date, time)

    logger.info("Booking confirmed: id=%s customer_db_id=%s", booking_id, customer_db_id)
    return {
        "id": booking_id,
        "customer_id": customer_db_id,
        "provider_id": provider_id,
        "date": date,
        "time": time,
        "status": BookingStatus.CONFIRMED,
        "created_at": now.isoformat() + "Z",
        "updated_at": now.isoformat() + "Z",
    }


# ---------------------------------------------------------------------------
# Cancel booking
# ---------------------------------------------------------------------------

async def cancel_booking(booking_id: str) -> dict:
    """Cancel an existing confirmed booking and release the slot."""
    db = get_db()
    booking = await db.bookings.find_one({"_id": booking_id})
    if not booking:
        raise BookingNotFoundError()

    if booking["status"] != BookingStatus.CONFIRMED:
        raise InvalidInputError(f"Cannot cancel a booking with status '{booking['status']}'")

    now = datetime.utcnow()
    await db.bookings.update_one(
        {"_id": booking_id},
        {"$set": {"status": BookingStatus.CANCELLED, "updated_at": now}},
    )

    # Free the slot
    await slot_service.release_slot(booking["provider_id"], booking["date"], booking["time"])

    logger.info("Booking cancelled: id=%s", booking_id)
    booking["status"] = BookingStatus.CANCELLED
    booking["updated_at"] = now
    booking["id"] = str(booking.pop("_id"))
    return booking


# ---------------------------------------------------------------------------
# Reschedule booking
# ---------------------------------------------------------------------------

async def reschedule_booking(
    booking_id: str, new_date: str, new_time: str, lock_id: str
) -> dict:
    """
    Reschedule = cancel old slot + confirm new slot atomically.
    The caller must have already locked the NEW slot.
    """
    db = get_db()
    booking = await db.bookings.find_one({"_id": booking_id})
    if not booking:
        raise BookingNotFoundError()
    if booking["status"] != BookingStatus.CONFIRMED:
        raise InvalidInputError(f"Cannot reschedule a booking with status '{booking['status']}'")

    provider_id = booking["provider_id"]

    # Validate the lock on the new slot
    valid = await lock_service.validate_lock(provider_id, new_date, new_time, lock_id)
    if not valid:
        raise LockExpiredError("Lock on new slot has expired")

    # Book the new slot
    booked = await slot_service.mark_slot_booked(provider_id, new_date, new_time)
    if not booked:
        raise SlotNotAvailableError("New slot could not be booked")

    # Release old slot
    await slot_service.release_slot(provider_id, booking["date"], booking["time"])

    # Update booking document
    now = datetime.utcnow()
    await db.bookings.update_one(
        {"_id": booking_id},
        {
            "$set": {
                "date": new_date,
                "time": new_time,
                "status": BookingStatus.CONFIRMED,
                "updated_at": now,
            }
        },
    )

    # Release Redis lock on new slot
    await lock_service.release_slot_lock(provider_id, new_date, new_time, lock_id)

    logger.info("Booking rescheduled: id=%s → %s %s", booking_id, new_date, new_time)
    return {
        "id": booking_id,
        "customer_id": booking["customer_id"],
        "provider_id": provider_id,
        "date": new_date,
        "time": new_time,
        "status": BookingStatus.CONFIRMED,
        "created_at": booking["created_at"].isoformat() if isinstance(booking["created_at"], datetime) else booking["created_at"],
        "updated_at": now.isoformat(),
    }
