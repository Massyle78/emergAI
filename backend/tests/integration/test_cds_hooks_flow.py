"""Integration test: CDS Hooks discovery and service invocation.

Exercises the full CDS Hooks 2.0 flow:
  1. Discover available services
  2. Invoke the triage-risk service
  3. Verify response structure conforms to spec
"""

from uuid import uuid4


class TestCdsHooksDiscoveryAndService:
    def test_discovery_returns_triage_service(self, client):
        resp = client.get("/cds-services")
        assert resp.status_code == 200
        body = resp.json()
        assert "services" in body
        services = body["services"]
        assert len(services) >= 1
        svc = services[0]
        assert svc["id"] == "triage-risk"
        assert svc["hook"] == "patient-view"
        assert svc["title"] != ""

    def test_triage_service_returns_cards(self, client):
        resp = client.post(
            "/cds-services/triage-risk",
            json={
                "hookInstance": str(uuid4()),
                "hook": "patient-view",
                "context": {"session_id": str(uuid4())},
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "cards" in body
        assert len(body["cards"]) >= 1

    def test_card_has_required_fields(self, client):
        resp = client.post(
            "/cds-services/triage-risk",
            json={
                "hookInstance": str(uuid4()),
                "hook": "patient-view",
                "context": {"session_id": str(uuid4())},
            },
        )
        card = resp.json()["cards"][0]
        assert "summary" in card
        assert "indicator" in card
        assert card["indicator"] in ("info", "warning", "critical")
        assert "source" in card
        assert "label" in card["source"]

    def test_rejects_missing_hook_instance(self, client):
        resp = client.post(
            "/cds-services/triage-risk",
            json={
                "hook": "patient-view",
                "context": {"session_id": str(uuid4())},
            },
        )
        assert resp.status_code == 422

    def test_rejects_missing_context(self, client):
        resp = client.post(
            "/cds-services/triage-risk",
            json={
                "hookInstance": str(uuid4()),
                "hook": "patient-view",
            },
        )
        assert resp.status_code == 422

    def test_discovery_and_invoke_flow(self, client):
        """End-to-end: discover → pick service → invoke."""
        disc = client.get("/cds-services")
        assert disc.status_code == 200
        service_id = disc.json()["services"][0]["id"]

        invoke = client.post(
            f"/cds-services/{service_id}",
            json={
                "hookInstance": str(uuid4()),
                "hook": "patient-view",
                "context": {"session_id": str(uuid4())},
            },
        )
        assert invoke.status_code == 200
        assert len(invoke.json()["cards"]) >= 1
