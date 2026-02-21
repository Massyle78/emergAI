"""Media validation and temporary file storage service.

Handles file type whitelisting, size enforcement, filename
sanitization, and secure writes to the temp media directory.
"""

import logging
import re
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

from fastapi import HTTPException, UploadFile

from app.config import Settings
from app.models.enums import MediaType
from app.models.media import MediaUploadResponse

logger = logging.getLogger("app.services.media")

_SAFE_FILENAME_PATTERN = re.compile(r"[^\w\-.]")
_BYTES_PER_MB = 1024 * 1024


def _sanitize_filename(filename: str | None) -> str:
    """Remove unsafe characters from the uploaded filename."""
    if not filename:
        return "unnamed"
    sanitized = _SAFE_FILENAME_PATTERN.sub("_", filename)
    return sanitized[:255] or "unnamed"


def _validate_content_type(
    content_type: str | None, allowed_types: list[str]
) -> str:
    """Verify the upload's MIME type is in the allowed list.

    Raises:
        HTTPException: 415 if the content type is not allowed.
    """
    if not content_type or content_type not in allowed_types:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported media type: {content_type}",
        )
    return content_type


def _validate_file_size(size_bytes: int, max_mb: int) -> None:
    """Enforce the maximum file size in megabytes.

    Raises:
        HTTPException: 413 if the file exceeds the size limit.
    """
    max_bytes = max_mb * _BYTES_PER_MB
    if size_bytes > max_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File size {size_bytes} bytes exceeds limit of {max_mb} MB",
        )


async def _read_file_content(upload: UploadFile) -> bytes:
    """Read the full content of an uploaded file."""
    return await upload.read()


def _write_to_temp(content: bytes, directory: Path, filename: str) -> Path:
    """Write file content to the temp directory and return the path."""
    directory.mkdir(parents=True, exist_ok=True)
    file_path = directory / filename
    file_path.write_bytes(content)
    return file_path


class MediaService:
    """Validates uploads and persists them to temporary storage."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._temp_dir = Path(settings.temp_media_dir)

    async def process_upload(
        self, upload: UploadFile, session_id: UUID, media_type: MediaType
    ) -> MediaUploadResponse:
        """Validate, store, and return metadata for an uploaded file."""
        allowed_types = self._get_allowed_types(media_type)
        max_mb = self._get_max_size_mb(media_type)

        content_type = _validate_content_type(upload.content_type, allowed_types)
        content = await _read_file_content(upload)
        _validate_file_size(len(content), max_mb)

        media_id = uuid4()
        safe_name = f"{media_id}_{_sanitize_filename(upload.filename)}"
        _write_to_temp(content, self._temp_dir, safe_name)

        logger.info("Stored %s upload %s (%d bytes)", media_type, media_id, len(content))

        return MediaUploadResponse(
            id=media_id,
            session_id=session_id,
            media_type=media_type,
            filename=safe_name,
            size_bytes=len(content),
            content_type=content_type,
            status="uploaded",
            uploaded_at=datetime.now(UTC),
        )

    def _get_allowed_types(self, media_type: MediaType) -> list[str]:
        """Return the allowed MIME types for the given media type."""
        if media_type == MediaType.VIDEO:
            return self._settings.video_types_list
        return self._settings.audio_types_list

    def _get_max_size_mb(self, media_type: MediaType) -> int:
        """Return the max file size in MB for the given media type."""
        if media_type == MediaType.VIDEO:
            return self._settings.max_video_size_mb
        return self._settings.max_audio_size_mb
