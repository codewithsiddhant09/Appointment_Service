"""
Conversation routes — text chat and voice endpoints.

POST /api/v1/chat          — text-based conversational booking
POST /api/v1/chat/voice    — voice-based (audio in, audio + text out)
GET  /api/v1/chat/session   — retrieve session state (debug / frontend sync)
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.llm.schemas import ChatRequest, ChatResponse, VoiceChatResponse
from app.services import conversation_service, voice_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["Conversation"])

MAX_AUDIO_SIZE = 25 * 1024 * 1024  # 25 MB (Whisper limit)


# ─── Text chat ────────────────────────────────────────────────────────

@router.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    """Send a text message and receive a structured response."""
    return await conversation_service.handle_message(
        session_id=req.session_id,
        user_message=req.message,
    )


# ─── Voice chat ───────────────────────────────────────────────────────

@router.post("/chat/voice", response_model=VoiceChatResponse)
async def voice_chat(
    audio: UploadFile = File(..., description="Audio file (webm, wav, mp3, m4a)"),
    session_id: Optional[str] = Form(None),
):
    """Send an audio file → transcribe → chat → synthesise reply."""

    # Read + validate size
    audio_bytes = await audio.read()
    if len(audio_bytes) > MAX_AUDIO_SIZE:
        raise HTTPException(413, "Audio file too large (max 25 MB)")
    if len(audio_bytes) == 0:
        raise HTTPException(400, "Empty audio file")

    # 1. Speech-to-text
    filename = audio.filename or "audio.webm"
    try:
        transcript = await voice_service.transcribe(audio_bytes, filename)
    except RuntimeError as exc:
        raise HTTPException(502, str(exc))

    if not transcript.strip():
        raise HTTPException(422, "Could not detect speech in the audio")

    # 2. Process through conversation engine
    chat_resp = await conversation_service.handle_message(
        session_id=session_id,
        user_message=transcript,
    )

    # 3. Text-to-speech
    audio_b64: Optional[str] = None
    try:
        audio_b64 = await voice_service.synthesise(chat_resp.reply)
    except RuntimeError:
        logger.warning("TTS failed — returning text only")

    return VoiceChatResponse(
        session_id=chat_resp.session_id,
        transcript=transcript,
        reply=chat_resp.reply,
        audio_base64=audio_b64,
        intent=chat_resp.intent,
        missing_fields=chat_resp.missing_fields,
        booking_confirmed=chat_resp.booking_confirmed,
        booking_id=chat_resp.booking_id,
    )


# ─── Debug: get session state ─────────────────────────────────────────

@router.get("/chat/session/{session_id}")
async def get_session(session_id: str):
    """Retrieve the current conversation session (for debugging / frontend sync)."""
    session = await conversation_service._load_session(session_id)
    if session is None:
        raise HTTPException(404, "Session not found or expired")
    return session.model_dump()
