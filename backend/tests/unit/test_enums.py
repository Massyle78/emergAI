"""Tests for domain enumerations."""

from app.models.enums import (
    AcuityLevel,
    CdsIndicator,
    MediaType,
    SymptomSeverity,
    TriageStatus,
)


class TestAcuityLevel:
    def test_values_match_esi_scale(self):
        assert AcuityLevel.RESUSCITATION == 1
        assert AcuityLevel.EMERGENT == 2
        assert AcuityLevel.URGENT == 3
        assert AcuityLevel.LESS_URGENT == 4
        assert AcuityLevel.NON_URGENT == 5

    def test_ordering(self):
        assert AcuityLevel.RESUSCITATION < AcuityLevel.NON_URGENT

    def test_total_count(self):
        assert len(AcuityLevel) == 5


class TestTriageStatus:
    def test_all_lifecycle_states_present(self):
        expected = {
            "pending", "capturing", "processing",
            "awaiting_review", "completed", "cancelled",
        }
        assert {s.value for s in TriageStatus} == expected

    def test_string_value(self):
        assert TriageStatus.PENDING == "pending"


class TestMediaType:
    def test_supported_types(self):
        assert MediaType.VIDEO == "video"
        assert MediaType.AUDIO == "audio"
        assert len(MediaType) == 2


class TestCdsIndicator:
    def test_all_indicators(self):
        assert CdsIndicator.INFO == "info"
        assert CdsIndicator.WARNING == "warning"
        assert CdsIndicator.CRITICAL == "critical"


class TestSymptomSeverity:
    def test_all_levels(self):
        expected = {"mild", "moderate", "severe", "critical"}
        assert {s.value for s in SymptomSeverity} == expected
