"""Normalized patient history models from FHIR resources.

Maps Metriport consolidated data (Condition, MedicationStatement,
AllergyIntolerance) to flat, validated Pydantic schemas used by
the triage orchestration engine.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

DISPLAY_MAX_LENGTH = 500
CODE_MAX_LENGTH = 50
SYSTEM_MAX_LENGTH = 200


class ClinicalCode(BaseModel):
    """A single code from a FHIR CodeableConcept coding entry."""

    system: str | None = Field(default=None, max_length=SYSTEM_MAX_LENGTH)
    code: str | None = Field(default=None, max_length=CODE_MAX_LENGTH)
    display: str | None = Field(default=None, max_length=DISPLAY_MAX_LENGTH)


class ConditionRecord(BaseModel):
    """Normalized active medical condition from FHIR Condition."""

    code: ClinicalCode
    clinical_status: str | None = None
    onset: str | None = None
    text: str | None = Field(default=None, max_length=DISPLAY_MAX_LENGTH)


class MedicationRecord(BaseModel):
    """Normalized medication from FHIR MedicationStatement."""

    code: ClinicalCode
    status: str | None = None
    dosage: str | None = None
    text: str | None = Field(default=None, max_length=DISPLAY_MAX_LENGTH)


class AllergyRecord(BaseModel):
    """Normalized allergy from FHIR AllergyIntolerance."""

    code: ClinicalCode
    clinical_status: str | None = None
    criticality: str | None = None
    text: str | None = Field(default=None, max_length=DISPLAY_MAX_LENGTH)


class PatientHistory(BaseModel):
    """Aggregated patient history from EHR data."""

    conditions: list[ConditionRecord] = Field(default_factory=list)
    medications: list[MedicationRecord] = Field(default_factory=list)
    allergies: list[AllergyRecord] = Field(default_factory=list)

    @property
    def is_empty(self) -> bool:
        """Check whether any history data was found."""
        return not (self.conditions or self.medications or self.allergies)

    @property
    def total_records(self) -> int:
        """Total number of records across all categories."""
        return len(self.conditions) + len(self.medications) + len(self.allergies)
