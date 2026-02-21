"""Metriport EHR integration service.

Fetches patient history (Conditions, MedicationStatements,
AllergyIntolerances) via the Metriport consolidated data query API
and normalizes the FHIR Bundle into internal PatientHistory models.

Implements a circuit breaker that trips after N consecutive failures
and refuses requests for a configurable cooldown period.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

import httpx

from app.config import Settings
from app.models.patient_history import (
    AllergyRecord,
    ClinicalCode,
    ConditionRecord,
    MedicationRecord,
    PatientHistory,
)

logger = logging.getLogger("app.services.metriport")

TRIAGE_RESOURCES = "Condition,MedicationStatement,AllergyIntolerance"


class MetriportError(Exception):
    """Base error for Metriport service failures."""


class MetriportCircuitOpenError(MetriportError):
    """The circuit breaker is open; requests are temporarily blocked."""


class MetriportTimeoutError(MetriportError):
    """The consolidated query did not complete within the allowed time."""


# ------------------------------------------------------------------
# Circuit breaker (simple state machine)
# ------------------------------------------------------------------
class CircuitBreaker:
    """Tracks consecutive failures and trips after a threshold.

    States: CLOSED (normal) → OPEN (blocking) → HALF_OPEN (probing).
    """

    def __init__(self, failure_threshold: int, cooldown_seconds: int) -> None:
        self._threshold = failure_threshold
        self._cooldown = cooldown_seconds
        self._failures = 0
        self._opened_at: float | None = None

    @property
    def is_open(self) -> bool:
        """True when the breaker is tripped and cooldown has not elapsed."""
        if self._opened_at is None:
            return False
        return (time.monotonic() - self._opened_at) < self._cooldown

    def record_success(self) -> None:
        """Reset the failure counter on a successful call."""
        self._failures = 0
        self._opened_at = None

    def record_failure(self) -> None:
        """Increment failures; trip the breaker if threshold is reached."""
        self._failures += 1
        if self._failures >= self._threshold:
            self._opened_at = time.monotonic()
            logger.warning(
                "Circuit breaker OPEN after %d failures (cooldown=%ds)",
                self._failures,
                self._cooldown,
            )

    def check(self) -> None:
        """Raise if the circuit is open.

        Raises:
            MetriportCircuitOpenError: When the breaker is tripped.
        """
        if self.is_open:
            raise MetriportCircuitOpenError(
                "Metriport circuit breaker is open; retry later"
            )


# ------------------------------------------------------------------
# FHIR parsing helpers (pure functions)
# ------------------------------------------------------------------
def _extract_code(codeable: dict[str, Any] | None) -> ClinicalCode:
    """Pull the first coding entry from a FHIR CodeableConcept."""
    if not codeable:
        return ClinicalCode()
    codings = codeable.get("coding", [])
    if not codings:
        return ClinicalCode(display=codeable.get("text"))
    first = codings[0]
    return ClinicalCode(
        system=first.get("system"),
        code=first.get("code"),
        display=first.get("display") or codeable.get("text"),
    )


def _extract_clinical_status(resource: dict[str, Any]) -> str | None:
    """Get the clinical-status text from a FHIR resource."""
    cs = resource.get("clinicalStatus")
    if not cs:
        return None
    codings = cs.get("coding", [])
    return codings[0].get("code") if codings else None


def parse_condition(resource: dict[str, Any]) -> ConditionRecord:
    """Normalise a FHIR Condition resource."""
    return ConditionRecord(
        code=_extract_code(resource.get("code")),
        clinical_status=_extract_clinical_status(resource),
        onset=resource.get("onsetDateTime"),
        text=resource.get("code", {}).get("text"),
    )


def parse_medication(resource: dict[str, Any]) -> MedicationRecord:
    """Normalise a FHIR MedicationStatement resource."""
    dosage_text = None
    dosages = resource.get("dosage", [])
    if dosages:
        dosage_text = dosages[0].get("text")
    return MedicationRecord(
        code=_extract_code(resource.get("medicationCodeableConcept")),
        status=resource.get("status"),
        dosage=dosage_text,
        text=resource.get("medicationCodeableConcept", {}).get("text"),
    )


def parse_allergy(resource: dict[str, Any]) -> AllergyRecord:
    """Normalise a FHIR AllergyIntolerance resource."""
    return AllergyRecord(
        code=_extract_code(resource.get("code")),
        clinical_status=_extract_clinical_status(resource),
        criticality=resource.get("criticality"),
        text=resource.get("code", {}).get("text"),
    )


def parse_fhir_bundle(bundle: dict[str, Any]) -> PatientHistory:
    """Parse a FHIR Bundle into a PatientHistory.

    Iterates over bundle entries and dispatches each resource to
    the appropriate parser based on resourceType.

    Time complexity: O(N) where N = number of bundle entries.
    """
    conditions: list[ConditionRecord] = []
    medications: list[MedicationRecord] = []
    allergies: list[AllergyRecord] = []

    for entry in bundle.get("entry", []):
        resource = entry.get("resource", {})
        rtype = resource.get("resourceType")
        if rtype == "Condition":
            conditions.append(parse_condition(resource))
        elif rtype == "MedicationStatement":
            medications.append(parse_medication(resource))
        elif rtype == "AllergyIntolerance":
            allergies.append(parse_allergy(resource))

    return PatientHistory(
        conditions=conditions,
        medications=medications,
        allergies=allergies,
    )


# ------------------------------------------------------------------
# Service class
# ------------------------------------------------------------------
class MetriportService:
    """Fetch and normalise patient history from Metriport.

    Uses the consolidated data query (POST + poll) pattern.
    Protected by a circuit breaker that trips after consecutive
    API failures and blocks requests for a cooldown period.

    Time complexity: O(P + N) where P = poll attempts, N = bundle entries.
    """

    def __init__(self, settings: Settings) -> None:
        self._base_url = settings.metriport_base_url.rstrip("/")
        self._poll_interval = settings.metriport_poll_interval_seconds
        self._max_polls = settings.metriport_max_poll_attempts
        self._breaker = CircuitBreaker(
            failure_threshold=settings.metriport_cb_failure_threshold,
            cooldown_seconds=settings.metriport_cb_cooldown_seconds,
        )
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            headers={
                "x-api-key": settings.metriport_api_key,
                "Content-Type": "application/json",
            },
            timeout=settings.metriport_timeout_seconds,
        )

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        await self._client.aclose()

    async def fetch_patient_history(self, patient_id: str) -> PatientHistory:
        """Fetch consolidated patient history from Metriport.

        Args:
            patient_id: The Metriport patient identifier.

        Returns:
            Normalised PatientHistory with conditions, medications, allergies.

        Raises:
            MetriportCircuitOpenError: Circuit breaker is tripped.
            MetriportTimeoutError: Polling exceeded max attempts.
            MetriportError: Any other API failure.
        """
        self._breaker.check()
        try:
            request_id = await self._start_query(patient_id)
            bundle = await self._poll_until_ready(patient_id, request_id)
            history = parse_fhir_bundle(bundle)
            self._breaker.record_success()
            logger.info(
                "Fetched %d records for patient %s",
                history.total_records,
                patient_id,
            )
            return history
        except MetriportCircuitOpenError:
            raise
        except Exception as exc:
            self._breaker.record_failure()
            if isinstance(exc, MetriportError):
                raise
            raise MetriportError(
                f"Failed to fetch patient history: {exc}"
            ) from exc

    async def _start_query(self, patient_id: str) -> str:
        """POST to start a consolidated data query.

        Returns the request_id for polling.
        """
        url = f"/medical/v1/patient/{patient_id}/consolidated/query"
        resp = await self._client.post(
            url,
            params={
                "resources": TRIAGE_RESOURCES,
                "conversionType": "json",
            },
        )
        resp.raise_for_status()
        data = resp.json()
        request_id = data.get("requestId")
        if not request_id:
            raise MetriportError("No requestId in query response")
        return request_id

    async def _poll_until_ready(
        self, patient_id: str, request_id: str
    ) -> dict[str, Any]:
        """Poll the query status until completed or timeout.

        Returns the FHIR Bundle dict.
        """
        url = f"/medical/v1/patient/{patient_id}/consolidated/query"
        for attempt in range(self._max_polls):
            resp = await self._client.get(
                url, params={"requestId": request_id}
            )
            resp.raise_for_status()
            data = resp.json()
            status = data.get("status")
            if status == "completed":
                return data.get("bundle", {})
            if status == "failed":
                raise MetriportError(
                    f"Consolidated query failed: {data.get('message', 'unknown')}"
                )
            await asyncio.sleep(self._poll_interval)

        raise MetriportTimeoutError(
            f"Query {request_id} did not complete after {self._max_polls} polls"
        )
