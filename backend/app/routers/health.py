"""Health check endpoint for load balancers and uptime monitoring."""

from fastapi import APIRouter

router = APIRouter(tags=["health"])

APP_VERSION = "0.1.0"


@router.get("/health")
async def health_check() -> dict:
    """Return application health status and version.

    Used by load balancers, container orchestrators, and uptime monitors
    to determine if the service is ready to receive traffic.
    """
    return {
        "status": "healthy",
        "version": APP_VERSION,
    }
