"""
Pydantic models for Booking entity.
"""

from pydantic import BaseModel, Field, field_validator
from enum import Enum
from datetime import datetime
from typing import Optional
import re


class BookingStatus(str, Enum):
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    RESCHEDULED = "rescheduled"


class BookingCreate(BaseModel):
    slot_id: str                                             # MongoDB slot _id
    customer_id: str = Field(min_length=7, max_length=20)   # customer phone (unique identifier)
    customer_name: str = Field(default="", max_length=200)
    provider_id: str
    date: str   # "YYYY-MM-DD"
    time: str   # "HH:MM"
    lock_id: Optional[str] = None                           # Redis lock — validated if present

    @field_validator("customer_id")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        if not re.match(r"^\+?[0-9\s\-]{7,20}$", v):
            raise ValueError("Invalid phone number format")
        return v

    @field_validator("date")
    @classmethod
    def validate_date(cls, v: str) -> str:
        try:
            datetime.strptime(v, "%Y-%m-%d")
        except ValueError:
            raise ValueError("Date must be in YYYY-MM-DD format")
        return v

    @field_validator("time")
    @classmethod
    def validate_time(cls, v: str) -> str:
        if not re.match(r"^([01]\d|2[0-3]):([0-5]\d)$", v):
            raise ValueError("Time must be in HH:MM format (24-hour)")
        return v


class BookingInDB(BaseModel):
    id: str = Field(alias="_id")
    customer_id: str
    provider_id: str
    date: str
    time: str
    status: BookingStatus = BookingStatus.CONFIRMED
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {"populate_by_name": True}


class BookingResponse(BaseModel):
    id: str
    customer_id: str
    provider_id: str
    date: str
    time: str
    status: BookingStatus
    created_at: datetime
    updated_at: datetime


class RescheduleRequest(BaseModel):
    new_date: str
    new_time: str
    lock_id: str  # Lock on the new slot

    @field_validator("new_date")
    @classmethod
    def validate_date(cls, v: str) -> str:
        try:
            datetime.strptime(v, "%Y-%m-%d")
        except ValueError:
            raise ValueError("Date must be in YYYY-MM-DD format")
        return v

    @field_validator("new_time")
    @classmethod
    def validate_time(cls, v: str) -> str:
        if not re.match(r"^([01]\d|2[0-3]):([0-5]\d)$", v):
            raise ValueError("Time must be in HH:MM format (24-hour)")
        return v


class LockSlotRequest(BaseModel):
    provider_id: str
    date: str
    time: str
    customer_phone: str

    @field_validator("date")
    @classmethod
    def validate_date(cls, v: str) -> str:
        try:
            parsed = datetime.strptime(v, "%Y-%m-%d")
            if parsed.date() < datetime.utcnow().date():
                raise ValueError("Cannot book a slot in the past")
        except ValueError as e:
            if "Cannot book" in str(e):
                raise
            raise ValueError("Date must be in YYYY-MM-DD format")
        return v

    @field_validator("time")
    @classmethod
    def validate_time(cls, v: str) -> str:
        if not re.match(r"^([01]\d|2[0-3]):([0-5]\d)$", v):
            raise ValueError("Time must be in HH:MM format (24-hour)")
        return v

    @field_validator("customer_phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        if not re.match(r"^\+?[0-9\s\-]{7,20}$", v):
            raise ValueError("Invalid phone number format")
        return v
