"""Integration test: full patient CRUD lifecycle.

Exercises create → get → update → list in a single flow to verify
the complete request/response chain through all middleware layers.
"""

from datetime import date
from uuid import uuid4

from app.models.patient import PatientRead
from app.repositories.patient_repository import get_patient_repository

from tests.conftest import auth_headers

_PATIENT_BODY = {
    "first_name": "Integration",
    "last_name": "Test",
    "date_of_birth": "1980-01-15",
}


class _InMemoryRepo:
    """Minimal in-memory patient repository for integration tests."""

    def __init__(self):
        self._store: dict = {}

    async def create(self, data):
        from datetime import UTC, datetime
        patient = PatientRead(
            id=uuid4(),
            first_name=data.first_name,
            last_name=data.last_name,
            date_of_birth=data.date_of_birth,
            phone=data.phone,
            medical_record_number=data.medical_record_number,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        self._store[patient.id] = patient
        return patient

    async def get_by_id(self, patient_id):
        from fastapi import HTTPException
        p = self._store.get(patient_id)
        if not p:
            raise HTTPException(status_code=404, detail="Patient not found")
        return p

    async def update(self, patient_id, data):
        from fastapi import HTTPException
        p = self._store.get(patient_id)
        if not p:
            raise HTTPException(status_code=404, detail="Patient not found")
        updated = p.model_copy(update=data)
        self._store[patient_id] = updated
        return updated

    async def list_all(self, limit=20, offset=0):
        items = list(self._store.values())
        return items[offset: offset + limit]


class TestPatientCRUDFlow:
    """Full lifecycle: create → get → update → list."""

    def test_full_crud_lifecycle(self, app, client):
        repo = _InMemoryRepo()
        app.dependency_overrides[get_patient_repository] = lambda: repo
        headers = auth_headers()

        # Create
        resp = client.post("/api/v1/patients", json=_PATIENT_BODY, headers=headers)
        assert resp.status_code == 201
        created = resp.json()
        pid = created["id"]
        assert created["first_name"] == "Integration"

        # Get
        resp = client.get(f"/api/v1/patients/{pid}", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["last_name"] == "Test"

        # Update
        resp = client.patch(
            f"/api/v1/patients/{pid}",
            json={**_PATIENT_BODY, "first_name": "Updated"},
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["first_name"] == "Updated"

        # List
        resp = client.get("/api/v1/patients", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["first_name"] == "Updated"

    def test_get_nonexistent_returns_404(self, app, client):
        repo = _InMemoryRepo()
        app.dependency_overrides[get_patient_repository] = lambda: repo
        headers = auth_headers()

        resp = client.get(f"/api/v1/patients/{uuid4()}", headers=headers)
        assert resp.status_code == 404

    def test_pagination_works(self, app, client):
        repo = _InMemoryRepo()
        app.dependency_overrides[get_patient_repository] = lambda: repo
        headers = auth_headers()

        for i in range(5):
            body = {**_PATIENT_BODY, "first_name": f"Patient{i}"}
            client.post("/api/v1/patients", json=body, headers=headers)

        resp = client.get("/api/v1/patients?limit=2&offset=0", headers=headers)
        assert resp.status_code == 200
        assert len(resp.json()) == 2

        resp = client.get("/api/v1/patients?limit=2&offset=3", headers=headers)
        assert resp.status_code == 200
        assert len(resp.json()) == 2
