"""
Rule-based fallback NLU — used when the LLM is unreachable or returns junk.

Covers the most common intents via keyword / regex matching.
"""

from __future__ import annotations

import re
from datetime import date, timedelta

from app.llm.schemas import ExtractedEntities, Intent


# ── Keyword maps ─────────────────────────────────────────────────────

_INTENT_KEYWORDS: dict[Intent, list[str]] = {
    Intent.CANCEL_APPOINTMENT: [
        "cancel", "remove", "delete", "drop",
    ],
    Intent.RESCHEDULE_APPOINTMENT: [
        "reschedule", "change", "move", "shift", "update",
    ],
    Intent.CHECK_AVAILABILITY: [
        "available", "availability", "open slots", "free",
        "when can", "what times",
    ],
    Intent.BOOK_APPOINTMENT: [
        "book", "appointment", "schedule", "reserve", "set up",
        "make an appointment", "new booking",
    ],
    Intent.GREETING: [
        "hello", "hi", "hey", "good morning", "good afternoon",
        "good evening", "howdy",
    ],
    Intent.GOODBYE: [
        "bye", "goodbye", "see you", "thanks", "thank you", "that's all",
    ],
}

_SERVICE_KEYWORDS: dict[str, list[str]] = {
    "doctor": ["doctor", "medical", "health", "checkup", "physician", "clinic"],
    "lawyer": ["lawyer", "legal", "attorney", "law", "counsel"],
    "salon": ["salon", "hair", "haircut", "beauty", "spa", "barber", "styling"],
}

# ── Date parsing helpers ─────────────────────────────────────────────

_RELATIVE_DAYS: dict[str, int] = {
    "today": 0,
    "tomorrow": 1,
    "day after tomorrow": 2,
}

_WEEKDAY_NAMES = {
    "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
    "friday": 4, "saturday": 5, "sunday": 6,
}


def _parse_relative_date(text: str) -> str | None:
    lower = text.lower()

    for label, offset in _RELATIVE_DAYS.items():
        if label in lower:
            return (date.today() + timedelta(days=offset)).isoformat()

    # "next Monday", "this Friday" etc.
    for name, weekday in _WEEKDAY_NAMES.items():
        if name in lower:
            today = date.today()
            days_ahead = (weekday - today.weekday() + 7) % 7
            if days_ahead == 0:
                days_ahead = 7  # "next X" — at least a week out
            return (today + timedelta(days=days_ahead)).isoformat()

    # Explicit ISO date
    m = re.search(r"\b(\d{4}-\d{2}-\d{2})\b", text)
    if m:
        return m.group(1)

    # US-style MM/DD or DD/MM — try MM/DD first (American default)
    m = re.search(r"\b(\d{1,2})[/\-.](\d{1,2})(?:[/\-.](\d{2,4}))?\b", text)
    if m:
        month, day = int(m.group(1)), int(m.group(2))
        year = int(m.group(3)) if m.group(3) else date.today().year
        if year < 100:
            year += 2000
        try:
            return date(year, month, day).isoformat()
        except ValueError:
            pass

    return None


# ── Time parsing ─────────────────────────────────────────────────────

_TIME_RE = re.compile(
    r"\b(\d{1,2})\s*[:.](\d{2})\s*(am|pm|AM|PM)?\b"   # requires HH:MM
    r"|\b(\d{1,2})\s*(am|pm|AM|PM)\b"                   # or H am/pm
)


def _parse_time(text: str) -> str | None:
    m = _TIME_RE.search(text)
    if not m:
        return None

    if m.group(1) is not None:
        # Branch 1: HH:MM with optional am/pm
        hour = int(m.group(1))
        minute = int(m.group(2) or 0)
        ampm = (m.group(3) or "").lower()
    else:
        # Branch 2: H am/pm (no minutes)
        hour = int(m.group(4))
        minute = 0
        ampm = (m.group(5) or "").lower()

    if ampm == "pm" and hour < 12:
        hour += 12
    elif ampm == "am" and hour == 12:
        hour = 0

    if 0 <= hour <= 23 and 0 <= minute <= 59:
        return f"{hour:02d}:{minute:02d}"
    return None


# ── Phone parsing ────────────────────────────────────────────────────

_PHONE_RE = re.compile(r"(?:\+?\d[\d\s\-().]{6,18}\d)")


def _parse_phone(text: str) -> str | None:
    m = _PHONE_RE.search(text)
    if m:
        digits = re.sub(r"[^\d+]", "", m.group(0))
        if len(digits) >= 7:
            return digits
    return None


# ── Name extraction (very simple heuristic) ──────────────────────────

_NAME_PATTERNS = [
    re.compile(r"(?:my name is|i'm|i am|name:\s*|call me)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)", re.IGNORECASE),
]


def _parse_name(text: str) -> str | None:
    for pat in _NAME_PATTERNS:
        m = pat.search(text)
        if m:
            return m.group(1).strip()
    return None


# ── Main fallback function ───────────────────────────────────────────

def fallback_extract(text: str) -> ExtractedEntities:
    """Extract intent + entities using rules only (no LLM)."""
    lower = text.lower()

    # Intent
    intent = Intent.UNKNOWN
    for candidate, keywords in _INTENT_KEYWORDS.items():
        if any(kw in lower for kw in keywords):
            intent = candidate
            break

    # Service
    service_name: str | None = None
    for svc, keywords in _SERVICE_KEYWORDS.items():
        if any(kw in lower for kw in keywords):
            service_name = svc
            break

    return ExtractedEntities(
        intent=intent,
        service_name=service_name,
        provider_name=None,  # too ambiguous for rules
        date=_parse_relative_date(text),
        time=_parse_time(text),
        customer_name=_parse_name(text),
        customer_phone=_parse_phone(text),
    )
