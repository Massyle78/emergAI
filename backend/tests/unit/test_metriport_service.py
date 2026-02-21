"""Unit tests for the Metriport EHR integration service.

FHIR parsing and circuit breaker logic are tested with real data.
HTTP interactions use httpx.MockTransport for deterministic responses
without real network calls.
"""

from __future__ import annotations

import time
from typing import Any

import httpx
import pytest

from app.config import Settings
from app.models.patient_history import (
    AllergyRecord,
    ConditionRecord,
    MedicationRecord,
    PatientHistory,
)
from app.services.metriport_service import (
    CircuitBreaker,
    MetriportCircuitOpenError,
    MetriportError,
    MetriportService,
    MetriportTimeoutError,
    _extract_clinical_status,
    _extract_code,
    parse_allergy,
    parse_condition,
    parse_fhir_bundle,
    parse_medication,
)

PATIENT_ID = "pat-123"


def _settings(**overrides: object) -> Settings:
    defaults: dict[str, object] = {
        "metriport_api_key": "test-api-key",
        "metriport_base_url": "https://api.test.metriport.com",
        "metriport_timeout_seconds": 5,
        "metriport_poll_interval_seconds": 0.1,
        "metriport_max_poll_attempts": 3,
        "metriport_cb_failure_threshold": 3,
        "metriport_cb_cooldown_seconds": 60,
    }
    defaults.update(overrides)
    return Settings(**defaults)  # type: ignore[arg-type]


def _condition_resource(**overrides: Any) -> dict:
    base: dict[str, Any] = {
        "resourceType": "Condition",
        "code": {
            "coding": [
                {
                    "system": "http://snomed.info/sct",
                    "code": "44054006",
                    "display": "Diabetes mellitus type 2",
                }
            ],
            "text": "Type 2 diabetes",
        },
        "clinicalStatus": {"coding": [{"code": "active"}]},
        "onsetDateTime": "2020-01-15",
    }
    base.update(overrides)
    return base


def _medication_resource(**overrides: Any) -> dict:
    base: dict[str, Any] = {
        "resourceType": "MedicationStatement",
        "medicationCodeableConcept": {
            "coding": [
                {
                    "system": "http://www.nlm.nih.gov/research/umls/rxnorm",
                    "code": "860975",
                    "display": "Metformin 500 MG",
                }
            ],
            "text": "Metformin 500mg",
        },
        "status": "active",
        "dosage": [{"text": "500mg twice daily"}],
    }
    base.update(overrides)
    return base


def _allergy_resource(**overrides: Any) -> dict:
    base: dict[str, Any] = {
        "resourceType": "AllergyIntolerance",
        "code": {
            "coding": [
                {
                    "system": "http://snomed.info/sct",
                    "code": "764146007",
                    "display": "Penicillin",
                }
            ],
            "text": "Penicillin allergy",
        },
        "clinicalStatus": {"coding": [{"code": "active"}]},
        "criticality": "high",
    }
    base.update(overrides)
    return base


def _fhir_bundle(*entries: dict) -> dict:
    return {
        "resourceType": "Bundle",
        "type": "searchset",
        "entry": [{"resource": e} for e in entries],
    }


# ---------------------------------------------------------------------------
# _extract_code
# ---------------------------------------------------------------------------
class TestExtractCode:
    def test_full_coding_entry(self) -> None:
        codeable = {
            "coding": [
                {"system": "http://snomed.info/sct", "code": "123", "display": "Test"}
            ],
            "text": "Test condition",
        }
        code = _extract_code(codeable)
        assert code.system == "http://snomed.info/sct"
        assert code.code == "123"
        assert code.display == "Test"

    def test_text_only_no_coding(self) -> None:
        code = _extract_code({"text": "Free text only"})
        assert code.display == "Free text only"
        assert code.code is None

    def test_none_input(self) -> None:
        code = _extract_code(None)
        assert code.system is None
        assert code.code is None
        assert code.display is None

    def test_empty_coding_list(self) -> None:
        code = _extract_code({"coding": [], "text": "Fallback"})
        assert code.display == "Fallback"

    def test_display_falls_back_to_text(self) -> None:
        codeable = {
            "coding": [{"system": "sys", "code": "c"}],
            "text": "From text",
        }
        code = _extract_code(codeable)
        assert code.display == "From text"


