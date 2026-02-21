/** Frontend mirrors of the backend triage data models. */

export type AcuityLevel = 1 | 2 | 3 | 4 | 5;

export type CdsIndicator = "info" | "warning" | "critical";

export type SymptomSeverity = "mild" | "moderate" | "severe" | "critical";

export const ACUITY_LABELS: Record<AcuityLevel, string> = {
  1: "Resuscitation",
  2: "Emergent",
  3: "Urgent",
  4: "Less Urgent",
  5: "Non-Urgent",
};

export const ACUITY_COLORS: Record<AcuityLevel, string> = {
  1: "bg-red-600",
  2: "bg-orange-500",
  3: "bg-yellow-500",
  4: "bg-emerald-500",
  5: "bg-blue-500",
};

export const ACUITY_TEXT_COLORS: Record<AcuityLevel, string> = {
  1: "text-red-700",
  2: "text-orange-700",
  3: "text-yellow-700",
  4: "text-emerald-700",
  5: "text-blue-700",
};

export const ACUITY_BG_LIGHT: Record<AcuityLevel, string> = {
  1: "bg-red-50",
  2: "bg-orange-50",
  3: "bg-yellow-50",
  4: "bg-emerald-50",
  5: "bg-blue-50",
};

export const INDICATOR_STYLES: Record<
  CdsIndicator,
  { bg: string; border: string; icon: string }
> = {
  critical: {
    bg: "bg-red-50",
    border: "border-red-200",
    icon: "text-red-600",
  },
  warning: {
    bg: "bg-amber-50",
    border: "border-amber-200",
    icon: "text-amber-600",
  },
  info: {
    bg: "bg-blue-50",
    border: "border-blue-200",
    icon: "text-blue-600",
  },
};

export interface BloodPressure {
  systolic: number;
  diastolic: number;
}

export interface Vitals {
  heart_rate_bpm: number;
  spo2_percent: number | null;
  respiratory_rate: number | null;
  blood_pressure: BloodPressure | null;
  confidence: number;
}

export interface SymptomDetail {
  name: string;
  severity: SymptomSeverity;
  description: string | null;
  body_region: string | null;
  onset_description: string | null;
}

export interface SymptomExtraction {
  chief_complaint: string;
  symptoms: SymptomDetail[];
  follow_up_questions: string[];
  confidence: number;
}

export interface ContributingFactor {
  name: string;
  weight: number;
  description: string;
}

export interface RiskAssessment {
  score: number;
  acuity_level: AcuityLevel;
  reasoning: string;
  contributing_factors: ContributingFactor[];
  similar_cases_count: number;
}

export interface CdsSource {
  label: string;
  url?: string;
}

export interface CdsSuggestion {
  label: string;
  uuid?: string;
  is_recommended: boolean;
}

export interface CdsCard {
  summary: string;
  detail: string | null;
  indicator: CdsIndicator;
  source: CdsSource;
  suggestions: CdsSuggestion[];
}

export interface PatientQueueItem {
  id: string;
  name: string;
  age: number;
  sex: string;
  chief_complaint: string;
  acuity_level: AcuityLevel;
  score: number;
  arrived_at: string;
  status: "waiting" | "in_review" | "completed";
}

export interface TriageResultData {
  session_id: string;
  patient: PatientQueueItem;
  vitals: Vitals | null;
  symptoms: SymptomExtraction | null;
  risk: RiskAssessment;
  cds_cards: CdsCard[];
  errors: string[];
}
