export type CaptureStep = "permissions" | "video" | "audio" | "review";

const STEPS: { key: CaptureStep; label: string }[] = [
  { key: "permissions", label: "Setup" },
  { key: "video", label: "Video" },
  { key: "audio", label: "Audio" },
  { key: "review", label: "Review" },
];

interface StepIndicatorProps {
  current: CaptureStep;
}

export function StepIndicator({ current }: StepIndicatorProps) {
  const currentIdx = STEPS.findIndex((s) => s.key === current);

  return (
    <nav className="flex items-center justify-center gap-2">
      {STEPS.map((step, i) => {
        const done = i < currentIdx;
        const active = i === currentIdx;

        return (
          <div key={step.key} className="flex items-center gap-2">
            {i > 0 && (
              <div
                className={`h-px w-8 ${done ? "bg-primary-500" : "bg-slate-200"}`}
              />
            )}
            <div className="flex flex-col items-center gap-1">
              <div
                className={`flex h-8 w-8 items-center justify-center rounded-full text-sm font-semibold transition-colors ${
                  done
                    ? "bg-primary-500 text-white"
                    : active
                      ? "bg-primary-100 text-primary-700 ring-2 ring-primary-500"
                      : "bg-slate-100 text-slate-400"
                }`}
              >
                {done ? (
                  <CheckIcon />
                ) : (
                  i + 1
                )}
              </div>
              <span
                className={`text-xs font-medium ${active ? "text-primary-700" : "text-slate-400"}`}
              >
                {step.label}
              </span>
            </div>
          </div>
        );
      })}
    </nav>
  );
}

function CheckIcon() {
  return (
    <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" strokeWidth={3} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="m4.5 12.75 6 6 9-13.5" />
    </svg>
  );
}
