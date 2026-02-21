"""Tests for Triage session domain models."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.models.enums import TriageStatus
from app.models.triage import (
    TriageSessionCreate,
    TriageSessionRead,
    TriageSessionUpdate,
)


class TestTriageSessionCreate:
    def test_valid(self):
        pid = uuid4()
        t = TriageSessionCreate(patient_id=pid)
        assert t.patient_id == pid

    def test_rejects_invalid_uuid(self):
        with pytest.raises(ValidationError):
            TriageSessionCreate(patient_id="not-a-uuid")


class TestTriageSessionUpdate:
    def test_valid_status(self):
        u = TriageSessionUpdate(status=TriageStatus.PROCESSING)
        assert u.status == TriageStatus.PROCESSING

    def test_rejects_invalid_status(self):
        with pytest.raises(ValidationError):
            TriageSessionUpdate(status="invalid_status")


class TestTriageSessionRead:
    def test_valid(self):
        now = datetime.now(UTC)
        t = TriageSessionRead(
            id=uuid4(),
            patient_id=uuid4(),
            status=TriageStatus.PENDING,
            started_at=now,
            created_at=now,
            updated_at=now,
        )
        assert t.completed_at is None
        assert t.status == TriageStatus.PENDING

    def test_completed_session(self):
        now = datetime.now(UTC)
        t = TriageSessionRead(
            id=uuid4(),
            patient_id=uuid4(),
            status=TriageStatus.COMPLETED,
            started_at=now,
            completed_at=now,
            created_at=now,
            updated_at=now,
        )
        assert t.completed_at is not None
        assert t.status == TriageStatus.COMPLETED
