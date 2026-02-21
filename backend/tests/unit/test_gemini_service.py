"""Unit tests for the Gemini multimodal inference service.

Pure-logic helpers are tested with real data (no mocks).
API-calling tests are marked ``integration`` and skipped when
GOOGLE_GENAI_API_KEY is not set.
"""

import json
import os
from pathlib import Path
from uuid import uuid4

import pytest
from google import genai

from app.config import Settings
from app.models.enums import SymptomSeverity
from app.models.symptoms import SymptomExtractionCreate
from app.services.gemini_service import (
    SYSTEM_PROMPT,
    GeminiExtractionError,
    GeminiResponseParseError,
    GeminiService,
    _GeminiResponse,
    _GeminiSymptom,
    build_user_prompt,
    get_response_schema,
    map_severity,
    map_to_extraction,
    parse_gemini_response,
)

SESSION_ID = uuid4()

HAS_API_KEY = bool(os.environ.get("GOOGLE_GENAI_API_KEY"))
skip_no_key = pytest.mark.skipif(
    not HAS_API_KEY, reason="GOOGLE_GENAI_API_KEY not set"
)


def _settings(**overrides: object) -> Settings:
    defaults: dict[str, object] = {
        "google_genai_api_key": os.environ.get("GOOGLE_GENAI_API_KEY", "test-key"),
        "gemini_model": "gemini-2.5-pro",
        "gemini_max_retries": 2,
        "gemini_retry_wait_seconds": 1,
        "gemini_temperature": 0.2,
    }
    defaults.update(overrides)
    return Settings(**defaults)  # type: ignore[arg-type]


def _valid_response_dict(**overrides: object) -> dict:
    base = {
        "chief_complaint": "Severe chest pain radiating to left arm",
        "symptoms": [
            {
                "name": "chest pain",
                "severity": "severe",
                "description": "Sharp, radiating to left arm",
                "body_region": "chest",
                "onset_description": "30 minutes ago",
            },
            {
                "name": "shortness of breath",
                "severity": "moderate",
                "description": "Difficulty breathing at rest",
                "body_region": "respiratory",
                "onset_description": "20 minutes ago",
            },
        ],
        "follow_up_questions": [
            "Do you have a history of heart disease?",
            "Are you currently on any medications?",
        ],
        "confidence": 0.85,
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# SYSTEM_PROMPT
# ---------------------------------------------------------------------------
class TestSystemPrompt:
    def test_prompt_contains_triage_context(self) -> None:
        assert "triage" in SYSTEM_PROMPT.lower()

    def test_prompt_mentions_severity_levels(self) -> None:
        for level in ("mild", "moderate", "severe", "critical"):
            assert level in SYSTEM_PROMPT

    def test_prompt_requests_json(self) -> None:
        assert "JSON" in SYSTEM_PROMPT


# ---------------------------------------------------------------------------
# build_user_prompt
# ---------------------------------------------------------------------------
class TestBuildUserPrompt:
    def test_both_files(self, tmp_path: Path) -> None:
        audio = tmp_path / "voice.mp3"
        image = tmp_path / "face.jpg"
        prompt = build_user_prompt(audio, image)
        assert "voice.mp3" in prompt
        assert "face.jpg" in prompt

    def test_audio_only(self, tmp_path: Path) -> None:
        audio = tmp_path / "voice.mp3"
        prompt = build_user_prompt(audio, None)
        assert "voice.mp3" in prompt
        assert "Image" not in prompt

    def test_image_only(self, tmp_path: Path) -> None:
        image = tmp_path / "face.jpg"
        prompt = build_user_prompt(None, image)
        assert "face.jpg" in prompt
        assert "Audio" not in prompt

    def test_no_files(self) -> None:
        prompt = build_user_prompt(None, None)
        assert "No media" in prompt


# ---------------------------------------------------------------------------
# parse_gemini_response
# ---------------------------------------------------------------------------
class TestParseGeminiResponse:
    def test_valid_json(self) -> None:
        raw = json.dumps(_valid_response_dict())
        result = parse_gemini_response(raw)
        assert isinstance(result, _GeminiResponse)
        assert result.chief_complaint == "Severe chest pain radiating to left arm"
        assert len(result.symptoms) == 2
        assert len(result.follow_up_questions) == 2
        assert result.confidence == 0.85

    def test_minimal_valid_json(self) -> None:
        raw = json.dumps({
            "chief_complaint": "Headache",
            "symptoms": [],
            "follow_up_questions": [],
            "confidence": 0.5,
        })
        result = parse_gemini_response(raw)
        assert result.chief_complaint == "Headache"
        assert result.symptoms == []

    def test_invalid_json_raises(self) -> None:
        with pytest.raises(GeminiResponseParseError, match="Invalid JSON"):
            parse_gemini_response("not json at all {{{")

    def test_missing_required_field_raises(self) -> None:
        incomplete = json.dumps({"chief_complaint": "pain"})
        with pytest.raises(GeminiResponseParseError, match="validation failed"):
            parse_gemini_response(incomplete)

    def test_confidence_out_of_range_raises(self) -> None:
        data = _valid_response_dict(confidence=1.5)
        with pytest.raises(GeminiResponseParseError, match="validation failed"):
            parse_gemini_response(json.dumps(data))

    def test_empty_string_raises(self) -> None:
        with pytest.raises(GeminiResponseParseError, match="Invalid JSON"):
            parse_gemini_response("")

    def test_symptom_detail_fields_parsed(self) -> None:
        raw = json.dumps(_valid_response_dict())
        result = parse_gemini_response(raw)
        symptom = result.symptoms[0]
        assert symptom.name == "chest pain"
        assert symptom.severity == "severe"
        assert symptom.body_region == "chest"
        assert symptom.onset_description == "30 minutes ago"


# ---------------------------------------------------------------------------
# map_severity
# ---------------------------------------------------------------------------
class TestMapSeverity:
    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            ("mild", SymptomSeverity.MILD),
            ("moderate", SymptomSeverity.MODERATE),
            ("severe", SymptomSeverity.SEVERE),
            ("critical", SymptomSeverity.CRITICAL),
            ("  Mild  ", SymptomSeverity.MILD),
            ("SEVERE", SymptomSeverity.SEVERE),
        ],
    )
    def test_known_severities(self, raw: str, expected: SymptomSeverity) -> None:
        assert map_severity(raw) == expected

    def test_unknown_severity_defaults_moderate(self) -> None:
        assert map_severity("extreme") == SymptomSeverity.MODERATE

    def test_empty_string_defaults_moderate(self) -> None:
        assert map_severity("") == SymptomSeverity.MODERATE


