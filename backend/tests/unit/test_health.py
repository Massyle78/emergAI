"""Tests for the health check endpoint."""

from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


def _create_test_client() -> TestClient:
    """Build a TestClient with test settings."""
    settings = Settings(app_env="testing")
    application = create_app(settings=settings)
    return TestClient(application)


class TestHealthEndpoint:
    def test_returns_200(self):
        client = _create_test_client()
        response = client.get("/health")
        assert response.status_code == 200

    def test_returns_healthy_status(self):
        client = _create_test_client()
        data = client.get("/health").json()
        assert data["status"] == "healthy"

    def test_includes_version(self):
        client = _create_test_client()
        data = client.get("/health").json()
        assert "version" in data
        assert data["version"] == "0.1.0"

    def test_response_is_json(self):
        client = _create_test_client()
        response = client.get("/health")
        assert response.headers["content-type"] == "application/json"
