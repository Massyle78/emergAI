"""Integration tests for application lifecycle, middleware, and configuration.

Verifies that the app factory produces a fully functional application
with CORS, error handlers, and all routers registered.
"""

from app.config import Settings
from app.main import create_app


class TestAppFactory:
    def test_creates_app_with_metadata(self, test_settings):
        app = create_app(settings=test_settings)
        assert app.title == "emergAI"
        assert app.version == "0.1.0"

    def test_docs_available_in_non_production(self, test_settings):
        app = create_app(settings=test_settings)
        assert app.docs_url == "/docs"
        assert app.redoc_url == "/redoc"

    def test_docs_disabled_in_production(self):
        settings = Settings(app_env="production", supabase_jwt_secret="x" * 33)
        app = create_app(settings=settings)
        assert app.docs_url is None
        assert app.redoc_url is None

    def test_settings_attached_to_state(self, test_settings):
        app = create_app(settings=test_settings)
        assert app.state.settings is test_settings


class TestCorsMiddleware:
    def test_cors_allows_configured_origin(self, client):
        resp = client.options(
            "/health",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert resp.headers.get("access-control-allow-origin") == "http://localhost:3000"

    def test_cors_blocks_unconfigured_origin(self, client):
        resp = client.options(
            "/health",
            headers={
                "Origin": "http://evil.com",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert resp.headers.get("access-control-allow-origin") != "http://evil.com"


class TestRouterRegistration:
    def test_health_endpoint_registered(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "healthy"

    def test_patients_endpoint_registered(self, client):
        resp = client.get("/api/v1/patients")
        assert resp.status_code == 401

    def test_media_endpoint_registered(self, client):
        resp = client.post("/api/v1/media/video")
        assert resp.status_code in (401, 422)

    def test_cds_services_endpoint_registered(self, client):
        resp = client.get("/cds-services")
        assert resp.status_code == 200

    def test_nonexistent_route_returns_404(self, client):
        resp = client.get("/api/v1/does-not-exist")
        assert resp.status_code == 404


class TestErrorHandlers:
    def test_404_returns_json_envelope(self, client):
        resp = client.get("/nothing-here")
        assert resp.status_code == 404
        body = resp.json()
        assert "error" in body
        assert body["error"]["status_code"] == 404

    def test_422_returns_field_level_errors(self, client, valid_headers):
        resp = client.post(
            "/api/v1/patients",
            json={"first_name": ""},
            headers=valid_headers,
        )
        assert resp.status_code == 422
        body = resp.json()
        assert "error" in body
        errors = body["error"]["detail"]
        assert isinstance(errors, list)
        assert any("field" in e for e in errors)
