"""Unit tests for the open-rppg vitals extraction service.

Uses real rppg.Model and real video files generated via OpenCV.
The model fixture is session-scoped so ONNX weights load only once.
"""

from pathlib import Path
from uuid import uuid4

import cv2
import numpy as np
import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from rppg import Model as RppgModel

from app.config import Settings
from app.models.vitals import VitalsCreate
from app.services.vitals_service import (
    LowQualitySignalError,
    NoFaceDetectedError,
    VitalsExtractionError,
    VitalsService,
    _check_signal_quality,
    _create_rppg_model,
    _extract_confidence,
    _extract_heart_rate,
    _validate_video_path,
    get_vitals_service,
)


SESSION_ID = uuid4()


def _settings(**overrides: object) -> Settings:
    defaults: dict[str, object] = {
        "rppg_model_name": "FacePhys.rlap",
        "min_signal_quality": 0.3,
    }
    defaults.update(overrides)
    return Settings(**defaults)  # type: ignore[arg-type]


def _write_black_video(path: Path, frames: int = 60, fps: int = 30) -> Path:
    """Create a minimal black video with no face (2 seconds at 30 fps)."""
    h, w = 240, 320
    fourcc = cv2.VideoWriter.fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(path), fourcc, fps, (w, h))
    for _ in range(frames):
        writer.write(np.zeros((h, w, 3), dtype=np.uint8))
    writer.release()
    return path


# ---------------------------------------------------------------------------
# _validate_video_path
# ---------------------------------------------------------------------------
class TestValidateVideoPath:
    def test_existing_file_passes(self, tmp_path: Path) -> None:
        video = tmp_path / "test.mp4"
        video.write_bytes(b"\x00")
        _validate_video_path(video)

    def test_missing_file_raises(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError, match="not found"):
            _validate_video_path(tmp_path / "missing.mp4")

    def test_directory_raises(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="not a file"):
            _validate_video_path(tmp_path)


# ---------------------------------------------------------------------------
# _extract_heart_rate
# ---------------------------------------------------------------------------
class TestExtractHeartRate:
    def test_valid_hr(self) -> None:
        assert _extract_heart_rate({"hr": 72.5}) == 72.5

    def test_none_result_raises(self) -> None:
        with pytest.raises(NoFaceDetectedError, match="No heart rate"):
            _extract_heart_rate(None)

    def test_none_hr_value_raises(self) -> None:
        with pytest.raises(NoFaceDetectedError, match="No heart rate"):
            _extract_heart_rate({"hr": None, "SQI": 0.5})

    def test_integer_hr_converted_to_float(self) -> None:
        result = _extract_heart_rate({"hr": 80})
        assert result == 80.0
        assert isinstance(result, float)


# ---------------------------------------------------------------------------
# _extract_confidence
# ---------------------------------------------------------------------------
class TestExtractConfidence:
    def test_normal_sqi(self) -> None:
        assert _extract_confidence({"SQI": 0.75}) == 0.75

    def test_missing_sqi_returns_zero(self) -> None:
        assert _extract_confidence({}) == 0.0

    def test_none_sqi_returns_zero(self) -> None:
        assert _extract_confidence({"SQI": None}) == 0.0

    def test_above_one_clamped(self) -> None:
        assert _extract_confidence({"SQI": 1.5}) == 1.0

    def test_below_zero_clamped(self) -> None:
        assert _extract_confidence({"SQI": -0.3}) == 0.0


# ---------------------------------------------------------------------------
# _check_signal_quality
# ---------------------------------------------------------------------------
class TestCheckSignalQuality:
    def test_above_threshold_passes(self) -> None:
        _check_signal_quality(0.8, threshold=0.3)

    def test_at_threshold_passes(self) -> None:
        _check_signal_quality(0.3, threshold=0.3)

    def test_below_threshold_raises(self) -> None:
        with pytest.raises(LowQualitySignalError, match="below threshold"):
            _check_signal_quality(0.1, threshold=0.3)


# ---------------------------------------------------------------------------
# _create_rppg_model (real import, real model)
# ---------------------------------------------------------------------------
class TestCreateRppgModel:
    def test_returns_real_rppg_model(self) -> None:
        model = _create_rppg_model("FacePhys.rlap")
        assert isinstance(model, RppgModel)

    def test_invalid_model_name_raises(self) -> None:
        with pytest.raises(ValueError, match="Invalid value"):
            _create_rppg_model("NonExistent.model")


# ---------------------------------------------------------------------------
# VitalsService – lazy model init (real model)
# ---------------------------------------------------------------------------
class TestVitalsServiceInit:
    def test_model_not_loaded_at_construction(self) -> None:
        svc = VitalsService(_settings())
        assert svc._model is None

    def test_model_loaded_on_first_get(self) -> None:
        svc = VitalsService(_settings())
        model = svc._get_model()
        assert isinstance(model, RppgModel)

    def test_model_cached_after_first_get(self) -> None:
        svc = VitalsService(_settings())
        first = svc._get_model()
        second = svc._get_model()
        assert first is second


