"""Risk assessment models for triage scoring and reasoning."""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import AcuityLevel

RISK_SCORE_MIN = 0.0
RISK_SCORE_MAX = 1.0
MAX_CONTRIBUTING_FACTORS = 20
FACTOR_DESCRIPTION_MAX_LENGTH = 500
REASONING_MAX_LENGTH = 2000


class ContributingFactor(BaseModel):
    """A single factor that influenced the risk score."""

    name: str = Field(..., min_length=1, max_length=100)
    weight: float = Field(..., ge=0.0, le=1.0)
    description: str = Field(..., min_length=1, max_length=FACTOR_DESCRIPTION_MAX_LENGTH)


class RiskAssessmentCreate(BaseModel):
    """Input schema for a computed risk assessment."""

    session_id: UUID
    score: float = Field(..., ge=RISK_SCORE_MIN, le=RISK_SCORE_MAX)
    acuity_level: AcuityLevel
    reasoning: str = Field(..., min_length=1, max_length=REASONING_MAX_LENGTH)
    contributing_factors: list[ContributingFactor] = Field(
        default_factory=list, max_length=MAX_CONTRIBUTING_FACTORS
    )
    similar_cases_count: int = Field(default=0, ge=0)


class RiskAssessmentRead(BaseModel):
    """Output schema for a stored risk assessment."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    session_id: UUID
    score: float
    acuity_level: AcuityLevel
    reasoning: str
    contributing_factors: list[ContributingFactor]
    similar_cases_count: int