# ---------------------------------------------------------------------------
# map_to_extraction
# ---------------------------------------------------------------------------
class TestMapToExtraction:
    def test_full_mapping(self) -> None:
        gemini_resp = _GeminiResponse(
            chief_complaint="Chest pain",
            symptoms=[
                _GeminiSymptom(
                    name="chest pain",
                    severity="severe",
                    description="Sharp pain",
                    body_region="chest",
                    onset_description="1 hour ago",
                ),
            ],
            follow_up_questions=["History of heart disease?"],
            confidence=0.9,
        )
        result = map_to_extraction(gemini_resp, SESSION_ID)

        assert isinstance(result, SymptomExtractionCreate)
        assert result.session_id == SESSION_ID
        assert result.chief_complaint == "Chest pain"
        assert len(result.symptoms) == 1
        assert result.symptoms[0].severity == SymptomSeverity.SEVERE
        assert result.follow_up_questions == ["History of heart disease?"]
        assert result.confidence == 0.9

    def test_empty_symptoms(self) -> None:
        gemini_resp = _GeminiResponse(
            chief_complaint="General malaise",
            symptoms=[],
            follow_up_questions=[],
            confidence=0.4,
        )
        result = map_to_extraction(gemini_resp, SESSION_ID)
        assert result.symptoms == []
        assert result.follow_up_questions == []

    def test_unknown_severity_mapped_to_moderate(self) -> None:
        gemini_resp = _GeminiResponse(
            chief_complaint="Rash",
            symptoms=[
                _GeminiSymptom(name="rash", severity="extreme"),
            ],
            follow_up_questions=[],
            confidence=0.6,
        )
        result = map_to_extraction(gemini_resp, SESSION_ID)
        assert result.symptoms[0].severity == SymptomSeverity.MODERATE


# ---------------------------------------------------------------------------
# get_response_schema
# ---------------------------------------------------------------------------
class TestGetResponseSchema:
    def test_returns_valid_json_schema(self) -> None:
        schema = get_response_schema()
        assert isinstance(schema, dict)
        assert "properties" in schema
        assert "chief_complaint" in schema["properties"]
        assert "symptoms" in schema["properties"]
        assert "confidence" in schema["properties"]

    def test_schema_is_json_serialisable(self) -> None:
        schema = get_response_schema()
        serialised = json.dumps(schema)
        assert isinstance(serialised, str)


# ---------------------------------------------------------------------------
# _GeminiResponse / _GeminiSymptom models
# ---------------------------------------------------------------------------
class TestInternalModels:
    def test_gemini_symptom_minimal(self) -> None:
        s = _GeminiSymptom(name="headache", severity="mild")
        assert s.description is None
        assert s.body_region is None

    def test_gemini_response_with_defaults(self) -> None:
        r = _GeminiResponse(
            chief_complaint="test",
            confidence=0.5,
        )
        assert r.symptoms == []
        assert r.follow_up_questions == []


# ---------------------------------------------------------------------------
# GeminiService construction
# ---------------------------------------------------------------------------
class TestGeminiServiceInit:
    def test_creates_real_genai_client(self) -> None:
        svc = GeminiService(_settings())
        assert isinstance(svc._client, genai.Client)

    def test_stores_config_values(self) -> None:
        svc = GeminiService(_settings(
            gemini_model="gemini-2.0-flash",
            gemini_temperature=0.5,
            gemini_max_retries=5,
        ))
        assert svc._model == "gemini-2.0-flash"
        assert svc._temperature == 0.5
        assert svc._max_retries == 5


class TestGeminiServiceBuildContents:
    def test_no_files_produces_text_only(self) -> None:
        svc = GeminiService(_settings())
        contents = svc._build_contents(None, None)
        assert len(contents) == 1
        assert isinstance(contents[0], str)


# ---------------------------------------------------------------------------
# Error hierarchy
# ---------------------------------------------------------------------------
class TestErrorHierarchy:
    def test_parse_error_is_extraction_error(self) -> None:
        assert issubclass(GeminiResponseParseError, GeminiExtractionError)

    def test_base_is_exception(self) -> None:
        assert issubclass(GeminiExtractionError, Exception)


# ---------------------------------------------------------------------------
# Integration tests (require GOOGLE_GENAI_API_KEY)
# ---------------------------------------------------------------------------
class TestGeminiServiceIntegration:
    @skip_no_key
    @pytest.mark.asyncio
    async def test_extract_symptoms_text_only(self) -> None:
        """Smoke test: send text-only prompt to real Gemini API."""
        svc = GeminiService(_settings())
        result = await svc.extract_symptoms(SESSION_ID)
        assert isinstance(result, SymptomExtractionCreate)
        assert result.session_id == SESSION_ID
        assert len(result.chief_complaint) > 0
