"""Tests for patient CRUD API routes.

Uses dependency overrides to inject mocked repository and auth.
No real database or JWT verification calls.
"""

import time
from datetime import UTC, date, datetime
from uuid import uuid4

import jwt as pyjwt
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.models.patient import PatientRead
from app.repositories.patient_repository import (
    PatientRepository,
    get_patient_repository,
)
from app.services.supabase_client import get_supabase
from app.utils.auth import get_current_user, AuthenticatedUser

TEST_SECRET = "test-jwt-secret-for-unit-tests-32b"
TEST_USER_ID = uuid4()
SAMPLE_PATIENT_ID = uuid4()
NOW = datetime.now(UTC)

SAMPLE_PATIENT = PatientRead(
    id=SAMPLE_PATIENT_ID,
    first_name="Jane",
    last_name="Doe",
    date_of_birth=date(1990, 5, 15),
    created_at=NOW,
    updated_at=NOW,
)


def _make_token() -> str:
    """Create a valid test JWT."""
    payload = {
        "sub": str(TEST_USER_ID),
        "email": "test@example.com",
        "role": "authenticated",
        "exp": int(time.time()) + 3600,
    }
    return pyjwt.encode(payload, TEST_SECRET, algorithm="HS256")


def _auth_headers() -> dict:
    """Return Authorization headers with a valid test token."""
    return {"Authorization": f"Bearer {_make_token()}"}


class _MockRepo:
    """In-memory mock of PatientRepository for route testing."""

    def __init__(self):
        self.patients: dict = {SAMPLE_PATIENT_ID: SAMPLE_PATIENT}

    async def create(self, data):
        from app.models.patient import PatientRead

        patient = PatientRead(
            id=uuid4(),
            first_name=data.first_name,
            last_name=data.last_name,
            date_of_birth=data.date_of_birth,
            phone=data.phone,
            medical_record_number=data.medical_record_number,
            created_at=NOW,
            updated_at=NOW,
        )
        self.patients[patient.id] = patient
        return patient

    async def get_by_id(self, patient_id):
        from fastapi import HTTPException

        patient = self.patients.get(patient_id)
        if not patient:
            raise HTTPException(status_code=404, detail="Patient not found")
        return patient

    async def update(self, patient_id, data):
        from fastapi import HTTPException

        patient = self.patients.get(patient_id)
        if not patient:
            raise HTTPException(status_code=404, detail="Patient not found")
        updated = patient.model_copy(update=data)
        self.patients[patient_id] = updated
        return updated

    async def list_all(self, limit=20, offset=0):
        all_patients = list(self.patients.values())
        return all_patients[offset : offset + limit]


def _create_test_client() -> TestClient:
    """Build a TestClient with mocked dependencies."""
    settings = Settings(app_env="testing", supabase_jwt_secret=TEST_SECRET)
    application = create_app(settings=settings)

    mock_repo = _MockRepo()

    application.dependency_overrides[get_patient_repository] = lambda: mock_repo
    application.dependency_overrides[get_supabase] = lambda: None

    return TestClient(application, raise_server_exceptions=False)


class TestCreatePatient:
    def test_returns_201_on_success(self):
        client = _create_test_client()
        response = client.post(
            "/api/v1/patients",
            json={
                "first_name": "John",
                "last_name": "Smith",
                "date_of_birth": "1985-03-20",
            },
            headers=_auth_headers(),
        )
        assert response.status_code == 201
        data = response.json()
        assert data["first_name"] == "John"
        assert "id" in data

    def test_returns_401_without_auth(self):
        client = _create_test_client()
        response = client.post(
            "/api/v1/patients",
            json={
                "first_name": "John",
                "last_name": "Smith",
                "date_of_birth": "1985-03-20",
            },
        )
        assert response.status_code == 401

    def test_returns_422_with_invalid_body(self):
        client = _create_test_client()
        response = client.post(
            "/api/v1/patients",
            json={"first_name": ""},
            headers=_auth_headers(),
        )
        assert response.status_code == 422


class TestGetPatient:
    def test_returns_200_when_found(self):
        client = _create_test_client()
        response = client.get(
            f"/api/v1/patients/{SAMPLE_PATIENT_ID}",
            headers=_auth_headers(),
        )
        assert response.status_code == 200
        assert response.json()["first_name"] == "Jane"

    def test_returns_404_when_not_found(self):
        client = _create_test_client()
        response = client.get(
            f"/api/v1/patients/{uuid4()}",
            headers=_auth_headers(),
        )
        assert response.status_code == 404

    def test_returns_401_without_auth(self):
        client = _create_test_client()
        response = client.get(f"/api/v1/patients/{SAMPLE_PATIENT_ID}")
        assert response.status_code == 401


class TestUpdatePatient:
    def test_returns_200_on_success(self):
        client = _create_test_client()
        response = client.patch(
            f"/api/v1/patients/{SAMPLE_PATIENT_ID}",
            json={
                "first_name": "Janet",
                "last_name": "Doe",
                "date_of_birth": "1990-05-15",
            },
            headers=_auth_headers(),
        )
        assert response.status_code == 200
        assert response.json()["first_name"] == "Janet"

    def test_returns_404_when_not_found(self):
        client = _create_test_client()
        response = client.patch(
            f"/api/v1/patients/{uuid4()}",
            json={
                "first_name": "Janet",
                "last_name": "Doe",
                "date_of_birth": "1990-05-15",
            },
            headers=_auth_headers(),
        )
        assert response.status_code == 404


class TestListPatients:
    def test_returns_200_with_list(self):
        client = _create_test_client()
        response = client.get(
            "/api/v1/patients",
            headers=_auth_headers(),
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1

    def test_returns_401_without_auth(self):
        client = _create_test_client()
        response = client.get("/api/v1/patients")
        assert response.status_code == 401

    def test_accepts_pagination_params(self):
        client = _create_test_client()
        response = client.get(
            "/api/v1/patients?limit=5&offset=0",
            headers=_auth_headers(),
        )
        assert response.status_code == 200

    def test_rejects_invalid_limit(self):
        client = _create_test_client()
        response = client.get(
            "/api/v1/patients?limit=0",
            headers=_auth_headers(),
        )
        assert response.status_code == 422

    def test_rejects_negative_offset(self):
        client = _create_test_client()
        response = client.get(
            "/api/v1/patients?offset=-1",
            headers=_auth_headers(),
        )
        assert response.status_code == 422
