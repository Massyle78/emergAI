import { useCallback, useRef, useState } from "react";

import { ApiError, pollStatus, uploadMedia } from "@/lib/api";
import { useAuth } from "@/hooks/useAuth";
import type { UploadPhase, UploadProgress } from "@/types";

interface UseUploadReturn {
  phase: UploadPhase;
  progress: UploadProgress;
  error: string | null;
  sessionId: string | null;
  processingStatus: string | null;
  submit: (videoBlob: Blob, audioBlob: Blob) => Promise<void>;
  retry: () => Promise<void>;
  reset: () => void;
}

/**
 * Orchestrates the full upload + processing flow.
 *
 * 1. Generates a session UUID
 * 2. Uploads video with progress tracking
 * 3. Uploads audio with progress tracking
 * 4. Polls backend for processing status
 * 5. Transitions to done / error with retry support
 */
export function useUpload(): UseUploadReturn {
  const { session } = useAuth();
  const token = session?.access_token ?? null;

  const [phase, setPhase] = useState<UploadPhase>("idle");
  const [progress, setProgress] = useState<UploadProgress>({
    video: 0,
    audio: 0,
  });
  const [error, setError] = useState<string | null>(null);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [processingStatus, setProcessingStatus] = useState<string | null>(null);

  const blobsRef = useRef<{ video: Blob; audio: Blob } | null>(null);

  const doUpload = useCallback(
    async (video: Blob, audio: Blob, sid: string) => {
      setError(null);

      setPhase("uploading-video");
      await uploadMedia("video", video, sid, token, (p) =>
        setProgress((prev) => ({ ...prev, video: p })),
      );

      setPhase("uploading-audio");
      await uploadMedia("audio", audio, sid, token, (p) =>
        setProgress((prev) => ({ ...prev, audio: p })),
      );

      setPhase("processing");
      await pollStatus(sid, token, setProcessingStatus);

      setPhase("done");
    },
    [token],
  );

  const submit = useCallback(
    async (videoBlob: Blob, audioBlob: Blob) => {
      const sid = crypto.randomUUID();
      setSessionId(sid);
      setProgress({ video: 0, audio: 0 });
      blobsRef.current = { video: videoBlob, audio: audioBlob };

      try {
        await doUpload(videoBlob, audioBlob, sid);
      } catch (err) {
        const msg =
          err instanceof ApiError
            ? `${err.message} (${err.statusCode})`
            : err instanceof Error
              ? err.message
              : "Upload failed";
        setError(msg);
        setPhase("error");
      }
    },
    [doUpload],
  );

  const retry = useCallback(async () => {
    if (!blobsRef.current || !sessionId) return;
    setProgress({ video: 0, audio: 0 });
    try {
      await doUpload(
        blobsRef.current.video,
        blobsRef.current.audio,
        sessionId,
      );
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Retry failed";
      setError(msg);
      setPhase("error");
    }
  }, [doUpload, sessionId]);

  const reset = useCallback(() => {
    setPhase("idle");
    setProgress({ video: 0, audio: 0 });
    setError(null);
    setSessionId(null);
    setProcessingStatus(null);
    blobsRef.current = null;
  }, []);

  return {
    phase,
    progress,
    error,
    sessionId,
    processingStatus,
    submit,
    retry,
    reset,
  };
}
