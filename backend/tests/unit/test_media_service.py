"""Tests for media validation and storage service.

Uses synthetic UploadFile objects and a temp directory — no real
media files or long-lived filesystem state.
"""

import io
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi import HTTPException, UploadFile

from app.config import Settings
from app.models.enums import MediaType
from app.services.media_service import (
    MediaService,
    _sanitize_filename,
    _validate_content_type,
    _validate_file_size,
)


def _fake_upload(
    content: bytes = b"fake-video-data",
    filename: str = "test.mp4",
    content_type: str = "video/mp4",
) -> UploadFile:
    """Create a synthetic UploadFile for testing."""
    return UploadFile(
        file=io.BytesIO(content),
        filename=filename,
        headers={"content-type": content_type},
    )


class TestSanitizeFilename:
    def test_removes_unsafe_characters(self):
        assert _sanitize_filename("my file (1).mp4") == "my_file__1_.mp4"

    def test_preserves_safe_characters(self):
        assert _sanitize_filename("video-2024.mp4") == "video-2024.mp4"

    def test_handles_none(self):
        assert _sanitize_filename(None) == "unnamed"

    def test_handles_empty_string(self):
        assert _sanitize_filename("") == "unnamed"

    def test_truncates_long_filenames(self):
        long_name = "a" * 300 + ".mp4"
        result = _sanitize_filename(long_name)
        assert len(result) <= 255


class TestValidateContentType:
    def test_accepts_allowed_type(self):
        result = _validate_content_type("video/mp4", ["video/mp4", "video/webm"])
        assert result == "video/mp4"

    def test_rejects_disallowed_type(self):
        with pytest.raises(HTTPException) as exc_info:
            _validate_content_type("image/png", ["video/mp4"])
        assert exc_info.value.status_code == 415

    def test_rejects_none_type(self):
        with pytest.raises(HTTPException) as exc_info:
            _validate_content_type(None, ["video/mp4"])
        assert exc_info.value.status_code == 415


class TestValidateFileSize:
    def test_accepts_within_limit(self):
        _validate_file_size(1024, max_mb=1)

    def test_rejects_oversized(self):
        with pytest.raises(HTTPException) as exc_info:
            _validate_file_size(2 * 1024 * 1024, max_mb=1)
        assert exc_info.value.status_code == 413

    def test_boundary_exact_limit(self):
        _validate_file_size(1024 * 1024, max_mb=1)


class TestMediaServiceProcessUpload:
    @pytest.mark.asyncio
    async def test_video_upload_success(self, tmp_path):
        settings = Settings(
            temp_media_dir=str(tmp_path),
            allowed_video_types="video/mp4,video/webm",
            max_video_size_mb=50,
        )
        service = MediaService(settings)
        upload = _fake_upload()

        result = await service.process_upload(upload, uuid4(), MediaType.VIDEO)

        assert result.media_type == MediaType.VIDEO
        assert result.status == "uploaded"
        assert result.size_bytes == len(b"fake-video-data")
        assert result.content_type == "video/mp4"

    @pytest.mark.asyncio
    async def test_audio_upload_success(self, tmp_path):
        settings = Settings(
            temp_media_dir=str(tmp_path),
            allowed_audio_types="audio/webm,audio/wav",
            max_audio_size_mb=20,
        )
        service = MediaService(settings)
        upload = _fake_upload(
            content=b"fake-audio-data",
            filename="recording.webm",
            content_type="audio/webm",
        )

        result = await service.process_upload(upload, uuid4(), MediaType.AUDIO)

        assert result.media_type == MediaType.AUDIO
        assert result.content_type == "audio/webm"

    @pytest.mark.asyncio
    async def test_rejects_wrong_content_type(self, tmp_path):
        settings = Settings(
            temp_media_dir=str(tmp_path),
            allowed_video_types="video/mp4",
        )
        service = MediaService(settings)
        upload = _fake_upload(content_type="image/png")

        with pytest.raises(HTTPException) as exc_info:
            await service.process_upload(upload, uuid4(), MediaType.VIDEO)
        assert exc_info.value.status_code == 415

    @pytest.mark.asyncio
    async def test_rejects_oversized_file(self, tmp_path):
        settings = Settings(
            temp_media_dir=str(tmp_path),
            allowed_video_types="video/mp4",
            max_video_size_mb=1,
        )
        service = MediaService(settings)
        oversized = b"x" * (2 * 1024 * 1024)
        upload = _fake_upload(content=oversized)

        with pytest.raises(HTTPException) as exc_info:
            await service.process_upload(upload, uuid4(), MediaType.VIDEO)
        assert exc_info.value.status_code == 413

    @pytest.mark.asyncio
    async def test_writes_file_to_temp_dir(self, tmp_path):
        settings = Settings(
            temp_media_dir=str(tmp_path),
            allowed_video_types="video/mp4",
        )
        service = MediaService(settings)
        upload = _fake_upload()

        result = await service.process_upload(upload, uuid4(), MediaType.VIDEO)

        written_files = list(tmp_path.iterdir())
        assert len(written_files) == 1
        assert written_files[0].read_bytes() == b"fake-video-data"

    @pytest.mark.asyncio
    async def test_sanitizes_filename_in_output(self, tmp_path):
        settings = Settings(
            temp_media_dir=str(tmp_path),
            allowed_video_types="video/mp4",
        )
        service = MediaService(settings)
        upload = _fake_upload(filename="../../etc/passwd.mp4")

        result = await service.process_upload(upload, uuid4(), MediaType.VIDEO)

        assert "/" not in result.filename
        assert "\\" not in result.filename
        written = list(tmp_path.iterdir())
        assert all(f.parent == tmp_path for f in written)
