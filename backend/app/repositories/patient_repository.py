"""Patient data access layer using Supabase postgrest client.

Implements the repository pattern to isolate data access from
business logic. All methods accept and return Pydantic models.
"""

import logging
from uuid import UUID

from fastapi import Depends, HTTPException
from supabase import AsyncClient

from app.models.patient import PatientCreate, PatientRead
from app.services.supabase_client import get_supabase

logger = logging.getLogger("app.repositories.patient")

_TABLE = "patients"


class PatientRepository:
    """CRUD operations for the patients table."""

    def __init__(self, client: AsyncClient) -> None:
        self._client = client

    async def create(self, data: PatientCreate) -> PatientRead:
        """Insert a new patient record and return the created row."""
        response = await (
            self._client.table(_TABLE)
            .insert(data.model_dump(mode="json"))
            .execute()
        )
        return PatientRead.model_validate(response.data[0])

    async def get_by_id(self, patient_id: UUID) -> PatientRead:
        """Fetch a single patient by primary key.

        Raises:
            HTTPException: 404 if no patient found with this ID.
        """
        response = await (
            self._client.table(_TABLE)
            .select("*")
            .eq("id", str(patient_id))
            .maybe_single()
            .execute()
        )
        if response.data is None:
            raise HTTPException(status_code=404, detail="Patient not found")
        return PatientRead.model_validate(response.data)

    async def update(self, patient_id: UUID, data: dict) -> PatientRead:
        """Update a patient record by primary key.

        Raises:
            HTTPException: 404 if no patient found with this ID.
        """
        response = await (
            self._client.table(_TABLE)
            .update(data)
            .eq("id", str(patient_id))
            .execute()
        )
        if not response.data:
            raise HTTPException(status_code=404, detail="Patient not found")
        return PatientRead.model_validate(response.data[0])

    async def list_all(self, limit: int = 100, offset: int = 0) -> list[PatientRead]:
        """Fetch a paginated list of patients ordered by creation date."""
        response = await (
            self._client.table(_TABLE)
            .select("*")
            .order("created_at", desc=True)
            .range(offset, offset + limit - 1)
            .execute()
        )
        return [PatientRead.model_validate(row) for row in response.data]


async def get_patient_repository(
    client: AsyncClient = Depends(get_supabase),
) -> PatientRepository:
    """FastAPI dependency that provides a PatientRepository instance."""
    return PatientRepository(client)