# ---------------------------------------------------------------------------
# VitalsService._build_vitals (data mapping, no model needed)
# ---------------------------------------------------------------------------
class TestBuildVitals:
    def test_maps_valid_result_to_vitals_create(self) -> None:
        svc = VitalsService(_settings())
        result = {"hr": 78.0, "SQI": 0.85, "hrv": {}, "latency": 0.1}
        vitals = svc._build_vitals(result, SESSION_ID)

        assert isinstance(vitals, VitalsCreate)
        assert vitals.session_id == SESSION_ID
        assert vitals.heart_rate_bpm == 78.0
        assert vitals.confidence == 0.85

    def test_optional_fields_default_to_none(self) -> None:
        svc = VitalsService(_settings())
        result = {"hr": 72.0, "SQI": 0.9}
        vitals = svc._build_vitals(result, SESSION_ID)

        assert vitals.spo2_percent is None
        assert vitals.respiratory_rate is None
        assert vitals.blood_pressure is None

    def test_low_sqi_rejected(self) -> None:
        svc = VitalsService(_settings(min_signal_quality=0.5))
        result = {"hr": 70.0, "SQI": 0.45}
        with pytest.raises(LowQualitySignalError):
            svc._build_vitals(result, SESSION_ID)

    def test_none_hr_rejected(self) -> None:
        svc = VitalsService(_settings())
        result = {"hr": None, "SQI": 0.8}
        with pytest.raises(NoFaceDetectedError, match="No heart rate"):
            svc._build_vitals(result, SESSION_ID)

    def test_custom_threshold_respected(self) -> None:
        result = {"hr": 70.0, "SQI": 0.45}

        strict = VitalsService(_settings(min_signal_quality=0.5))
        with pytest.raises(LowQualitySignalError):
            strict._build_vitals(result, SESSION_ID)

        lenient = VitalsService(_settings(min_signal_quality=0.4))
        vitals = lenient._build_vitals(result, SESSION_ID)
        assert vitals.heart_rate_bpm == 70.0


# ---------------------------------------------------------------------------
# VitalsService.extract_vitals – path validation (no model needed)
# ---------------------------------------------------------------------------
class TestExtractVitalsPathValidation:
    def test_missing_file_raises(self, tmp_path: Path) -> None:
        svc = VitalsService(_settings())
        with pytest.raises(FileNotFoundError):
            svc.extract_vitals(tmp_path / "nope.mp4", SESSION_ID)

    def test_directory_path_raises(self, tmp_path: Path) -> None:
        svc = VitalsService(_settings())
        with pytest.raises(ValueError, match="not a file"):
            svc.extract_vitals(tmp_path, SESSION_ID)


# ---------------------------------------------------------------------------
# VitalsService.extract_vitals – real model + real video
# ---------------------------------------------------------------------------
class TestExtractVitalsWithRealModel:
    def test_no_face_video_raises(self, tmp_path: Path) -> None:
        """A solid-black video has no face → NoFaceDetectedError or LowQualitySignalError."""
        video = _write_black_video(tmp_path / "black.mp4")
        svc = VitalsService(_settings())
        with pytest.raises(VitalsExtractionError):
            svc.extract_vitals(video, SESSION_ID)

    def test_corrupt_file_raises(self, tmp_path: Path) -> None:
        """Random bytes are not a valid video container."""
        corrupt = tmp_path / "corrupt.mp4"
        corrupt.write_bytes(b"\x00\x01\x02\x03" * 256)
        svc = VitalsService(_settings())
        with pytest.raises(VitalsExtractionError):
            svc.extract_vitals(corrupt, SESSION_ID)


# ---------------------------------------------------------------------------
# VitalsService._run_extraction – error wrapping
# ---------------------------------------------------------------------------
class TestRunExtraction:
    def test_corrupt_video_wrapped_as_extraction_error(
        self, tmp_path: Path
    ) -> None:
        corrupt = tmp_path / "bad.mp4"
        corrupt.write_bytes(b"\xff" * 100)
        svc = VitalsService(_settings())
        with pytest.raises(VitalsExtractionError):
            svc._run_extraction(corrupt)

    def test_empty_video_raises(self, tmp_path: Path) -> None:
        """A video container with zero decodable frames."""
        empty = tmp_path / "empty.mp4"
        fourcc = cv2.VideoWriter.fourcc(*"mp4v")
        writer = cv2.VideoWriter(str(empty), fourcc, 30, (320, 240))
        writer.release()
        svc = VitalsService(_settings())
        with pytest.raises(VitalsExtractionError):
            svc._run_extraction(empty)


# ---------------------------------------------------------------------------
# get_vitals_service – real FastAPI dependency injection
# ---------------------------------------------------------------------------
class TestGetVitalsServiceDependency:
    def test_dependency_provides_vitals_service(self) -> None:
        app = FastAPI()
        app.state.settings = _settings()

        @app.get("/test-dep")
        def _endpoint(
            svc: VitalsService = Depends(get_vitals_service),
        ) -> dict[str, str]:
            return {"service_type": type(svc).__name__}

        client = TestClient(app)
        resp = client.get("/test-dep")
        assert resp.status_code == 200
        assert resp.json()["service_type"] == "VitalsService"


# ---------------------------------------------------------------------------
# Error hierarchy
# ---------------------------------------------------------------------------
class TestErrorHierarchy:
    def test_no_face_is_extraction_error(self) -> None:
        assert issubclass(NoFaceDetectedError, VitalsExtractionError)

    def test_low_quality_is_extraction_error(self) -> None:
        assert issubclass(LowQualitySignalError, VitalsExtractionError)

    def test_base_is_exception(self) -> None:
        assert issubclass(VitalsExtractionError, Exception)
