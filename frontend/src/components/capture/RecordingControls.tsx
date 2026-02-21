interface RecordingControlsProps {
  recording: boolean;
  elapsed: number;
  onStart: () => void;
  onStop: () => void;
  label?: string;
  maxSeconds?: number;
}

/**
 * Start / stop button pair with elapsed time display.
 *
 * When `maxSeconds` is provided a remaining-time countdown
 * is shown instead of elapsed time.
 */
export function RecordingControls({
  recording,
  elapsed,
  onStart,
  onStop,
  label = "Record",
  maxSeconds,
}: RecordingControlsProps) {
  const display = maxSeconds
    ? formatTime(Math.max(0, maxSeconds - elapsed))
    : formatTime(elapsed);

  return (
    <div className="flex flex-col items-center gap-4">
      {/* Timer */}
      <div className="flex items-center gap-2">
        {recording && (
          <span className="relative flex h-3 w-3">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-danger-500 opacity-75" />
            <span className="relative inline-flex h-3 w-3 rounded-full bg-danger-500" />
          </span>
        )}
        <span className="font-mono text-2xl font-semibold tabular-nums text-slate-700">
          {display}
        </span>
      </div>

      {/* Button */}
      {recording ? (
        <button onClick={onStop} className="kiosk-btn-primary bg-danger-600 hover:bg-danger-500 shadow-danger-600/25 hover:shadow-danger-500/25">
          <StopIcon />
          Stop Recording
        </button>
      ) : (
        <button onClick={onStart} className="kiosk-btn-primary">
          <CircleIcon />
          {label}
        </button>
      )}
    </div>
  );
}

function formatTime(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${m}:${String(s).padStart(2, "0")}`;
}

function StopIcon() {
  return (
    <svg className="h-5 w-5" fill="currentColor" viewBox="0 0 24 24">
      <rect x="6" y="6" width="12" height="12" rx="2" />
    </svg>
  );
}

function CircleIcon() {
  return (
    <svg className="h-5 w-5" fill="currentColor" viewBox="0 0 24 24">
      <circle cx="12" cy="12" r="8" />
    </svg>
  );
}
