"""Symptom extraction models from Gemini multimodal inference."""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import SymptomSeverity

CHIEF_COMPLAINT_MAX_LENGTH = 500
SYMPTOM_NAME_MAX_LENGTH = 200
SYMPTOM_DESCRIPTION_MAX_LENGTH = 1000
FOLLOW_UP_QUESTION_MAX_LENGTH = 500
MAX_FOLLOW_UP_QUESTIONS = 10
MAX_SYMPTOMS = 50


class SymptomDetail(BaseModel):
    """A single symptom detected by the AI inference pipeline."""

    name: str = Field(..., min_length=1, max_length=SYMPTOM_NAME_MAX_LENGTH)
    severity: SymptomSeverity
    description: str | None = Field(
        default=None, max_length=SYMPTOM_DESCRIPTION_MAX_LENGTH
    )
    body_region: str | None = None
    onset_description: str | None = None


class SymptomExtractionCreate(BaseModel):
    """Input schema for symptom extraction results from Gemini."""

    session_id: UUID
    chief_complaint: str = Field(
        ..., min_length=1, max_length=CHIEF_COMPLAINT_MAX_LENGTH
    )
    symptoms: list[SymptomDetail] = Field(
        default_factory=list, max_length=MAX_SYMPTOMS
    )
    follow_up_questions: list[str] = Field(
        default_factory=list, max_length=MAX_FOLLOW_UP_QUESTIONS
    )
    confidence: float = Field(..., ge=0.0, le=1.0)


class SymptomExtractionRead(BaseModel):
    """Output schema for a stored symptom extraction."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    session_id: UUID
    chief_complaint: str
    symptoms: list[SymptomDetail]
    follow_up_questions: list[str]
    confidence: float
