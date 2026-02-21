"""FastAPI application factory.

Entry point for the emergAI backend. The factory pattern allows
creating multiple app instances with different configs (e.g., testing).
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import Settings
from app.routers.health import router as health_router
from app.utils.errors import register_error_handlers
from app.utils.logging import setup_logging


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build and return a fully configured FastAPI application.

    Args:
        settings: Optional settings override (used in tests).
                  Defaults to loading from environment.
    """
    settings = settings or Settings()

    setup_logging()

    application = _build_application(settings)
    _add_cors_middleware(application, settings)
    register_error_handlers(application)
    _include_routers(application)

    return application


def _build_application(settings: Settings) -> FastAPI:
    """Create the FastAPI instance with metadata."""
    return FastAPI(
        title="emergAI",
        description="Multimodal ER Triage & Risk Prediction Platform",
        version="0.1.0",
        docs_url="/docs" if not settings.is_production else None,
        redoc_url="/redoc" if not settings.is_production else None,
    )


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


app = create_app()
