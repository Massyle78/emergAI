"""Models for pgvector similarity search results and embedding input."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field

from app.models.enums import SymptomSeverity


class SimilarCase(BaseModel):
    """A historical triage session returned by KNN similarity search."""

    id: UUID
    patient_id: UUID
    status: str
    similarity: float = Field(ge=0.0, le=1.0)


class EmbeddingInput(BaseModel):
    """Structured data to be serialized into text for embedding.

    Captures the clinical snapshot of a triage session so that
    semantically similar cases cluster together in vector space.
    """

    chief_complaint: str
    symptoms: list[str] = Field(default_factory=list)
    severities: list[str] = Field(default_factory=list)
    vitals_summary: str | None = None
    conditions: list[str] = Field(default_factory=list)
    medications: list[str] = Field(default_factory=list)
    allergies: list[str] = Field(default_factory=list)


def build_embedding_text(data: EmbeddingInput) -> str:
    """Serialize an EmbeddingInput into a single text string.

    The format is deterministic so identical clinical snapshots
    produce identical embeddings.
    """
    parts: list[str] = [f"Chief complaint: {data.chief_complaint}"]
    if data.symptoms:
        symptom_strs = [
            f"{s} ({sev})" if sev else s
            for s, sev in zip(data.symptoms, data.severities + [""] * len(data.symptoms))
        ]
        parts.append("Symptoms: " + "; ".join(symptom_strs))
    if data.vitals_summary:
        parts.append(f"Vitals: {data.vitals_summary}")
    if data.conditions:
        parts.append("History: " + "; ".join(data.conditions))
    if data.medications:
        parts.append("Medications: " + "; ".join(data.medications))
    if data.allergies:
        parts.append("Allergies: " + "; ".join(data.allergies))
    return "\n".join(parts)
