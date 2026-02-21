"""Repository for pgvector embedding storage and similarity search.

Uses Supabase's postgrest client to update the embedding column
on triage_sessions and calls an RPC function for KNN retrieval.
"""

from __future__ import annotations

import logging
from uuid import UUID

from fastapi import Depends
from supabase import AsyncClient

from app.models.similarity import SimilarCase
from app.services.supabase_client import get_supabase

logger = logging.getLogger("app.repositories.similarity")

_TABLE = "triage_sessions"
_RPC_MATCH = "match_triage_sessions"


class SimilarityRepository:
    """Store and search triage session embeddings via pgvector.

    Time complexity:
        store_embedding: O(1) single row UPDATE.
        find_similar: O(N log K) approximate KNN via IVFFlat index.
    """

    def __init__(self, client: AsyncClient) -> None:
        self._client = client

    async def store_embedding(
        self, session_id: UUID, embedding: list[float]
    ) -> None:
        """Write an embedding vector to the triage_sessions row.

        Args:
            session_id: The triage session to update.
            embedding: The float vector to store.
        """
        await (
            self._client.table(_TABLE)
            .update({"embedding": embedding})
            .eq("id", str(session_id))
            .execute()
        )
        logger.info(
            "Stored %d-dim embedding for session %s",
            len(embedding),
            session_id,
        )

    async def find_similar(
        self, embedding: list[float], limit: int = 5
    ) -> list[SimilarCase]:
        """Find the K nearest triage sessions by cosine similarity.

        Args:
            embedding: The query vector.
            limit: Maximum number of results to return.

        Returns:
            List of SimilarCase ordered by descending similarity.
        """
        response = await self._client.rpc(
            _RPC_MATCH,
            {"query_embedding": embedding, "match_count": limit},
        ).execute()
        cases = [SimilarCase.model_validate(row) for row in response.data]
        logger.info("Found %d similar cases", len(cases))
        return cases


async def get_similarity_repository(
    client: AsyncClient = Depends(get_supabase),
) -> SimilarityRepository:
    """FastAPI dependency that provides a SimilarityRepository."""
    return SimilarityRepository(client)
