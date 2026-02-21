"""Shared test fixtures used by unit, integration, contract, and security tests."""

import time
from uuid import UUID, uuid4

import jwt as pyjwt
import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.services.supabase_client import get_supabase

TEST_SECRET = "test-jwt-secret-for-shared-fixtures-32bytes"
TEST_USER_ID = UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")


@pytest.fixture()
def test_settings(tmp_path) -> Settings:
    return Settings(
        app_env="testing",
        supabase_jwt_secret=TEST_SECRET,
        temp_media_dir=str(tmp_path / "media"),
        allowed_video_types="video/mp4,video/webm",
        allowed_audio_types="audio/webm,audio/wav",
        max_video_size_mb=1,
        max_audio_size_mb=1,
        cors_origins="http://localhost:3000",
    )


@pytest.fixture()
def app(test_settings):
    application = create_app(settings=test_settings)
    application.dependency_overrides[get_supabase] = lambda: None
    return application


@pytest.fixture()
def client(app) -> TestClient:
    return TestClient(app, raise_server_exceptions=False)


def make_jwt(
    user_id: UUID | None = None,
    email: str = "test@example.com",
    role: str = "authenticated",
    expired: bool = False,
    secret: str = TEST_SECRET,
) -> str:
    """Create a signed JWT for testing."""
    payload = {
        "sub": str(user_id or TEST_USER_ID),
        "email": email,
        "role": role,
        "exp": int(time.time()) + (-3600 if expired else 3600),
    }
    return pyjwt.encode(payload, secret, algorithm="HS256")


def auth_headers(token: str | None = None) -> dict[str, str]:
    """Return Authorization headers with a valid test JWT."""
    return {"Authorization": f"Bearer {token or make_jwt()}"}


@pytest.fixture()
def valid_token() -> str:
    return make_jwt()


@pytest.fixture()
def valid_headers() -> dict[str, str]:
    return auth_headers()
