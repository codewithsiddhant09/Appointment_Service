"""
Slot management service.

Handles slot generation, availability queries, and status transitions
with optimistic concurrency control.
"""

from datetime import datetime, timedelta
from app.core.database import get_db
from app.core.exceptions import (
    SlotNotAvailableError,
    InvalidInputError,
)
from app.core.logging import logger
from app.models.slot import SlotStatus


async def get_available_slots(provider_id: str, date: str) -> list[dict]:
    """
    Return all available slots for a provider on a given date.
    Also reclaims slots whose locks have expired.
    """
    _validate_date(date)
    db = get_db()

    # Reclaim expired locks → mark them available again
    now = datetime.utcnow()
    await db.slots.update_many(
        {
            "provider_id": provider_id,
            "date": date,
            "status": SlotStatus.LOCKED,
            "lock_expires_at": {"$lte": now},
        },
        {
            "$set": {"status": SlotStatus.AVAILABLE, "locked_by": None, "lock_expires_at": None},
        },
    )

    cursor = db.slots.find({
        "provider_id": provider_id,
        "date": date,
        "status": SlotStatus.AVAILABLE,
    })
    slots = await cursor.to_list(length=200)
    return [
        {
            "id": str(s["_id"]),
            "provider_id": s["provider_id"],
            "date": s["date"],
            "time": s["time"],
            "status": s["status"],
        }
        for s in slots
    ]


async def mark_slot_locked(
    provider_id: str,
    date: str,
    time: str,
    customer_id: str,
    lock_expires_at: datetime,
) -> bool:
    """
    Atomically transition a slot from AVAILABLE → LOCKED using optimistic
    concurrency (status check acts as guard).

    Returns True if successful, False if slot was not available.
    """
    db = get_db()
    result = await db.slots.update_one(
        {
            "provider_id": provider_id,
            "date": date,
            "time": time,
            "status": SlotStatus.AVAILABLE,
        },
        {
            "$set": {
                "status": SlotStatus.LOCKED,
                "locked_by": customer_id,
                "lock_expires_at": lock_expires_at,
            },
            "$inc": {"version": 1},
        },
    )
    return result.modified_count == 1


async def mark_slot_booked(provider_id: str, date: str, time: str) -> bool:
    """Atomically transition a slot from LOCKED → BOOKED."""
    db = get_db()
    result = await db.slots.update_one(
        {
            "provider_id": provider_id,
            "date": date,
            "time": time,
            "status": SlotStatus.LOCKED,
        },
        {
            "$set": {
                "status": SlotStatus.BOOKED,
                "locked_by": None,
                "lock_expires_at": None,
            },
            "$inc": {"version": 1},
        },
    )
    return result.modified_count == 1


async def release_slot(provider_id: str, date: str, time: str) -> bool:
    """Release a booked or locked slot back to available."""
    db = get_db()
    result = await db.slots.update_one(
        {
            "provider_id": provider_id,
            "date": date,
            "time": time,
            "status": {"$in": [SlotStatus.BOOKED, SlotStatus.LOCKED]},
        },
        {
            "$set": {
                "status": SlotStatus.AVAILABLE,
                "locked_by": None,
                "lock_expires_at": None,
            },
            "$inc": {"version": 1},
        },
    )
    return result.modified_count == 1


async def generate_slots_for_provider(
    provider_id: str, date: str, start_time: str, end_time: str, duration_minutes: int = 30
) -> int:
    """
    Generate time slots for a provider on a specific date.
    Skips slots that already exist (upsert-like via unique index).
    Returns the count of newly created slots.
    """
    _validate_date(date)
    start = datetime.strptime(f"{date} {start_time}", "%Y-%m-%d %H:%M")
    end = datetime.strptime(f"{date} {end_time}", "%Y-%m-%d %H:%M")
    if start >= end:
        raise InvalidInputError("start_time must be before end_time")

    db = get_db()
    created = 0
    current = start
    while current < end:
        slot_time = current.strftime("%H:%M")
        try:
            await db.slots.insert_one({
                "_id": f"{provider_id}_{date}_{slot_time}",
                "provider_id": provider_id,
                "date": date,
                "time": slot_time,
                "status": SlotStatus.AVAILABLE,
                "locked_by": None,
                "lock_expires_at": None,
                "version": 0,
            })
            created += 1
        except Exception:
            # Duplicate key — slot already exists, skip
            pass
        current += timedelta(minutes=duration_minutes)

    logger.info("Generated %d new slots for provider %s on %s", created, provider_id, date)
    return created


def _validate_date(date: str) -> None:
    try:
        datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        raise InvalidInputError("Date must be in YYYY-MM-DD format")
