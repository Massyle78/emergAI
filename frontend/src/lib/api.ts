import type { MediaUploadResponse } from "@/types";

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "";

/**
 * Upload a media file to the backend ingestion endpoint.
 *
 * Uses XMLHttpRequest instead of fetch so we can track upload
 * progress via the `onProgress` callback.
 */
export function uploadMedia(
  type: "video" | "audio",
  blob: Blob,
  sessionId: string,
  token: string | null,
  onProgress?: (percent: number) => void,
): Promise<MediaUploadResponse> {
  return new Promise((resolve, reject) => {
    const formData = new FormData();
    formData.append("session_id", sessionId);
    formData.append("file", blob, `recording.webm`);

    const xhr = new XMLHttpRequest();
    xhr.open("POST", `${API_BASE}/api/v1/media/${type}`);

    if (token) {
      xhr.setRequestHeader("Authorization", `Bearer ${token}`);
    }

    xhr.upload.onprogress = (e) => {
      if (e.lengthComputable && onProgress) {
        onProgress(Math.round((e.loaded / e.total) * 100));
      }
    };

    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        resolve(JSON.parse(xhr.responseText) as MediaUploadResponse);
      } else {
        reject(new ApiError(`Upload failed (${xhr.status})`, xhr.status));
      }
    };

    xhr.onerror = () => reject(new ApiError("Network error", 0));
    xhr.ontimeout = () => reject(new ApiError("Upload timed out", 0));
    xhr.timeout = 120_000;

    xhr.send(formData);
  });
}

const POLL_INTERVAL_MS = 2000;
const MAX_POLLS = 60;

/**
 * Poll the backend for processing status until complete or timeout.
 */
export async function pollStatus(
  sessionId: string,
  token: string | null,
  onStatus?: (status: string) => void,
): Promise<void> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };
  if (token) headers["Authorization"] = `Bearer ${token}`;

  for (let i = 0; i < MAX_POLLS; i++) {
    try {
      const resp = await fetch(
        `${API_BASE}/api/v1/media/status/${sessionId}`,
        { headers },
      );

      if (!resp.ok) {
        onStatus?.("checking");
        await sleep(POLL_INTERVAL_MS);
        continue;
      }

      const data = (await resp.json()) as { status: string };
      onStatus?.(data.status);

      if (data.status === "completed" || data.status === "failed") {
        return;
      }
    } catch {
      onStatus?.("checking");
    }
    await sleep(POLL_INTERVAL_MS);
  }
}

function sleep(ms: number): Promise<void> {
  return new Promise((r) => setTimeout(r, ms));
}

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly statusCode: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}
