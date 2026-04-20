"""
Conversation manager — orchestrates the multi-turn booking flow.

Responsibilities
────────────────
* Maintain per-session state in Redis (turns, accumulated fields).
* Each turn:  extract → resolve → act → respond.
* Falls back to rule-based NLU when the LLM fails.
* Validates extracted data against the real catalog before accepting.
"""

from __future__ import annotations

import json
import logging
import uuid
from typing import Optional

from app.core.config import get_settings
from app.llm import llm_service
from app.llm.fallback import fallback_extract
from app.llm.schemas import (
    BookingFields,
    ChatResponse,
    ConversationSession,
    ConversationTurn,
    ExtractedEntities,
    Intent,
)
from app.services import booking_service, catalog_service, slot_service
from app.services.lock_service import get_redis

logger = logging.getLogger(__name__)

_SESSION_TTL = 1800  # 30 minutes


# ─── Session persistence (Redis) ─────────────────────────────────────

def _session_key(session_id: str) -> str:
    return f"convo:{session_id}"


async def _load_session(session_id: str) -> Optional[ConversationSession]:
    r = get_redis()
    raw = await r.get(_session_key(session_id))
    if raw:
        return ConversationSession.model_validate_json(raw)
    return None


async def _save_session(session: ConversationSession) -> None:
    r = get_redis()
    await r.set(
        _session_key(session.session_id),
        session.model_dump_json(),
        ex=_SESSION_TTL,
    )


# ─── Catalog helpers (build context strings for the LLM) ─────────────

async def _services_text() -> str:
    services = await catalog_service.list_services()
    return "\n".join(f"- {s['name']} (id={s['id']})" for s in services) or "(none)"


async def _providers_text(service_id: Optional[str] = None) -> str:
    providers = await catalog_service.list_providers(service_id)
    return "\n".join(f"- {p['name']} (id={p['id']})" for p in providers) or "(none)"


# ─── Resolve extracted names → real IDs ──────────────────────────────

async def _resolve_service(name: Optional[str], fields: BookingFields) -> None:
    """If the user mentioned a service name, look it up and fill the ID."""
    if not name or fields.service_id:
        return
    services = await catalog_service.list_services()
    lower = name.lower()
    for s in services:
        if lower in s["name"].lower() or s["name"].lower() in lower:
            fields.service_id = s["id"]
            fields.service_name = s["name"]
            return


async def _resolve_provider(name: Optional[str], fields: BookingFields) -> None:
    """If the user mentioned a provider name, look it up and fill the ID."""
    if not name or fields.provider_id:
        return
    providers = await catalog_service.list_providers(fields.service_id)
    lower = name.lower()
    for p in providers:
        if lower in p["name"].lower() or p["name"].lower() in lower:
            fields.provider_id = p["id"]
            fields.provider_name = p["name"]
            return


# ─── Merge extracted entities into session fields ─────────────────────

async def _merge_entities(
    entities: ExtractedEntities,
    fields: BookingFields,
) -> None:
    """Overlay newly extracted entities onto the accumulated fields."""
    await _resolve_service(entities.service_name, fields)
    await _resolve_provider(entities.provider_name, fields)

    # Always take the latest date/time from the user (allows corrections)
    if entities.date:
        fields.date = entities.date
    if entities.time:
        fields.time = entities.time
    if entities.customer_name and not fields.customer_name:
        fields.customer_name = entities.customer_name
    if entities.customer_phone and not fields.customer_phone:
        fields.customer_phone = entities.customer_phone
    if entities.booking_id:
        fields.booking_id = entities.booking_id


# ─── Validate slot availability ───────────────────────────────────────

async def _validate_slot(fields: BookingFields) -> Optional[str]:
    """Return an error string if the chosen slot is unavailable, else None."""
    if not (fields.provider_id and fields.date and fields.time):
        return None
    slots = await slot_service.get_available_slots(fields.provider_id, fields.date)
    available_times = {s["time"] for s in slots}
    if fields.time not in available_times:
        return (
            f"The time {fields.time} on {fields.date} is not available. "
            f"Available times: {', '.join(sorted(available_times)) or 'none'}."
        )
    return None


# ─── Execute booking actions ──────────────────────────────────────────

async def _execute_booking(fields: BookingFields) -> str:
    """Lock slot → confirm booking.  Returns a human-friendly result."""
    try:
        lock = await booking_service.lock_slot(
            fields.provider_id,
            fields.date,
            fields.time,
            fields.customer_phone,
        )
        fields.lock_id = lock["lock_id"]

        booking = await booking_service.confirm_booking(
            customer_id=fields.customer_phone,   # phone is the customer identifier
            customer_name=fields.customer_name,
            provider_id=fields.provider_id,
            date=fields.date,
            time=fields.time,
            lock_id=fields.lock_id,
        )
        fields.booking_id = booking["id"]
        return f"Booking confirmed!  Your booking ID is {booking['id']}."
    except Exception as exc:
        logger.exception("Booking execution failed")
        return f"Error: {exc}"


async def _execute_cancel(fields: BookingFields) -> str:
    if not fields.booking_id:
        return "I need your booking ID to cancel.  Could you provide it?"
    try:
        await booking_service.cancel_booking(fields.booking_id)
        return "Your booking has been cancelled."
    except Exception as exc:
        return f"Error cancelling: {exc}"


