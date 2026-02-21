"""Tests for the CDS Hooks output formatter.

All formatter functions are pure, so tests verify deterministic
output without mocks or I/O.
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from app.models.cds_hooks import CdsCard, CdsHookResponse
from app.models.enums import AcuityLevel, CdsIndicator, SymptomSeverity
from app.models.patient_history import (
    ClinicalCode,
    ConditionRecord,
    PatientHistory,
)
from app.models.risk import ContributingFactor, RiskAssessmentCreate
from app.models.similarity import SimilarCase
from app.models.symptoms import SymptomDetail, SymptomExtractionCreate
from app.models.triage_result import TriageResult
from app.models.vitals import VitalsCreate
from app.services.cds_formatter import (
    SOURCE,
    _truncate,
    acuity_to_indicator,
    build_risk_card,
    build_suggestions,
    build_symptom_card,
    build_vitals_card,
    format_triage_response,
)

SESSION_ID = uuid4()


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------
def _risk(
    score: float = 0.50,
    acuity: AcuityLevel = AcuityLevel.URGENT,
    reasoning: str = "Test reasoning",
    factors: list[ContributingFactor] | None = None,
    similar: int = 0,
) -> RiskAssessmentCreate:
    return RiskAssessmentCreate(
        session_id=SESSION_ID,
        score=score,
        acuity_level=acuity,
        reasoning=reasoning,
        contributing_factors=factors or [],
        similar_cases_count=similar,
    )


def _result(
    risk: RiskAssessmentCreate | None = None,
    vitals: VitalsCreate | None = None,
    symptoms: SymptomExtractionCreate | None = None,
    errors: list[str] | None = None,
    similar_cases: list[SimilarCase] | None = None,
) -> TriageResult:
    return TriageResult(
        session_id=SESSION_ID,
        risk=risk or _risk(),
        vitals=vitals,
        symptoms=symptoms,
        errors=errors or [],
        similar_cases=similar_cases or [],
    )


def _vitals(hr: float = 80.0, confidence: float = 0.95) -> VitalsCreate:
    return VitalsCreate(
        session_id=SESSION_ID,
        heart_rate_bpm=hr,
        confidence=confidence,
    )


def _symptoms(
    chief: str = "chest pain",
    symptom_list: list[SymptomDetail] | None = None,
    confidence: float = 0.9,
) -> SymptomExtractionCreate:
    return SymptomExtractionCreate(
        session_id=SESSION_ID,
        chief_complaint=chief,
        symptoms=symptom_list or [],
        follow_up_questions=[],
        confidence=confidence,
    )


# ==================================================================
# acuity_to_indicator
# ==================================================================
class TestAcuityToIndicator:
    def test_resuscitation_is_critical(self) -> None:
        assert acuity_to_indicator(AcuityLevel.RESUSCITATION) == CdsIndicator.CRITICAL

    def test_emergent_is_critical(self) -> None:
        assert acuity_to_indicator(AcuityLevel.EMERGENT) == CdsIndicator.CRITICAL

    def test_urgent_is_warning(self) -> None:
        assert acuity_to_indicator(AcuityLevel.URGENT) == CdsIndicator.WARNING

    def test_less_urgent_is_info(self) -> None:
        assert acuity_to_indicator(AcuityLevel.LESS_URGENT) == CdsIndicator.INFO

    def test_non_urgent_is_info(self) -> None:
        assert acuity_to_indicator(AcuityLevel.NON_URGENT) == CdsIndicator.INFO


# ==================================================================
# build_suggestions
# ==================================================================
class TestBuildSuggestions:
    def test_resuscitation_has_recommended(self) -> None:
        sug = build_suggestions(AcuityLevel.RESUSCITATION)
        assert len(sug) == 2
        assert sug[0].is_recommended is True
        assert "resuscitation" in sug[0].label.lower()

    def test_emergent(self) -> None:
        sug = build_suggestions(AcuityLevel.EMERGENT)
        assert len(sug) == 2
        assert sug[0].is_recommended is True

    def test_urgent(self) -> None:
        sug = build_suggestions(AcuityLevel.URGENT)
        assert len(sug) == 2
        assert "triage" in sug[0].label.lower()

    def test_less_urgent(self) -> None:
        sug = build_suggestions(AcuityLevel.LESS_URGENT)
        assert len(sug) == 2
        assert sug[0].is_recommended is False

    def test_non_urgent(self) -> None:
        sug = build_suggestions(AcuityLevel.NON_URGENT)
        assert len(sug) == 2


# ==================================================================
# build_risk_card
# ==================================================================
class TestBuildRiskCard:
    def test_basic_card(self) -> None:
        r = _result()
        card = build_risk_card(r)

        assert isinstance(card, CdsCard)
        assert "ESI 3" in card.summary
        assert "Urgent" in card.summary
        assert "0.50" in card.summary
        assert card.indicator == CdsIndicator.WARNING
        assert card.source == SOURCE
        assert card.detail is not None
        assert "Test reasoning" in card.detail

    def test_critical_acuity(self) -> None:
        r = _result(risk=_risk(score=0.92, acuity=AcuityLevel.RESUSCITATION))
        card = build_risk_card(r)
        assert card.indicator == CdsIndicator.CRITICAL
        assert "ESI 1" in card.summary
        assert len(card.suggestions) == 2

    def test_includes_contributing_factors(self) -> None:
        factors = [
            ContributingFactor(name="HR", weight=0.5, description="elevated"),
        ]
        r = _result(risk=_risk(factors=factors))
        card = build_risk_card(r)
        assert "HR" in card.detail
        assert "elevated" in card.detail

    def test_includes_similar_cases(self) -> None:
        r = _result(risk=_risk(similar=3))
        card = build_risk_card(r)
        assert "3 historical case(s)" in card.detail

    def test_partial_result_note(self) -> None:
        r = _result(errors=["vitals: failed"])
        card = build_risk_card(r)
        assert "incomplete" in card.detail.lower()

    def test_no_partial_note_on_clean_result(self) -> None:
        r = _result()
        card = build_risk_card(r)
        assert "incomplete" not in card.detail.lower()


# ==================================================================
# build_vitals_card
# ==================================================================
class TestBuildVitalsCard:
    def test_normal_hr_returns_none(self) -> None:
        assert build_vitals_card(_vitals(hr=75.0)) is None

    def test_boundary_low_returns_none(self) -> None:
        assert build_vitals_card(_vitals(hr=60.0)) is None

    def test_boundary_high_returns_none(self) -> None:
        assert build_vitals_card(_vitals(hr=100.0)) is None

    def test_tachycardia(self) -> None:
        card = build_vitals_card(_vitals(hr=120.0))
        assert card is not None
        assert "Tachycardia" in card.summary
        assert "120" in card.summary
        assert card.indicator == CdsIndicator.WARNING

    def test_bradycardia(self) -> None:
        card = build_vitals_card(_vitals(hr=48.0))
        assert card is not None
        assert "Bradycardia" in card.summary
        assert "48" in card.summary

    def test_detail_includes_confidence(self) -> None:
        card = build_vitals_card(_vitals(hr=130.0, confidence=0.85))
        assert card is not None
        assert "85%" in card.detail


# ==================================================================
# build_symptom_card
# ==================================================================
class TestBuildSymptomCard:
    def test_no_symptoms_returns_none(self) -> None:
        assert build_symptom_card(_symptoms()) is None

    def test_with_symptoms(self) -> None:
        symptoms = _symptoms(
            chief="headache",
            symptom_list=[
                SymptomDetail(name="headache", severity=SymptomSeverity.MODERATE),
            ],
        )
        card = build_symptom_card(symptoms)
        assert card is not None
        assert "headache" in card.summary
        assert card.indicator == CdsIndicator.INFO
        assert "1" in card.detail

    def test_multiple_symptoms(self) -> None:
        symptoms = _symptoms(
            symptom_list=[
                SymptomDetail(
                    name="chest pain",
                    severity=SymptomSeverity.SEVERE,
                    description="sharp, radiating",
                ),
                SymptomDetail(name="dyspnea", severity=SymptomSeverity.MODERATE),
            ],
        )
        card = build_symptom_card(symptoms)
        assert card is not None
        assert "chest pain" in card.detail
        assert "sharp, radiating" in card.detail
        assert "dyspnea" in card.detail

    def test_includes_follow_up_questions(self) -> None:
        symptoms = SymptomExtractionCreate(
            session_id=SESSION_ID,
            chief_complaint="abdominal pain",
            symptoms=[SymptomDetail(name="pain", severity=SymptomSeverity.MODERATE)],
            follow_up_questions=["When did the pain start?"],
            confidence=0.8,
        )
        card = build_symptom_card(symptoms)
        assert card is not None
        assert "When did the pain start?" in card.detail

    def test_confidence_in_detail(self) -> None:
        symptoms = _symptoms(
            symptom_list=[
                SymptomDetail(name="cough", severity=SymptomSeverity.MILD),
            ],
            confidence=0.75,
        )
        card = build_symptom_card(symptoms)
        assert card is not None
        assert "75%" in card.detail

    def test_long_chief_complaint_truncated(self) -> None:
        long_chief = "A" * 200
        symptoms = _symptoms(
            chief=long_chief,
            symptom_list=[
                SymptomDetail(name="pain", severity=SymptomSeverity.MILD),
            ],
        )
        card = build_symptom_card(symptoms)
        assert card is not None
        assert len(card.summary) <= 140


# ==================================================================
# format_triage_response
# ==================================================================
class TestFormatTriageResponse:
    def test_minimal_result_one_card(self) -> None:
        r = _result()
        resp = format_triage_response(r)
        assert isinstance(resp, CdsHookResponse)
        assert len(resp.cards) == 1

    def test_with_abnormal_vitals_two_cards(self) -> None:
        r = _result(vitals=_vitals(hr=140.0))
        resp = format_triage_response(r)
        assert len(resp.cards) == 2

    def test_with_normal_vitals_one_card(self) -> None:
        r = _result(vitals=_vitals(hr=75.0))
        resp = format_triage_response(r)
        assert len(resp.cards) == 1

    def test_with_symptoms_two_cards(self) -> None:
        symptoms = _symptoms(
            symptom_list=[
                SymptomDetail(name="fever", severity=SymptomSeverity.MODERATE),
            ],
        )
        r = _result(symptoms=symptoms)
        resp = format_triage_response(r)
        assert len(resp.cards) == 2

    def test_full_result_three_cards(self) -> None:
        symptoms = _symptoms(
            symptom_list=[
                SymptomDetail(name="fever", severity=SymptomSeverity.MODERATE),
            ],
        )
        r = _result(vitals=_vitals(hr=125.0), symptoms=symptoms)
        resp = format_triage_response(r)
        assert len(resp.cards) == 3

    def test_card_order(self) -> None:
        symptoms = _symptoms(
            symptom_list=[
                SymptomDetail(name="pain", severity=SymptomSeverity.SEVERE),
            ],
        )
        r = _result(vitals=_vitals(hr=135.0), symptoms=symptoms)
        resp = format_triage_response(r)
        assert "ESI" in resp.cards[0].summary
        assert "Tachycardia" in resp.cards[1].summary
        assert "pain" in resp.cards[2].summary.lower()


# ==================================================================
# _truncate helper
# ==================================================================
class TestTruncate:
    def test_short_text_unchanged(self) -> None:
        assert _truncate("hello", 10) == "hello"

    def test_exact_length(self) -> None:
        assert _truncate("hello", 5) == "hello"

    def test_over_limit(self) -> None:
        assert _truncate("hello world", 8) == "hello..."

    def test_very_long(self) -> None:
        result = _truncate("A" * 200, 50)
        assert len(result) == 50
        assert result.endswith("...")
