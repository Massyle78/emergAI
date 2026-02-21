import type { SymptomExtraction, SymptomSeverity } from "@/types/dashboard";

interface SymptomPanelProps {
  symptoms: SymptomExtraction;
}

const SEVERITY_STYLES: Record<SymptomSeverity, string> = {
  critical: "bg-red-100 text-red-800",
  severe: "bg-orange-100 text-orange-800",
  moderate: "bg-yellow-100 text-yellow-800",
  mild: "bg-emerald-100 text-emerald-800",
};

export function SymptomPanel({ symptoms }: SymptomPanelProps) {
  return (
    <div className="rounded-xl bg-white p-4 ring-1 ring-slate-200">
      <h3 className="mb-1 text-sm font-semibold text-slate-700">
        Symptoms{" "}
        <span className="font-normal text-slate-400">
          ({(symptoms.confidence * 100).toFixed(0)}% confidence)
        </span>
      </h3>
      <p className="mb-3 text-sm text-slate-600 italic">
        &ldquo;{symptoms.chief_complaint}&rdquo;
      </p>

      {symptoms.symptoms.length > 0 && (
        <div className="space-y-2">
          {symptoms.symptoms.map((s, i) => (
            <div
              key={i}
              className="flex items-start gap-2 rounded-lg bg-slate-50 p-2.5"
            >
              <span
                className={`mt-0.5 inline-flex rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase ${SEVERITY_STYLES[s.severity]}`}
              >
                {s.severity}
              </span>
              <div className="min-w-0 flex-1">
                <p className="text-sm font-medium text-slate-900">{s.name}</p>
                {s.description && (
                  <p className="text-xs text-slate-500">{s.description}</p>
                )}
                {(s.body_region || s.onset_description) && (
                  <p className="mt-0.5 text-[11px] text-slate-400">
                    {s.body_region && <span>Region: {s.body_region}</span>}
                    {s.body_region && s.onset_description && " · "}
                    {s.onset_description && (
                      <span>Onset: {s.onset_description}</span>
                    )}
                  </p>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {symptoms.follow_up_questions.length > 0 && (
        <div className="mt-3 rounded-lg bg-primary-50 p-3">
          <p className="mb-1 text-xs font-semibold text-primary-800">
            Suggested Follow-up Questions
          </p>
          <ul className="space-y-1">
            {symptoms.follow_up_questions.map((q, i) => (
              <li
                key={i}
                className="flex gap-1.5 text-xs text-primary-700"
              >
                <span className="mt-1 h-1 w-1 flex-shrink-0 rounded-full bg-primary-400" />
                {q}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
