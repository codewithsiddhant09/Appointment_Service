"""
Voice service — Whisper STT (OpenAI) + AWS Polly TTS.

Accepts raw audio bytes, returns transcript / synthesised speech.
"""

from __future__ import annotations

import asyncio
import base64
import io
import logging
from typing import Optional

import boto3
from botocore.exceptions import BotoCoreError, ClientError
from openai import AsyncOpenAI, APIError, APITimeoutError

from app.core.config import get_settings

logger = logging.getLogger(__name__)

_openai_client: Optional[AsyncOpenAI] = None
_polly_client = None


def _get_openai_client() -> AsyncOpenAI:
    global _openai_client
    if _openai_client is None:
        settings = get_settings()
        _openai_client = AsyncOpenAI(
            api_key=settings.OPENAI_API_KEY,
            timeout=settings.LLM_TIMEOUT_SECONDS,
        )
    return _openai_client


def _get_polly_client():
    global _polly_client
    if _polly_client is None:
        settings = get_settings()
        _polly_client = boto3.client(
            "polly",
            aws_access_key_id=settings.AWS_ACCESS_KEY,
            aws_secret_access_key=settings.AWS_SECRET_KEY,
            region_name=settings.AWS_REGION,
        )
    return _polly_client


# ─── Speech-to-text (OpenAI Whisper) ──────────────────────────────────

async def transcribe(audio_bytes: bytes, filename: str = "audio.webm") -> str:
    """Transcribe audio to text using OpenAI Whisper."""
    settings = get_settings()
    client = _get_openai_client()

    buf = io.BytesIO(audio_bytes)
    buf.name = filename

    try:
        result = await client.audio.transcriptions.create(
            model=settings.WHISPER_MODEL,
            file=buf,
            language="en",
        )
        transcript = result.text.strip()
        logger.info("Whisper transcript (%d chars): %s…", len(transcript), transcript[:80])
        return transcript
    except (APIError, APITimeoutError) as exc:
        logger.error("Whisper transcription failed: %s", exc)
        raise RuntimeError(f"Speech-to-text failed: {exc}") from exc


# ─── Text-to-speech (AWS Polly) ───────────────────────────────────────

async def synthesise(text: str) -> str:
    """Convert text to speech using AWS Polly.

    Returns:
        Base64-encoded audio string (mp3 by default).
    """
    settings = get_settings()
    polly = _get_polly_client()

    # Polly has a 3000 char limit per request — truncate if needed
    if len(text) > 2900:
        text = text[:2900] + "…"

    try:
        # boto3 is synchronous, run in a thread to avoid blocking the event loop
        loop = asyncio.get_running_loop()
        response = await loop.run_in_executor(
            None,
            lambda: polly.synthesize_speech(
                Text=text,
                OutputFormat=settings.POLLY_OUTPUT_FORMAT,
                VoiceId=settings.POLLY_VOICE_ID,
                Engine="neural",
            ),
        )

        audio_stream = response.get("AudioStream")
        if audio_stream is None:
            raise RuntimeError("Polly returned no audio stream")

        audio_bytes = audio_stream.read()
        logger.info("Polly TTS: %d bytes, voice=%s", len(audio_bytes), settings.POLLY_VOICE_ID)
        return base64.b64encode(audio_bytes).decode("ascii")

    except (BotoCoreError, ClientError) as exc:
        logger.error("AWS Polly TTS failed: %s", exc)
        raise RuntimeError(f"Text-to-speech failed: {exc}") from exc
