"""
Routes for slot management.
"""

from fastapi import APIRouter, Query
from app.services import slot_service

router = APIRouter(prefix="/api/v1", tags=["Slots"])


@router.get("/slots")
async def get_available_slots(
    provider_id: str = Query(..., description="Provider ID"),
    date: str = Query(..., description="Date in YYYY-MM-DD format"),
):
    """Return all available (unlocked, unbooked) slots for a provider on a date."""
    return await slot_service.get_available_slots(provider_id, date)


@router.post("/slots/generate")
async def generate_slots(
    provider_id: str = Query(...),
    date: str = Query(...),
    start_time: str = Query("09:00"),
    end_time: str = Query("17:00"),
    duration_minutes: int = Query(30),
):
    """
    Admin endpoint — generate time slots for a provider on a date.
    Idempotent: existing slots are not duplicated.
    """
    count = await slot_service.generate_slots_for_provider(
        provider_id, date, start_time, end_time, duration_minutes
    )
    return {"created": count, "provider_id": provider_id, "date": date}
