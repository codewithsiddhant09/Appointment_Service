"""
FastAPI application factory.

- Registers lifespan events (DB + Redis connect/disconnect).
- Mounts all route modules.
- Installs a global exception handler for AppException.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.database import connect_db, close_db
from app.core.exceptions import AppException
from app.core.logging import logger
from app.services.lock_service import connect_redis, close_redis
from app.routes import catalog, slots, bookings, conversation


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting up…")
    await connect_db()
    await connect_redis()
    yield
    # Shutdown
    logger.info("Shutting down…")
    await close_redis()
    await close_db()


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        lifespan=lifespan,
    )

    # CORS — restrict origins
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Global exception handler
    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
        )

    # Routes
    app.include_router(catalog.router)
    app.include_router(slots.router)
    app.include_router(bookings.router)
    app.include_router(conversation.router)

    # Health check
    @app.get("/health", tags=["Health"])
    async def health():
        return {"status": "ok"}

    return app


app = create_app()
