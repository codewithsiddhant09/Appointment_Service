"""
Routes for services and providers (catalog).
"""

from fastapi import APIRouter, Query
from typing import Optional
from app.services import catalog_service

router = APIRouter(prefix="/api/v1", tags=["Catalog"])


@router.get("/services")
async def get_services():
    """List all available service categories."""
    return await catalog_service.list_services()


@router.get("/providers")
async def get_providers(service_id: Optional[str] = Query(None, description="Filter by service")):
    """List providers, optionally filtered by service."""
    return await catalog_service.list_providers(service_id)


@router.get("/providers/{provider_id}")
async def get_provider(provider_id: str):
    """Get a single provider's details."""
    return await catalog_service.get_provider(provider_id)
