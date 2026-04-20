"""
Routes for booking lifecycle: lock → confirm → cancel / reschedule.
"""

from fastapi import APIRouter
from app.models.booking import BookingCreate, RescheduleRequest, LockSlotRequest
from app.services import booking_service
from app.core.logging import logger

router = APIRouter(prefix="/api/v1", tags=["Bookings"])


# ---------------------------------------------------------------------------
# Lock a slot (step 1 of 2-phase booking)
# ---------------------------------------------------------------------------

@router.post("/slots/lock")
async def lock_slot(req: LockSlotRequest):
    """
    Temporarily lock a slot for a customer.

    The lock expires automatically after the configured TTL (default 5 min).
    The returned `lock_id` must be passed when confirming the booking.
    """
    return await booking_service.lock_slot(
        provider_id=req.provider_id,
        date=req.date,
        time=req.time,
        customer_phone=req.customer_phone,
    )


# ---------------------------------------------------------------------------
# Confirm booking (step 2 of 2-phase booking)
# ---------------------------------------------------------------------------

@router.post("/bookings")
async def confirm_booking(req: BookingCreate):
    """
    Confirm a booking for a previously locked slot.

    Validates slot ownership via MongoDB (slot.locked_by == customer_id).
    Also validates Redis lock when lock_id is provided.
    """
    logger.debug(
        "POST /bookings: slot_id=%s customer_id=%s provider=%s %s %s",
        req.slot_id, req.customer_id, req.provider_id, req.date, req.time,
    )
    return await booking_service.confirm_booking(
        slot_id=req.slot_id,
        customer_id=req.customer_id,
        customer_name=req.customer_name,
        provider_id=req.provider_id,
        date=req.date,
        time=req.time,
        lock_id=req.lock_id,
    )


# ---------------------------------------------------------------------------
# Cancel booking
# ---------------------------------------------------------------------------

@router.patch("/bookings/{booking_id}/cancel")
async def cancel_booking(booking_id: str):
    """Cancel a confirmed booking and free the slot."""
    return await booking_service.cancel_booking(booking_id)


# ---------------------------------------------------------------------------
# Reschedule booking
# ---------------------------------------------------------------------------

@router.patch("/bookings/{booking_id}/reschedule")
async def reschedule_booking(booking_id: str, req: RescheduleRequest):
    """
    Reschedule a confirmed booking to a new date/time.

    The caller must first lock the new slot and pass the `lock_id`.
    """
    return await booking_service.reschedule_booking(
        booking_id=booking_id,
        new_date=req.new_date,
        new_time=req.new_time,
        lock_id=req.lock_id,
    )
