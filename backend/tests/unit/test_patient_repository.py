"""Tests for PatientRepository with fully mocked Supabase client.

No real database calls — the postgrest builder chain is mocked.
"""

from datetime import UTC, date, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.models.patient import PatientCreate, PatientRead
from app.repositories.patient_repository import PatientRepository

SAMPLE_ID = uuid4()
NOW = datetime.now(UTC)

SAMPLE_ROW = {
    "id": str(SAMPLE_ID),
    "first_name": "Jane",
    "last_name": "Doe",
    "date_of_birth": "1990-05-15",
    "phone": None,
    "medical_record_number": None,
    "created_at": NOW.isoformat(),
    "updated_at": NOW.isoformat(),
}


def _mock_client() -> AsyncMock:
    """Create a mock Supabase client with a chainable table builder."""
    client = AsyncMock()
    return client


def _setup_chain(client: AsyncMock, response_data):
    """Configure the mock builder chain to return given data."""
    mock_response = MagicMock()
    mock_response.data = response_data

    builder = MagicMock()
    builder.insert = MagicMock(return_value=builder)
    builder.select = MagicMock(return_value=builder)
    builder.update = MagicMock(return_value=builder)
    builder.eq = MagicMock(return_value=builder)
    builder.order = MagicMock(return_value=builder)
    builder.range = MagicMock(return_value=builder)
    builder.maybe_single = MagicMock(return_value=builder)
    builder.execute = AsyncMock(return_value=mock_response)

    client.table = MagicMock(return_value=builder)
    return builder


class TestPatientRepositoryCreate:
    @pytest.mark.asyncio
    async def test_creates_and_returns_patient(self):
        client = _mock_client()
        _setup_chain(client, [SAMPLE_ROW])
        repo = PatientRepository(client)

        result = await repo.create(
            PatientCreate(
                first_name="Jane",
                last_name="Doe",
                date_of_birth=date(1990, 5, 15),
            )
        )
        assert isinstance(result, PatientRead)
        assert result.first_name == "Jane"
        client.table.assert_called_with("patients")


class TestPatientRepositoryGetById:
    @pytest.mark.asyncio
    async def test_returns_patient_when_found(self):
        client = _mock_client()
        _setup_chain(client, SAMPLE_ROW)
        repo = PatientRepository(client)

        result = await repo.get_by_id(SAMPLE_ID)
        assert isinstance(result, PatientRead)
        assert str(result.id) == str(SAMPLE_ID)

    @pytest.mark.asyncio
    async def test_raises_404_when_not_found(self):
        client = _mock_client()
        _setup_chain(client, None)
        repo = PatientRepository(client)

        with pytest.raises(HTTPException) as exc_info:
            await repo.get_by_id(uuid4())
        assert exc_info.value.status_code == 404


class TestPatientRepositoryUpdate:
    @pytest.mark.asyncio
    async def test_updates_and_returns_patient(self):
        client = _mock_client()
        updated_row = {**SAMPLE_ROW, "first_name": "Janet"}
        _setup_chain(client, [updated_row])
        repo = PatientRepository(client)

        result = await repo.update(SAMPLE_ID, {"first_name": "Janet"})
        assert result.first_name == "Janet"

    @pytest.mark.asyncio
    async def test_raises_404_when_not_found(self):
        client = _mock_client()
        _setup_chain(client, [])
        repo = PatientRepository(client)

        with pytest.raises(HTTPException) as exc_info:
            await repo.update(uuid4(), {"first_name": "Janet"})
        assert exc_info.value.status_code == 404


class TestPatientRepositoryListAll:
    @pytest.mark.asyncio
    async def test_returns_list_of_patients(self):
        client = _mock_client()
        _setup_chain(client, [SAMPLE_ROW, SAMPLE_ROW])
        repo = PatientRepository(client)

        results = await repo.list_all()
        assert len(results) == 2
        assert all(isinstance(r, PatientRead) for r in results)

    @pytest.mark.asyncio
    async def test_returns_empty_list(self):
        client = _mock_client()
        _setup_chain(client, [])
        repo = PatientRepository(client)

        results = await repo.list_all()
        assert results == []

    @pytest.mark.asyncio
    async def test_passes_pagination_params(self):
        client = _mock_client()
        builder = _setup_chain(client, [])
        repo = PatientRepository(client)

        await repo.list_all(limit=10, offset=20)
        builder.range.assert_called_once_with(20, 29)
