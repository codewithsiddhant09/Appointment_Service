"""
Pydantic models for Service entity.
"""

from pydantic import BaseModel, Field
from enum import Enum


class ServiceCategory(str, Enum):
    DOCTOR = "doctor"
    LAWYER = "lawyer"
    SALON = "salon"


class ServiceInDB(BaseModel):
    id: str = Field(alias="_id")
    name: str
    category: ServiceCategory

    model_config = {"populate_by_name": True}


class ServiceResponse(BaseModel):
    id: str
    name: str
    category: ServiceCategory
