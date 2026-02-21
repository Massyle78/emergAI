"""Gemini AI service for symptom extraction and triage assessment."""

import json
import os
import re
from uuid import UUID

from dotenv import load_dotenv
from google import genai
from tenacity import retry, stop_after_attempt, wait_exponential

from app.models.enums import AcuityLevel, SymptomSeverity
from app.models.risk import ContributingFactor, RiskAssessmentCreate
from app.models.symptoms import SymptomDetail, SymptomExtractionCreate
from app.prompts.triage_prompt import SYSTEM_PROMPT, build_initial_message

load_dotenv()

client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
MODEL = "gemini-3-flash-preview"

# in-memory session store — swap for Redis in production
_sessions: dict[str, list[dict]] = {}

# ---------- session management ----------

def _get_or_create_session(session_id: str) -> list[dict]:
    if session_id not in _sessions:
        _sessions[session_id] = []
    return _sessions[session_id]


def _append_turn(session_id: str, role: str, text: str) -> None:
    _sessions[session_id].append(
        {"role": role, "parts": [{"text": text}]}
    )


# ---------- gemini call ----------

@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=10))
def _call_gemini(contents: list[dict]) -> str:
    response = client.models.generate_content(
        model=MODEL,
        contents=contents,
        config={"system_instruction": SYSTEM_PROMPT}
    )
    return response.text


# ---------- JSON extraction ----------

def _extract_json(text: str) -> dict | None:
    try:
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            return json.loads(match.group())
    except json.JSONDecodeError:
        return None


# ---------- public API ----------

def start_session(session_id: str, patient_data: dict) -> dict:
    """
    Called once when patient submits the intake form.
    Returns Gemini's first follow-up question or triage result.
    """
    _get_or_create_session(session_id)
    initial_message = build_initial_message(patient_data)
    _append_turn(session_id, "user", initial_message)

    reply = _call_gemini(_sessions[session_id])
    _append_turn(session_id, "model", reply)

    return _process_reply(session_id, reply)


def send_message(session_id: str, message: str) -> dict:
    """
    Called for each patient follow-up answer.
    Returns next question or triage result.
    """
    history = _get_or_create_session(session_id)
    _append_turn(session_id, "user", message)

    reply = _call_gemini(history)
    _append_turn(session_id, "model", reply)

    return _process_reply(session_id, reply)


def _process_reply(session_id: str, reply: str) -> dict:
    """Parse Gemini's reply — either a question or a completed triage."""
    raw = _extract_json(reply)

    if raw and raw.get("ready_for_triage"):
        symptom_extraction = _build_symptom_extraction(session_id, raw)
        risk_assessment = _build_risk_assessment(session_id, raw)
        return {
            "reply": reply,
            "triage_complete": True,
            "symptom_extraction": symptom_extraction.model_dump(),
            "risk_assessment": risk_assessment.model_dump()
        }

    return {"reply": reply, "triage_complete": False}


# ---------- model builders ----------

def _build_symptom_extraction(session_id: str, data: dict) -> SymptomExtractionCreate:
    symptoms = [
        SymptomDetail(
            name=s["name"],
            severity=SymptomSeverity(s["severity"]),
            description=s.get("description"),
            body_region=s.get("body_region"),
            onset_description=s.get("onset_description")
        )
        for s in data.get("symptoms", [])
    ]
    return SymptomExtractionCreate(
        session_id=UUID(session_id),
        chief_complaint=data["chief_complaint"],
        symptoms=symptoms,
        follow_up_questions=data.get("follow_up_questions", []),
        confidence=data["confidence"]
    )


def _build_risk_assessment(session_id: str, data: dict) -> RiskAssessmentCreate:
    factors = [
        ContributingFactor(
            name=f["name"],
            weight=f["weight"],
            description=f["description"]
        )
        for f in data.get("contributing_factors", [])
    ]
    return RiskAssessmentCreate(
        session_id=UUID(session_id),
        score=data["score"],
        acuity_level=AcuityLevel(data["acuity_level"]),
        reasoning=data["reasoning"],
        contributing_factors=factors
    )