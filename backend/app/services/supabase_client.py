"""Supabase client lifecycle management and FastAPI dependency provider."""

import logging
from typing import AsyncGenerator

from fastapi import Request
from supabase import AsyncClient, create_async_client

from app.config import Settings

logger = logging.getLogger("app.supabase")


async def create_supabase_client(settings: Settings) -> AsyncClient:
    """Create and return a configured async Supabase client.

    Args:
        settings: Application settings containing Supabase credentials.

    Returns:
        An initialized AsyncClient ready for database operations.
    """
    client = await create_async_client(
        settings.supabase_url,
        settings.supabase_service_role_key,
    )
    logger.info("Supabase client initialized for %s", settings.supabase_url)
    return client


async def get_supabase(request: Request) -> AsyncGenerator[AsyncClient, None]:
    """FastAPI dependency that yields the Supabase client from app state.

    The client is stored on the app instance during startup and
    shared across all requests for connection pooling efficiency.
    """
    client: AsyncClient = request.app.state.supabase
    yield client
