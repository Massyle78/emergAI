import { useCallback, useEffect, useMemo, useRef, useState } from "react";

export type RecorderStatus = "idle" | "recording" | "stopped";

const CHUNK_INTERVAL_MS = 1000;

interface UseMediaRecorderReturn {
  status: RecorderStatus;
  blob: Blob | null;
  elapsed: number;
  start: () => void;
  stop: () => void;
  reset: () => void;
}

/**
 * Record media from a stream using the MediaRecorder API.
 *
 * Data is collected in 1-second chunks. After `stop()` is called
 * the chunks are merged into a single Blob accessible via `blob`.
 * `elapsed` tracks recording duration in seconds.
 */
export function useMediaRecorder(
  stream: MediaStream | null,
  mimeType?: string,
): UseMediaRecorderReturn {
  const [status, setStatus] = useState<RecorderStatus>("idle");
  const [chunks, setChunks] = useState<Blob[]>([]);
  const [elapsed, setElapsed] = useState(0);

  const recorderRef = useRef<MediaRecorder | null>(null);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const clearTimer = useCallback(() => {
    if (timerRef.current !== null) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
  }, []);

  const start = useCallback(() => {
    if (!stream) return;
    setChunks([]);
    setElapsed(0);

    const options: MediaRecorderOptions = {};
    if (mimeType && MediaRecorder.isTypeSupported(mimeType)) {
      options.mimeType = mimeType;
    }

    const recorder = new MediaRecorder(stream, options);
    recorder.ondataavailable = (e) => {
      if (e.data.size > 0) {
        setChunks((prev) => [...prev, e.data]);
      }
    };
    recorder.onstop = () => {
      setStatus("stopped");
      clearTimer();
    };

    recorder.start(CHUNK_INTERVAL_MS);
    recorderRef.current = recorder;
    setStatus("recording");

    timerRef.current = setInterval(() => {
      setElapsed((prev) => prev + 1);
    }, 1000);
  }, [stream, mimeType, clearTimer]);

  const stop = useCallback(() => {
    if (recorderRef.current?.state === "recording") {
      recorderRef.current.stop();
    }
  }, []);

  const reset = useCallback(() => {
    setChunks([]);
    setElapsed(0);
    setStatus("idle");
    recorderRef.current = null;
  }, []);

  useEffect(() => {
    return () => clearTimer();
  }, [clearTimer]);

  const blob = useMemo(() => {
    if (status !== "stopped" || chunks.length === 0) return null;
    const type = recorderRef.current?.mimeType || mimeType || "video/webm";
    return new Blob(chunks, { type });
  }, [chunks, status, mimeType]);

  return { status, blob, elapsed, start, stop, reset };
}
