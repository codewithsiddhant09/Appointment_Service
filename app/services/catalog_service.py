"""
Service-layer logic for Service and Provider entities (read-only lookups).
"""

from app.core.database import get_db
from app.core.exceptions import ProviderNotFoundError
from app.core.logging import logger


async def list_services() -> list[dict]:
    """Return all services (only docs with the canonical name+category schema)."""
    db = get_db()
    cursor = db.services.find({"name": {"$exists": True}, "category": {"$exists": True}})
    services = await cursor.to_list(length=100)
    return [{"id": str(s["_id"]), "name": s["name"], "category": s["category"]} for s in services]


async def list_providers(service_id: str | None = None) -> list[dict]:
    """Return providers, optionally filtered by service_id (canonical schema only)."""
    db = get_db()
    # Only include docs that have the canonical singular service_id field
    query: dict = {"name": {"$exists": True}, "service_id": {"$exists": True}}
    if service_id is not None:
        query["service_id"] = service_id
    cursor = db.providers.find(query)
    providers = await cursor.to_list(length=500)
    results = []
    for p in providers:
        results.append({
            "id": str(p["_id"]),
            "name": p["name"],
            "service_id": p["service_id"],
            "availability": p.get("availability", []),
        })
    return results


async def get_provider(provider_id: str) -> dict:
    """Fetch a single provider or raise."""
    db = get_db()
    p = await db.providers.find_one({"_id": provider_id})
    if not p:
        raise ProviderNotFoundError()
    return {
        "id": str(p["_id"]),
        "name": p["name"],
        "service_id": p["service_id"],
        "availability": p.get("availability", []),
    }
