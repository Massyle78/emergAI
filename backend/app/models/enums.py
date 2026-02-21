"""Domain enumerations for the emergAI triage platform."""

from enum import IntEnum, StrEnum


class AcuityLevel(IntEnum):
    """Emergency Severity Index (ESI) acuity levels.

    ESI 1 = most urgent (resuscitation), ESI 5 = least urgent (non-urgent).
    """

    RESUSCITATION = 1
    EMERGENT = 2
    URGENT = 3
    LESS_URGENT = 4
    NON_URGENT = 5


class TriageStatus(StrEnum):
    """Lifecycle states of a triage session."""

    PENDING = "pending"
    CAPTURING = "capturing"
    PROCESSING = "processing"
    AWAITING_REVIEW = "awaiting_review"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class MediaType(StrEnum):
    """Supported media types for patient intake capture."""

    VIDEO = "video"
    AUDIO = "audio"


class CdsIndicator(StrEnum):
    """CDS Hooks card urgency indicator per HL7 spec."""

    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class SymptomSeverity(StrEnum):
    """Severity classification for an individual symptom."""

    MILD = "mild"
    MODERATE = "moderate"
    SEVERE = "severe"
    CRITICAL = "critical"
