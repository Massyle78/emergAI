"""Tests for Symptom extraction domain models."""

from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.models.enums import SymptomSeverity
from app.models.symptoms import (
    SymptomDetail,
    SymptomExtractionCreate,
)


class TestSymptomDetail:
    def test_valid_minimal(self):
        s = SymptomDetail(name="Chest pain", severity=SymptomSeverity.SEVERE)
        assert s.name == "Chest pain"
        assert s.description is None
        assert s.body_region is None

    def test_valid_full(self):
        s = SymptomDetail(
            name="Headache",
            severity=SymptomSeverity.MODERATE,
            description="Throbbing pain in temporal region",
            body_region="head",
            onset_description="Started 2 hours ago",
        )
        assert s.body_region == "head"

    def test_rejects_empty_name(self):
        with pytest.raises(ValidationError):
            SymptomDetail(name="", severity=SymptomSeverity.MILD)

    def test_rejects_name_exceeding_max(self):
        with pytest.raises(ValidationError):
            SymptomDetail(name="A" * 201, severity=SymptomSeverity.MILD)


class TestSymptomExtractionCreate:
    def test_valid_minimal(self):
        e = SymptomExtractionCreate(
            session_id=uuid4(),
            chief_complaint="Chest pain radiating to left arm",
            confidence=0.85,
        )
        assert e.symptoms == []
        assert e.follow_up_questions == []

    def test_valid_with_symptoms(self):
        symptom = SymptomDetail(
            name="Chest pain",
            severity=SymptomSeverity.SEVERE,
        )
        e = SymptomExtractionCreate(
            session_id=uuid4(),
            chief_complaint="Chest pain",
            symptoms=[symptom],
            follow_up_questions=["When did the pain start?"],
            confidence=0.9,
        )
        assert len(e.symptoms) == 1
        assert len(e.follow_up_questions) == 1

    def test_rejects_empty_chief_complaint(self):
        with pytest.raises(ValidationError):
            SymptomExtractionCreate(
                session_id=uuid4(),
                chief_complaint="",
                confidence=0.5,
            )

    def test_rejects_confidence_out_of_range(self):
        with pytest.raises(ValidationError):
            SymptomExtractionCreate(
                session_id=uuid4(),
                chief_complaint="Pain",
                confidence=1.5,
            )

    def test_rejects_chief_complaint_exceeding_max(self):
        with pytest.raises(ValidationError):
            SymptomExtractionCreate(
                session_id=uuid4(),
                chief_complaint="A" * 501,
                confidence=0.5,
            )