# ─── Affirmation / negation detection ────────────────────────────────

_YES_WORDS = {"yes", "yeah", "yep", "sure", "ok", "okay", "confirm", "go ahead", "do it", "please"}
_NO_WORDS = {"no", "nah", "nope", "cancel", "stop", "don't", "not now", "never mind"}


def _is_affirmative(text: str) -> Optional[bool]:
    lower = text.strip().lower()
    if any(w in lower for w in _YES_WORDS):
        return True
    if any(w in lower for w in _NO_WORDS):
        return False
    return None


# ─── Main entry point ────────────────────────────────────────────────

async def handle_message(
    session_id: Optional[str],
    user_message: str,
) -> ChatResponse:
    """Process one user turn and return a ChatResponse."""

    # 1. Load or create session
    session: Optional[ConversationSession] = None
    if session_id:
        session = await _load_session(session_id)
    if session is None:
        session = ConversationSession(session_id=session_id or uuid.uuid4().hex)

    # 2. Record user turn
    session.turns.append(ConversationTurn(role="user", content=user_message))

    # 3. If we were awaiting booking confirmation, check yes/no
    if session.awaiting_confirmation:
        answer = _is_affirmative(user_message)
        if answer is True:
            session.awaiting_confirmation = False
            # Validate slot one more time
            slot_err = await _validate_slot(session.fields)
            if slot_err:
                action_result = slot_err
            else:
                action_result = await _execute_booking(session.fields)
            reply = await llm_service.generate_response(session, action_result=action_result)
            session.turns.append(ConversationTurn(role="assistant", content=reply))
            await _save_session(session)
            return ChatResponse(
                session_id=session.session_id,
                reply=reply,
                intent=session.current_intent,
                extracted=ExtractedEntities(intent=session.current_intent),
                missing_fields=session.fields.missing_for_booking(),
                booking_confirmed="confirmed" in action_result.lower(),
                booking_id=session.fields.booking_id,
            )
        elif answer is False:
            session.awaiting_confirmation = False
            reply = "No problem — the booking was not made. Feel free to change any details or start over."
            session.turns.append(ConversationTurn(role="assistant", content=reply))
            await _save_session(session)
            return ChatResponse(
                session_id=session.session_id,
                reply=reply,
                intent=session.current_intent,
                extracted=ExtractedEntities(intent=session.current_intent),
                missing_fields=session.fields.missing_for_booking(),
            )
        # If neither yes nor no, fall through to normal extraction
        session.awaiting_confirmation = False

    # 4. Extract intent + entities (LLM → fallback)
    services_text = await _services_text()
    providers_text = await _providers_text(session.fields.service_id)

    try:
        entities = await llm_service.extract_entities(
            user_message, session, services_text, providers_text,
        )
    except Exception:
        logger.info("LLM extraction failed — using rule-based fallback")
        entities = fallback_extract(user_message)

    session.current_intent = entities.intent

    # 5. Merge entities into session fields
    await _merge_entities(entities, session.fields)

    # 6. Handle intents
    action_result = ""
    fields = session.fields

    if entities.intent == Intent.CANCEL_APPOINTMENT:
        if entities.booking_id:
            fields.booking_id = entities.booking_id
        action_result = await _execute_cancel(fields)

    elif entities.intent in (Intent.BOOK_APPOINTMENT, Intent.CHECK_AVAILABILITY, Intent.UNKNOWN):
        # Check if all fields are present
        missing = fields.missing_for_booking()
        if not missing:
            # Validate the slot
            slot_err = await _validate_slot(fields)
            if slot_err:
                action_result = slot_err
                # Clear invalid time so user can re-pick
                fields.time = None
            else:
                # Ask for confirmation
                session.awaiting_confirmation = True
        elif entities.intent == Intent.CHECK_AVAILABILITY and fields.provider_id and fields.date:
            slots = await slot_service.get_available_slots(fields.provider_id, fields.date)
            times = [s["time"] for s in slots]
            if times:
                action_result = f"Available times on {fields.date}: {', '.join(times)}."
            else:
                action_result = f"No available slots on {fields.date}."

    elif entities.intent == Intent.GREETING:
        action_result = ""  # LLM will generate a greeting

    elif entities.intent == Intent.GOODBYE:
        action_result = ""

    # 7. Generate response
    try:
        reply = await llm_service.generate_response(
            session,
            action_result=action_result,
            awaiting_confirmation=session.awaiting_confirmation,
        )
    except Exception:
        # Ultimate fallback
        missing = fields.missing_for_booking()
        if session.awaiting_confirmation:
            reply = "I have all the details. Shall I confirm this booking? (yes/no)"
        elif missing:
            reply = f"I still need: {', '.join(missing)}. Could you provide those?"
        else:
            reply = action_result or "How can I help you?"

    session.turns.append(ConversationTurn(role="assistant", content=reply))
    await _save_session(session)

    return ChatResponse(
        session_id=session.session_id,
        reply=reply,
        intent=session.current_intent,
        extracted=entities,
        missing_fields=fields.missing_for_booking(),
        booking_confirmed=bool(fields.booking_id and "confirmed" in action_result.lower()),
        booking_id=fields.booking_id,
    )
