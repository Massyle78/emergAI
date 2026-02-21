"""Media upload API routes for video and audio intake capture."""

from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile

from app.models.enums import MediaType
from app.models.media import MediaUploadResponse
from app.services.media_service import MediaService
from app.utils.auth import AuthenticatedUser, get_current_user

router = APIRouter(prefix="/media", tags=["media"])


def _get_media_service(request: Request) -> MediaService:
    """Provide a MediaService instance from app settings."""
    return MediaService(request.app.state.settings)


@router.post("/video", status_code=201, response_model=MediaUploadResponse)
async def upload_video(
    session_id: UUID = Form(...),
    file: UploadFile = File(...),
    _user: AuthenticatedUser = Depends(get_current_user),
    service: MediaService = Depends(_get_media_service),
) -> MediaUploadResponse:
    """Upload a video file for rPPG vitals extraction."""
    return await service.process_upload(file, session_id, MediaType.VIDEO)


@router.post("/audio", status_code=201, response_model=MediaUploadResponse)
async def upload_audio(
    session_id: UUID = Form(...),
    file: UploadFile = File(...),
    _user: AuthenticatedUser = Depends(get_current_user),
    service: MediaService = Depends(_get_media_service),
) -> MediaUploadResponse:
    """Upload an audio file for Gemini symptom extraction."""
    return await service.process_upload(file, session_id, MediaType.AUDIO)
