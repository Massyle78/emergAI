"""Gemini 2.5 Pro multimodal inference service for symptom extraction.

Sends audio + image files to the Gemini API with a structured JSON
schema so the model returns typed symptom data that maps directly
to SymptomExtractionCreate.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any
from uuid import UUID

from google import genai
from google.genai import types
from pydantic import BaseModel, Field
from tenacity import (
    RetryError,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.config import Settings
from app.models.enums import SymptomSeverity
from app.models.symptoms import (
    SymptomDetail,
    SymptomExtractionCreate,
)

logger = logging.getLogger("app.services.gemini")


SYSTEM_PROMPT = (
    "You are an expert emergency-department triage assistant. "
    "Analyze the provided patient audio and/or image to extract:\n"
    "1. The chief complaint (a concise statement of the main reason "
    "for the visit).\n"
    "2. All individual symptoms with severity (mild, moderate, severe, "
    "critical), body region, and onset.\n"
    "3. Clinically relevant follow-up questions to refine the assessment.\n"
    "4. An overall confidence score (0.0–1.0) reflecting how certain "
    "you are in the extraction.\n\n"
    "Return ONLY valid JSON matching the provided schema."
)


class GeminiExtractionError(Exception):
    """Base error for Gemini inference failures."""


class GeminiResponseParseError(GeminiExtractionError):
    """Gemini returned a response that could not be parsed."""


# ------------------------------------------------------------------
# Internal response schema for Gemini structured output
# ------------------------------------------------------------------
class _GeminiSymptom(BaseModel):
    """Single symptom as returned by Gemini."""

    name: str
    severity: str = Field(description="One of: mild, moderate, severe, critical")
    description: str | None = None
    body_region: str | None = None
    onset_description: str | None = None


class _GeminiResponse(BaseModel):
    """Top-level structured response from Gemini."""

    chief_complaint: str
    symptoms: list[_GeminiSymptom] = Field(default_factory=list)
    follow_up_questions: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)


# ------------------------------------------------------------------
# Pure helper functions
# ------------------------------------------------------------------
def build_user_prompt(audio_path: Path | None, image_path: Path | None) -> str:
    """Build the user-facing part of the prompt describing inputs."""
    parts: list[str] = []
    if audio_path:
        parts.append(f"Audio file provided: {audio_path.name}")
    if image_path:
        parts.append(f"Image file provided: {image_path.name}")
    if not parts:
        return "No media files provided. Extract symptoms from context."
    return (
        "Analyze the attached media to extract the patient's symptoms, "
        "chief complaint, and follow-up questions.\n"
        + "\n".join(parts)
    )


def parse_gemini_response(raw_text: str) -> _GeminiResponse:
    """Parse and validate the raw JSON text from Gemini.

    Raises:
        GeminiResponseParseError: If the text is not valid JSON or
            does not conform to the expected schema.
    """
    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise GeminiResponseParseError(
            f"Invalid JSON from Gemini: {exc}"
        ) from exc
    try:
        return _GeminiResponse.model_validate(data)
    except Exception as exc:
        raise GeminiResponseParseError(
            f"Schema validation failed: {exc}"
        ) from exc


def map_severity(raw: str) -> SymptomSeverity:
    """Convert a raw severity string to the SymptomSeverity enum.

    Falls back to MODERATE for unrecognised values.
    """
    normalised = raw.strip().lower()
    try:
        return SymptomSeverity(normalised)
    except ValueError:
        logger.warning("Unknown severity '%s', defaulting to moderate", raw)
        return SymptomSeverity.MODERATE


def map_to_extraction(
    response: _GeminiResponse, session_id: UUID
) -> SymptomExtractionCreate:
    """Map the internal Gemini response to a domain model."""
    symptoms = [
        SymptomDetail(
            name=s.name,
            severity=map_severity(s.severity),
            description=s.description,
            body_region=s.body_region,
            onset_description=s.onset_description,
        )
        for s in response.symptoms
    ]
    return SymptomExtractionCreate(
        session_id=session_id,
        chief_complaint=response.chief_complaint,
        symptoms=symptoms,
        follow_up_questions=response.follow_up_questions,
        confidence=response.confidence,
    )


def get_response_schema() -> dict[str, Any]:
    """Return the JSON schema that Gemini must conform to."""
    return _GeminiResponse.model_json_schema()


# ------------------------------------------------------------------
# Service class
# ------------------------------------------------------------------
class GeminiService:
    """Multimodal symptom extraction via Gemini 2.5 Pro.

    Time complexity: O(1) per call (single API round-trip).
    Latency dominated by network + model inference (~5-15 s).
    """

    def __init__(self, settings: Settings) -> None:
        self._model = settings.gemini_model
        self._temperature = settings.gemini_temperature
        self._max_retries = settings.gemini_max_retries
        self._retry_wait = settings.gemini_retry_wait_seconds
        self._client = genai.Client(api_key=settings.google_genai_api_key)

    async def extract_symptoms(
        self,
        session_id: UUID,
        audio_path: Path | None = None,
        image_path: Path | None = None,
    ) -> SymptomExtractionCreate:
        """Analyse media and return structured symptom data.

        Args:
            session_id: Triage session this extraction belongs to.
            audio_path: Optional path to the patient audio file.
            image_path: Optional path to the patient image file.

        Returns:
            Validated SymptomExtractionCreate.

        Raises:
            GeminiExtractionError: On API or parsing failure.
        """
        contents = self._build_contents(audio_path, image_path)
        raw_text = await self._call_api(contents)
        parsed = parse_gemini_response(raw_text)
        result = map_to_extraction(parsed, session_id)

        logger.info(
            "Extracted %d symptoms (confidence=%.2f) for session %s",
            len(result.symptoms),
            result.confidence,
            session_id,
        )
        return result

    def _build_contents(
        self, audio_path: Path | None, image_path: Path | None
    ) -> list[Any]:
        """Assemble the content parts list for the API call."""
        parts: list[Any] = [build_user_prompt(audio_path, image_path)]
        if audio_path:
            parts.append(self._upload_file(audio_path))
        if image_path:
            parts.append(self._upload_file(image_path))
        return parts

    def _upload_file(self, file_path: Path) -> Any:
        """Upload a file to the Gemini Files API."""
        return self._client.files.upload(file=str(file_path))

    async def _call_api(self, contents: list[Any]) -> str:
        """Call Gemini with retries and return the raw response text."""
        retrier = retry(
            retry=retry_if_exception_type(Exception),
            stop=stop_after_attempt(self._max_retries),
            wait=wait_exponential(
                multiplier=self._retry_wait, min=self._retry_wait, max=30
            ),
            reraise=True,
        )

        @retrier
        def _do_call() -> str:
            return self._generate(contents)

        try:
            return _do_call()
        except RetryError as exc:
            raise GeminiExtractionError(
                f"Gemini API failed after {self._max_retries} retries"
            ) from exc
        except GeminiExtractionError:
            raise
        except Exception as exc:
            raise GeminiExtractionError(
                f"Gemini API call failed: {exc}"
            ) from exc

    def _generate(self, contents: list[Any]) -> str:
        """Execute a single generate_content call."""
        response = self._client.models.generate_content(
            model=self._model,
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                temperature=self._temperature,
                response_mime_type="application/json",
                response_json_schema=get_response_schema(),
            ),
        )
        if not response.text:
            raise GeminiExtractionError("Gemini returned empty response")
        return response.text
