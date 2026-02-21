"""CDS Hooks models per HL7 CDS Hooks 2.0 specification.

Reference: https://cds-hooks.hl7.org/2.0/
"""

from __future__ import annotations

from pydantic import BaseModel, Field, HttpUrl

from app.models.enums import CdsIndicator

SUMMARY_MAX_LENGTH = 140
DETAIL_MAX_LENGTH = 5000
LABEL_MAX_LENGTH = 200


# ------------------------------------------------------------------
# Response models (§ CDS Service Response)
# ------------------------------------------------------------------
class CdsSource(BaseModel):
    """Source attribution for a CDS Hook card."""

    label: str = Field(..., min_length=1, max_length=LABEL_MAX_LENGTH)
    url: HttpUrl | None = None
    icon: HttpUrl | None = None


class CdsSuggestion(BaseModel):
    """An actionable suggestion attached to a CDS Hook card."""

    label: str = Field(..., min_length=1, max_length=LABEL_MAX_LENGTH)
    uuid: str | None = None
    is_recommended: bool = False


class CdsCard(BaseModel):
    """A single CDS Hooks response card.

    Cards are the primary display unit in the CDS Hooks spec,
    shown to clinicians within the EHR workflow.
    """

    summary: str = Field(..., min_length=1, max_length=SUMMARY_MAX_LENGTH)
    detail: str | None = Field(default=None, max_length=DETAIL_MAX_LENGTH)
    indicator: CdsIndicator
    source: CdsSource
    suggestions: list[CdsSuggestion] = Field(default_factory=list)


class CdsHookResponse(BaseModel):
    """Top-level CDS Hooks service response containing cards."""

    cards: list[CdsCard] = Field(default_factory=list)


# ------------------------------------------------------------------
# Discovery models (§ Discovery)
# ------------------------------------------------------------------
class CdsServiceDefinition(BaseModel):
    """A single CDS service advertised via the discovery endpoint."""

    hook: str = Field(..., min_length=1)
    title: str = Field(default="")
    description: str = Field(default="")
    id: str = Field(..., min_length=1)
    prefetch: dict[str, str] = Field(default_factory=dict)


class CdsDiscoveryResponse(BaseModel):
    """Discovery response listing all available CDS services."""

    services: list[CdsServiceDefinition] = Field(default_factory=list)


# ------------------------------------------------------------------
# Request models (§ CDS Service Request)
# ------------------------------------------------------------------
class CdsHookContext(BaseModel):
    """Context payload for emergAI triage hook requests.

    The ``session_id`` is required so the service can look up
    or receive the triage result for formatting.
    """

    session_id: str = Field(..., min_length=1)


class CdsHookRequest(BaseModel):
    """Incoming CDS Hooks service request.

    Follows the HL7 CDS Hooks 2.0 request shape with a custom
    context schema for triage sessions.
    """

    hook_instance: str = Field(..., alias="hookInstance", min_length=1)
    hook: str = Field(..., min_length=1)
    context: CdsHookContext
    fhir_server: str | None = Field(default=None, alias="fhirServer")
    prefetch: dict[str, object] = Field(default_factory=dict)
