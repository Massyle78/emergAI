"""Integration tests for cross-cutting error handling.

Verifies authentication failures, validation errors, and 404s
return consistent JSON error envelopes across all endpoints.
"""

from uuid import uuid4

from tests.conftest import auth_headers, make_jwt


class TestAuthenticationErrors:
    def test_missing_auth_header_returns_401(self, client):
        resp = client.get("/api/v1/patients")
        assert resp.status_code == 401
        body = resp.json()
        assert body["error"]["status_code"] == 401
        assert "authorization" in body["error"]["detail"].lower()

    def test_expired_token_returns_401(self, client):
        token = make_jwt(expired=True)
        resp = client.get("/api/v1/patients", headers=auth_headers(token))
        assert resp.status_code == 401
        assert "expired" in resp.json()["error"]["detail"].lower()

    def test_invalid_token_returns_401(self, client):
        resp = client.get(
            "/api/v1/patients",
            headers={"Authorization": "Bearer invalid.jwt.token"},
        )
        assert resp.status_code == 401

    def test_wrong_scheme_returns_401(self, client):
        resp = client.get(
            "/api/v1/patients",
            headers={"Authorization": "Basic dXNlcjpwYXNz"},
        )
        assert resp.status_code == 401
        assert "scheme" in resp.json()["error"]["detail"].lower()


class TestValidationErrors:
    def test_invalid_json_body_returns_422(self, client, valid_headers):
        resp = client.post(
            "/api/v1/patients",
            json={"first_name": ""},
            headers=valid_headers,
        )
        assert resp.status_code == 422
        body = resp.json()
        assert body["error"]["status_code"] == 422
        assert isinstance(body["error"]["detail"], list)

    def test_invalid_uuid_path_param_returns_422(self, client, valid_headers):
        resp = client.get(
            "/api/v1/patients/not-a-uuid",
            headers=valid_headers,
        )
        assert resp.status_code == 422

    def test_invalid_query_params_returns_422(self, client, valid_headers):
        resp = client.get(
            "/api/v1/patients?limit=-5",
            headers=valid_headers,
        )
        assert resp.status_code == 422

    def test_cds_missing_required_field_returns_422(self, client):
        resp = client.post("/cds-services/triage-risk", json={})
        assert resp.status_code == 422


class TestNotFoundErrors:
    def test_unknown_api_route_returns_404(self, client):
        resp = client.get("/api/v1/nonexistent")
        assert resp.status_code == 404
        body = resp.json()
        assert body["error"]["status_code"] == 404

    def test_unknown_top_level_route_returns_404(self, client):
        resp = client.get("/unknown-path")
        assert resp.status_code == 404


class TestConsistentErrorEnvelope:
    """All error responses must follow the same JSON shape."""

    def test_401_has_error_envelope(self, client):
        resp = client.get("/api/v1/patients")
        body = resp.json()
        assert "error" in body
        assert "status_code" in body["error"]
        assert "detail" in body["error"]

    def test_404_has_error_envelope(self, client):
        resp = client.get("/nope")
        body = resp.json()
        assert "error" in body
        assert "status_code" in body["error"]
        assert "detail" in body["error"]

    def test_422_has_error_envelope(self, client, valid_headers):
        resp = client.post(
            "/api/v1/patients",
            json={"first_name": ""},
            headers=valid_headers,
        )
        body = resp.json()
        assert "error" in body
        assert body["error"]["status_code"] == 422
