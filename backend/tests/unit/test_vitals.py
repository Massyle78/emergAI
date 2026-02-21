"""Tests for Vitals domain models."""

from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.models.vitals import BloodPressure, VitalsCreate


class TestBloodPressure:
    def test_valid(self):
        bp = BloodPressure(systolic=120.0, diastolic=80.0)
        assert bp.systolic == 120.0
        assert bp.diastolic == 80.0

    def test_rejects_systolic_below_min(self):
        with pytest.raises(ValidationError):
            BloodPressure(systolic=39.0, diastolic=80.0)

    def test_rejects_systolic_above_max(self):
        with pytest.raises(ValidationError):
            BloodPressure(systolic=301.0, diastolic=80.0)

    def test_rejects_diastolic_below_min(self):
        with pytest.raises(ValidationError):
            BloodPressure(systolic=120.0, diastolic=19.0)

    def test_rejects_diastolic_above_max(self):
        with pytest.raises(ValidationError):
            BloodPressure(systolic=120.0, diastolic=201.0)

    def test_boundary_values_accepted(self):
        bp = BloodPressure(systolic=40.0, diastolic=20.0)
        assert bp.systolic == 40.0
        bp_max = BloodPressure(systolic=300.0, diastolic=200.0)
        assert bp_max.diastolic == 200.0


class TestVitalsCreate:
    def test_valid_minimal(self):
        v = VitalsCreate(
            session_id=uuid4(),
            heart_rate_bpm=72.0,
            confidence=0.95,
        )
        assert v.heart_rate_bpm == 72.0
        assert v.spo2_percent is None
        assert v.respiratory_rate is None
        assert v.blood_pressure is None

    def test_valid_full(self):
        v = VitalsCreate(
            session_id=uuid4(),
            heart_rate_bpm=80.0,
            spo2_percent=98.0,
            respiratory_rate=16.0,
            blood_pressure=BloodPressure(systolic=120.0, diastolic=80.0),
            confidence=0.9,
        )
        assert v.spo2_percent == 98.0
        assert v.blood_pressure is not None

    def test_rejects_heart_rate_below_min(self):
        with pytest.raises(ValidationError):
            VitalsCreate(
                session_id=uuid4(),
                heart_rate_bpm=19.0,
                confidence=0.5,
            )

    def test_rejects_heart_rate_above_max(self):
        with pytest.raises(ValidationError):
            VitalsCreate(
                session_id=uuid4(),
                heart_rate_bpm=301.0,
                confidence=0.5,
            )

    def test_rejects_spo2_above_100(self):
        with pytest.raises(ValidationError):
            VitalsCreate(
                session_id=uuid4(),
                heart_rate_bpm=72.0,
                spo2_percent=101.0,
                confidence=0.5,
            )

    def test_rejects_negative_confidence(self):
        with pytest.raises(ValidationError):
            VitalsCreate(
                session_id=uuid4(),
                heart_rate_bpm=72.0,
                confidence=-0.1,
            )

    def test_rejects_confidence_above_one(self):
        with pytest.raises(ValidationError):
            VitalsCreate(
                session_id=uuid4(),
                heart_rate_bpm=72.0,
                confidence=1.1,
            )

    def test_boundary_heart_rate_min(self):
        v = VitalsCreate(
            session_id=uuid4(),
            heart_rate_bpm=20.0,
            confidence=0.0,
        )
        assert v.heart_rate_bpm == 20.0

    def test_boundary_heart_rate_max(self):
        v = VitalsCreate(
            session_id=uuid4(),
            heart_rate_bpm=300.0,
            confidence=1.0,
        )
        assert v.heart_rate_bpm == 300.0

    def test_rejects_respiratory_rate_below_min(self):
        with pytest.raises(ValidationError):
            VitalsCreate(
                session_id=uuid4(),
                heart_rate_bpm=72.0,
                respiratory_rate=3.0,
                confidence=0.5,
            )

    def test_rejects_respiratory_rate_above_max(self):
        with pytest.raises(ValidationError):
            VitalsCreate(
                session_id=uuid4(),
                heart_rate_bpm=72.0,
                respiratory_rate=61.0,
                confidence=0.5,
            )
