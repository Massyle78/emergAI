"""Tests for the triage orchestration engine.

Pure scoring functions are tested exhaustively with concrete values.
The TriageOrchestrator class tests use mocked services to verify
parallel dispatch, graceful degradation, and result aggregation
without real network calls.
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest

from app.models.enums import AcuityLevel, SymptomSeverity
from app.models.patient_history import (
    AllergyRecord,
    ClinicalCode,
    ConditionRecord,
    MedicationRecord,
    PatientHistory,
)
from app.models.risk import ContributingFactor, RiskAssessmentCreate
from app.models.similarity import EmbeddingInput, SimilarCase
from app.models.symptoms import SymptomDetail, SymptomExtractionCreate
from app.models.triage_result import TriageResult
from app.models.vitals import VitalsCreate
from app.services.triage_orchestrator import (
    BASELINE_SCORE,
    HISTORY_WEIGHT,
    SYMPTOM_WEIGHT,
    VITALS_WEIGHT,
    TriageOrchestrator,
    build_embedding_input,
    build_reasoning,
    compute_composite_score,
    compute_history_score,
    compute_risk,
    compute_symptom_score,
    compute_vitals_score,
    score_to_acuity,
    severity_score,
)

# ------------------------------------------------------------------
# Fixtures / helpers
# ------------------------------------------------------------------
SESSION_ID = uuid4()


def _make_symptom(
    name: str = "headache",
    severity: SymptomSeverity = SymptomSeverity.MODERATE,
) -> SymptomDetail:
    return SymptomDetail(name=name, severity=severity)


def _make_extraction(
    symptoms: list[SymptomDetail] | None = None,
    confidence: float = 0.90,
    chief: str = "chest pain",
) -> SymptomExtractionCreate:
    return SymptomExtractionCreate(
        session_id=SESSION_ID,
        chief_complaint=chief,
        symptoms=symptoms or [],
        follow_up_questions=[],
        confidence=confidence,
    )


def _make_vitals(
    hr: float = 80.0,
    confidence: float = 0.95,
) -> VitalsCreate:
    return VitalsCreate(
        session_id=SESSION_ID,
        heart_rate_bpm=hr,
        confidence=confidence,
    )


def _make_history(
    conditions: int = 0,
    medications: int = 0,
    allergies: int = 0,
) -> PatientHistory:
    code = ClinicalCode(display="Test")
    return PatientHistory(
        conditions=[ConditionRecord(code=code) for _ in range(conditions)],
        medications=[MedicationRecord(code=code) for _ in range(medications)],
        allergies=[AllergyRecord(code=code) for _ in range(allergies)],
    )


def _make_similar_case() -> SimilarCase:
    return SimilarCase(
        id=uuid4(),
        patient_id=uuid4(),
        status="completed",
        similarity=0.88,
    )


def _settings(**overrides: object) -> MagicMock:
    defaults = {
        "rppg_model_name": "FacePhys.rlap",
        "min_signal_quality": 0.3,
        "google_genai_api_key": "test-key",
        "gemini_model": "gemini-2.5-pro",
        "gemini_max_retries": 1,
        "gemini_retry_wait_seconds": 1,
        "gemini_temperature": 0.2,
        "metriport_api_key": "test-key",
        "metriport_base_url": "https://api.metriport.com",
        "metriport_timeout_seconds": 10,
        "metriport_poll_interval_seconds": 0.1,
        "metriport_max_poll_attempts": 2,
        "metriport_cb_failure_threshold": 3,
        "metriport_cb_cooldown_seconds": 30,
        "embedding_model": "gemini-embedding-001",
        "embedding_dimensions": 768,
        "similarity_match_count": 5,
    }
    defaults.update(overrides)
    mock = MagicMock()
    for k, v in defaults.items():
        setattr(mock, k, v)
    return mock


# ==================================================================
# severity_score
# ==================================================================
class TestSeverityScore:
    def test_critical(self) -> None:
        assert severity_score(SymptomSeverity.CRITICAL) == 0.95

    def test_severe(self) -> None:
        assert severity_score(SymptomSeverity.SEVERE) == 0.70

    def test_moderate(self) -> None:
        assert severity_score(SymptomSeverity.MODERATE) == 0.40

    def test_mild(self) -> None:
        assert severity_score(SymptomSeverity.MILD) == 0.15


# ==================================================================
# compute_symptom_score
# ==================================================================
class TestComputeSymptomScore:
    def test_none_returns_baseline(self) -> None:
        score, factors = compute_symptom_score(None)
        assert score == BASELINE_SCORE
        assert len(factors) == 1
        assert "unavailable" in factors[0].name.lower()

    def test_empty_symptoms_low_score(self) -> None:
        ext = _make_extraction(symptoms=[])
        score, factors = compute_symptom_score(ext)
        assert score == 0.10
        assert len(factors) == 1

    def test_single_mild(self) -> None:
        ext = _make_extraction(
            symptoms=[_make_symptom(severity=SymptomSeverity.MILD)],
            confidence=1.0,
        )
        score, _ = compute_symptom_score(ext)
        expected = 0.70 * 0.15 + 0.30 * 0.15
        assert score == pytest.approx(expected, abs=0.01)

    def test_critical_high_confidence(self) -> None:
        ext = _make_extraction(
            symptoms=[_make_symptom(severity=SymptomSeverity.CRITICAL)],
            confidence=1.0,
        )
        score, factors = compute_symptom_score(ext)
        expected = 0.70 * 0.95 + 0.30 * 0.95
        assert score == pytest.approx(expected, abs=0.01)
        assert "critical" in factors[0].description.lower()

    def test_confidence_modulation(self) -> None:
        full = _make_extraction(
            symptoms=[_make_symptom(severity=SymptomSeverity.SEVERE)],
            confidence=1.0,
        )
        half = _make_extraction(
            symptoms=[_make_symptom(severity=SymptomSeverity.SEVERE)],
            confidence=0.5,
        )
        s_full, _ = compute_symptom_score(full)
        s_half, _ = compute_symptom_score(half)
        assert s_full > s_half
        assert s_half == pytest.approx(s_full * 0.5, abs=0.01)

    def test_mixed_severities(self) -> None:
        ext = _make_extraction(
            symptoms=[
                _make_symptom("pain", SymptomSeverity.SEVERE),
                _make_symptom("nausea", SymptomSeverity.MILD),
            ],
            confidence=1.0,
        )
        score, factors = compute_symptom_score(ext)
        max_sev = 0.70
        avg_sev = (0.70 + 0.15) / 2
        expected = 0.70 * max_sev + 0.30 * avg_sev
        assert score == pytest.approx(expected, abs=0.01)
        assert "2 symptom(s)" in factors[0].description


# ==================================================================
# compute_vitals_score
# ==================================================================
class TestComputeVitalsScore:
    def test_none_returns_none(self) -> None:
        score, factors = compute_vitals_score(None)
        assert score is None
        assert factors == []

    def test_normal_hr(self) -> None:
        v = _make_vitals(hr=75.0, confidence=1.0)
        score, factors = compute_vitals_score(v)
        assert score == pytest.approx(0.10, abs=0.01)
        assert "normal" in factors[0].description.lower()

    def test_mild_tachycardia(self) -> None:
        v = _make_vitals(hr=115.0, confidence=1.0)
        score, factors = compute_vitals_score(v)
        assert score == pytest.approx(0.50, abs=0.01)
        assert "outside normal" in factors[0].description.lower()

    def test_critical_tachycardia(self) -> None:
        v = _make_vitals(hr=140.0, confidence=1.0)
        score, factors = compute_vitals_score(v)
        assert score == pytest.approx(0.85, abs=0.01)
        assert "critically" in factors[0].description.lower()

    def test_critical_bradycardia(self) -> None:
        v = _make_vitals(hr=45.0, confidence=1.0)
        score, factors = compute_vitals_score(v)
        assert score == pytest.approx(0.85, abs=0.01)

    def test_confidence_modulates(self) -> None:
        v = _make_vitals(hr=140.0, confidence=0.5)
        score, _ = compute_vitals_score(v)
        assert score == pytest.approx(0.85 * 0.5, abs=0.01)


# ==================================================================
# compute_history_score
# ==================================================================
class TestComputeHistoryScore:
    def test_none_returns_none(self) -> None:
        score, factors = compute_history_score(None)
        assert score is None
        assert factors == []

    def test_empty_history(self) -> None:
        h = _make_history()
        score, factors = compute_history_score(h)
        assert score is None
        assert factors == []

    def test_conditions_only(self) -> None:
        h = _make_history(conditions=3)
        score, factors = compute_history_score(h)
        assert score == pytest.approx(0.30, abs=0.01)
        assert len(factors) == 1
        assert "3 active condition" in factors[0].description

    def test_all_types(self) -> None:
        h = _make_history(conditions=2, medications=2, allergies=1)
        score, factors = compute_history_score(h)
        expected = 0.20 + 0.10 + 0.08
        assert score == pytest.approx(expected, abs=0.01)
        assert len(factors) == 3

    def test_caps_at_one(self) -> None:
        h = _make_history(conditions=10, medications=10, allergies=10)
        score, _ = compute_history_score(h)
        assert score <= 1.0


# ==================================================================
# compute_composite_score
# ==================================================================
class TestComputeCompositeScore:
    def test_all_components(self) -> None:
        result = compute_composite_score(0.60, 0.40, 0.20)
        expected = (0.60 * SYMPTOM_WEIGHT + 0.40 * VITALS_WEIGHT + 0.20 * HISTORY_WEIGHT)
        assert result == pytest.approx(expected, abs=0.001)

    def test_missing_vitals(self) -> None:
        result = compute_composite_score(0.60, None, 0.20)
        total = SYMPTOM_WEIGHT + HISTORY_WEIGHT
        expected = (0.60 * SYMPTOM_WEIGHT + 0.20 * HISTORY_WEIGHT) / total
        assert result == pytest.approx(expected, abs=0.001)

    def test_symptoms_only(self) -> None:
        result = compute_composite_score(0.80, None, None)
        assert result == pytest.approx(0.80, abs=0.001)

    def test_all_zero(self) -> None:
        result = compute_composite_score(0.0, 0.0, 0.0)
        assert result == pytest.approx(0.0, abs=0.001)


# ==================================================================
# score_to_acuity
# ==================================================================
class TestScoreToAcuity:
    def test_esi_1_resuscitation(self) -> None:
        assert score_to_acuity(0.90) == AcuityLevel.RESUSCITATION

    def test_esi_2_emergent(self) -> None:
        assert score_to_acuity(0.70) == AcuityLevel.EMERGENT

    def test_esi_3_urgent(self) -> None:
        assert score_to_acuity(0.50) == AcuityLevel.URGENT

    def test_esi_4_less_urgent(self) -> None:
        assert score_to_acuity(0.30) == AcuityLevel.LESS_URGENT

    def test_esi_5_non_urgent(self) -> None:
        assert score_to_acuity(0.10) == AcuityLevel.NON_URGENT

    def test_boundary_085(self) -> None:
        assert score_to_acuity(0.85) == AcuityLevel.RESUSCITATION

    def test_boundary_065(self) -> None:
        assert score_to_acuity(0.65) == AcuityLevel.EMERGENT


# ==================================================================
# build_embedding_input
# ==================================================================
class TestBuildEmbeddingInput:
    def test_full_data(self) -> None:
        vitals = _make_vitals(hr=90.0)
        symptoms = _make_extraction(
            symptoms=[_make_symptom("cough", SymptomSeverity.MODERATE)],
        )
        history = _make_history(conditions=1, medications=1, allergies=1)

        result = build_embedding_input(vitals, symptoms, history)

        assert isinstance(result, EmbeddingInput)
        assert result.chief_complaint == "chest pain"
        assert result.symptoms == ["cough"]
        assert result.severities == ["moderate"]
        assert "90" in (result.vitals_summary or "")
        assert len(result.conditions) == 1
        assert len(result.medications) == 1
        assert len(result.allergies) == 1

    def test_no_vitals(self) -> None:
        symptoms = _make_extraction(symptoms=[_make_symptom()])
        result = build_embedding_input(None, symptoms, None)
        assert result.vitals_summary is None

    def test_no_symptoms(self) -> None:
        result = build_embedding_input(_make_vitals(), None, None)
        assert result.chief_complaint == "Unknown"
        assert result.symptoms == []

    def test_no_data(self) -> None:
        result = build_embedding_input(None, None, None)
        assert result.chief_complaint == "Unknown"
        assert result.vitals_summary is None
        assert result.conditions == []


# ==================================================================
# build_reasoning
# ==================================================================
class TestBuildReasoning:
    def test_full_reasoning(self) -> None:
        factors = [
            ContributingFactor(name="Symptom severity", weight=0.6, description="high"),
            ContributingFactor(name="Heart rate", weight=0.3, description="elevated"),
        ]
        symptoms = _make_extraction(
            symptoms=[_make_symptom("chest pain", SymptomSeverity.SEVERE)],
        )
        vitals = _make_vitals(hr=120.0)
        history = _make_history(conditions=2, medications=1, allergies=0)

        text = build_reasoning(
            0.72, AcuityLevel.EMERGENT, factors,
            symptoms, vitals, history, 3,
        )

        assert "0.72" in text
        assert "ESI 2" in text
        assert "chest pain" in text
        assert "120" in text
        assert "2 condition(s)" in text
        assert "3 similar" in text
        assert "Symptom severity" in text

    def test_minimal_reasoning(self) -> None:
        text = build_reasoning(
            0.50, AcuityLevel.URGENT, [],
            None, None, None, 0,
        )
        assert "0.50" in text
        assert "not available" in text.lower()


# ==================================================================
# compute_risk (integration of pure functions)
# ==================================================================
class TestComputeRisk:
    def test_full_data(self) -> None:
        symptoms = _make_extraction(
            symptoms=[_make_symptom("pain", SymptomSeverity.SEVERE)],
            confidence=0.9,
        )
        vitals = _make_vitals(hr=120.0, confidence=0.9)
        history = _make_history(conditions=2, medications=1)
        cases = [_make_similar_case()]

        risk = compute_risk(SESSION_ID, vitals, symptoms, history, cases)

        assert isinstance(risk, RiskAssessmentCreate)
        assert risk.session_id == SESSION_ID
        assert 0.0 <= risk.score <= 1.0
        assert isinstance(risk.acuity_level, AcuityLevel)
        assert len(risk.reasoning) > 0
        assert len(risk.contributing_factors) >= 1
        assert risk.similar_cases_count == 1

    def test_no_data(self) -> None:
        risk = compute_risk(SESSION_ID, None, None, None, [])
        assert risk.score == pytest.approx(BASELINE_SCORE, abs=0.01)
        assert risk.similar_cases_count == 0

    def test_symptoms_only(self) -> None:
        symptoms = _make_extraction(
            symptoms=[_make_symptom("cough", SymptomSeverity.MILD)],
            confidence=1.0,
        )
        risk = compute_risk(SESSION_ID, None, symptoms, None, [])
        assert risk.score < 0.25
        assert risk.acuity_level in (AcuityLevel.LESS_URGENT, AcuityLevel.NON_URGENT)


# ==================================================================
# TriageResult model
# ==================================================================
class TestTriageResultModel:
    def test_creation(self) -> None:
        risk = compute_risk(SESSION_ID, None, None, None, [])
        result = TriageResult(session_id=SESSION_ID, risk=risk)

        assert result.session_id == SESSION_ID
        assert result.vitals is None
        assert result.symptoms is None
        assert result.history is None
        assert result.similar_cases == []
        assert result.errors == []

    def test_is_partial_with_errors(self) -> None:
        risk = compute_risk(SESSION_ID, None, None, None, [])
        result = TriageResult(
            session_id=SESSION_ID,
            risk=risk,
            errors=["vitals: extraction failed"],
        )
        assert result.is_partial is True

    def test_not_partial_without_errors(self) -> None:
        risk = compute_risk(SESSION_ID, None, None, None, [])
        result = TriageResult(session_id=SESSION_ID, risk=risk)
        assert result.is_partial is False


# ==================================================================
# TriageOrchestrator
# ==================================================================
def _mock_orchestrator(
    vitals_result: object = None,
    symptoms_result: object = None,
    history_result: object = None,
    embed_result: list[float] | None = None,
    similar_result: list[SimilarCase] | None = None,
) -> TriageOrchestrator:
    """Build an orchestrator with fully mocked services."""
    vitals_svc = MagicMock()
    vitals_svc.extract_vitals = MagicMock(return_value=vitals_result)

    gemini_svc = MagicMock()
    gemini_svc.extract_symptoms = AsyncMock(return_value=symptoms_result)

    metriport_svc = MagicMock()
    metriport_svc.fetch_patient_history = AsyncMock(return_value=history_result)

    embedding_svc = MagicMock()
    embedding_svc.embed_triage_data = MagicMock(
        return_value=embed_result or [0.1] * 768
    )

    similarity_repo = MagicMock()
    similarity_repo.store_embedding = AsyncMock()
    similarity_repo.find_similar = AsyncMock(
        return_value=similar_result or []
    )

    settings = _settings()
    return TriageOrchestrator(
        vitals_service=vitals_svc,
        gemini_service=gemini_svc,
        metriport_service=metriport_svc,
        embedding_service=embedding_svc,
        similarity_repo=similarity_repo,
        settings=settings,
    )


@pytest.mark.asyncio
class TestTriageOrchestratorRunTriage:
    async def test_full_success(self) -> None:
        vitals = _make_vitals()
        symptoms = _make_extraction(
            symptoms=[_make_symptom("headache", SymptomSeverity.MODERATE)],
        )
        history = _make_history(conditions=1)
        similar = [_make_similar_case()]

        orch = _mock_orchestrator(
            vitals_result=vitals,
            symptoms_result=symptoms,
            history_result=history,
            similar_result=similar,
        )

        from pathlib import Path
        result = await orch.run_triage(
            session_id=SESSION_ID,
            video_path=Path("/fake/video.mp4"),
            audio_path=Path("/fake/audio.wav"),
            metriport_patient_id="patient-123",
        )

        assert isinstance(result, TriageResult)
        assert result.vitals is vitals
        assert result.symptoms is symptoms
        assert result.history is history
        assert len(result.similar_cases) == 1
        assert result.errors == []
        assert result.risk.session_id == SESSION_ID

    async def test_vitals_failure_graceful(self) -> None:
        symptoms = _make_extraction(
            symptoms=[_make_symptom()],
        )
        orch = _mock_orchestrator(symptoms_result=symptoms)
        orch._vitals.extract_vitals = MagicMock(
            side_effect=RuntimeError("No face detected")
        )

        from pathlib import Path
        result = await orch.run_triage(
            session_id=SESSION_ID,
            video_path=Path("/fake/video.mp4"),
        )

        assert result.vitals is None
        assert result.symptoms is symptoms
        assert len(result.errors) == 1
        assert "vitals" in result.errors[0]

    async def test_all_services_fail(self) -> None:
        orch = _mock_orchestrator()
        orch._vitals.extract_vitals = MagicMock(
            side_effect=RuntimeError("vitals err")
        )
        orch._gemini.extract_symptoms = AsyncMock(
            side_effect=RuntimeError("gemini err")
        )
        orch._metriport.fetch_patient_history = AsyncMock(
            side_effect=RuntimeError("metriport err")
        )

        from pathlib import Path
        result = await orch.run_triage(
            session_id=SESSION_ID,
            video_path=Path("/fake/video.mp4"),
            metriport_patient_id="patient-123",
        )

        assert result.vitals is None
        assert result.symptoms is None
        assert result.history is None
        assert len(result.errors) == 3
        assert result.risk.score == pytest.approx(BASELINE_SCORE, abs=0.01)

    async def test_no_optional_inputs(self) -> None:
        """When no video or metriport ID is provided, only Gemini runs."""
        symptoms = _make_extraction(symptoms=[_make_symptom()])
        orch = _mock_orchestrator(symptoms_result=symptoms)

        result = await orch.run_triage(session_id=SESSION_ID)

        assert result.vitals is None
        assert result.symptoms is symptoms
        assert result.history is None
        assert result.errors == []

    async def test_embedding_failure_returns_empty_similar(self) -> None:
        symptoms = _make_extraction(symptoms=[_make_symptom()])
        orch = _mock_orchestrator(symptoms_result=symptoms)
        orch._embedding.embed_triage_data = MagicMock(
            side_effect=RuntimeError("API down")
        )

        result = await orch.run_triage(session_id=SESSION_ID)

        assert result.similar_cases == []
        assert result.risk is not None
