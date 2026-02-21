import { useCallback, useRef, useState } from "react";

export type StreamStatus = "idle" | "requesting" | "active" | "denied";

interface UseMediaStreamReturn {
  stream: MediaStream | null;
  status: StreamStatus;
  error: string | null;
  request: () => Promise<void>;
  stop: () => void;
}

/**
 * Manage a getUserMedia stream lifecycle.
 *
 * Call `request()` to prompt the user for camera/mic access.
 * Call `stop()` to release all tracks and free the hardware.
 * The hook cleans up automatically on unmount.
 */
export function useMediaStream(
  constraints: MediaStreamConstraints,
): UseMediaStreamReturn {
  const [stream, setStream] = useState<MediaStream | null>(null);
  const [status, setStatus] = useState<StreamStatus>("idle");
  const [error, setError] = useState<string | null>(null);
  const streamRef = useRef<MediaStream | null>(null);

  const stop = useCallback(() => {
    streamRef.current?.getTracks().forEach((t) => t.stop());
    streamRef.current = null;
    setStream(null);
    setStatus("idle");
  }, []);

  const request = useCallback(async () => {
    setStatus("requesting");
    setError(null);
    try {
      const s = await navigator.mediaDevices.getUserMedia(constraints);
      streamRef.current = s;
      setStream(s);
      setStatus("active");
    } catch (err) {
      const msg =
        err instanceof Error ? err.message : "Failed to access media device";
      setError(msg);
      setStatus("denied");
    }
  }, [constraints]);

  return { stream, status, error, request, stop };
}
