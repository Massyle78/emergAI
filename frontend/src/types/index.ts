import type { User, Session } from "@supabase/supabase-js";

export interface AuthState {
  user: User | null;
  session: Session | null;
  loading: boolean;
}

export interface TriageSession {
  id: string;
  patientId: string;
  status: TriageStatus;
  createdAt: string;
}

export type TriageStatus =
  | "pending"
  | "capturing"
  | "processing"
  | "awaiting_review"
  | "completed"
  | "cancelled";
