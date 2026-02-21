"""Media upload models for intake video and audio capture."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import MediaType

MAX_FILENAME_LENGTH = 255


class MediaUploadResponse(BaseModel):
    """Response schema returned after a successful media upload."""

    id: UUID
    session_id: UUID
    media_type: MediaType
    filename: str = Field(..., max_length=MAX_FILENAME_LENGTH)
    size_bytes: int = Field(..., ge=0)
    content_type: str
    status: str = Field(default="uploaded")
    uploaded_at: datetime


class MediaProcessingStatus(BaseModel):
    """Status of async media processing for polling."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    session_id: UUID
    media_type: MediaType
    status: str
