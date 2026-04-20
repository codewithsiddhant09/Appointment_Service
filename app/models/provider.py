"""
Pydantic models for Provider entity.
"""

from pydantic import BaseModel, Field
from typing import Optional


class DayAvailability(BaseModel):
    """Availability window for a single day."""
    day: str  # e.g. "monday"
    start_time: str  # "09:00"
    end_time: str  # "17:00"
    slot_duration_minutes: int = 30


class ProviderInDB(BaseModel):
    id: str = Field(alias="_id")
    name: str
    service_id: str
    availability: list[DayAvailability] = []

    model_config = {"populate_by_name": True}


class ProviderResponse(BaseModel):
    id: str
    name: str
    service_id: str
    availability: list[DayAvailability] = []


class ProviderQueryParams(BaseModel):
    service_id: Optional[str] = None
