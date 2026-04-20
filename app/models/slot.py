"""
Pydantic models for Slot entity.
"""

from pydantic import BaseModel, Field
from enum import Enum
from typing import Optional
from datetime import datetime


class SlotStatus(str, Enum):
    AVAILABLE = "available"
    LOCKED = "locked"
    BOOKED = "booked"


class SlotInDB(BaseModel):
    id: str = Field(alias="_id")
    provider_id: str
    date: str  # "YYYY-MM-DD"
    time: str  # "HH:MM"
    status: SlotStatus = SlotStatus.AVAILABLE
    locked_by: Optional[str] = None  # customer_id who locked
    lock_expires_at: Optional[datetime] = None
    version: int = 0  # Optimistic concurrency control

    model_config = {"populate_by_name": True}


class SlotResponse(BaseModel):
    id: str
    provider_id: str
    date: str
    time: str
    status: SlotStatus


class SlotQueryParams(BaseModel):
    provider_id: str
    date: str  # "YYYY-MM-DD"
