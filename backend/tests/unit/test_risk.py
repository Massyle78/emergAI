"""Tests for Risk assessment domain models."""

from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.models.enums import AcuityLevel
from app.models.risk import ContributingFactor, RiskAssessmentCreate


class TestContributingFactor:
    def test_valid(self):
        f = ContributingFactor(
            name="Elevated heart rate",
            weight=0.7,
            description="HR above 120 bpm at rest suggests cardiovascular stress",
        )
        assert f.weight == 0.7

    def test_rejects_weight_above_one(self):
        with pytest.raises(ValidationError):
            ContributingFactor(
                name="Test",
                weight=1.1,
                description="Desc",
            )

    def test_rejects_negative_weight(self):
        with pytest.raises(ValidationError):
            ContributingFactor(
                name="Test",
                weight=-0.1,
                description="Desc",
            )

    def test_rejects_empty_name(self):
        with pytest.raises(ValidationError):
            ContributingFactor(name="", weight=0.5, description="Desc")

    def test_rejects_empty_description(self):
        with pytest.raises(ValidationError):
            ContributingFactor(name="Test", weight=0.5, description="")


class TestRiskAssessmentCreate:
    def test_valid_minimal(self):
        r = RiskAssessmentCreate(
            session_id=uuid4(),
            score=0.85,
            acuity_level=AcuityLevel.EMERGENT,
            reasoning="High vitals combined with chest pain history",
        )
        assert r.score == 0.85
        assert r.contributing_factors == []
        assert r.similar_cases_count == 0

    def test_valid_with_factors(self):
        factor = ContributingFactor(
            name="Chest pain",
            weight=0.9,
            description="Acute onset chest pain with radiation",
        )
        r = RiskAssessmentCreate(
            session_id=uuid4(),
            score=0.95,
            acuity_level=AcuityLevel.RESUSCITATION,
            reasoning="Critical presentation",
            contributing_factors=[factor],
            similar_cases_count=3,
        )
        assert len(r.contributing_factors) == 1
        assert r.similar_cases_count == 3

    def test_rejects_score_below_zero(self):
        with pytest.raises(ValidationError):
            RiskAssessmentCreate(
                session_id=uuid4(),
                score=-0.1,
                acuity_level=AcuityLevel.URGENT,
                reasoning="Test",
            )

    def test_rejects_score_above_one(self):
        with pytest.raises(ValidationError):
            RiskAssessmentCreate(
                session_id=uuid4(),
                score=1.1,
                acuity_level=AcuityLevel.URGENT,
                reasoning="Test",
            )

    def test_rejects_empty_reasoning(self):
        with pytest.raises(ValidationError):
            RiskAssessmentCreate(
                session_id=uuid4(),
                score=0.5,
                acuity_level=AcuityLevel.URGENT,
                reasoning="",
            )

    def test_rejects_negative_similar_cases(self):
        with pytest.raises(ValidationError):
            RiskAssessmentCreate(
                session_id=uuid4(),
                score=0.5,
                acuity_level=AcuityLevel.URGENT,
                reasoning="Test",
                similar_cases_count=-1,
            )

    def test_boundary_score_zero(self):
        r = RiskAssessmentCreate(
            session_id=uuid4(),
            score=0.0,
            acuity_level=AcuityLevel.NON_URGENT,
            reasoning="Low risk presentation",
        )
        assert r.score == 0.0

    def test_boundary_score_one(self):
        r = RiskAssessmentCreate(
            session_id=uuid4(),
            score=1.0,
            acuity_level=AcuityLevel.RESUSCITATION,
            reasoning="Maximum risk",
        )
        assert r.score == 1.0
