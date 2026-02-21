"""Integration test: triage orchestrator → CDS formatter pipeline.

Tests the data flow from orchestrated service results through
risk computation, CDS card generation, and response formatting.
This is a non-HTTP integration test verifying that the internal
services compose correctly.
"""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.config import Settings
from app.models.enums import AcuityLevel, CdsIndicator
from app.services.cds_formatter import format_triage_response
from app.services.triage_orchestrator import TriageOrchestrator


def _settings() -> Settings:
    return Settings(
        app_env="testing",
        supabase_jwt_secret="x" * 33,
        google_genai_api_key="test-key",
        embedding_model="test-model",
        embedding_dimensions=768,
        similarity_match_count=5,
    )


def _mock_vitals_service(hr: float = 110.0, confidence: float = 0.85):
    svc = MagicMock()
    svc.extract_vitals.return_value = MagicMock(
        heart_rate_bpm=hr,
        spo2_percent=94.0,
        respiratory_rate=20.0,
        blood_pressure=None,
        confidence=confidence,
        session_id=uuid4(),
    )
    return svc


def _mock_gemini_service():
    svc = AsyncMock()
    svc.extract_symptoms.return_value = MagicMock(
        chief_complaint="Chest pain",
        symptoms=[
            MagicMock(
                name="Chest Pain",
                severity=MagicMock(value="severe"),
                description="Sharp pain",
            ),
        ],
        follow_up_questions=["Duration?"],
        confidence=0.9,
        session_id=uuid4(),
    )
    return svc


class TestTriagePipelineIntegration:
    """Orchestrator output feeds directly into CDS formatter."""

    @pytest.mark.asyncio
    async def test_orchestrate_then_format(self):
        settings = _settings()
        vitals_svc = _mock_vitals_service()
        gemini_svc = _mock_gemini_service()

        orchestrator = TriageOrchestrator(
            vitals_service=vitals_svc,
            gemini_service=gemini_svc,
            metriport_service=None,
            embedding_service=None,
            similarity_repo=None,
            settings=settings,
        )

        result = await orchestrator.run_triage(
            session_id=uuid4(),
            video_path="/fake/video.webm",
            audio_path="/fake/audio.webm",
        )

        assert result.risk is not None
        assert result.risk.score > 0

        cds_response = format_triage_response(result)
        assert len(cds_response.cards) >= 1

        risk_card = cds_response.cards[0]
        assert "ESI" in risk_card.summary
        assert risk_card.indicator in (
            CdsIndicator.CRITICAL,
            CdsIndicator.WARNING,
            CdsIndicator.INFO,
        )
        assert risk_card.source.label == "emergAI Triage Engine"

    @pytest.mark.asyncio
    async def test_partial_failure_still_produces_cards(self):
        settings = _settings()
        vitals_svc = _mock_vitals_service()
        gemini_svc = AsyncMock()
        gemini_svc.extract_symptoms.side_effect = RuntimeError("Gemini down")

        orchestrator = TriageOrchestrator(
            vitals_service=vitals_svc,
            gemini_service=gemini_svc,
            metriport_service=None,
            embedding_service=None,
            similarity_repo=None,
            settings=settings,
        )

        result = await orchestrator.run_triage(
            session_id=uuid4(),
            video_path="/fake/video.webm",
            audio_path="/fake/audio.webm",
        )

        assert result.is_partial
        assert len(result.errors) > 0

        cds_response = format_triage_response(result)
        assert len(cds_response.cards) >= 1
        assert "incomplete" in (cds_response.cards[0].detail or "").lower()

    @pytest.mark.asyncio
    async def test_acuity_mapping_consistency(self):
        """High-risk input → high acuity → critical indicator."""
        settings = _settings()
        vitals_svc = _mock_vitals_service(hr=140.0)
        gemini_svc = _mock_gemini_service()

        orchestrator = TriageOrchestrator(
            vitals_service=vitals_svc,
            gemini_service=gemini_svc,
            metriport_service=None,
            embedding_service=None,
            similarity_repo=None,
            settings=settings,
        )

        result = await orchestrator.run_triage(
            session_id=uuid4(),
            video_path="/fake/video.webm",
            audio_path="/fake/audio.webm",
        )

        cds_response = format_triage_response(result)
        risk_card = cds_response.cards[0]

        if result.risk.acuity_level <= AcuityLevel.EMERGENT:
            assert risk_card.indicator == CdsIndicator.CRITICAL
        elif result.risk.acuity_level == AcuityLevel.URGENT:
            assert risk_card.indicator == CdsIndicator.WARNING
