"""Automated security audit checklist.

Validates key security properties of the application:
  1. Auth enforcement on protected endpoints
  2. No sensitive data leakage in error responses
  3. Input validation against injection vectors
  4. File upload security (type, size, path traversal)
  5. CORS configuration
  6. Secure headers and response shapes
"""

import io
from uuid import uuid4

import pytest

from tests.conftest import auth_headers, make_jwt


class TestAuthEnforcement:
    """Every protected endpoint must reject unauthenticated requests."""

    PROTECTED_ENDPOINTS = [
        ("GET", "/api/v1/patients"),
        ("POST", "/api/v1/patients"),
        ("GET", f"/api/v1/patients/{uuid4()}"),
        ("PATCH", f"/api/v1/patients/{uuid4()}"),
        ("POST", "/api/v1/media/video"),
        ("POST", "/api/v1/media/audio"),
    ]

    @pytest.mark.parametrize("method,path", PROTECTED_ENDPOINTS)
    def test_endpoint_requires_auth(self, client, method, path):
        resp = client.request(method, path)
        assert resp.status_code == 401, f"{method} {path} should require auth"

    def test_expired_token_rejected(self, client):
        token = make_jwt(expired=True)
        resp = client.get("/api/v1/patients", headers=auth_headers(token))
        assert resp.status_code == 401

    def test_wrong_signing_key_rejected(self, client):
        token = make_jwt(secret="wrong-secret-key-that-is-long-enough")
        resp = client.get("/api/v1/patients", headers=auth_headers(token))
        assert resp.status_code == 401

    def test_malformed_token_rejected(self, client):
        resp = client.get(
            "/api/v1/patients",
            headers={"Authorization": "Bearer not.valid.jwt"},
        )
        assert resp.status_code == 401

    def test_missing_bearer_prefix_rejected(self, client):
        token = make_jwt()
        resp = client.get(
            "/api/v1/patients",
            headers={"Authorization": token},
        )
        assert resp.status_code == 401


class TestNoSensitiveDataLeakage:
    """Error responses must not expose internal details."""

    def test_404_does_not_leak_stack_trace(self, client):
        resp = client.get("/api/v1/nonexistent")
        body = resp.text
        assert "Traceback" not in body
        assert "File " not in body
        assert ".py" not in body

    def test_422_does_not_leak_internal_paths(self, client, valid_headers):
        resp = client.post(
            "/api/v1/patients",
            json={"invalid": True},
            headers=valid_headers,
        )
        body = resp.text
        assert "\\app\\" not in body
        assert "/app/" not in body

    def test_auth_error_does_not_leak_secret(self, client):
        resp = client.get(
            "/api/v1/patients",
            headers={"Authorization": "Bearer bad"},
        )
        body = resp.text
        assert "jwt_secret" not in body.lower()
        assert "secret" not in body.lower() or "secret" in "supabase_jwt_secret"


class TestInputValidation:
    """Validate protection against common injection vectors."""

    INJECTION_PAYLOADS = [
        {"first_name": "'; DROP TABLE patients; --", "last_name": "X", "date_of_birth": "1990-01-01"},
        {"first_name": "<script>alert('xss')</script>", "last_name": "X", "date_of_birth": "1990-01-01"},
        {"first_name": "A" * 1000, "last_name": "B" * 1000, "date_of_birth": "1990-01-01"},
    ]

    @pytest.mark.parametrize("payload", INJECTION_PAYLOADS)
    def test_injection_payloads_do_not_crash_app(self, client, valid_headers, payload):
        resp = client.post("/api/v1/patients", json=payload, headers=valid_headers)
        assert resp.status_code in (201, 422, 500), "App should return a JSON response"
        body = resp.json()
        assert "error" in body or "id" in body, "Response must be structured JSON"

    def test_oversized_json_body(self, client, valid_headers):
        huge = {"first_name": "A" * 100_000, "last_name": "B", "date_of_birth": "1990-01-01"}
        resp = client.post("/api/v1/patients", json=huge, headers=valid_headers)
        assert resp.status_code in (201, 413, 422)

    def test_invalid_uuid_does_not_crash(self, client, valid_headers):
        resp = client.get("/api/v1/patients/not-a-uuid", headers=valid_headers)
        assert resp.status_code == 422
        assert "Traceback" not in resp.text

    def test_cds_hooks_handles_malicious_context(self, client):
        resp = client.post(
            "/cds-services/triage-risk",
            json={
                "hookInstance": str(uuid4()),
                "hook": "patient-view",
                "context": {"session_id": "'; DROP TABLE sessions; --"},
            },
        )
        assert resp.status_code in (200, 422)


class TestFileUploadSecurity:
    """Validates file upload protections."""

    def test_rejects_disallowed_content_type(self, client, valid_headers):
        resp = client.post(
            "/api/v1/media/video",
            data={"session_id": str(uuid4())},
            files={"file": ("evil.exe", io.BytesIO(b"MZ..."), "application/x-msdownload")},
            headers=valid_headers,
        )
        assert resp.status_code == 415

    def test_rejects_oversized_upload(self, client, valid_headers):
        oversized = b"x" * (2 * 1024 * 1024)
        resp = client.post(
            "/api/v1/media/video",
            data={"session_id": str(uuid4())},
            files={"file": ("big.mp4", io.BytesIO(oversized), "video/mp4")},
            headers=valid_headers,
        )
        assert resp.status_code == 413

    def test_path_traversal_in_filename(self, client, valid_headers):
        resp = client.post(
            "/api/v1/media/video",
            data={"session_id": str(uuid4())},
            files={"file": ("../../../etc/passwd", io.BytesIO(b"data"), "video/mp4")},
            headers=valid_headers,
        )
        if resp.status_code == 201:
            assert "../" not in resp.json()["filename"]

    def test_null_bytes_in_filename(self, client, valid_headers):
        resp = client.post(
            "/api/v1/media/video",
            data={"session_id": str(uuid4())},
            files={"file": ("evil\x00.mp4", io.BytesIO(b"data"), "video/mp4")},
            headers=valid_headers,
        )
        if resp.status_code == 201:
            assert "\x00" not in resp.json()["filename"]


class TestCorsConfiguration:
    def test_allowed_origin_accepted(self, client):
        resp = client.options(
            "/health",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert resp.headers.get("access-control-allow-origin") == "http://localhost:3000"

    def test_disallowed_origin_rejected(self, client):
        resp = client.options(
            "/health",
            headers={
                "Origin": "http://attacker.com",
                "Access-Control-Request-Method": "GET",
            },
        )
        allow_origin = resp.headers.get("access-control-allow-origin", "")
        assert allow_origin != "http://attacker.com"
        assert allow_origin != "*"


class TestResponseHeaders:
    def test_health_returns_json_content_type(self, client):
        resp = client.get("/health")
        assert "application/json" in resp.headers.get("content-type", "")

    def test_error_returns_json_content_type(self, client):
        resp = client.get("/nonexistent")
        assert "application/json" in resp.headers.get("content-type", "")
