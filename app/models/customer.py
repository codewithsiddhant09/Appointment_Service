"""
Pydantic models for Customer entity.
"""

from pydantic import BaseModel, Field, field_validator
import re


class CustomerCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    phone: str = Field(min_length=7, max_length=20)

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        pattern = r"^\+?[0-9\s\-]{7,20}$"
        if not re.match(pattern, v):
            raise ValueError("Invalid phone number format")
        return v


class CustomerInDB(BaseModel):
    id: str = Field(alias="_id")
    name: str
    phone: str

    model_config = {"populate_by_name": True}


class CustomerResponse(BaseModel):
    id: str
    name: str
    phone: str