# ---------------------------------------------------------------------------
# _extract_clinical_status
# ---------------------------------------------------------------------------
class TestExtractClinicalStatus:
    def test_active_status(self) -> None:
        resource = {"clinicalStatus": {"coding": [{"code": "active"}]}}
        assert _extract_clinical_status(resource) == "active"

    def test_missing_status(self) -> None:
        assert _extract_clinical_status({}) is None

    def test_empty_coding(self) -> None:
        resource = {"clinicalStatus": {"coding": []}}
        assert _extract_clinical_status(resource) is None


# ---------------------------------------------------------------------------
# parse_condition
# ---------------------------------------------------------------------------
class TestParseCondition:
    def test_full_condition(self) -> None:
        r = parse_condition(_condition_resource())
        assert isinstance(r, ConditionRecord)
        assert r.code.display == "Diabetes mellitus type 2"
        assert r.clinical_status == "active"
        assert r.onset == "2020-01-15"
        assert r.text == "Type 2 diabetes"

    def test_minimal_condition(self) -> None:
        r = parse_condition({"resourceType": "Condition"})
        assert r.code.display is None
        assert r.clinical_status is None
        assert r.onset is None


# ---------------------------------------------------------------------------
# parse_medication
# ---------------------------------------------------------------------------
class TestParseMedication:
    def test_full_medication(self) -> None:
        r = parse_medication(_medication_resource())
        assert isinstance(r, MedicationRecord)
        assert r.code.display == "Metformin 500 MG"
        assert r.status == "active"
        assert r.dosage == "500mg twice daily"
        assert r.text == "Metformin 500mg"

    def test_no_dosage(self) -> None:
        res = _medication_resource()
        del res["dosage"]
        r = parse_medication(res)
        assert r.dosage is None

    def test_minimal_medication(self) -> None:
        r = parse_medication({"resourceType": "MedicationStatement"})
        assert r.code.display is None
        assert r.status is None


# ---------------------------------------------------------------------------
# parse_allergy
# ---------------------------------------------------------------------------
class TestParseAllergy:
    def test_full_allergy(self) -> None:
        r = parse_allergy(_allergy_resource())
        assert isinstance(r, AllergyRecord)
        assert r.code.display == "Penicillin"
        assert r.clinical_status == "active"
        assert r.criticality == "high"
        assert r.text == "Penicillin allergy"

    def test_minimal_allergy(self) -> None:
        r = parse_allergy({"resourceType": "AllergyIntolerance"})
        assert r.code.display is None
        assert r.criticality is None


# ---------------------------------------------------------------------------
# parse_fhir_bundle
# ---------------------------------------------------------------------------
class TestParseFhirBundle:
    def test_mixed_bundle(self) -> None:
        bundle = _fhir_bundle(
            _condition_resource(),
            _medication_resource(),
            _allergy_resource(),
        )
        history = parse_fhir_bundle(bundle)
        assert isinstance(history, PatientHistory)
        assert len(history.conditions) == 1
        assert len(history.medications) == 1
        assert len(history.allergies) == 1
        assert history.total_records == 3

    def test_empty_bundle(self) -> None:
        history = parse_fhir_bundle({"resourceType": "Bundle"})
        assert history.is_empty
        assert history.total_records == 0

    def test_unknown_resource_types_ignored(self) -> None:
        bundle = _fhir_bundle(
            {"resourceType": "Observation", "status": "final"},
            _condition_resource(),
        )
        history = parse_fhir_bundle(bundle)
        assert len(history.conditions) == 1
        assert history.total_records == 1

    def test_multiple_same_type(self) -> None:
        bundle = _fhir_bundle(
            _condition_resource(),
            _condition_resource(onsetDateTime="2022-06-01"),
        )
        history = parse_fhir_bundle(bundle)
        assert len(history.conditions) == 2


