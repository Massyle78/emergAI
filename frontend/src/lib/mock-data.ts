/**
 * Simulated patient queue data for the clinician dashboard.
 *
 * In production this would come from the backend via REST or
 * real-time subscriptions. The mock data demonstrates all ESI
 * levels and CDS card variants.
 */

import type {
  PatientQueueItem,
  TriageResultData,
} from "@/types/dashboard";

const PATIENTS: PatientQueueItem[] = [
  {
    id: "a1b2c3d4-0001-4000-8000-000000000001",
    name: "Maria Chen",
    age: 58,
    sex: "F",
    chief_complaint: "Severe chest pain radiating to left arm",
    acuity_level: 2,
    score: 0.87,
    arrived_at: new Date(Date.now() - 18 * 60_000).toISOString(),
    status: "waiting",
  },
  {
    id: "a1b2c3d4-0002-4000-8000-000000000002",
    name: "James Walker",
    age: 34,
    sex: "M",
    chief_complaint: "Laceration on right forearm, moderate bleeding",
    acuity_level: 3,
    score: 0.52,
    arrived_at: new Date(Date.now() - 42 * 60_000).toISOString(),
    status: "waiting",
  },
  {
    id: "a1b2c3d4-0003-4000-8000-000000000003",
    name: "Aisha Patel",
    age: 72,
    sex: "F",
    chief_complaint: "Difficulty breathing, history of COPD",
    acuity_level: 2,
    score: 0.81,
    arrived_at: new Date(Date.now() - 7 * 60_000).toISOString(),
    status: "in_review",
  },
  {
    id: "a1b2c3d4-0004-4000-8000-000000000004",
    name: "David Kim",
    age: 19,
    sex: "M",
    chief_complaint: "Twisted ankle during basketball, swelling",
    acuity_level: 4,
    score: 0.28,
    arrived_at: new Date(Date.now() - 55 * 60_000).toISOString(),
    status: "waiting",
  },
  {
    id: "a1b2c3d4-0005-4000-8000-000000000005",
    name: "Elena Rodriguez",
    age: 45,
    sex: "F",
    chief_complaint: "Persistent headache and dizziness for 3 days",
    acuity_level: 3,
    score: 0.55,
    arrived_at: new Date(Date.now() - 30 * 60_000).toISOString(),
    status: "waiting",
  },
  {
    id: "a1b2c3d4-0006-4000-8000-000000000006",
    name: "Robert Thompson",
    age: 67,
    sex: "M",
    chief_complaint: "Unresponsive, brought in by EMS",
    acuity_level: 1,
    score: 0.96,
    arrived_at: new Date(Date.now() - 3 * 60_000).toISOString(),
    status: "in_review",
  },
];

