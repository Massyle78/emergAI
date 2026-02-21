import type { UploadPhase, UploadProgress as Progress } from "@/types";

interface UploadProgressProps {
  phase: UploadPhase;
  progress: Progress;
  error: string | null;
  processingStatus: string | null;
  onRetry: () => void;
  onDone: () => void;
}

/**
 * Upload + processing progress card shown after the user
 * submits their recordings for analysis.
 */
export function UploadProgress({
  phase,
  progress,
  error,
  processingStatus,
  onRetry,
  onDone,
}: UploadProgressProps) {
  return (
    <div className="kiosk-card space-y-6">
      <div className="text-center">
        <h2 className="text-2xl font-bold text-slate-900">
          {phase === "error" ? "Upload Failed" : headingFor(phase)}
        </h2>
        <p className="mt-1 text-sm text-slate-500">{subtitleFor(phase)}</p>
      </div>

      {/* File progress bars */}
      <div className="space-y-4">
        <ProgressBar
          label="Video"
          percent={progress.video}
          active={phase === "uploading-video"}
          done={isAfter(phase, "uploading-video")}
        />
        <ProgressBar
          label="Audio"
          percent={progress.audio}
          active={phase === "uploading-audio"}
          done={isAfter(phase, "uploading-audio")}
        />
      </div>

      {/* Processing status */}
      {phase === "processing" && (
        <ProcessingIndicator status={processingStatus} />
      )}

      {/* Done */}
      {phase === "done" && (
        <div className="flex flex-col items-center gap-4">
          <div className="flex h-14 w-14 items-center justify-center rounded-full bg-accent-100">
            <svg
              className="h-7 w-7 text-accent-600"
              fill="none"
              viewBox="0 0 24 24"
              strokeWidth={2}
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
          </div>
          <p className="font-medium text-accent-700">
            Analysis complete! Your triage results are ready.
          </p>
          <button onClick={onDone} className="kiosk-btn-primary">
            View Results
          </button>
        </div>
      )}

      {/* Error + retry */}
      {phase === "error" && error && (
        <div className="flex flex-col items-center gap-4">
          <div className="flex h-14 w-14 items-center justify-center rounded-full bg-red-100">
            <svg
              className="h-7 w-7 text-danger-600"
              fill="none"
              viewBox="0 0 24 24"
              strokeWidth={2}
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z"
              />
            </svg>
          </div>
          <p className="text-sm text-danger-600">{error}</p>
          <button onClick={onRetry} className="kiosk-btn-primary">
            Retry Upload
          </button>
        </div>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Sub-components                                                     */
/* ------------------------------------------------------------------ */
interface ProgressBarProps {
  label: string;
  percent: number;
  active: boolean;
  done: boolean;
}

function ProgressBar({ label, percent, active, done }: ProgressBarProps) {
  return (
    <div>
      <div className="mb-1 flex items-center justify-between text-sm">
        <span className="font-medium text-slate-700">{label}</span>
        <span className="tabular-nums text-slate-500">
          {done ? (
            <span className="text-accent-600">Complete</span>
          ) : active ? (
            `${percent}%`
          ) : (
            "Waiting"
          )}
        </span>
      </div>
      <div className="h-2.5 overflow-hidden rounded-full bg-slate-100">
        <div
          className={`h-full rounded-full transition-all duration-300 ${
            done
              ? "bg-accent-500"
              : active
                ? "bg-primary-500"
                : "bg-slate-200"
          }`}
          style={{ width: `${done ? 100 : percent}%` }}
        />
      </div>
    </div>
  );
}

function ProcessingIndicator({ status }: { status: string | null }) {
  return (
    <div className="flex flex-col items-center gap-3">
      <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary-200 border-t-primary-600" />
      <p className="text-sm text-slate-500">
        {status === "checking"
          ? "Connecting to processing pipeline..."
          : `Processing: ${status ?? "analyzing"}...`}
      </p>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */
function headingFor(phase: UploadPhase): string {
  switch (phase) {
    case "uploading-video":
    case "uploading-audio":
      return "Uploading Recordings";
    case "processing":
      return "Analyzing Your Data";
    case "done":
      return "Analysis Complete";
    default:
      return "Submitting";
  }
}

function subtitleFor(phase: UploadPhase): string {
  switch (phase) {
    case "uploading-video":
      return "Sending your video to the server...";
    case "uploading-audio":
      return "Sending your audio to the server...";
    case "processing":
      return "Our AI is analyzing your vitals and symptoms.";
    case "done":
      return "Your triage assessment is ready for review.";
    case "error":
      return "Something went wrong. You can retry the upload.";
    default:
      return "Preparing your submission...";
  }
}

function isAfter(current: UploadPhase, target: UploadPhase): boolean {
  const order: UploadPhase[] = [
    "idle",
    "uploading-video",
    "uploading-audio",
    "processing",
    "done",
  ];
  return order.indexOf(current) > order.indexOf(target);
}
