"""Triage session models representing a single patient encounter."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import TriageStatus


class TriageSessionCreate(BaseModel):
    """Input schema for initiating a new triage session."""

    patient_id: UUID


class TriageSessionUpdate(BaseModel):
    """Input schema for updating a triage session's status."""

    status: TriageStatus


class TriageSessionRead(BaseModel):
    """Output schema for a triage session with full lifecycle data."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    patient_id: UUID
    status: TriageStatus = Field(default=TriageStatus.PENDING)
    started_at: datetime
    completed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
