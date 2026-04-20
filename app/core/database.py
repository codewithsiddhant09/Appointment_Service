"""
MongoDB connection manager and index setup.
"""

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo import IndexModel, ASCENDING
from app.core.config import get_settings
from app.core.logging import logger

_client: AsyncIOMotorClient | None = None
_db: AsyncIOMotorDatabase | None = None


async def connect_db() -> None:
    """Initialize MongoDB connection and create indexes."""
    global _client, _db
    settings = get_settings()
    logger.info("Connecting to MongoDB at %s", settings.MONGO_URI)
    _client = AsyncIOMotorClient(settings.MONGO_URI)
    _db = _client[settings.MONGO_DB_NAME]
    await _create_indexes()
    logger.info("MongoDB connected — database: %s", settings.MONGO_DB_NAME)


async def close_db() -> None:
    """Close MongoDB connection."""
    global _client, _db
    if _client:
        _client.close()
        _client = None
        _db = None
        logger.info("MongoDB connection closed")


def get_db() -> AsyncIOMotorDatabase:
    """Return the active database handle."""
    if _db is None:
        raise RuntimeError("Database not initialized. Call connect_db() first.")
    return _db


async def _create_indexes() -> None:
    """
    Create all required indexes.
    The unique compound index on slots (provider_id, date, time) prevents
    double-booking at the database level.
    """
    db = get_db()

    # --- Slots collection ---
    await db.slots.create_indexes([
        IndexModel(
            [("provider_id", ASCENDING), ("date", ASCENDING), ("time", ASCENDING)],
            unique=True,
            name="unique_provider_date_time",
        ),
        IndexModel(
            [("provider_id", ASCENDING), ("date", ASCENDING), ("status", ASCENDING)],
            name="idx_slot_lookup",
        ),
        IndexModel(
            [("lock_expires_at", ASCENDING)],
            name="idx_lock_expiry",
        ),
    ])

    # --- Bookings collection ---
    await db.bookings.create_indexes([
        IndexModel(
            [("provider_id", ASCENDING), ("date", ASCENDING), ("time", ASCENDING)],
            unique=True,
            # Only enforce uniqueness for active bookings
            partialFilterExpression={"status": "confirmed"},
            name="unique_active_booking",
        ),
        IndexModel(
            [("customer_id", ASCENDING)],
            name="idx_booking_customer",
        ),
    ])

    # --- Customers collection ---
    await db.customers.create_indexes([
        IndexModel(
            [("phone", ASCENDING)],
            unique=True,
            name="unique_customer_phone",
        ),
    ])

    # --- Providers collection ---
    await db.providers.create_indexes([
        IndexModel(
            [("service_id", ASCENDING)],
            name="idx_provider_service",
        ),
    ])

    logger.info("Database indexes created")
