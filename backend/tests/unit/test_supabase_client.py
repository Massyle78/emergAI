"""Tests for Supabase client lifecycle and dependency provider."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.config import Settings
from app.services.supabase_client import create_supabase_client, get_supabase


class TestCreateSupabaseClient:
    @pytest.mark.asyncio
    async def test_creates_client_with_settings(self):
        settings = Settings(
            supabase_url="https://test.supabase.co",
            supabase_service_role_key="test-key",
        )
        mock_client = AsyncMock()
        with patch(
            "app.services.supabase_client.create_async_client",
            return_value=mock_client,
        ) as mock_create:
            client = await create_supabase_client(settings)
            mock_create.assert_called_once_with(
                "https://test.supabase.co",
                "test-key",
            )
            assert client is mock_client

    @pytest.mark.asyncio
    async def test_logs_initialization(self):
        settings = Settings(
            supabase_url="https://test.supabase.co",
            supabase_service_role_key="test-key",
        )
        with patch(
            "app.services.supabase_client.create_async_client",
            return_value=AsyncMock(),
        ), patch("app.services.supabase_client.logger") as mock_logger:
            await create_supabase_client(settings)
            mock_logger.info.assert_called_once()


class TestGetSupabase:
    @pytest.mark.asyncio
    async def test_yields_client_from_app_state(self):
        mock_client = AsyncMock()
        mock_request = MagicMock()
        mock_request.app.state.supabase = mock_client

        gen = get_supabase(mock_request)
        client = await gen.__anext__()
        assert client is mock_client
