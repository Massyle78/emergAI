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

export interface MediaUploadResponse {
  id: string;
  session_id: string;
  media_type: "video" | "audio";
  filename: string;
  size_bytes: number;
  content_type: string;
  status: string;
  uploaded_at: string;
}

export type UploadPhase =
  | "idle"
  | "uploading-video"
  | "uploading-audio"
  | "processing"
  | "done"
  | "error";

export interface UploadProgress {
  video: number;
  audio: number;
}
