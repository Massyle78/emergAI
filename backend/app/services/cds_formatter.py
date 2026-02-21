"""CDS Hooks output formatter.

Converts a TriageResult into an HL7 CDS Hooks 2.0 compliant
CdsHookResponse.  All functions are pure (no I/O) so they can
be tested deterministically without mocks.

Card generation strategy:
  1. **Risk assessment card** – always present; carries the ESI
     level, composite score, and reasoning chain.
  2. **Vitals alert card** – present when heart-rate data exists
     and falls outside the normal range.
  3. **Symptom summary card** – present when symptom extraction
     produced at least one symptom.
"""

from __future__ import annotations

from app.models.cds_hooks import (
    CdsCard,
    CdsHookResponse,
    CdsSource,
    CdsSuggestion,
)
from app.models.enums import AcuityLevel, CdsIndicator
from app.models.symptoms import SymptomExtractionCreate
from app.models.triage_result import TriageResult
from app.models.vitals import VitalsCreate

SOURCE = CdsSource(label="emergAI Triage Engine")

_NORMAL_HR_LOW = 60.0
_NORMAL_HR_HIGH = 100.0

_ACUITY_LABELS: dict[AcuityLevel, str] = {
    AcuityLevel.RESUSCITATION: "Resuscitation",
    AcuityLevel.EMERGENT: "Emergent",
    AcuityLevel.URGENT: "Urgent",
    AcuityLevel.LESS_URGENT: "Less Urgent",
    AcuityLevel.NON_URGENT: "Non-Urgent",
}


# ------------------------------------------------------------------
# Mapping helpers
# ------------------------------------------------------------------
def acuity_to_indicator(acuity: AcuityLevel) -> CdsIndicator:
    """Map an ESI acuity level to the appropriate CDS indicator."""
    if acuity <= AcuityLevel.EMERGENT:
        return CdsIndicator.CRITICAL
    if acuity == AcuityLevel.URGENT:
        return CdsIndicator.WARNING
    return CdsIndicator.INFO


def build_suggestions(acuity: AcuityLevel) -> list[CdsSuggestion]:
    """Generate clinically appropriate action suggestions for the acuity."""
    if acuity == AcuityLevel.RESUSCITATION:
        return [
            CdsSuggestion(label="Initiate resuscitation protocol", is_recommended=True),
            CdsSuggestion(label="Page attending physician"),
        ]
    if acuity == AcuityLevel.EMERGENT:
        return [
            CdsSuggestion(label="Expedite clinical evaluation", is_recommended=True),
            CdsSuggestion(label="Order diagnostic workup"),
        ]
    if acuity == AcuityLevel.URGENT:
        return [
            CdsSuggestion(label="Standard triage evaluation", is_recommended=True),
            CdsSuggestion(label="Monitor vitals"),
        ]
    return [
        CdsSuggestion(label="Routine assessment"),
        CdsSuggestion(label="Schedule follow-up if needed"),
    ]


# ------------------------------------------------------------------
# Card builders
# ------------------------------------------------------------------
def build_risk_card(result: TriageResult) -> CdsCard:
    """Build the primary risk assessment card (always present)."""
    risk = result.risk
    acuity = risk.acuity_level
    label = _ACUITY_LABELS.get(acuity, str(acuity))

    summary = f"ESI {acuity.value} – {label} (score {risk.score:.2f})"

    detail_parts = [f"**Risk Score:** {risk.score:.2f}", f"**Reasoning:** {risk.reasoning}"]
    if risk.contributing_factors:
        lines = [f"- {f.name}: {f.description}" for f in risk.contributing_factors]
        detail_parts.append("**Contributing Factors:**\n" + "\n".join(lines))
    if risk.similar_cases_count:
        detail_parts.append(
            f"**Similar Cases:** {risk.similar_cases_count} historical case(s) found"
        )
    if result.is_partial:
        detail_parts.append(
            "**Note:** Some data sources were unavailable; "
            "this assessment may be incomplete."
        )

    return CdsCard(
        summary=summary,
        detail="\n\n".join(detail_parts),
        indicator=acuity_to_indicator(acuity),
        source=SOURCE,
        suggestions=build_suggestions(acuity),
    )


def build_vitals_card(vitals: VitalsCreate) -> CdsCard | None:
    """Build a vitals alert card when HR is outside normal range.

    Returns None if vitals are within normal limits.
    """
    hr = vitals.heart_rate_bpm
    if _NORMAL_HR_LOW <= hr <= _NORMAL_HR_HIGH:
        return None

    if hr < _NORMAL_HR_LOW:
        summary = f"Bradycardia detected: HR {hr:.0f} bpm"
    else:
        summary = f"Tachycardia detected: HR {hr:.0f} bpm"

    detail = (
        f"Heart rate of {hr:.0f} bpm is outside the normal range "
        f"({_NORMAL_HR_LOW:.0f}–{_NORMAL_HR_HIGH:.0f} bpm). "
        f"Measurement confidence: {vitals.confidence:.0%}."
    )

    return CdsCard(
        summary=summary,
        detail=detail,
        indicator=CdsIndicator.WARNING,
        source=SOURCE,
    )


def build_symptom_card(symptoms: SymptomExtractionCreate) -> CdsCard | None:
    """Build a symptom summary card when symptoms were extracted.

    Returns None when no symptoms were detected.
    """
    if not symptoms.symptoms:
        return None

    summary = f'Chief complaint: "{_truncate(symptoms.chief_complaint, 100)}"'

    lines = [
        f"- **{s.name}** ({s.severity.value})"
        + (f": {s.description}" if s.description else "")
        for s in symptoms.symptoms
    ]
    detail_parts = [
        f"**Symptoms ({len(symptoms.symptoms)}):**",
        "\n".join(lines),
    ]
    if symptoms.follow_up_questions:
        q_lines = [f"- {q}" for q in symptoms.follow_up_questions]
        detail_parts.append("**Follow-up questions:**\n" + "\n".join(q_lines))
    detail_parts.append(f"Extraction confidence: {symptoms.confidence:.0%}")

    return CdsCard(
        summary=summary,
        detail="\n\n".join(detail_parts),
        indicator=CdsIndicator.INFO,
        source=SOURCE,
    )


# ------------------------------------------------------------------
# Top-level formatter
# ------------------------------------------------------------------
def format_triage_response(result: TriageResult) -> CdsHookResponse:
    """Convert a TriageResult into a CDS Hooks response with cards.

    Always produces at least one card (the risk assessment).
    Optional vitals and symptom cards are appended when the
    corresponding data is available and clinically noteworthy.
    """
    cards: list[CdsCard] = [build_risk_card(result)]

    if result.vitals is not None:
        vitals_card = build_vitals_card(result.vitals)
        if vitals_card is not None:
            cards.append(vitals_card)

    if result.symptoms is not None:
        symptom_card = build_symptom_card(result.symptoms)
        if symptom_card is not None:
            cards.append(symptom_card)

    return CdsHookResponse(cards=cards)


# ------------------------------------------------------------------
# Utilities
# ------------------------------------------------------------------
def _truncate(text: str, max_len: int) -> str:
    """Truncate text with ellipsis if it exceeds *max_len*."""
    if len(text) <= max_len:
        return text
    return text[: max_len - 3] + "..."