# ---------------------------------------------------------------------------
# PatientHistory properties
# ---------------------------------------------------------------------------
class TestPatientHistoryModel:
    def test_is_empty_true(self) -> None:
        assert PatientHistory().is_empty

    def test_is_empty_false(self) -> None:
        h = PatientHistory(conditions=[parse_condition(_condition_resource())])
        assert not h.is_empty

    def test_total_records(self) -> None:
        h = PatientHistory(
            conditions=[parse_condition(_condition_resource())],
            medications=[parse_medication(_medication_resource())],
            allergies=[
                parse_allergy(_allergy_resource()),
                parse_allergy(_allergy_resource()),
            ],
        )
        assert h.total_records == 4


# ---------------------------------------------------------------------------
# CircuitBreaker
# ---------------------------------------------------------------------------
class TestCircuitBreaker:
    def test_starts_closed(self) -> None:
        cb = CircuitBreaker(failure_threshold=3, cooldown_seconds=60)
        assert not cb.is_open
        cb.check()

    def test_trips_after_threshold(self) -> None:
        cb = CircuitBreaker(failure_threshold=3, cooldown_seconds=60)
        cb.record_failure()
        cb.record_failure()
        assert not cb.is_open
        cb.record_failure()
        assert cb.is_open
        with pytest.raises(MetriportCircuitOpenError, match="circuit breaker"):
            cb.check()

    def test_success_resets_failures(self) -> None:
        cb = CircuitBreaker(failure_threshold=3, cooldown_seconds=60)
        cb.record_failure()
        cb.record_failure()
        cb.record_success()
        cb.record_failure()
        assert not cb.is_open

    def test_cooldown_expires(self) -> None:
        cb = CircuitBreaker(failure_threshold=1, cooldown_seconds=0)
        cb.record_failure()
        assert not cb.is_open

    def test_check_passes_when_closed(self) -> None:
        cb = CircuitBreaker(failure_threshold=5, cooldown_seconds=60)
        cb.check()


# ---------------------------------------------------------------------------
# MetriportService construction
# ---------------------------------------------------------------------------
class TestMetriportServiceInit:
    def test_creates_httpx_client(self) -> None:
        svc = MetriportService(_settings())
        assert isinstance(svc._client, httpx.AsyncClient)

    def test_base_url_stored(self) -> None:
        svc = MetriportService(_settings())
        assert "test.metriport.com" in svc._base_url


# ---------------------------------------------------------------------------
# MetriportService with httpx.MockTransport
# ---------------------------------------------------------------------------
def _make_service_with_transport(
    transport: httpx.MockTransport, **settings_overrides: object
) -> MetriportService:
    """Build a MetriportService whose httpx client uses a mock transport."""
    svc = MetriportService(_settings(**settings_overrides))
    svc._client = httpx.AsyncClient(
        transport=transport,
        base_url=svc._base_url,
        headers=dict(svc._client.headers),
        timeout=svc._client.timeout,
    )
    return svc


