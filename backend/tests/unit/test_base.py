"""Tests for base models and mixins."""

from datetime import datetime
from uuid import UUID

from app.models.base import IdentifiableModel, TimestampMixin


class TestTimestampMixin:
    def test_defaults_to_current_time(self):
        m = TimestampMixin()
        assert isinstance(m.created_at, datetime)
        assert isinstance(m.updated_at, datetime)

    def test_accepts_explicit_timestamps(self):
        ts = datetime(2025, 1, 1, 12, 0, 0)
        m = TimestampMixin(created_at=ts, updated_at=ts)
        assert m.created_at == ts
        assert m.updated_at == ts


class TestIdentifiableModel:
    def test_generates_uuid(self):
        m = IdentifiableModel()
        assert isinstance(m.id, UUID)

    def test_unique_ids(self):
        m1 = IdentifiableModel()
        m2 = IdentifiableModel()
        assert m1.id != m2.id

    def test_accepts_explicit_id(self):
        from uuid import uuid4

        uid = uuid4()
        m = IdentifiableModel(id=uid)
        assert m.id == uid

    def test_has_timestamps(self):
        m = IdentifiableModel()
        assert isinstance(m.created_at, datetime)
        assert isinstance(m.updated_at, datetime)
