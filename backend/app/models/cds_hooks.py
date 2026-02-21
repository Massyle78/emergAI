"""CDS Hooks card models per HL7 CDS Hooks specification.

Reference: https://cds-hooks.hl7.org/2.0/#cds-service-response
"""

from pydantic import BaseModel, Field, HttpUrl

from app.models.enums import CdsIndicator

SUMMARY_MAX_LENGTH = 140
DETAIL_MAX_LENGTH = 5000
LABEL_MAX_LENGTH = 200


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
