"""Tests for the CDS Hooks router endpoints.

Uses FastAPI's TestClient for HTTP-level assertions without
real network calls.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture()
def client() -> TestClient:
    app = create_app()
    return TestClient(app)


# ==================================================================
# GET /cds-services  (Discovery)
# ==================================================================
class TestDiscoveryEndpoint:
    def test_returns_200(self, client: TestClient) -> None:
        resp = client.get("/cds-services")
        assert resp.status_code == 200

    def test_response_has_services_list(self, client: TestClient) -> None:
        data = client.get("/cds-services").json()
        assert "services" in data
        assert isinstance(data["services"], list)

    def test_triage_service_advertised(self, client: TestClient) -> None:
        data = client.get("/cds-services").json()
        ids = [s["id"] for s in data["services"]]
        assert "triage-risk" in ids

    def test_triage_service_fields(self, client: TestClient) -> None:
        data = client.get("/cds-services").json()
        svc = data["services"][0]
        assert svc["hook"] == "patient-view"
        assert svc["title"] != ""
        assert svc["description"] != ""

    def test_content_type_json(self, client: TestClient) -> None:
        resp = client.get("/cds-services")
        assert "application/json" in resp.headers["content-type"]


# ==================================================================
# POST /cds-services/triage-risk  (Service)
# ==================================================================
class TestTriageRiskEndpoint:
    def _payload(self, session_id: str = "abc-123") -> dict:
        return {
            "hookInstance": "d1577c69-dfbe-44ad-938d-e3903c811b71",
            "hook": "patient-view",
            "context": {"session_id": session_id},
        }

    def test_returns_200(self, client: TestClient) -> None:
        resp = client.post("/cds-services/triage-risk", json=self._payload())
        assert resp.status_code == 200

    def test_response_has_cards(self, client: TestClient) -> None:
        data = client.post(
            "/cds-services/triage-risk", json=self._payload()
        ).json()
        assert "cards" in data
        assert isinstance(data["cards"], list)
        assert len(data["cards"]) >= 1

    def test_card_has_required_fields(self, client: TestClient) -> None:
        data = client.post(
            "/cds-services/triage-risk", json=self._payload()
        ).json()
        card = data["cards"][0]
        assert "summary" in card
        assert "indicator" in card
        assert "source" in card
        assert card["indicator"] in ("info", "warning", "critical")

    def test_session_id_reflected(self, client: TestClient) -> None:
        data = client.post(
            "/cds-services/triage-risk",
            json=self._payload(session_id="my-session"),
        ).json()
        card = data["cards"][0]
        assert "my-session" in card["summary"]

    def test_missing_hook_instance_422(self, client: TestClient) -> None:
        resp = client.post(
            "/cds-services/triage-risk",
            json={"hook": "patient-view", "context": {"session_id": "x"}},
        )
        assert resp.status_code == 422

    def test_missing_context_422(self, client: TestClient) -> None:
        resp = client.post(
            "/cds-services/triage-risk",
            json={
                "hookInstance": "abc",
                "hook": "patient-view",
            },
        )
        assert resp.status_code == 422

    def test_missing_session_id_422(self, client: TestClient) -> None:
        resp = client.post(
            "/cds-services/triage-risk",
            json={
                "hookInstance": "abc",
                "hook": "patient-view",
                "context": {},
            },
        )
        assert resp.status_code == 422

    def test_optional_fhir_server(self, client: TestClient) -> None:
        payload = self._payload()
        payload["fhirServer"] = "https://fhir.example.com"
        resp = client.post("/cds-services/triage-risk", json=payload)
        assert resp.status_code == 200

    def test_optional_prefetch(self, client: TestClient) -> None:
        payload = self._payload()
        payload["prefetch"] = {"patient": "Patient/123"}
        resp = client.post("/cds-services/triage-risk", json=payload)
        assert resp.status_code == 200
