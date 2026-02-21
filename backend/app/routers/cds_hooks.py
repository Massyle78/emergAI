"""CDS Hooks discovery and service endpoints.

Implements the HL7 CDS Hooks 2.0 API surface:
  GET  /cds-services              – Discovery
  POST /cds-services/triage-risk  – Triage risk service
"""

from __future__ import annotations

import logging

from fastapi import APIRouter

from app.models.cds_hooks import (
    CdsDiscoveryResponse,
    CdsHookRequest,
    CdsHookResponse,
    CdsServiceDefinition,
)

logger = logging.getLogger("app.routers.cds_hooks")

router = APIRouter(tags=["CDS Hooks"])

TRIAGE_SERVICE = CdsServiceDefinition(
    hook="patient-view",
    title="emergAI Triage Risk Assessment",
    description=(
        "Provides real-time multimodal risk assessment and triage "
        "recommendations based on vitals, symptoms, and patient history."
    ),
    id="triage-risk",
)


@router.get(
    "/cds-services",
    response_model=CdsDiscoveryResponse,
    summary="CDS Hooks Discovery",
)
async def discover_services() -> CdsDiscoveryResponse:
    """Return the list of CDS services this server provides.

    Per the HL7 CDS Hooks 2.0 spec, EHR systems call this
    endpoint to discover available decision-support services.
    """
    return CdsDiscoveryResponse(services=[TRIAGE_SERVICE])


@router.post(
    "/cds-services/triage-risk",
    response_model=CdsHookResponse,
    summary="Triage Risk CDS Service",
)
async def triage_risk_service(
    request: CdsHookRequest,
) -> CdsHookResponse:
    """Accept a CDS Hook request and return triage risk cards.

    In the current implementation the endpoint validates the
    incoming request and returns a placeholder response.  Once
    a triage-result persistence layer is available the service
    will look up the session referenced by ``context.session_id``
    and format the stored result into CDS cards.
    """
    session_id = request.context.session_id
    logger.info(
        "CDS hook request for session %s (hook=%s)",
        session_id,
        request.hook,
    )

    from app.models.cds_hooks import CdsCard, CdsSource
    from app.models.enums import CdsIndicator

    card = CdsCard(
        summary=f"Triage pending for session {session_id}",
        detail=(
            "The triage result for this session has not been persisted yet. "
            "Invoke the orchestration pipeline and call this endpoint again."
        ),
        indicator=CdsIndicator.INFO,
        source=CdsSource(label="emergAI Triage Engine"),
    )
    return CdsHookResponse(cards=[card])
