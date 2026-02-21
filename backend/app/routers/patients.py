"""Patient CRUD API routes.

All routes require JWT authentication via the get_current_user dependency.
Data access is delegated to PatientRepository via dependency injection.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.models.patient import PatientCreate, PatientRead
from app.repositories.patient_repository import (
    PatientRepository,
    get_patient_repository,
)
from app.utils.auth import AuthenticatedUser, get_current_user

router = APIRouter(prefix="/patients", tags=["patients"])

_MAX_PAGE_SIZE = 100


@router.post("", status_code=201, response_model=PatientRead)
async def create_patient(
    body: PatientCreate,
    _user: AuthenticatedUser = Depends(get_current_user),
    repo: PatientRepository = Depends(get_patient_repository),
) -> PatientRead:
    """Register a new patient at intake."""
    return await repo.create(body)


@router.get("/{patient_id}", response_model=PatientRead)
async def get_patient(
    patient_id: UUID,
    _user: AuthenticatedUser = Depends(get_current_user),
    repo: PatientRepository = Depends(get_patient_repository),
) -> PatientRead:
    """Retrieve a single patient by ID."""
    return await repo.get_by_id(patient_id)


@router.patch("/{patient_id}", response_model=PatientRead)
async def update_patient(
    patient_id: UUID,
    body: PatientCreate,
    _user: AuthenticatedUser = Depends(get_current_user),
    repo: PatientRepository = Depends(get_patient_repository),
) -> PatientRead:
    """Update an existing patient record."""
    update_data = body.model_dump(exclude_unset=True, mode="json")
    return await repo.update(patient_id, update_data)


@router.get("", response_model=list[PatientRead])
async def list_patients(
    _user: AuthenticatedUser = Depends(get_current_user),
    repo: PatientRepository = Depends(get_patient_repository),
    limit: int = Query(default=20, ge=1, le=_MAX_PAGE_SIZE),
    offset: int = Query(default=0, ge=0),
) -> list[PatientRead]:
    """List patients with pagination."""
    return await repo.list_all(limit=limit, offset=offset)
