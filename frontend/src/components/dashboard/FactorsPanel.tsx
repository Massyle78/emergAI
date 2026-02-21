import type { ContributingFactor } from "@/types/dashboard";

interface FactorsPanelProps {
  factors: ContributingFactor[];
  reasoning: string;
  similarCasesCount: number;
}

export function FactorsPanel({
  factors,
  reasoning,
  similarCasesCount,
}: FactorsPanelProps) {
  return (
    <div className="rounded-xl bg-white p-4 ring-1 ring-slate-200">
      <h3 className="mb-3 text-sm font-semibold text-slate-700">
        Reasoning Path
      </h3>
      <p className="mb-4 text-sm leading-relaxed text-slate-600">
        {reasoning}
      </p>

      {factors.length > 0 && (
        <div className="space-y-2.5">
          <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">
            Contributing Factors
          </p>
          {factors.map((f, i) => (
            <div key={i}>
              <div className="mb-1 flex items-center justify-between text-xs">
                <span className="font-medium text-slate-700">{f.name}</span>
                <span className="tabular-nums text-slate-500">
                  {(f.weight * 100).toFixed(0)}%
                </span>
              </div>
              <div className="h-2 overflow-hidden rounded-full bg-slate-100">
                <div
                  className="h-full rounded-full bg-primary-500 transition-all duration-500"
                  style={{ width: `${f.weight * 100}%` }}
                />
              </div>
              <p className="mt-0.5 text-[11px] text-slate-400">
                {f.description}
              </p>
            </div>
          ))}
        </div>
      )}

      {similarCasesCount > 0 && (
        <div className="mt-4 flex items-center gap-2 rounded-lg bg-slate-50 p-3">
          <svg
            className="h-4 w-4 text-slate-400"
            fill="none"
            viewBox="0 0 24 24"
            strokeWidth={1.5}
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M20.25 6.375c0 2.278-3.694 4.125-8.25 4.125S3.75 8.653 3.75 6.375m16.5 0c0-2.278-3.694-4.125-8.25-4.125S3.75 4.097 3.75 6.375m16.5 0v11.25c0 2.278-3.694 4.125-8.25 4.125s-8.25-1.847-8.25-4.125V6.375m16.5 0v3.75m-16.5-3.75v3.75m16.5 0v3.75C20.25 16.153 16.556 18 12 18s-8.25-1.847-8.25-4.125v-3.75m16.5 0c0 2.278-3.694 4.125-8.25 4.125s-8.25-1.847-8.25-4.125"
            />
          </svg>
          <span className="text-xs text-slate-600">
            <span className="font-semibold">{similarCasesCount}</span> similar
            historical case{similarCasesCount !== 1 ? "s" : ""} found via
            vector similarity search
          </span>
        </div>
      )}
    </div>
  );
}
