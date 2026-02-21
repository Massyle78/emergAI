"""Load test scaffolding for the emergAI backend.

Run with:
    pip install locust
    locust -f tests/load/locustfile.py --host http://localhost:8000

Scenarios exercise the most common API paths under load:
  1. Health check (baseline)
  2. CDS Hooks discovery
  3. CDS Hooks service invocation
  4. Patient CRUD (requires auth setup)
"""

import uuid

try:
    from locust import HttpUser, between, task
except ImportError:
    import sys
    print("locust is not installed. Install with: pip install locust", file=sys.stderr)
    raise SystemExit(1)


class HealthCheckUser(HttpUser):
    """Baseline load test hitting the health endpoint."""

    wait_time = between(0.5, 2)
    weight = 3

    @task
    def health(self):
        self.client.get("/health")


class CdsHooksUser(HttpUser):
    """Simulates an EHR system querying CDS Hooks."""

    wait_time = between(1, 3)
    weight = 5

    @task(3)
    def discover(self):
        self.client.get("/cds-services")

    @task(7)
    def invoke_triage(self):
        self.client.post(
            "/cds-services/triage-risk",
            json={
                "hookInstance": str(uuid.uuid4()),
                "hook": "patient-view",
                "context": {"session_id": str(uuid.uuid4())},
            },
        )


class PatientApiUser(HttpUser):
    """Simulates authenticated patient CRUD operations.

    Requires AUTH_TOKEN environment variable to be set with a valid JWT.
    Falls back to unauthenticated calls (will get 401s) for scaffolding.
    """

    wait_time = between(1, 5)
    weight = 2

    def on_start(self):
        import os
        token = os.environ.get("AUTH_TOKEN", "")
        self.auth_headers = {"Authorization": f"Bearer {token}"} if token else {}

    @task(5)
    def list_patients(self):
        self.client.get(
            "/api/v1/patients",
            headers=self.auth_headers,
        )

    @task(2)
    def create_patient(self):
        self.client.post(
            "/api/v1/patients",
            json={
                "first_name": f"Load-{uuid.uuid4().hex[:6]}",
                "last_name": "Test",
                "date_of_birth": "1990-01-01",
            },
            headers=self.auth_headers,
        )
