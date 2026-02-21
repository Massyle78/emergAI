"""FastAPI application factory.

Entry point for the emergAI backend. The factory pattern allows
creating multiple app instances with different configs (e.g., testing).
"""

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import Settings
from app.routers.health import router as health_router
from app.routers.patients import router as patients_router
from app.utils.errors import register_error_handlers
from app.utils.logging import setup_logging

logger = logging.getLogger("app")


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build and return a fully configured FastAPI application.

    Args:
        settings: Optional settings override (used in tests).
                  Defaults to loading from environment.
    """
    settings = settings or Settings()

    setup_logging()

    application = _build_application(settings)
    application.state.settings = settings
    _add_cors_middleware(application, settings)
    register_error_handlers(application)
    _include_routers(application)

    return application


def _build_application(settings: Settings) -> FastAPI:
    """Create the FastAPI instance with metadata and lifespan."""
    return FastAPI(
        title="emergAI",
        description="Multimodal ER Triage & Risk Prediction Platform",
        version="0.1.0",
        lifespan=_lifespan,
        docs_url="/docs" if not settings.is_production else None,
        redoc_url="/redoc" if not settings.is_production else None,
    )


@asynccontextmanager
async def _lifespan(application: FastAPI) -> AsyncGenerator[None, None]:
    """Manage application startup and shutdown resources."""
    settings: Settings = application.state.settings
    await _startup(application, settings)
    yield
    await _shutdown(application)


async def _startup(application: FastAPI, settings: Settings) -> None:
    """Initialize shared resources on application startup."""
    if settings.supabase_url and settings.supabase_service_role_key:
        from app.services.supabase_client import create_supabase_client

        application.state.supabase = await create_supabase_client(settings)
    else:
        application.state.supabase = None
        logger.warning("Supabase credentials not configured; client disabled")


async def _shutdown(application: FastAPI) -> None:
    """Clean up shared resources on application shutdown."""
    logger.info("Application shutting down")


def _add_cors_middleware(application: FastAPI, settings: Settings) -> None:
    """Attach CORS middleware with configured origins."""
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


def _include_routers(application: FastAPI) -> None:
    """Register all API routers on the application."""
    application.include_router(health_router)
    application.include_router(patients_router, prefix="/api/v1")


app = create_app()
