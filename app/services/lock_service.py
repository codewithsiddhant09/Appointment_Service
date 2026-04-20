"""
Distributed lock service using Redis.

Provides atomic slot locking with automatic TTL expiry to prevent
stale locks from blocking the system.
"""

import uuid
from datetime import datetime, timedelta

import redis.asyncio as redis

from app.core.config import get_settings
from app.core.logging import logger

_redis: redis.Redis | None = None

# Lua script for atomic lock release — only the lock owner can release.
_UNLOCK_SCRIPT = """
if redis.call("get", KEYS[1]) == ARGV[1] then
    return redis.call("del", KEYS[1])
else
    return 0
end
"""


async def connect_redis() -> None:
    global _redis
    settings = get_settings()
    logger.info("Connecting to Redis at %s", settings.REDIS_URL)
    _redis = redis.from_url(settings.REDIS_URL, decode_responses=True)
    await _redis.ping()
    logger.info("Redis connected")


async def close_redis() -> None:
    global _redis
    if _redis:
        await _redis.aclose()
        _redis = None
        logger.info("Redis connection closed")


def get_redis() -> redis.Redis:
    if _redis is None:
        raise RuntimeError("Redis not initialized. Call connect_redis() first.")
    return _redis


def _slot_lock_key(provider_id: str, date: str, time: str) -> str:
    """Deterministic Redis key for a slot lock."""
    return f"slot_lock:{provider_id}:{date}:{time}"


async def acquire_slot_lock(
    provider_id: str, date: str, time: str, customer_phone: str
) -> tuple[str | None, datetime | None]:
    """
    Attempt to acquire a distributed lock on a slot.

    Returns (lock_id, expires_at) on success, (None, None) if already locked.
    Uses SET NX EX for atomic acquire + TTL.
    """
    settings = get_settings()
    r = get_redis()
    lock_key = _slot_lock_key(provider_id, date, time)
    lock_id = uuid.uuid4().hex
    lock_value = f"{lock_id}:{customer_phone}"
    ttl = settings.SLOT_LOCK_TTL_SECONDS

    acquired = await r.set(lock_key, lock_value, nx=True, ex=ttl)
    if acquired:
        expires_at = datetime.utcnow() + timedelta(seconds=ttl)
        logger.info(
            "Lock acquired: key=%s lock_id=%s ttl=%ds", lock_key, lock_id, ttl
        )
        return lock_id, expires_at

    logger.warning("Lock NOT acquired (already held): key=%s", lock_key)
    return None, None


async def validate_lock(
    provider_id: str, date: str, time: str, lock_id: str
) -> bool:
    """Check that the given lock_id still owns the slot lock."""
    r = get_redis()
    lock_key = _slot_lock_key(provider_id, date, time)
    value = await r.get(lock_key)
    if value is None:
        return False
    stored_lock_id = value.split(":")[0]
    return stored_lock_id == lock_id


async def release_slot_lock(
    provider_id: str, date: str, time: str, lock_id: str
) -> bool:
    """
    Release a slot lock atomically — only if the caller owns it.
    Uses a Lua script to avoid race conditions.
    """
    r = get_redis()
    lock_key = _slot_lock_key(provider_id, date, time)

    value = await r.get(lock_key)
    if value is None:
        return False

    # Verify the caller actually owns this lock before releasing
    stored_lock_id = value.split(":")[0]
    if stored_lock_id != lock_id:
        logger.warning(
            "Lock release rejected: caller lock_id=%s != stored=%s key=%s",
            lock_id, stored_lock_id, lock_key,
        )
        return False

    result = await r.eval(_UNLOCK_SCRIPT, 1, lock_key, value)
    released = result == 1
    if released:
        logger.info("Lock released: key=%s lock_id=%s", lock_key, lock_id)
    return released


async def extend_lock(
    provider_id: str, date: str, time: str, lock_id: str, extra_seconds: int = 60
) -> bool:
    """Extend the TTL of an existing lock if caller still owns it."""
    r = get_redis()
    lock_key = _slot_lock_key(provider_id, date, time)
    value = await r.get(lock_key)
    if value is None:
        return False
    stored_lock_id = value.split(":")[0]
    if stored_lock_id != lock_id:
        return False
    settings = get_settings()
    new_ttl = min(extra_seconds, settings.SLOT_LOCK_TTL_SECONDS)
    await r.expire(lock_key, new_ttl)
    return True


async def force_release_slot_lock(provider_id: str, date: str, time: str) -> None:
    """Release a slot lock unconditionally (call only after MongoDB ownership is validated)."""
    r = get_redis()
    lock_key = _slot_lock_key(provider_id, date, time)
    deleted = await r.delete(lock_key)
    if deleted:
        logger.info("Force-released Redis lock: key=%s", lock_key)
    else:
        logger.debug("Force-release: key already gone (expired): key=%s", lock_key)
