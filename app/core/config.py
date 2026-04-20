"""
Application configuration loaded from environment variables.
"""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Application
    APP_NAME: str = "Appointment Booking System"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # MongoDB
    MONGO_URI: str = "mongodb://localhost:27017"
    MONGO_DB_NAME: str = "appointment_db"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Slot locking
    SLOT_LOCK_TTL_SECONDS: int = 300  # 5 minutes

    # Retry
    MAX_BOOKING_RETRIES: int = 3

    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:3000"]

    # OpenAI / LLM
    OPENAI_API_KEY: str = ""
    LLM_MODEL: str = "gpt-4o"
    LLM_TIMEOUT_SECONDS: float = 30.0

    # Voice — Whisper STT (OpenAI)
    WHISPER_MODEL: str = "whisper-1"

    # Voice — AWS Polly TTS
    AWS_ACCESS_KEY: str = ""
    AWS_SECRET_KEY: str = ""
    AWS_REGION: str = "us-east-1"
    POLLY_VOICE_ID: str = "Joey"
    POLLY_OUTPUT_FORMAT: str = "mp3"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


@lru_cache()
def get_settings() -> Settings:
    return Settings()
