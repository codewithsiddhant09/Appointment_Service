"""
OpenAI GPT service — handles extraction and response generation.

Falls back to rule-based parsing on any LLM failure.
"""

from __future__ import annotations

import json
import logging
from datetime import date as _date
from typing import Optional

from openai import AsyncOpenAI, APIError, APITimeoutError

from app.core.config import get_settings
from app.llm.prompts import (
    EXTRACTION_SYSTEM,
    EXTRACTION_USER,
    RESPONSE_SYSTEM,
    RESPONSE_USER,
)
from app.llm.schemas import (
    ConversationSession,
    ConversationTurn,
    ExtractedEntities,
    Intent,
)

logger = logging.getLogger(__name__)

_client: Optional[AsyncOpenAI] = None


def _get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        settings = get_settings()
        _client = AsyncOpenAI(
            api_key=settings.OPENAI_API_KEY,
            timeout=settings.LLM_TIMEOUT_SECONDS,
        )
    return _client


def _history_text(session: ConversationSession, max_turns: int = 20) -> str:
    """Render recent turns as a readable string for the prompt."""
    recent = session.turns[-max_turns:]
    if not recent:
        return "(no prior messages)"
    return "\n".join(f"{t.role}: {t.content}" for t in recent)


# ─── Entity extraction ───────────────────────────────────────────────

async def extract_entities(
    user_message: str,
    session: ConversationSession,
    services_list: str,
    providers_list: str,
) -> ExtractedEntities:
    """Call GPT to extract intent + entities from the user message.

    Returns ExtractedEntities on success.
    Raises on unrecoverable error (caller should use fallback).
    """
    settings = get_settings()
    client = _get_client()

    system_prompt = EXTRACTION_SYSTEM.format(
        services_list=services_list,
        providers_list=providers_list,
        today=_date.today().isoformat(),
    )
    user_prompt = EXTRACTION_USER.format(
        history=_history_text(session),
        user_message=user_message,
    )

    try:
        resp = await client.chat.completions.create(
            model=settings.LLM_MODEL,
            temperature=0.0,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
        )

        raw = resp.choices[0].message.content or "{}"
        data = json.loads(raw)
        return ExtractedEntities(**data)

    except (json.JSONDecodeError, TypeError, KeyError) as exc:
        logger.warning("LLM returned unparseable JSON: %s", exc)
        raise
    except (APIError, APITimeoutError) as exc:
        logger.warning("OpenAI API error during extraction: %s", exc)
        raise


# ─── Response generation ─────────────────────────────────────────────

async def generate_response(
    session: ConversationSession,
    action_result: str = "",
    awaiting_confirmation: bool = False,
) -> str:
    """Generate a natural-language reply via GPT."""
    settings = get_settings()
    client = _get_client()

    fields = session.fields
    missing = fields.missing_for_booking()

    user_prompt = RESPONSE_USER.format(
        history=_history_text(session),
        service=fields.service_name or "—",
        provider=fields.provider_name or "—",
        date=fields.date or "—",
        time=fields.time or "—",
        customer_name=fields.customer_name or "—",
        customer_phone=fields.customer_phone or "—",
        missing_fields=", ".join(missing) if missing else "none",
        intent=session.current_intent.value,
        action_result=action_result or "none",
        awaiting_confirmation=str(awaiting_confirmation).lower(),
    )

    try:
        resp = await client.chat.completions.create(
            model=settings.LLM_MODEL,
            temperature=0.7,
            max_tokens=300,
            messages=[
                {"role": "system", "content": RESPONSE_SYSTEM},
                {"role": "user", "content": user_prompt},
            ],
        )
        return (resp.choices[0].message.content or "").strip()

    except (APIError, APITimeoutError) as exc:
        logger.warning("OpenAI API error during response gen: %s", exc)
        # Fallback: build a mechanical response
        return _mechanical_response(missing, action_result, awaiting_confirmation)


def _mechanical_response(
    missing: list[str],
    action_result: str,
    awaiting_confirmation: bool,
) -> str:
    """Deterministic fallback when the LLM is unavailable."""
    if action_result and "confirmed" in action_result.lower():
        return f"Your booking is confirmed! {action_result}"
    if action_result and "error" in action_result.lower():
        return f"Sorry, something went wrong: {action_result}"
    if awaiting_confirmation:
        return "Everything looks good. Shall I confirm this booking? (yes/no)"
    if missing:
        field_labels = {
            "service_id": "which service you'd like (e.g. doctor, lawyer, salon)",
            "provider_id": "which provider you'd prefer",
            "date": "what date works for you (e.g. tomorrow, next Monday)",
            "time": "what time you'd like",
            "customer_name": "your full name",
            "customer_phone": "your phone number",
        }
        next_field = missing[0]
        return f"Could you tell me {field_labels.get(next_field, next_field)}?"
    return "I have all the details. Would you like me to go ahead and book this?"
