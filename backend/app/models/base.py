"""Shared base models and mixins for the emergAI domain."""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


def _utc_now() -> datetime:
    """Return the current UTC time as a timezone-aware datetime."""
    return datetime.now(UTC)


class TimestampMixin(BaseModel):
    """Mixin providing created/updated timestamp fields."""

    created_at: datetime = Field(default_factory=_utc_now)
    updated_at: datetime = Field(default_factory=_utc_now)


class IdentifiableModel(TimestampMixin):
    """Base model with a UUID primary key and timestamps."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(default_factory=uuid4)
