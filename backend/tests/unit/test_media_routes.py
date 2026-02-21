"""Tests for media upload API routes.

Uses dependency overrides for auth and a real temp directory
for the MediaService (lightweight — no external calls).
"""

import io
import time
from uuid import uuid4

import jwt as pyjwt
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.services.supabase_client import get_supabase

TEST_SECRET = "test-jwt-secret-for-unit-tests-32b"
TEST_USER_ID = uuid4()


def _make_token() -> str:
    payload = {
        "sub": str(TEST_USER_ID),
        "email": "test@example.com",
        "role": "authenticated",
        "exp": int(time.time()) + 3600,
    }
    return pyjwt.encode(payload, TEST_SECRET, algorithm="HS256")


def _auth_headers() -> dict:
    return {"Authorization": f"Bearer {_make_token()}"}


def _create_test_client(tmp_path) -> TestClient:
    settings = Settings(
        app_env="testing",
        supabase_jwt_secret=TEST_SECRET,
        temp_media_dir=str(tmp_path),
        allowed_video_types="video/mp4,video/webm",
        allowed_audio_types="audio/webm,audio/wav",
        max_video_size_mb=1,
        max_audio_size_mb=1,
    )
    application = create_app(settings=settings)
    application.dependency_overrides[get_supabase] = lambda: None
    return TestClient(application, raise_server_exceptions=False)


class TestVideoUpload:
    def test_returns_201_on_success(self, tmp_path):
        client = _create_test_client(tmp_path)
        response = client.post(
            "/api/v1/media/video",
            data={"session_id": str(uuid4())},
            files={"file": ("test.mp4", io.BytesIO(b"video-data"), "video/mp4")},
            headers=_auth_headers(),
        )
        assert response.status_code == 201
        data = response.json()
        assert data["media_type"] == "video"
        assert data["status"] == "uploaded"
        assert "id" in data

    def test_returns_401_without_auth(self, tmp_path):
        client = _create_test_client(tmp_path)
        response = client.post(
            "/api/v1/media/video",
            data={"session_id": str(uuid4())},
            files={"file": ("test.mp4", io.BytesIO(b"data"), "video/mp4")},
        )
        assert response.status_code == 401

    def test_returns_415_for_wrong_type(self, tmp_path):
        client = _create_test_client(tmp_path)
        response = client.post(
            "/api/v1/media/video",
            data={"session_id": str(uuid4())},
            files={"file": ("img.png", io.BytesIO(b"data"), "image/png")},
            headers=_auth_headers(),
        )
        assert response.status_code == 415

    def test_returns_413_for_oversized(self, tmp_path):
        client = _create_test_client(tmp_path)
        oversized = b"x" * (2 * 1024 * 1024)
        response = client.post(
            "/api/v1/media/video",
            data={"session_id": str(uuid4())},
            files={"file": ("big.mp4", io.BytesIO(oversized), "video/mp4")},
            headers=_auth_headers(),
        )
        assert response.status_code == 413


class TestAudioUpload:
    def test_returns_201_on_success(self, tmp_path):
        client = _create_test_client(tmp_path)
        response = client.post(
            "/api/v1/media/audio",
            data={"session_id": str(uuid4())},
            files={"file": ("rec.webm", io.BytesIO(b"audio-data"), "audio/webm")},
            headers=_auth_headers(),
        )
        assert response.status_code == 201
        data = response.json()
        assert data["media_type"] == "audio"

    def test_returns_415_for_wrong_type(self, tmp_path):
        client = _create_test_client(tmp_path)
        response = client.post(
            "/api/v1/media/audio",
            data={"session_id": str(uuid4())},
            files={"file": ("test.mp4", io.BytesIO(b"data"), "video/mp4")},
            headers=_auth_headers(),
        )
        assert response.status_code == 415

    def test_returns_413_for_oversized(self, tmp_path):
        client = _create_test_client(tmp_path)
        oversized = b"x" * (2 * 1024 * 1024)
        response = client.post(
            "/api/v1/media/audio",
            data={"session_id": str(uuid4())},
            files={"file": ("big.wav", io.BytesIO(oversized), "audio/wav")},
            headers=_auth_headers(),
        )
        assert response.status_code == 413