class TestFetchPatientHistory:
    @pytest.mark.asyncio
    async def test_successful_fetch(self) -> None:
        """POST returns requestId, first poll returns completed with bundle."""
        call_count = {"n": 0}

        def handler(request: httpx.Request) -> httpx.Response:
            call_count["n"] += 1
            if request.method == "POST":
                return httpx.Response(
                    200,
                    json={"requestId": "req-1", "status": "processing"},
                )
            return httpx.Response(
                200,
                json={
                    "status": "completed",
                    "bundle": _fhir_bundle(
                        _condition_resource(), _allergy_resource()
                    ),
                },
            )

        transport = httpx.MockTransport(handler)
        svc = _make_service_with_transport(transport)

        history = await svc.fetch_patient_history(PATIENT_ID)
        assert len(history.conditions) == 1
        assert len(history.allergies) == 1
        assert call_count["n"] == 2
        await svc.close()

    @pytest.mark.asyncio
    async def test_polls_multiple_times(self) -> None:
        """Returns processing twice, then completed."""
        poll_count = {"n": 0}

        def handler(request: httpx.Request) -> httpx.Response:
            if request.method == "POST":
                return httpx.Response(
                    200, json={"requestId": "req-2", "status": "processing"}
                )
            poll_count["n"] += 1
            if poll_count["n"] < 3:
                return httpx.Response(200, json={"status": "processing"})
            return httpx.Response(
                200,
                json={"status": "completed", "bundle": _fhir_bundle()},
            )

        svc = _make_service_with_transport(httpx.MockTransport(handler))
        history = await svc.fetch_patient_history(PATIENT_ID)
        assert history.is_empty
        assert poll_count["n"] == 3
        await svc.close()

    @pytest.mark.asyncio
    async def test_timeout_after_max_polls(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            if request.method == "POST":
                return httpx.Response(
                    200, json={"requestId": "req-3", "status": "processing"}
                )
            return httpx.Response(200, json={"status": "processing"})

        svc = _make_service_with_transport(
            httpx.MockTransport(handler), metriport_max_poll_attempts=2
        )
        with pytest.raises(MetriportTimeoutError, match="did not complete"):
            await svc.fetch_patient_history(PATIENT_ID)
        await svc.close()

    @pytest.mark.asyncio
    async def test_query_failed_status(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            if request.method == "POST":
                return httpx.Response(
                    200, json={"requestId": "req-4", "status": "processing"}
                )
            return httpx.Response(
                200,
                json={"status": "failed", "message": "upstream error"},
            )

        svc = _make_service_with_transport(httpx.MockTransport(handler))
        with pytest.raises(MetriportError, match="upstream error"):
            await svc.fetch_patient_history(PATIENT_ID)
        await svc.close()

    @pytest.mark.asyncio
    async def test_http_error_triggers_circuit_breaker(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(500, json={"error": "internal"})

        svc = _make_service_with_transport(
            httpx.MockTransport(handler),
            metriport_cb_failure_threshold=2,
        )
        with pytest.raises(MetriportError):
            await svc.fetch_patient_history(PATIENT_ID)
        with pytest.raises(MetriportError):
            await svc.fetch_patient_history(PATIENT_ID)
        with pytest.raises(MetriportCircuitOpenError):
            await svc.fetch_patient_history(PATIENT_ID)
        await svc.close()

    @pytest.mark.asyncio
    async def test_missing_request_id(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"status": "processing"})

        svc = _make_service_with_transport(httpx.MockTransport(handler))
        with pytest.raises(MetriportError, match="No requestId"):
            await svc.fetch_patient_history(PATIENT_ID)
        await svc.close()

    @pytest.mark.asyncio
    async def test_success_resets_circuit_breaker(self) -> None:
        call_count = {"n": 0}

        def handler(request: httpx.Request) -> httpx.Response:
            call_count["n"] += 1
            if call_count["n"] <= 2:
                return httpx.Response(500)
            if request.method == "POST":
                return httpx.Response(
                    200, json={"requestId": "r", "status": "processing"}
                )
            return httpx.Response(
                200,
                json={"status": "completed", "bundle": _fhir_bundle()},
            )

        svc = _make_service_with_transport(
            httpx.MockTransport(handler),
            metriport_cb_failure_threshold=3,
        )
        with pytest.raises(MetriportError):
            await svc.fetch_patient_history(PATIENT_ID)
        with pytest.raises(MetriportError):
            await svc.fetch_patient_history(PATIENT_ID)
        history = await svc.fetch_patient_history(PATIENT_ID)
        assert history.is_empty
        svc._breaker.record_failure()
        assert not svc._breaker.is_open
        await svc.close()


# ---------------------------------------------------------------------------
# Error hierarchy
# ---------------------------------------------------------------------------
class TestErrorHierarchy:
    def test_circuit_open_is_metriport_error(self) -> None:
        assert issubclass(MetriportCircuitOpenError, MetriportError)

    def test_timeout_is_metriport_error(self) -> None:
        assert issubclass(MetriportTimeoutError, MetriportError)

    def test_base_is_exception(self) -> None:
        assert issubclass(MetriportError, Exception)
