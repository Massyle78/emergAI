"""Service wrapper around open-rppg for contactless vitals extraction.

Lazily initializes the rPPG model on first use to avoid loading heavy
ONNX weights at import time. Processes a video file and maps the raw
heart-rate / SQI output to a validated VitalsCreate schema.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any
from uuid import UUID

from fastapi import Request

from app.config import Settings
from app.models.vitals import VitalsCreate

logger = logging.getLogger("app.services.vitals")


class VitalsExtractionError(Exception):
    """Base error for vitals extraction failures."""


class NoFaceDetectedError(VitalsExtractionError):
    """No face was detected in the video, so HR cannot be derived."""


class LowQualitySignalError(VitalsExtractionError):
    """Signal quality is below the configured threshold."""


def _create_rppg_model(model_name: str) -> Any:
    """Import and instantiate an rppg Model.

    Isolated to keep the heavy import out of module-level scope and
    to make unit-test patching straightforward.
    """
    from rppg import Model  # noqa: WPS433 (nested import by design)

    return Model(model=model_name)


def _validate_video_path(video_path: Path) -> None:
    """Ensure the video file exists and is a regular file."""
    if not video_path.exists():
        raise FileNotFoundError(f"Video file not found: {video_path}")
    if not video_path.is_file():
        raise ValueError(f"Path is not a file: {video_path}")


def _extract_heart_rate(result: dict[str, Any] | None) -> float:
    """Pull heart rate (bpm) from the rppg result dict.

    Raises:
        NoFaceDetectedError: When the model returns None / no HR.
    """
    if result is None or result.get("hr") is None:
        raise NoFaceDetectedError("No heart rate detected in video")
    return float(result["hr"])


def _extract_confidence(result: dict[str, Any]) -> float:
    """Clamp the Signal Quality Index (SQI) to [0, 1]."""
    sqi = result.get("SQI")
    if sqi is None:
        return 0.0
    return max(0.0, min(1.0, float(sqi)))


def _check_signal_quality(confidence: float, threshold: float) -> None:
    """Reject readings whose SQI falls below *threshold*.

    Raises:
        LowQualitySignalError: When confidence < threshold.
    """
    if confidence < threshold:
        raise LowQualitySignalError(
            f"Signal quality {confidence:.2f} below threshold {threshold}"
        )


class VitalsService:
    """Extract heart-rate vitals from video using open-rppg.

    The underlying ONNX model is loaded lazily on the first call to
    ``extract_vitals`` so application startup remains fast.

    Time complexity: O(N) where N = number of video frames.
    Memory: proportional to the model weights (~50 MB) + frame buffer.
    """

    def __init__(self, settings: Settings) -> None:
        self._model_name = settings.rppg_model_name
        self._min_sqi = settings.min_signal_quality
        self._model: Any | None = None

    def _get_model(self) -> Any:
        """Return the rppg Model, creating it on first access."""
        if self._model is None:
            logger.info("Initializing rppg model: %s", self._model_name)
            self._model = _create_rppg_model(self._model_name)
        return self._model

    def extract_vitals(self, video_path: Path, session_id: UUID) -> VitalsCreate:
        """Extract heart-rate vitals from a video file.

        Args:
            video_path: Path to the uploaded video.
            session_id: Triage session this reading belongs to.

        Returns:
            A validated VitalsCreate with heart_rate_bpm and confidence.

        Raises:
            FileNotFoundError: Video file does not exist.
            NoFaceDetectedError: No face / HR could be extracted.
            LowQualitySignalError: SQI below configured threshold.
            VitalsExtractionError: Any other processing failure.
        """
        _validate_video_path(video_path)
        result = self._run_extraction(video_path)
        return self._build_vitals(result, session_id)

    def _run_extraction(self, video_path: Path) -> dict[str, Any]:
        """Invoke the rppg model on the given video file."""
        model = self._get_model()
        try:
            result = model.process_video(str(video_path))
        except VitalsExtractionError:
            raise
        except Exception as exc:
            raise VitalsExtractionError(
                f"rPPG processing failed: {exc}"
            ) from exc
        if result is None:
            raise NoFaceDetectedError("rPPG returned no result")
        return result

    def _build_vitals(
        self, result: dict[str, Any], session_id: UUID
    ) -> VitalsCreate:
        """Map raw rppg output to a validated VitalsCreate."""
        heart_rate = _extract_heart_rate(result)
        confidence = _extract_confidence(result)
        _check_signal_quality(confidence, self._min_sqi)

        logger.info(
            "Extracted HR=%.1f bpm (SQI=%.2f) for session %s",
            heart_rate,
            confidence,
            session_id,
        )

        return VitalsCreate(
            session_id=session_id,
            heart_rate_bpm=heart_rate,
            confidence=confidence,
        )


def get_vitals_service(request: Request) -> VitalsService:
    """FastAPI dependency that provides a VitalsService instance."""
    settings: Settings = request.app.state.settings
    return VitalsService(settings=settings)