const TRIAGE_DETAILS: Record<string, Omit<TriageResultData, "patient">> = {
  "a1b2c3d4-0006-4000-8000-000000000006": {
    session_id: "a1b2c3d4-0006-4000-8000-000000000006",
    vitals: {
      heart_rate_bpm: 132,
      spo2_percent: 88,
      respiratory_rate: 28,
      blood_pressure: { systolic: 85, diastolic: 55 },
      confidence: 0.72,
    },
    symptoms: null,
    risk: {
      score: 0.96,
      acuity_level: 1,
      reasoning:
        "Patient is unresponsive with critically low SpO2 (88%) and hypotension (85/55 mmHg). " +
        "Tachycardia at 132 bpm and tachypnea at 28 breaths/min indicate hemodynamic instability. " +
        "Immediate resuscitation protocol required.",
      contributing_factors: [
        { name: "Vitals", weight: 0.95, description: "Critical hypotension and desaturation" },
        { name: "Consciousness", weight: 1.0, description: "Unresponsive — GCS assessment needed" },
      ],
      similar_cases_count: 3,
    },
    cds_cards: [
      {
        summary: "ESI 1 – Resuscitation (score 0.96)",
        detail:
          "**Risk Score:** 0.96\n\n" +
          "**Reasoning:** Patient is unresponsive with critically low SpO2 and hypotension. " +
          "Immediate resuscitation protocol required.\n\n" +
          "**Contributing Factors:**\n- Vitals: Critical hypotension and desaturation\n" +
          "- Consciousness: Unresponsive — GCS assessment needed\n\n" +
          "**Similar Cases:** 3 historical case(s) found",
        indicator: "critical",
        source: { label: "emergAI Triage Engine" },
        suggestions: [
          { label: "Initiate resuscitation protocol", is_recommended: true },
          { label: "Page attending physician", is_recommended: false },
        ],
      },
    ],
    errors: [],
  },
  "a1b2c3d4-0001-4000-8000-000000000001": {
    session_id: "a1b2c3d4-0001-4000-8000-000000000001",
    vitals: {
      heart_rate_bpm: 108,
      spo2_percent: 96,
      respiratory_rate: 20,
      blood_pressure: { systolic: 150, diastolic: 92 },
      confidence: 0.88,
    },
    symptoms: {
      chief_complaint: "Severe chest pain radiating to left arm, started 45 minutes ago",
      symptoms: [
        { name: "Chest Pain", severity: "severe", description: "Crushing substernal pain radiating to left arm", body_region: "Chest", onset_description: "Acute onset 45 min ago" },
        { name: "Diaphoresis", severity: "moderate", description: "Profuse sweating", body_region: null, onset_description: "With chest pain onset" },
        { name: "Nausea", severity: "mild", description: "Mild nausea without vomiting", body_region: "Abdomen", onset_description: null },
      ],
      follow_up_questions: [
        "Any prior cardiac history or stent placement?",
        "Are you currently taking blood thinners?",
      ],
      confidence: 0.92,
    },
    risk: {
      score: 0.87,
      acuity_level: 2,
      reasoning:
        "Presentation consistent with acute coronary syndrome. Crushing chest pain radiating to left arm " +
        "with diaphoresis in a 58-year-old female. Mild tachycardia and hypertension noted. " +
        "Expedited evaluation and cardiac workup recommended.",
      contributing_factors: [
        { name: "Symptom Score", weight: 0.9, description: "Classic ACS presentation with radiating chest pain" },
        { name: "Vitals Score", weight: 0.65, description: "Mild tachycardia (108 bpm), hypertensive" },
        { name: "Age/Sex", weight: 0.5, description: "58F — elevated cardiac risk profile" },
      ],
      similar_cases_count: 7,
    },
    cds_cards: [
      {
        summary: "ESI 2 – Emergent (score 0.87)",
        detail:
          "**Risk Score:** 0.87\n\n**Reasoning:** Presentation consistent with acute coronary syndrome.\n\n" +
          "**Contributing Factors:**\n- Symptom Score: Classic ACS presentation\n- Vitals Score: Mild tachycardia\n\n" +
          "**Similar Cases:** 7 historical case(s) found",
        indicator: "critical",
        source: { label: "emergAI Triage Engine" },
        suggestions: [
          { label: "Expedite clinical evaluation", is_recommended: true },
          { label: "Order diagnostic workup", is_recommended: false },
        ],
      },
      {
        summary: "Tachycardia detected: HR 108 bpm",
        detail: "Heart rate of 108 bpm is outside the normal range (60–100 bpm). Measurement confidence: 88%.",
        indicator: "warning",
        source: { label: "emergAI Triage Engine" },
        suggestions: [],
      },
      {
        summary: 'Chief complaint: "Severe chest pain radiating to left arm"',
        detail:
          "**Symptoms (3):**\n- **Chest Pain** (severe): Crushing substernal pain radiating to left arm\n" +
          "- **Diaphoresis** (moderate): Profuse sweating\n- **Nausea** (mild): Mild nausea without vomiting\n\n" +
          "**Follow-up questions:**\n- Any prior cardiac history or stent placement?\n" +
          "- Are you currently taking blood thinners?\n\nExtraction confidence: 92%",
        indicator: "info",
        source: { label: "emergAI Triage Engine" },
        suggestions: [],
      },
    ],
    errors: [],
  },
  "a1b2c3d4-0003-4000-8000-000000000003": {
    session_id: "a1b2c3d4-0003-4000-8000-000000000003",
    vitals: {
      heart_rate_bpm: 98,
      spo2_percent: 91,
      respiratory_rate: 26,
      blood_pressure: null,
      confidence: 0.8,
    },
    symptoms: {
      chief_complaint: "Worsening shortness of breath over the past 2 days",
      symptoms: [
        { name: "Dyspnea", severity: "severe", description: "Progressively worsening, now at rest", body_region: "Chest", onset_description: "Gradual over 2 days" },
        { name: "Productive Cough", severity: "moderate", description: "Greenish sputum", body_region: "Chest", onset_description: "3 days" },
      ],
      follow_up_questions: [
        "When was your last COPD exacerbation?",
        "Are you on home oxygen?",
      ],
      confidence: 0.89,
    },
    risk: {
      score: 0.81,
      acuity_level: 2,
      reasoning:
        "72-year-old female with known COPD presenting with acute dyspnea at rest and SpO2 of 91%. " +
        "Productive cough with purulent sputum suggests infectious exacerbation. " +
        "Requires urgent respiratory support and workup.",
      contributing_factors: [
        { name: "Symptom Score", weight: 0.85, description: "Severe dyspnea at rest with productive cough" },
        { name: "Vitals Score", weight: 0.75, description: "SpO2 91%, tachypnea 26/min" },
        { name: "History Score", weight: 0.7, description: "Known COPD — high exacerbation risk" },
      ],
      similar_cases_count: 12,
    },
    cds_cards: [
      {
        summary: "ESI 2 – Emergent (score 0.81)",
        detail:
          "**Risk Score:** 0.81\n\n**Reasoning:** COPD exacerbation with hypoxemia.\n\n" +
          "**Similar Cases:** 12 historical case(s) found",
        indicator: "critical",
        source: { label: "emergAI Triage Engine" },
        suggestions: [
          { label: "Expedite clinical evaluation", is_recommended: true },
          { label: "Order diagnostic workup", is_recommended: false },
        ],
      },
    ],
    errors: [],
  },
  "a1b2c3d4-0002-4000-8000-000000000002": {
    session_id: "a1b2c3d4-0002-4000-8000-000000000002",
    vitals: {
      heart_rate_bpm: 82,
      spo2_percent: 99,
      respiratory_rate: 16,
      blood_pressure: { systolic: 128, diastolic: 78 },
      confidence: 0.91,
    },
    symptoms: {
      chief_complaint: "Cut on right forearm from a kitchen knife",
      symptoms: [
        { name: "Laceration", severity: "moderate", description: "4 cm laceration, moderate bleeding controlled with pressure", body_region: "Right forearm", onset_description: "30 minutes ago" },
        { name: "Pain", severity: "moderate", description: "Localized pain at wound site", body_region: "Right forearm", onset_description: null },
      ],
      follow_up_questions: [
        "Is your tetanus vaccination up to date?",
        "Any numbness or tingling distal to the wound?",
      ],
      confidence: 0.95,
    },
    risk: {
      score: 0.52,
      acuity_level: 3,
      reasoning:
        "Isolated forearm laceration with controlled bleeding. Vitals stable. " +
        "Requires wound evaluation, possible suturing, and tetanus status check.",
      contributing_factors: [
        { name: "Symptom Score", weight: 0.5, description: "Moderate laceration, controlled bleeding" },
        { name: "Vitals Score", weight: 0.1, description: "All vitals within normal limits" },
      ],
      similar_cases_count: 22,
    },
    cds_cards: [
      {
        summary: "ESI 3 – Urgent (score 0.52)",
        detail:
          "**Risk Score:** 0.52\n\n**Reasoning:** Isolated forearm laceration. Vitals stable.\n\n" +
          "**Similar Cases:** 22 historical case(s) found",
        indicator: "warning",
        source: { label: "emergAI Triage Engine" },
        suggestions: [
          { label: "Standard triage evaluation", is_recommended: true },
          { label: "Monitor vitals", is_recommended: false },
        ],
      },
    ],
    errors: [],
  },
  "a1b2c3d4-0005-4000-8000-000000000005": {
    session_id: "a1b2c3d4-0005-4000-8000-000000000005",
    vitals: {
      heart_rate_bpm: 76,
      spo2_percent: 98,
      respiratory_rate: 14,
      blood_pressure: { systolic: 135, diastolic: 88 },
      confidence: 0.93,
    },
    symptoms: {
      chief_complaint: "Persistent headache and dizziness for 3 days",
      symptoms: [
        { name: "Headache", severity: "moderate", description: "Bilateral, pressure-type, not relieved by OTC meds", body_region: "Head", onset_description: "3 days ago, progressive" },
        { name: "Dizziness", severity: "moderate", description: "Intermittent lightheadedness, no vertigo", body_region: null, onset_description: "Concurrent with headache" },
      ],
      follow_up_questions: [
        "Any recent head trauma?",
        "Any visual changes or neurological symptoms?",
      ],
      confidence: 0.87,
    },
    risk: {
      score: 0.55,
      acuity_level: 3,
      reasoning:
        "45-year-old female with 3-day progressive headache and dizziness. Vitals stable but mildly hypertensive. " +
        "Neurological red flags should be ruled out. Standard evaluation timeline appropriate.",
      contributing_factors: [
        { name: "Symptom Score", weight: 0.55, description: "Persistent headache unresponsive to OTC treatment" },
        { name: "Vitals Score", weight: 0.2, description: "Mildly elevated BP, otherwise normal" },
        { name: "Duration", weight: 0.4, description: "3-day duration warrants investigation" },
      ],
      similar_cases_count: 15,
    },
    cds_cards: [
      {
        summary: "ESI 3 – Urgent (score 0.55)",
        detail:
          "**Risk Score:** 0.55\n\n**Reasoning:** Progressive headache with dizziness, mild hypertension.\n\n" +
          "**Similar Cases:** 15 historical case(s) found",
        indicator: "warning",
        source: { label: "emergAI Triage Engine" },
        suggestions: [
          { label: "Standard triage evaluation", is_recommended: true },
          { label: "Monitor vitals", is_recommended: false },
        ],
      },
    ],
    errors: [],
  },
  "a1b2c3d4-0004-4000-8000-000000000004": {
    session_id: "a1b2c3d4-0004-4000-8000-000000000004",
    vitals: {
      heart_rate_bpm: 72,
      spo2_percent: 99,
      respiratory_rate: 15,
      blood_pressure: { systolic: 118, diastolic: 72 },
      confidence: 0.95,
    },
    symptoms: {
      chief_complaint: "Twisted ankle during basketball game",
      symptoms: [
        { name: "Ankle Sprain", severity: "mild", description: "Swelling and tenderness on lateral right ankle", body_region: "Right ankle", onset_description: "1 hour ago during basketball" },
        { name: "Pain", severity: "moderate", description: "Weight-bearing painful but possible", body_region: "Right ankle", onset_description: null },
      ],
      follow_up_questions: [
        "Can you bear weight on it?",
        "Any previous ankle injuries?",
      ],
      confidence: 0.96,
    },
    risk: {
      score: 0.28,
      acuity_level: 4,
      reasoning:
        "Young healthy male with isolated ankle injury. Vitals completely normal. " +
        "Low-acuity musculoskeletal complaint suitable for routine assessment.",
      contributing_factors: [
        { name: "Symptom Score", weight: 0.3, description: "Minor musculoskeletal injury" },
        { name: "Vitals Score", weight: 0.05, description: "All vitals within normal limits" },
      ],
      similar_cases_count: 35,
    },
    cds_cards: [
      {
        summary: "ESI 4 – Less Urgent (score 0.28)",
        detail:
          "**Risk Score:** 0.28\n\n**Reasoning:** Isolated ankle sprain, stable vitals.\n\n" +
          "**Similar Cases:** 35 historical case(s) found",
        indicator: "info",
        source: { label: "emergAI Triage Engine" },
        suggestions: [
          { label: "Routine assessment", is_recommended: false },
          { label: "Schedule follow-up if needed", is_recommended: false },
        ],
      },
    ],
    errors: [],
  },
};

export function getPatientQueue(): PatientQueueItem[] {
  return [...PATIENTS].sort((a, b) => {
    if (a.acuity_level !== b.acuity_level) return a.acuity_level - b.acuity_level;
    return new Date(a.arrived_at).getTime() - new Date(b.arrived_at).getTime();
  });
}

export function getTriageResult(patientId: string): TriageResultData | null {
  const patient = PATIENTS.find((p) => p.id === patientId);
  const details = TRIAGE_DETAILS[patientId];
  if (!patient || !details) return null;
  return { ...details, patient };
}
