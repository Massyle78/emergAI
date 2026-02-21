"""Triage orchestration engine.

Coordinates parallel dispatch of vitals extraction (open-rppg),
symptom extraction (Gemini), and EHR history retrieval (Metriport).
Aggregates outputs, generates embeddings for similarity search, and
computes a composite risk score with a human-readable reasoning chain.

All scoring logic lives in pure functions at module level for easy
unit testing; the TriageOrchestrator class owns the async I/O.
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from uuid import UUID

from app.config import Settings
from app.models.enums import AcuityLevel, SymptomSeverity
from app.models.patient_history import PatientHistory
from app.models.risk import ContributingFactor, RiskAssessmentCreate
from app.models.similarity import EmbeddingInput, SimilarCase
from app.models.symptoms import SymptomDetail, SymptomExtractionCreate
from app.models.triage_result import TriageResult
from app.models.vitals import VitalsCreate
from app.repositories.similarity_repository import SimilarityRepository
from app.services.embedding_service import EmbeddingService
from app.services.gemini_service import GeminiService
from app.services.metriport_service import MetriportService
from app.services.vitals_service import VitalsService

logger = logging.getLogger("app.services.orchestrator")

# ------------------------------------------------------------------
# Constants
# ------------------------------------------------------------------
SYMPTOM_WEIGHT = 0.40
VITALS_WEIGHT = 0.30
HISTORY_WEIGHT = 0.30

_SEVERITY_SCORES: dict[SymptomSeverity, float] = {
    SymptomSeverity.CRITICAL: 0.95,
    SymptomSeverity.SEVERE: 0.70,
    SymptomSeverity.MODERATE: 0.40,
    SymptomSeverity.MILD: 0.15,
}

_NORMAL_HR_LOW = 60.0
_NORMAL_HR_HIGH = 100.0
_CRITICAL_HR_LOW = 50.0
_CRITICAL_HR_HIGH = 130.0

_ACUITY_THRESHOLDS: list[tuple[float, AcuityLevel]] = [
    (0.85, AcuityLevel.RESUSCITATION),
    (0.65, AcuityLevel.EMERGENT),
    (0.45, AcuityLevel.URGENT),
    (0.25, AcuityLevel.LESS_URGENT),
]

BASELINE_SCORE = 0.50


# ------------------------------------------------------------------
# Pure scoring functions
# ------------------------------------------------------------------
def severity_score(severity: SymptomSeverity) -> float:
    """Map a symptom severity enum to a 0-1 risk contribution."""
    return _SEVERITY_SCORES[severity]


def compute_symptom_score(
    symptoms: SymptomExtractionCreate | None,
) -> tuple[float, list[ContributingFactor]]:
    """Derive a 0-1 symptom risk component.

    Returns (score, contributing_factors).  When *symptoms* is None
    (extraction failed) a moderate baseline is returned.
    """
    if symptoms is None:
        return BASELINE_SCORE, [
            ContributingFactor(
                name="Symptom extraction unavailable",
                weight=BASELINE_SCORE,
                description=(
                    "Symptom data could not be extracted; "
                    "defaulting to moderate baseline"
                ),
            ),
        ]

    details: list[SymptomDetail] = symptoms.symptoms
    if not details:
        return 0.10, [
            ContributingFactor(
                name="No symptoms detected",
                weight=0.10,
                description="AI did not detect any symptoms from the provided media",
            ),
        ]

    sev_values = [severity_score(d.severity) for d in details]
    max_sev = max(sev_values)
    avg_sev = sum(sev_values) / len(sev_values)
    raw = 0.70 * max_sev + 0.30 * avg_sev
    score = min(1.0, raw * symptoms.confidence)

    max_symptom = max(details, key=lambda d: severity_score(d.severity))
    factors = [
        ContributingFactor(
            name="Symptom severity",
            weight=round(score, 3),
            description=(
                f"Highest severity: {max_symptom.severity.value} "
                f"({max_symptom.name}); {len(details)} symptom(s) detected "
                f"(confidence {symptoms.confidence:.0%})"
            ),
        ),
    ]
    return score, factors


def compute_vitals_score(
    vitals: VitalsCreate | None,
) -> tuple[float | None, list[ContributingFactor]]:
    """Derive a 0-1 vitals risk component from heart-rate data.

    Returns (None, []) when vitals are unavailable so the composite
    calculation can redistribute weight.
    """
    if vitals is None:
        return None, []

    hr = vitals.heart_rate_bpm
    if hr < _CRITICAL_HR_LOW or hr > _CRITICAL_HR_HIGH:
        raw = 0.85
        desc = f"HR {hr:.0f} bpm is critically abnormal"
    elif hr < _NORMAL_HR_LOW or hr > _NORMAL_HR_HIGH:
        raw = 0.50
        desc = f"HR {hr:.0f} bpm is outside normal range (60-100)"
    else:
        raw = 0.10
        desc = f"HR {hr:.0f} bpm is within normal range"

    score = min(1.0, raw * vitals.confidence)
    factors = [
        ContributingFactor(
            name="Heart rate",
            weight=round(score, 3),
            description=desc,
        ),
    ]
    return score, factors


def compute_history_score(
    history: PatientHistory | None,
) -> tuple[float | None, list[ContributingFactor]]:
    """Derive a 0-1 history risk component from EHR data.

    Returns (None, []) when history is unavailable.
    """
    if history is None or history.is_empty:
        return None, []

    cond = min(len(history.conditions) * 0.10, 0.50)
    meds = min(len(history.medications) * 0.05, 0.30)
    allergy = min(len(history.allergies) * 0.08, 0.30)
    score = min(1.0, cond + meds + allergy)

    factors: list[ContributingFactor] = []
    if history.conditions:
        factors.append(
            ContributingFactor(
                name="Medical conditions",
                weight=round(cond, 3),
                description=f"{len(history.conditions)} active condition(s) on record",
            )
        )
    if history.medications:
        factors.append(
            ContributingFactor(
                name="Medications",
                weight=round(meds, 3),
                description=f"{len(history.medications)} active medication(s)",
            )
        )
    if history.allergies:
        factors.append(
            ContributingFactor(
                name="Allergies",
                weight=round(allergy, 3),
                description=f"{len(history.allergies)} allergy/intolerance(s) on record",
            )
        )
    return score, factors


def compute_composite_score(
    symptom: float,
    vitals: float | None,
    history: float | None,
) -> float:
    """Weighted average with dynamic weight normalisation.

    Components whose value is None are excluded and their weight
    is redistributed proportionally among the remaining components.
    """
    components: list[tuple[float, float]] = [(symptom, SYMPTOM_WEIGHT)]
    if vitals is not None:
        components.append((vitals, VITALS_WEIGHT))
    if history is not None:
        components.append((history, HISTORY_WEIGHT))

    total_weight = sum(w for _, w in components)
    if total_weight == 0:
        return BASELINE_SCORE

    return sum(score * weight for score, weight in components) / total_weight


def score_to_acuity(score: float) -> AcuityLevel:
    """Map a composite risk score to an ESI acuity level."""
    for threshold, level in _ACUITY_THRESHOLDS:
        if score >= threshold:
            return level
    return AcuityLevel.NON_URGENT


def build_reasoning(
    composite: float,
    acuity: AcuityLevel,
    factors: list[ContributingFactor],
    symptoms: SymptomExtractionCreate | None,
    vitals: VitalsCreate | None,
    history: PatientHistory | None,
    similar_count: int,
) -> str:
    """Build a human-readable reasoning chain for the risk assessment."""
    parts = [f"Risk score {composite:.2f} (ESI {acuity.value} - {acuity.name})."]

    if symptoms and symptoms.symptoms:
        parts.append(f'Chief complaint: "{symptoms.chief_complaint}".')
    elif symptoms:
        parts.append("No symptoms detected by AI extraction.")
    else:
        parts.append("Symptom extraction was not available.")

    if vitals:
        parts.append(f"Heart rate: {vitals.heart_rate_bpm:.0f} bpm.")
    else:
        parts.append("Vitals data was not available.")

    if history and not history.is_empty:
        parts.append(
            f"Patient history: {len(history.conditions)} condition(s), "
            f"{len(history.medications)} medication(s), "
            f"{len(history.allergies)} allergy/intolerance(s)."
        )
    else:
        parts.append("No patient history available.")

    if similar_count:
        parts.append(f"{similar_count} similar historical case(s) found.")

    if factors:
        factor_strs = [f"{f.name} ({f.weight:.2f})" for f in factors]
        parts.append("Contributing factors: " + ", ".join(factor_strs) + ".")

    return " ".join(parts)


def build_embedding_input(
    vitals: VitalsCreate | None,
    symptoms: SymptomExtractionCreate | None,
    history: PatientHistory | None,
) -> EmbeddingInput:
    """Map service outputs to an EmbeddingInput for vector search."""
    chief = symptoms.chief_complaint if symptoms else "Unknown"
    names = [s.name for s in symptoms.symptoms] if symptoms else []
    sevs = [s.severity.value for s in symptoms.symptoms] if symptoms else []

    vs: str | None = None
    if vitals:
        vs = f"HR {vitals.heart_rate_bpm:.0f} bpm (confidence {vitals.confidence:.0%})"

    conds: list[str] = []
    meds: list[str] = []
    algs: list[str] = []
    if history:
        conds = [c.code.display or c.text or "Unknown" for c in history.conditions]
        meds = [m.code.display or m.text or "Unknown" for m in history.medications]
        algs = [a.code.display or a.text or "Unknown" for a in history.allergies]

    return EmbeddingInput(
        chief_complaint=chief,
        symptoms=names,
        severities=sevs,
        vitals_summary=vs,
        conditions=conds,
        medications=meds,
        allergies=algs,
    )


def compute_risk(
    session_id: UUID,
    vitals: VitalsCreate | None,
    symptoms: SymptomExtractionCreate | None,
    history: PatientHistory | None,
    similar_cases: list[SimilarCase],
) -> RiskAssessmentCreate:
    """Full risk computation pipeline.

    Computes component scores, combines them into a composite,
    maps to ESI acuity, and builds a reasoning chain.
    """
    sym_score, sym_factors = compute_symptom_score(symptoms)
    vit_score, vit_factors = compute_vitals_score(vitals)
    his_score, his_factors = compute_history_score(history)

    all_factors = sym_factors + vit_factors + his_factors
    composite = compute_composite_score(sym_score, vit_score, his_score)
    acuity = score_to_acuity(composite)

    reasoning = build_reasoning(
        composite, acuity, all_factors,
        symptoms, vitals, history, len(similar_cases),
    )

    return RiskAssessmentCreate(
        session_id=session_id,
        score=round(composite, 4),
        acuity_level=acuity,
        reasoning=reasoning,
        contributing_factors=all_factors,
        similar_cases_count=len(similar_cases),
    )


# ------------------------------------------------------------------
# Orchestrator class
# ------------------------------------------------------------------
class TriageOrchestrator:
    """Coordinate triage services and compute risk assessments.

    Dispatches vitals, symptom, and history extraction in parallel
    using ``asyncio.gather``.  Individual service failures are
    captured and surfaced as partial results rather than aborting
    the entire triage run.

    Time complexity: O(max(T_vitals, T_gemini, T_metriport) + T_embed)
    """

    def __init__(
        self,
        vitals_service: VitalsService,
        gemini_service: GeminiService,
        metriport_service: MetriportService,
        embedding_service: EmbeddingService,
        similarity_repo: SimilarityRepository,
        settings: Settings,
    ) -> None:
        self._vitals = vitals_service
        self._gemini = gemini_service
        self._metriport = metriport_service
        self._embedding = embedding_service
        self._similarity = similarity_repo
        self._match_count = settings.similarity_match_count

    async def run_triage(
        self,
        session_id: UUID,
        video_path: Path | None = None,
        audio_path: Path | None = None,
        image_path: Path | None = None,
        metriport_patient_id: str | None = None,
    ) -> TriageResult:
        """Execute a full triage orchestration run.

        Args:
            session_id: Triage session identifier.
            video_path: Video file for rPPG vitals extraction.
            audio_path: Audio file for Gemini symptom extraction.
            image_path: Image file for Gemini symptom extraction.
            metriport_patient_id: Metriport patient ID for EHR fetch.

        Returns:
            TriageResult containing all service outputs, risk
            assessment, and any errors from failed services.
        """
        logger.info("Starting triage orchestration for session %s", session_id)

        vitals, symptoms, history, errors = await self._dispatch(
            session_id, video_path, audio_path, image_path,
            metriport_patient_id,
        )

        similar_cases = await self._embed_and_search(
            session_id, vitals, symptoms, history,
        )

        risk = compute_risk(session_id, vitals, symptoms, history, similar_cases)

        logger.info(
            "Triage complete for session %s: score=%.2f, ESI=%d, errors=%d",
            session_id, risk.score, risk.acuity_level.value, len(errors),
        )

        return TriageResult(
            session_id=session_id,
            vitals=vitals,
            symptoms=symptoms,
            history=history,
            similar_cases=similar_cases,
            risk=risk,
            errors=errors,
        )

    async def _dispatch(
        self,
        session_id: UUID,
        video_path: Path | None,
        audio_path: Path | None,
        image_path: Path | None,
        metriport_patient_id: str | None,
    ) -> tuple[
        VitalsCreate | None,
        SymptomExtractionCreate | None,
        PatientHistory | None,
        list[str],
    ]:
        """Launch extraction services in parallel and collect results."""
        tasks: list[asyncio.Task[object]] = []
        labels: list[str] = []

        if video_path:
            tasks.append(
                asyncio.ensure_future(
                    asyncio.to_thread(
                        self._vitals.extract_vitals, video_path, session_id
                    )
                )
            )
            labels.append("vitals")

        tasks.append(
            asyncio.ensure_future(
                self._gemini.extract_symptoms(
                    session_id, audio_path, image_path
                )
            )
        )
        labels.append("symptoms")

        if metriport_patient_id:
            tasks.append(
                asyncio.ensure_future(
                    self._metriport.fetch_patient_history(metriport_patient_id)
                )
            )
            labels.append("history")

        results = await asyncio.gather(*tasks, return_exceptions=True)

        vitals: VitalsCreate | None = None
        symptoms: SymptomExtractionCreate | None = None
        history: PatientHistory | None = None
        errors: list[str] = []

        for label, result in zip(labels, results):
            if isinstance(result, BaseException):
                msg = f"{label}: {result}"
                errors.append(msg)
                logger.warning(
                    "Service '%s' failed for session %s: %s",
                    label, session_id, result,
                )
            elif label == "vitals":
                vitals = result  # type: ignore[assignment]
            elif label == "symptoms":
                symptoms = result  # type: ignore[assignment]
            elif label == "history":
                history = result  # type: ignore[assignment]

        return vitals, symptoms, history, errors

    async def _embed_and_search(
        self,
        session_id: UUID,
        vitals: VitalsCreate | None,
        symptoms: SymptomExtractionCreate | None,
        history: PatientHistory | None,
    ) -> list[SimilarCase]:
        """Generate embedding, store it, and find similar cases.

        Returns an empty list on any failure so the triage result
        is still usable without similarity data.
        """
        try:
            embedding_input = build_embedding_input(vitals, symptoms, history)
            embedding = await asyncio.to_thread(
                self._embedding.embed_triage_data, embedding_input
            )
            await self._similarity.store_embedding(session_id, embedding)
            cases = await self._similarity.find_similar(
                embedding, self._match_count
            )
            logger.info(
                "Found %d similar cases for session %s",
                len(cases), session_id,
            )
            return cases
        except Exception as exc:
            logger.warning(
                "Embedding/similarity search failed for session %s: %s",
                session_id, exc,
            )
            return []
