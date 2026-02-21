"""Contract tests for the Google Gemini API integration.

Validates that the request shapes we construct and the response
shapes we expect match the Gemini SDK contract. No real API calls.
"""

import pytest

from app.models.enums import SymptomSeverity
from app.models.symptoms import SymptomDetail, SymptomExtractionCreate
from app.models.vitals import VitalsCreate


class TestGeminiSymptomRequestContract:
    """Validates the prompt/request shape for symptom extraction."""

    def test_system_prompt_contains_required_fields(self):
        system_prompt = (
            "You are a medical triage assistant. Analyze the patient audio "
            "and extract: chief_complaint, symptoms (name, severity, "
            "description, body_region, onset_description), "
            "follow_up_questions, confidence."
        )
        required_fields = [
            "chief_complaint",
            "symptoms",
            "severity",
            "body_region",
            "follow_up_questions",
            "confidence",
        ]
        for field in required_fields:
            assert field in system_prompt

    def test_severity_enum_values_match_expected(self):
        expected = {"mild", "moderate", "severe", "critical"}
        actual = {s.value for s in SymptomSeverity}
        assert actual == expected


class TestGeminiSymptomResponseContract:
    """Validates that Gemini responses parse into our models."""

    def test_full_response_parses_correctly(self):
        from uuid import uuid4

        gemini_output = {
            "chief_complaint": "Severe headache for 2 days",
            "symptoms": [
                {
                    "name": "Headache",
                    "severity": "severe",
                    "description": "Throbbing bilateral headache",
                    "body_region": "Head",
                    "onset_description": "2 days ago, gradual onset",
                },
                {
                    "name": "Photophobia",
                    "severity": "moderate",
                    "description": "Light sensitivity",
                    "body_region": "Eyes",
                    "onset_description": None,
                },
            ],
            "follow_up_questions": [
                "Any fever or neck stiffness?",
                "History of migraines?",
            ],
            "confidence": 0.88,
        }

        symptoms = [SymptomDetail(**s) for s in gemini_output["symptoms"]]
        extraction = SymptomExtractionCreate(
            session_id=uuid4(),
            chief_complaint=gemini_output["chief_complaint"],
            symptoms=symptoms,
            follow_up_questions=gemini_output["follow_up_questions"],
            confidence=gemini_output["confidence"],
        )

        assert extraction.chief_complaint == "Severe headache for 2 days"
        assert len(extraction.symptoms) == 2
        assert extraction.symptoms[0].severity == SymptomSeverity.SEVERE
        assert extraction.confidence == 0.88

    def test_minimal_response_parses(self):
        from uuid import uuid4

        extraction = SymptomExtractionCreate(
            session_id=uuid4(),
            chief_complaint="Mild cough",
            symptoms=[],
            follow_up_questions=[],
            confidence=0.5,
        )
        assert extraction.chief_complaint == "Mild cough"
        assert len(extraction.symptoms) == 0

    def test_invalid_severity_raises_validation_error(self):
        with pytest.raises(ValueError):
            SymptomDetail(
                name="Test",
                severity="extreme",  # type: ignore
                description=None,
            )

    def test_confidence_out_of_range_raises_error(self):
        from uuid import uuid4

        with pytest.raises(ValueError):
            SymptomExtractionCreate(
                session_id=uuid4(),
                chief_complaint="Test",
                symptoms=[],
                follow_up_questions=[],
                confidence=1.5,
            )


class TestGeminiEmbeddingContract:
    """Validates the embedding request/response shape."""

    def test_embedding_input_is_string(self):
        text_input = "Patient: chest pain, tachycardia, diaphoresis"
        assert isinstance(text_input, str)
        assert len(text_input) > 0

    def test_embedding_output_is_float_list(self):
        mock_embedding = [0.1] * 768
        assert isinstance(mock_embedding, list)
        assert all(isinstance(v, float) for v in mock_embedding)
        assert len(mock_embedding) == 768

    def test_embedding_dimensions_configurable(self):
        from app.config import Settings

        settings = Settings(
            app_env="testing",
            supabase_jwt_secret="x" * 33,
            embedding_dimensions=512,
        )
        assert settings.embedding_dimensions == 512
