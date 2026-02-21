import { useEffect, useRef } from "react";

interface WebcamPreviewProps {
  stream: MediaStream | null;
  mirrored?: boolean;
}

/**
 * Live camera preview that binds a MediaStream to a `<video>` element.
 *
 * When `stream` becomes null the video is cleared. The feed is
 * muted to avoid audio feedback when the same stream captures
 * both video and audio.
 */
export function WebcamPreview({ stream, mirrored = true }: WebcamPreviewProps) {
  const videoRef = useRef<HTMLVideoElement>(null);

  useEffect(() => {
    const el = videoRef.current;
    if (!el) return;
    el.srcObject = stream;
  }, [stream]);

  return (
    <div className="relative aspect-video overflow-hidden rounded-xl bg-slate-900 shadow-inner">
      <video
        ref={videoRef}
        autoPlay
        playsInline
        muted
        className={`h-full w-full object-cover ${mirrored ? "scale-x-[-1]" : ""}`}
      />
      {!stream && <Placeholder />}
    </div>
  );
}

function Placeholder() {
  return (
    <div className="absolute inset-0 flex flex-col items-center justify-center gap-3 text-slate-500">
      <svg
        className="h-12 w-12 opacity-40"
        fill="none"
        viewBox="0 0 24 24"
        strokeWidth={1.5}
        stroke="currentColor"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          d="m15.75 10.5 4.72-4.72a.75.75 0 0 1 1.28.53v11.38a.75.75 0 0 1-1.28.53l-4.72-4.72M4.5 18.75h9a2.25 2.25 0 0 0 2.25-2.25v-9a2.25 2.25 0 0 0-2.25-2.25h-9A2.25 2.25 0 0 0 2.25 7.5v9a2.25 2.25 0 0 0 2.25 2.25Z"
        />
      </svg>
      <span className="text-sm">Camera not active</span>
    </div>
  );
}
