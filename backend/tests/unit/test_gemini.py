"""Standalone test — run with: python -m backend.test_gemini"""

from app.services.gemini_service import send_message, start_session
import uuid

session_id = str(uuid.uuid4())

patient = {
    "name": "John Doe",
    "dob": "1966-03-15",
    "gender": "male",
    "weight": 80,
    "chief_complaint": "chest pain and shortness of breath",
    "symptom_onset": "2 hours ago",
    "pain_score": 8,
    "key_symptoms": ["chest pain", "shortness of breath", "sweating"],
    "medical_history": ["hypertension"],
    "medications": ["atenolol"],
    "heart_rate": 102
}

result = start_session(session_id, patient)
print(f"Gemini: {result['reply']}\n")

while not result["triage_complete"]:
    user_input = input("You: ")
    result = send_message(session_id, user_input)
    print(f"Gemini: {result['reply']}\n")

print("✅ Triage complete")
print("Symptom extraction:", result["symptom_extraction"])
print("Risk assessment:", result["risk_assessment"])