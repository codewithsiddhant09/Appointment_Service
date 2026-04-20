"""
Pydantic schemas for LLM input/output and conversation state.
"""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


# ── Intents ──────────────────────────────────────────────────────────

class Intent(str, Enum):
    BOOK_APPOINTMENT = "book_appointment"
    CANCEL_APPOINTMENT = "cancel_appointment"
    RESCHEDULE_APPOINTMENT = "reschedule_appointment"
    CHECK_AVAILABILITY = "check_availability"
    GREETING = "greeting"
    GOODBYE = "goodbye"
    UNKNOWN = "unknown"


# ── Extracted entities from a single user turn ───────────────────────

class ExtractedEntities(BaseModel):
    """Structured data the LLM extracts from user text."""

    intent: Intent = Intent.UNKNOWN
    service_name: Optional[str] = Field(None, description="E.g. 'doctor', 'lawyer', 'salon'")
    provider_name: Optional[str] = Field(None, description="Provider / doctor / stylist name")
    date: Optional[str] = Field(None, description="ISO date  YYYY-MM-DD")
    time: Optional[str] = Field(None, description="24-hr time  HH:MM")
    customer_name: Optional[str] = None
    customer_phone: Optional[str] = None
    booking_id: Optional[str] = Field(None, description="For cancel / reschedule")

    # New date/time when rescheduling
    new_date: Optional[str] = None
    new_time: Optional[str] = None


# ── Conversation session state ───────────────────────────────────────

class BookingFields(BaseModel):
    """Accumulated booking fields across turns."""

    service_id: Optional[str] = None
    service_name: Optional[str] = None
    provider_id: Optional[str] = None
    provider_name: Optional[str] = None
    date: Optional[str] = None
    time: Optional[str] = None
    customer_name: Optional[str] = None
    customer_phone: Optional[str] = None
    lock_id: Optional[str] = None
    booking_id: Optional[str] = None

    def missing_for_booking(self) -> list[str]:
        """Return field names still required to complete a booking."""
        required = ["service_id", "provider_id", "date", "time", "customer_name", "customer_phone"]
        return [f for f in required if not getattr(self, f)]


class ConversationTurn(BaseModel):
    role: str  # "user" | "assistant"
    content: str


class ConversationSession(BaseModel):
    session_id: str
    turns: list[ConversationTurn] = Field(default_factory=list)
    fields: BookingFields = Field(default_factory=BookingFields)
    current_intent: Intent = Intent.UNKNOWN
    awaiting_confirmation: bool = False


# ── API request / response ───────────────────────────────────────────

class ChatRequest(BaseModel):
    session_id: Optional[str] = Field(None, description="Omit to start a new session")
    message: str = Field(..., min_length=1, max_length=2000)


class ChatResponse(BaseModel):
    session_id: str
    reply: str
    intent: Intent
    extracted: ExtractedEntities
    missing_fields: list[str]
    booking_confirmed: bool = False
    booking_id: Optional[str] = None


class VoiceChatRequest(BaseModel):
    session_id: Optional[str] = None
    # audio bytes are sent as multipart form – handled in the route


class VoiceChatResponse(BaseModel):
    session_id: str
    transcript: str
    reply: str
    audio_base64: Optional[str] = Field(None, description="Base64-encoded TTS audio (mp3)")
    intent: Intent
    missing_fields: list[str]
    booking_confirmed: bool = False
    booking_id: Optional[str] = None
