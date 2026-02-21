"""Tests for Patient domain models."""

from datetime import UTC, date, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.models.patient import PatientCreate, PatientRead


class TestPatientCreate:
    def test_valid_minimal(self):
        p = PatientCreate(
            first_name="Jane",
            last_name="Doe",
            date_of_birth=date(1990, 5, 15),
        )
        assert p.first_name == "Jane"
        assert p.last_name == "Doe"
        assert p.phone is None
        assert p.medical_record_number is None

    def test_valid_full(self):
        p = PatientCreate(
            first_name="Jane",
            last_name="Doe",
            date_of_birth=date(1990, 5, 15),
            phone="+1-555-0123",
            medical_record_number="MRN-12345",
        )
        assert p.phone == "+1-555-0123"
        assert p.medical_record_number == "MRN-12345"

    def test_strips_whitespace_from_names(self):
        p = PatientCreate(
            first_name="  Jane  ",
            last_name="  Doe  ",
            date_of_birth=date(1990, 1, 1),
        )
        assert p.first_name == "Jane"
        assert p.last_name == "Doe"

    def test_rejects_empty_first_name(self):
        with pytest.raises(ValidationError):
            PatientCreate(
                first_name="",
                last_name="Doe",
                date_of_birth=date(1990, 1, 1),
            )

    def test_rejects_whitespace_only_name(self):
        with pytest.raises(ValidationError):
            PatientCreate(
                first_name="   ",
                last_name="Doe",
                date_of_birth=date(1990, 1, 1),
            )

    def test_rejects_future_date_of_birth(self):
        with pytest.raises(ValidationError, match="future"):
            PatientCreate(
                first_name="Jane",
                last_name="Doe",
                date_of_birth=date(2099, 1, 1),
            )

    def test_rejects_name_exceeding_max_length(self):
        with pytest.raises(ValidationError):
            PatientCreate(
                first_name="A" * 101,
                last_name="Doe",
                date_of_birth=date(1990, 1, 1),
            )

    def test_accepts_today_as_dob(self):
        p = PatientCreate(
            first_name="Newborn",
            last_name="Baby",
            date_of_birth=date.today(),
        )
        assert p.date_of_birth == date.today()


class TestPatientRead:
    def test_from_dict(self):
        uid = uuid4()
        now = datetime.now(UTC)
        p = PatientRead(
            id=uid,
            first_name="Jane",
            last_name="Doe",
            date_of_birth=date(1990, 5, 15),
            created_at=now,
            updated_at=now,
        )
        assert p.id == uid
        assert p.first_name == "Jane"

    def test_optional_fields_default_none(self):
        uid = uuid4()
        now = datetime.now(UTC)
        p = PatientRead(
            id=uid,
            first_name="Jane",
            last_name="Doe",
            date_of_birth=date(1990, 5, 15),
            created_at=now,
            updated_at=now,
        )
        assert p.phone is None
        assert p.medical_record_number is None
