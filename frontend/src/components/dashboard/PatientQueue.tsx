import {
  ACUITY_BG_LIGHT,
  ACUITY_COLORS,
  ACUITY_LABELS,
  ACUITY_TEXT_COLORS,
  type PatientQueueItem,
} from "@/types/dashboard";

interface PatientQueueProps {
  patients: PatientQueueItem[];
  selectedId: string | null;
  onSelect: (id: string) => void;
}

export function PatientQueue({
  patients,
  selectedId,
  onSelect,
}: PatientQueueProps) {
  return (
    <aside className="flex h-full flex-col border-r border-slate-200 bg-white">
      <div className="border-b border-slate-200 px-4 py-3">
        <h2 className="text-sm font-semibold text-slate-900">Patient Queue</h2>
        <p className="text-xs text-slate-500">
          {patients.length} patient{patients.length !== 1 ? "s" : ""} waiting
        </p>
      </div>

      <div className="flex-1 overflow-y-auto">
        {patients.map((p) => (
          <button
            key={p.id}
            onClick={() => onSelect(p.id)}
            className={`w-full border-b border-slate-100 px-4 py-3 text-left transition-colors hover:bg-slate-50 ${
              selectedId === p.id
                ? "bg-primary-50 ring-inset ring-1 ring-primary-200"
                : ""
            }`}
          >
            <div className="flex items-start justify-between gap-2">
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  <span
                    className={`inline-flex h-5 min-w-5 items-center justify-center rounded text-[10px] font-bold text-white ${ACUITY_COLORS[p.acuity_level]}`}
                  >
                    {p.acuity_level}
                  </span>
                  <span className="truncate text-sm font-medium text-slate-900">
                    {p.name}
                  </span>
                </div>
                <p className="mt-0.5 truncate text-xs text-slate-500">
                  {p.chief_complaint}
                </p>
              </div>
              <StatusBadge status={p.status} />
            </div>

            <div className="mt-1.5 flex items-center gap-3 text-[11px] text-slate-400">
              <span>
                {p.age}{p.sex[0]} 
              </span>
              <span className={`font-medium ${ACUITY_TEXT_COLORS[p.acuity_level]}`}>
                {ACUITY_LABELS[p.acuity_level]}
              </span>
              <span className="ml-auto tabular-nums">
                {timeAgo(p.arrived_at)}
              </span>
            </div>
          </button>
        ))}
      </div>

      <div className="border-t border-slate-200 px-4 py-2">
        <div className="flex flex-wrap gap-2">
          {([1, 2, 3, 4, 5] as const).map((level) => {
            const count = patients.filter(
              (p) => p.acuity_level === level,
            ).length;
            if (count === 0) return null;
            return (
              <span
                key={level}
                className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-medium ${ACUITY_BG_LIGHT[level]} ${ACUITY_TEXT_COLORS[level]}`}
              >
                ESI {level}
                <span className="font-bold">{count}</span>
              </span>
            );
          })}
        </div>
      </div>
    </aside>
  );
}

function StatusBadge({ status }: { status: PatientQueueItem["status"] }) {
  if (status === "in_review") {
    return (
      <span className="flex items-center gap-1 rounded-full bg-amber-50 px-2 py-0.5 text-[10px] font-medium text-amber-700 ring-1 ring-amber-200">
        <span className="relative flex h-1.5 w-1.5">
          <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-amber-400 opacity-75" />
          <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-amber-500" />
        </span>
        In Review
      </span>
    );
  }
  if (status === "completed") {
    return (
      <span className="rounded-full bg-accent-50 px-2 py-0.5 text-[10px] font-medium text-accent-700 ring-1 ring-accent-200">
        Done
      </span>
    );
  }
  return null;
}

function timeAgo(iso: string): string {
  const mins = Math.floor((Date.now() - new Date(iso).getTime()) / 60_000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  return `${hrs}h ${mins % 60}m ago`;
}
