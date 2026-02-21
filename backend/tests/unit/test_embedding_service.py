"""Unit tests for embedding service and similarity models.

Pure-logic helpers tested with real data; API tests guarded
by GOOGLE_GENAI_API_KEY availability.
"""

import os
from uuid import uuid4

import pytest
from google import genai

from app.config import Settings
from app.models.similarity import (
    EmbeddingInput,
    SimilarCase,
    build_embedding_text,
)
from app.services.embedding_service import (
    EmbeddingError,
    EmbeddingService,
    _extract_values,
    _validate_text,
)

HAS_API_KEY = bool(os.environ.get("GOOGLE_GENAI_API_KEY"))
skip_no_key = pytest.mark.skipif(
    not HAS_API_KEY, reason="GOOGLE_GENAI_API_KEY not set"
)


def _settings(**overrides: object) -> Settings:
    defaults: dict[str, object] = {
        "google_genai_api_key": os.environ.get("GOOGLE_GENAI_API_KEY", "test-key"),
        "embedding_model": "gemini-embedding-001",
        "embedding_dimensions": 768,
    }
    defaults.update(overrides)
    return Settings(**defaults)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# build_embedding_text
# ---------------------------------------------------------------------------
class TestBuildEmbeddingText:
    def test_chief_complaint_only(self) -> None:
        data = EmbeddingInput(chief_complaint="Chest pain")
        text = build_embedding_text(data)
        assert text == "Chief complaint: Chest pain"

    def test_full_data(self) -> None:
        data = EmbeddingInput(
            chief_complaint="Chest pain",
            symptoms=["chest pain", "dyspnea"],
            severities=["severe", "moderate"],
            vitals_summary="HR=110, SpO2=94%",
            conditions=["Hypertension", "Diabetes"],
            medications=["Metformin", "Lisinopril"],
            allergies=["Penicillin"],
        )
        text = build_embedding_text(data)
        assert "Chief complaint: Chest pain" in text
        assert "chest pain (severe)" in text
        assert "dyspnea (moderate)" in text
        assert "HR=110" in text
        assert "Hypertension" in text
        assert "Metformin" in text
        assert "Penicillin" in text

    def test_symptoms_without_severities(self) -> None:
        data = EmbeddingInput(
            chief_complaint="Headache",
            symptoms=["headache", "nausea"],
            severities=["mild"],
        )
        text = build_embedding_text(data)
        assert "headache (mild)" in text
        assert "nausea" in text
        assert "nausea ()" not in text

    def test_no_optional_fields(self) -> None:
        data = EmbeddingInput(chief_complaint="Fever")
        text = build_embedding_text(data)
        assert "Symptoms" not in text
        assert "Vitals" not in text
        assert "History" not in text
        assert "Medications" not in text
        assert "Allergies" not in text

    def test_deterministic_output(self) -> None:
        data = EmbeddingInput(
            chief_complaint="Abdominal pain",
            symptoms=["cramps"],
            severities=["moderate"],
        )
        assert build_embedding_text(data) == build_embedding_text(data)


# ---------------------------------------------------------------------------
# EmbeddingInput model
# ---------------------------------------------------------------------------
class TestEmbeddingInput:
    def test_defaults(self) -> None:
        data = EmbeddingInput(chief_complaint="test")
        assert data.symptoms == []
        assert data.severities == []
        assert data.vitals_summary is None
        assert data.conditions == []
        assert data.medications == []
        assert data.allergies == []


# ---------------------------------------------------------------------------
# SimilarCase model
# ---------------------------------------------------------------------------
class TestSimilarCase:
    def test_valid_case(self) -> None:
        case = SimilarCase(
            id=uuid4(),
            patient_id=uuid4(),
            status="completed",
            similarity=0.92,
        )
        assert case.similarity == 0.92

    def test_similarity_bounds(self) -> None:
        SimilarCase(id=uuid4(), patient_id=uuid4(), status="x", similarity=0.0)
        SimilarCase(id=uuid4(), patient_id=uuid4(), status="x", similarity=1.0)

    def test_similarity_out_of_range(self) -> None:
        with pytest.raises(Exception):
            SimilarCase(
                id=uuid4(), patient_id=uuid4(), status="x", similarity=1.5
            )


# ---------------------------------------------------------------------------
# _validate_text
# ---------------------------------------------------------------------------
class TestValidateText:
    def test_non_empty_passes(self) -> None:
        _validate_text("hello world")

    def test_empty_string_raises(self) -> None:
        with pytest.raises(ValueError, match="must not be empty"):
            _validate_text("")

    def test_whitespace_only_raises(self) -> None:
        with pytest.raises(ValueError, match="must not be empty"):
            _validate_text("   \n\t  ")


# ---------------------------------------------------------------------------
# _extract_values
# ---------------------------------------------------------------------------
class TestExtractValues:
    def test_no_embeddings_raises(self) -> None:
        class FakeResponse:
            embeddings = None
        with pytest.raises(EmbeddingError, match="no embeddings"):
            _extract_values(FakeResponse())  # type: ignore[arg-type]

    def test_empty_list_raises(self) -> None:
        class FakeResponse:
            embeddings = []
        with pytest.raises(EmbeddingError, match="no embeddings"):
            _extract_values(FakeResponse())  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# EmbeddingService construction
# ---------------------------------------------------------------------------
class TestEmbeddingServiceInit:
    def test_creates_genai_client(self) -> None:
        svc = EmbeddingService(_settings())
        assert isinstance(svc._client, genai.Client)
        assert svc._model == "gemini-embedding-001"
        assert svc._dimensions == 768


# ---------------------------------------------------------------------------
# EmbeddingService.embed_text – validation
# ---------------------------------------------------------------------------
class TestEmbedTextValidation:
    def test_empty_text_raises_value_error(self) -> None:
        svc = EmbeddingService(_settings())
        with pytest.raises(ValueError, match="must not be empty"):
            svc.embed_text("")


# ---------------------------------------------------------------------------
# Integration: real Gemini embedding API
# ---------------------------------------------------------------------------
class TestEmbeddingServiceIntegration:
    @skip_no_key
    def test_embed_text_returns_vector(self) -> None:
        svc = EmbeddingService(_settings())
        vector = svc.embed_text("Patient presents with chest pain and dyspnea")
        assert isinstance(vector, list)
        assert len(vector) == 768
        assert all(isinstance(v, float) for v in vector)

    @skip_no_key
    def test_embed_triage_data(self) -> None:
        svc = EmbeddingService(_settings())
        data = EmbeddingInput(
            chief_complaint="Severe headache",
            symptoms=["headache", "photophobia"],
            severities=["severe", "moderate"],
        )
        vector = svc.embed_triage_data(data)
        assert len(vector) == 768

    @skip_no_key
    def test_similar_inputs_closer_than_different(self) -> None:
        """Semantic similarity: similar clinical texts should have
        higher cosine similarity than unrelated ones."""
        import numpy as np

        svc = EmbeddingService(_settings())
        v1 = np.array(svc.embed_text("chest pain radiating to left arm"))
        v2 = np.array(svc.embed_text("cardiac pain spreading to left shoulder"))
        v3 = np.array(svc.embed_text("broken ankle from a fall"))

        sim_similar = float(np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2)))
        sim_different = float(np.dot(v1, v3) / (np.linalg.norm(v1) * np.linalg.norm(v3)))
        assert sim_similar > sim_different


# ---------------------------------------------------------------------------
# Error hierarchy
# ---------------------------------------------------------------------------
class TestErrorHierarchy:
    def test_base_is_exception(self) -> None:
        assert issubclass(EmbeddingError, Exception)
