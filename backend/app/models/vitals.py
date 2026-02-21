"""Vitals reading models extracted from rPPG video analysis."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

HEART_RATE_MIN = 20.0
HEART_RATE_MAX = 300.0
SPO2_MIN = 0.0
SPO2_MAX = 100.0
RESPIRATORY_RATE_MIN = 4.0
RESPIRATORY_RATE_MAX = 60.0
SYSTOLIC_BP_MIN = 40.0
SYSTOLIC_BP_MAX = 300.0
DIASTOLIC_BP_MIN = 20.0
DIASTOLIC_BP_MAX = 200.0
CONFIDENCE_MIN = 0.0
CONFIDENCE_MAX = 1.0


class BloodPressure(BaseModel):
    """Systolic/diastolic blood pressure reading in mmHg."""

    systolic: float = Field(..., ge=SYSTOLIC_BP_MIN, le=SYSTOLIC_BP_MAX)
    diastolic: float = Field(..., ge=DIASTOLIC_BP_MIN, le=DIASTOLIC_BP_MAX)


class VitalsCreate(BaseModel):
    """Input schema for a vitals reading produced by open-rppg."""

    session_id: UUID
    heart_rate_bpm: float = Field(..., ge=HEART_RATE_MIN, le=HEART_RATE_MAX)
    spo2_percent: float | None = Field(default=None, ge=SPO2_MIN, le=SPO2_MAX)
    respiratory_rate: float | None = Field(
        default=None, ge=RESPIRATORY_RATE_MIN, le=RESPIRATORY_RATE_MAX
    )
    blood_pressure: BloodPressure | None = None
    confidence: float = Field(..., ge=CONFIDENCE_MIN, le=CONFIDENCE_MAX)


class VitalsRead(BaseModel):
    """Output schema for a stored vitals reading."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    session_id: UUID
    heart_rate_bpm: float
    spo2_percent: float | None = None
    respiratory_rate: float | None = None
    blood_pressure: BloodPressure | None = None
    confidence: float
    recorded_at: datetime
