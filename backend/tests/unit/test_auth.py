"""Tests for JWT authentication dependency.

Uses synthetic JWTs created with a known secret — no real Supabase calls.
"""

import time
from uuid import uuid4

import jwt as pyjwt
import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.utils.auth import (
    AuthenticatedUser,
    _build_user,
    _decode_jwt,
    _extract_token,
    get_current_user,
)

TEST_SECRET = "test-jwt-secret-for-unit-tests-32b"
TEST_USER_ID = str(uuid4())


def _make_token(payload: dict, secret: str = TEST_SECRET) -> str:
    """Create a signed JWT for testing."""
    return pyjwt.encode(payload, secret, algorithm="HS256")


def _valid_payload() -> dict:
    """Return a valid JWT payload with standard Supabase claims."""
    return {
        "sub": TEST_USER_ID,
        "email": "test@example.com",
        "role": "authenticated",
        "exp": int(time.time()) + 3600,
    }


def _create_auth_test_app() -> tuple[FastAPI, TestClient]:
    """Build a test app with a protected route."""
    settings = Settings(
        app_env="testing",
        supabase_jwt_secret=TEST_SECRET,
    )
    application = create_app(settings=settings)

    @application.get("/protected")
    async def protected_route(user: AuthenticatedUser = Depends(get_current_user)):
        return {"user_id": str(user.id), "role": user.role}

    client = TestClient(application, raise_server_exceptions=False)
    return application, client


class TestExtractToken:
    def test_valid_bearer_token(self):
        token = _extract_token("Bearer abc123")
        assert token == "abc123"

    def test_missing_header_raises_401(self):
        from fastapi.exceptions import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            _extract_token(None)
        assert exc_info.value.status_code == 401
        assert "Missing" in exc_info.value.detail

    def test_non_bearer_scheme_raises_401(self):
        from fastapi.exceptions import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            _extract_token("Basic abc123")
        assert exc_info.value.status_code == 401
        assert "scheme" in exc_info.value.detail.lower()


class TestDecodeJwt:
    def test_valid_token(self):
        token = _make_token(_valid_payload())
        payload = _decode_jwt(token, TEST_SECRET)
        assert payload["sub"] == TEST_USER_ID

    def test_expired_token_raises_401(self):
        from fastapi.exceptions import HTTPException

        expired_payload = _valid_payload()
        expired_payload["exp"] = int(time.time()) - 3600
        token = _make_token(expired_payload)
        with pytest.raises(HTTPException) as exc_info:
            _decode_jwt(token, TEST_SECRET)
        assert exc_info.value.status_code == 401
        assert "expired" in exc_info.value.detail.lower()

    def test_wrong_secret_raises_401(self):
        from fastapi.exceptions import HTTPException

        token = _make_token(_valid_payload())
        with pytest.raises(HTTPException) as exc_info:
            _decode_jwt(token, "wrong-secret")
        assert exc_info.value.status_code == 401

    def test_malformed_token_raises_401(self):
        from fastapi.exceptions import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            _decode_jwt("not.a.valid.jwt", TEST_SECRET)
        assert exc_info.value.status_code == 401


class TestBuildUser:
    def test_valid_payload(self):
        payload = _valid_payload()
        user = _build_user(payload)
        assert str(user.id) == TEST_USER_ID
        assert user.email == "test@example.com"
        assert user.role == "authenticated"

    def test_missing_sub_raises_401(self):
        from fastapi.exceptions import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            _build_user({"email": "test@example.com"})
        assert exc_info.value.status_code == 401
        assert "subject" in exc_info.value.detail.lower()

    def test_defaults_role_when_missing(self):
        user = _build_user({"sub": TEST_USER_ID})
        assert user.role == "authenticated"

    def test_email_optional(self):
        user = _build_user({"sub": TEST_USER_ID})
        assert user.email is None


class TestGetCurrentUserIntegration:
    def test_valid_token_returns_user(self):
        _, client = _create_auth_test_app()
        token = _make_token(_valid_payload())
        response = client.get(
            "/protected",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == TEST_USER_ID
        assert data["role"] == "authenticated"

    def test_missing_header_returns_401(self):
        _, client = _create_auth_test_app()
        response = client.get("/protected")
        assert response.status_code == 401

    def test_expired_token_returns_401(self):
        _, client = _create_auth_test_app()
        expired = _valid_payload()
        expired["exp"] = int(time.time()) - 3600
        token = _make_token(expired)
        response = client.get(
            "/protected",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 401

    def test_wrong_secret_returns_401(self):
        _, client = _create_auth_test_app()
        token = _make_token(_valid_payload(), secret="wrong-secret")
        response = client.get(
            "/protected",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 401

    def test_error_body_is_structured(self):
        _, client = _create_auth_test_app()
        response = client.get("/protected")
        body = response.json()
        assert "error" in body
        assert body["error"]["status_code"] == 401


class TestAuthenticatedUserModel:
    def test_valid_construction(self):
        uid = uuid4()
        user = AuthenticatedUser(id=uid, email="a@b.com", role="admin")
        assert user.id == uid
        assert user.email == "a@b.com"
        assert user.role == "admin"

    def test_defaults(self):
        uid = uuid4()
        user = AuthenticatedUser(id=uid)
        assert user.email is None
        assert user.role == "authenticated"
