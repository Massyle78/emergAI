"""Embedding generation service using the Gemini embedding API.

Converts triage session text into a 768-dimensional vector for
storage in pgvector and cosine-similarity search.
"""

from __future__ import annotations

import logging

from google import genai
from google.genai import types

from app.config import Settings
from app.models.similarity import EmbeddingInput, build_embedding_text

logger = logging.getLogger("app.services.embedding")


class EmbeddingError(Exception):
    """Raised when embedding generation fails."""


def _validate_text(text: str) -> None:
    """Ensure the input text is non-empty.

    Raises:
        ValueError: When the text is blank.
    """
    if not text.strip():
        raise ValueError("Embedding input text must not be empty")


def _extract_values(response: types.EmbedContentResponse) -> list[float]:
    """Pull the float vector from the API response.

    Raises:
        EmbeddingError: When the response contains no embeddings.
    """
    if not response.embeddings:
        raise EmbeddingError("Gemini returned no embeddings")
    return list(response.embeddings[0].values)


class EmbeddingService:
    """Generate text embeddings via the Gemini embedding API.

    Time complexity: O(1) per call (single API round-trip).
    Memory: proportional to the embedding dimension (768 floats ≈ 6 KB).
    """

    def __init__(self, settings: Settings) -> None:
        self._model = settings.embedding_model
        self._dimensions = settings.embedding_dimensions
        self._client = genai.Client(api_key=settings.google_genai_api_key)

    def embed_text(self, text: str) -> list[float]:
        """Generate an embedding vector for the given text.

        Args:
            text: The input text to embed.

        Returns:
            A list of floats representing the embedding vector.

        Raises:
            ValueError: If the input text is empty.
            EmbeddingError: If the API call fails.
        """
        _validate_text(text)
        try:
            response = self._client.models.embed_content(
                model=self._model,
                contents=text,
                config=types.EmbedContentConfig(
                    output_dimensionality=self._dimensions,
                ),
            )
        except Exception as exc:
            raise EmbeddingError(
                f"Embedding generation failed: {exc}"
            ) from exc
        return _extract_values(response)

    def embed_triage_data(self, data: EmbeddingInput) -> list[float]:
        """Generate an embedding from structured triage data.

        Serializes the EmbeddingInput to text, then embeds.

        Args:
            data: Structured clinical snapshot.

        Returns:
            Embedding vector as a list of floats.
        """
        text = build_embedding_text(data)
        logger.info("Embedding triage text (%d chars)", len(text))
        return self.embed_text(text)
