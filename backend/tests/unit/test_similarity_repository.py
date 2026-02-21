"""Tests for SimilarityRepository using the same Supabase client
chain approach as test_patient_repository.py.
"""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.models.similarity import SimilarCase
from app.repositories.similarity_repository import SimilarityRepository

SESSION_ID = uuid4()
PATIENT_ID = uuid4()
EMBEDDING = [0.1] * 768


def _mock_client() -> AsyncMock:
    """Create a mock Supabase client."""
    return AsyncMock()


def _setup_table_chain(client: AsyncMock, response_data: object) -> MagicMock:
    """Configure .table() builder chain."""
    mock_response = MagicMock()
    mock_response.data = response_data

    builder = MagicMock()
    builder.update = MagicMock(return_value=builder)
    builder.eq = MagicMock(return_value=builder)
    builder.execute = AsyncMock(return_value=mock_response)

    client.table = MagicMock(return_value=builder)
    return builder


def _setup_rpc_chain(client: AsyncMock, response_data: object) -> MagicMock:
    """Configure .rpc() builder chain."""
    mock_response = MagicMock()
    mock_response.data = response_data

    builder = MagicMock()
    builder.execute = AsyncMock(return_value=mock_response)

    client.rpc = MagicMock(return_value=builder)
    return builder


# ---------------------------------------------------------------------------
# store_embedding
# ---------------------------------------------------------------------------
class TestStoreEmbedding:
    @pytest.mark.asyncio
    async def test_updates_triage_sessions_row(self) -> None:
        client = _mock_client()
        builder = _setup_table_chain(client, [{"id": str(SESSION_ID)}])

        repo = SimilarityRepository(client)
        await repo.store_embedding(SESSION_ID, EMBEDDING)

        client.table.assert_called_with("triage_sessions")
        builder.update.assert_called_once_with({"embedding": EMBEDDING})
        builder.eq.assert_called_once_with("id", str(SESSION_ID))


# ---------------------------------------------------------------------------
# find_similar
# ---------------------------------------------------------------------------
class TestFindSimilar:
    @pytest.mark.asyncio
    async def test_returns_similar_cases(self) -> None:
        cases_data = [
            {
                "id": str(uuid4()),
                "patient_id": str(uuid4()),
                "status": "completed",
                "similarity": 0.95,
            },
            {
                "id": str(uuid4()),
                "patient_id": str(uuid4()),
                "status": "completed",
                "similarity": 0.82,
            },
        ]
        client = _mock_client()
        _setup_rpc_chain(client, cases_data)

        repo = SimilarityRepository(client)
        results = await repo.find_similar(EMBEDDING, limit=5)

        assert len(results) == 2
        assert all(isinstance(c, SimilarCase) for c in results)
        assert results[0].similarity == 0.95
        client.rpc.assert_called_once_with(
            "match_triage_sessions",
            {"query_embedding": EMBEDDING, "match_count": 5},
        )

    @pytest.mark.asyncio
    async def test_empty_results(self) -> None:
        client = _mock_client()
        _setup_rpc_chain(client, [])

        repo = SimilarityRepository(client)
        results = await repo.find_similar(EMBEDDING)

        assert results == []

    @pytest.mark.asyncio
    async def test_default_limit(self) -> None:
        client = _mock_client()
        _setup_rpc_chain(client, [])

        repo = SimilarityRepository(client)
        await repo.find_similar(EMBEDDING)

        client.rpc.assert_called_once_with(
            "match_triage_sessions",
            {"query_embedding": EMBEDDING, "match_count": 5},
        )

    @pytest.mark.asyncio
    async def test_custom_limit(self) -> None:
        client = _mock_client()
        _setup_rpc_chain(client, [])

        repo = SimilarityRepository(client)
        await repo.find_similar(EMBEDDING, limit=10)

        client.rpc.assert_called_once_with(
            "match_triage_sessions",
            {"query_embedding": EMBEDDING, "match_count": 10},
        )
