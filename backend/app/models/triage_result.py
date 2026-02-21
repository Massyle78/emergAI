"""Composite output of the triage orchestration engine.

Bundles the individual service results (vitals, symptoms, history,
similar cases) with the computed risk assessment and any errors
from services that failed during parallel dispatch.
"""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field

from app.models.patient_history import PatientHistory
from app.models.risk import RiskAssessmentCreate
from app.models.similarity import SimilarCase
from app.models.symptoms import SymptomExtractionCreate
from app.models.vitals import VitalsCreate


class TriageResult(BaseModel):
    """Aggregated result of a full triage orchestration run.

    Fields set to None indicate that the corresponding service
    was either not invoked (no input provided) or failed gracefully.
    Any failures are recorded in *errors* so the caller can surface
    them alongside the partial result.
    """

    session_id: UUID
    vitals: VitalsCreate | None = None
    symptoms: SymptomExtractionCreate | None = None
    history: PatientHistory | None = None
    similar_cases: list[SimilarCase] = Field(default_factory=list)
    risk: RiskAssessmentCreate
    errors: list[str] = Field(default_factory=list)

    @property
    def is_partial(self) -> bool:
        """True when at least one service did not produce results."""
        return bool(self.errors)
