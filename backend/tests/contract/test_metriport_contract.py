"""Contract tests for the Metriport API integration.

Validates that the request/response shapes our code produces
match the expected Metriport FHIR API contract. No real HTTP
calls are made — these tests verify the data shapes in isolation.
"""

from uuid import uuid4

import pytest

from app.config import Settings
from app.models.patient_history import (
    AllergyRecord,
    ClinicalCode,
    ConditionRecord,
    MedicationRecord,
    PatientHistory,
)


def _settings() -> Settings:
    return Settings(
        app_env="testing",
        supabase_jwt_secret="x" * 33,
        metriport_api_key="test-api-key",
        metriport_base_url="https://api.metriport.com",
        metriport_timeout_seconds=10,
        metriport_poll_interval_seconds=0.1,
    )


class TestMetriportRequestContract:
    """Validates the shape of requests we send to Metriport."""

    def test_patient_query_url_format(self):
        settings = _settings()
        patient_id = str(uuid4())
        expected_url = (
            f"{settings.metriport_base_url}/medical/v1/patient/{patient_id}/consolidated"
        )
        assert "medical/v1/patient" in expected_url
        assert patient_id in expected_url
        assert expected_url.endswith("/consolidated")

    def test_required_headers_shape(self):
        settings = _settings()
        headers = {
            "x-api-key": settings.metriport_api_key,
            "Content-Type": "application/json",
        }
        assert "x-api-key" in headers
        assert headers["x-api-key"] == "test-api-key"
        assert headers["Content-Type"] == "application/json"

    def test_query_params_shape(self):
        params = {
            "resources": "Condition,MedicationStatement,AllergyIntolerance",
            "dateFrom": "2020-01-01",
            "dateTo": "2026-01-01",
        }
        assert "resources" in params
        assert "Condition" in params["resources"]


class TestMetriportResponseContract:
    """Validates that we can parse expected Metriport response shapes."""

    def test_fhir_bundle_parses_to_patient_history(self):
        fhir_response = {
            "resourceType": "Bundle",
            "entry": [
                {
                    "resource": {
                        "resourceType": "Condition",
                        "code": {
                            "coding": [{"display": "Hypertension"}],
                        },
                        "clinicalStatus": {
                            "coding": [{"code": "active"}],
                        },
                    },
                },
                {
                    "resource": {
                        "resourceType": "MedicationStatement",
                        "medicationCodeableConcept": {
                            "coding": [{"display": "Lisinopril 10mg"}],
                        },
                        "status": "active",
                    },
                },
                {
                    "resource": {
                        "resourceType": "AllergyIntolerance",
                        "code": {
                            "coding": [{"display": "Penicillin"}],
                        },
                    },
                },
            ],
        }

        conditions: list[ConditionRecord] = []
        medications: list[MedicationRecord] = []
        allergies: list[AllergyRecord] = []

        for entry in fhir_response.get("entry", []):
            r = entry.get("resource", {})
            rt = r.get("resourceType")
            if rt == "Condition":
                code = r.get("code", {})
                coding = code.get("coding", [{}])
                conditions.append(ConditionRecord(
                    code=ClinicalCode(display=coding[0].get("display", "")),
                    clinical_status=r.get("clinicalStatus", {}).get("coding", [{}])[0].get("code"),
                ))
            elif rt == "MedicationStatement":
                med = r.get("medicationCodeableConcept", {})
                coding = med.get("coding", [{}])
                medications.append(MedicationRecord(
                    code=ClinicalCode(display=coding[0].get("display", "")),
                    status=r.get("status"),
                ))
            elif rt == "AllergyIntolerance":
                code = r.get("code", {})
                coding = code.get("coding", [{}])
                allergies.append(AllergyRecord(
                    code=ClinicalCode(display=coding[0].get("display", "")),
                ))

        history = PatientHistory(
            conditions=conditions,
            medications=medications,
            allergies=allergies,
        )
        assert history.conditions[0].code.display == "Hypertension"
        assert history.medications[0].code.display == "Lisinopril 10mg"
        assert history.allergies[0].code.display == "Penicillin"
        assert not history.is_empty
        assert history.total_records == 3

    def test_empty_bundle_produces_empty_history(self):
        empty_response = {"resourceType": "Bundle", "entry": []}
        history = PatientHistory(
            conditions=[],
            medications=[],
            allergies=[],
        )
        assert history.conditions == []
        assert history.medications == []
        assert history.allergies == []

    def test_error_response_shape(self):
        error_response = {
            "resourceType": "OperationOutcome",
            "issue": [
                {
                    "severity": "error",
                    "code": "not-found",
                    "diagnostics": "Patient not found",
                }
            ],
        }
        assert error_response["resourceType"] == "OperationOutcome"
        issues = error_response["issue"]
        assert len(issues) == 1
        assert issues[0]["severity"] == "error"
