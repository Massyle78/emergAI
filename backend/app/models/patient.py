"""Patient domain models for intake and record management."""

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

PATIENT_NAME_MAX_LENGTH = 100
PATIENT_NAME_MIN_LENGTH = 1
PHONE_MAX_LENGTH = 20
MRN_MAX_LENGTH = 50


class PatientCreate(BaseModel):
    """Input schema for registering a new patient at intake."""

    first_name: str = Field(
        ..., min_length=PATIENT_NAME_MIN_LENGTH, max_length=PATIENT_NAME_MAX_LENGTH
    )
    last_name: str = Field(
        ..., min_length=PATIENT_NAME_MIN_LENGTH, max_length=PATIENT_NAME_MAX_LENGTH
    )
    date_of_birth: date
    phone: str | None = Field(default=None, max_length=PHONE_MAX_LENGTH)
    medical_record_number: str | None = Field(default=None, max_length=MRN_MAX_LENGTH)

    @field_validator("first_name", "last_name")
    @classmethod
    def strip_and_validate_name(cls, value: str) -> str:
        """Strip whitespace and reject names with only whitespace."""
        stripped = value.strip()
        if not stripped:
            msg = "Name must contain non-whitespace characters"
            raise ValueError(msg)
        return stripped

    @field_validator("date_of_birth")
    @classmethod
    def validate_not_future(cls, value: date) -> date:
        """Reject dates of birth in the future."""
        if value > date.today():
            msg = "Date of birth cannot be in the future"
            raise ValueError(msg)
        return value


class PatientRead(BaseModel):
    """Output schema for a patient record retrieved from storage."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    first_name: str
    last_name: str
    date_of_birth: date
    phone: str | None = None
    medical_record_number: str | None = None
    created_at: datetime
    updated_at: datetime
