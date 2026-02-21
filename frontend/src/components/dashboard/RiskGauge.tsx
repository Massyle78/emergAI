import {
  ACUITY_BG_LIGHT,
  ACUITY_COLORS,
  ACUITY_LABELS,
  ACUITY_TEXT_COLORS,
  type AcuityLevel,
} from "@/types/dashboard";

interface RiskGaugeProps {
  score: number;
  acuityLevel: AcuityLevel;
}

const GAUGE_RADIUS = 60;
const GAUGE_STROKE = 10;
const GAUGE_CIRCUMFERENCE = Math.PI * GAUGE_RADIUS;

/**
 * Semi-circular risk gauge with ESI badge.
 * Score 0–1 maps to the arc fill and color.
 */
export function RiskGauge({ score, acuityLevel }: RiskGaugeProps) {
  const offset = GAUGE_CIRCUMFERENCE * (1 - score);
  const label = ACUITY_LABELS[acuityLevel];

  return (
    <div className="flex flex-col items-center gap-3">
      <div className="relative">
        <svg
          width={GAUGE_RADIUS * 2 + GAUGE_STROKE}
          height={GAUGE_RADIUS + GAUGE_STROKE + 8}
          className="overflow-visible"
        >
          {/* Background arc */}
          <path
            d={arcPath(GAUGE_RADIUS, GAUGE_STROKE)}
            fill="none"
            stroke="#e2e8f0"
            strokeWidth={GAUGE_STROKE}
            strokeLinecap="round"
          />
          {/* Filled arc */}
          <path
            d={arcPath(GAUGE_RADIUS, GAUGE_STROKE)}
            fill="none"
            stroke={arcColor(score)}
            strokeWidth={GAUGE_STROKE}
            strokeLinecap="round"
            strokeDasharray={GAUGE_CIRCUMFERENCE}
            strokeDashoffset={offset}
            className="transition-all duration-700 ease-out"
          />
        </svg>

        {/* Center score */}
        <div className="absolute inset-0 flex items-end justify-center pb-1">
          <span className="text-3xl font-bold tabular-nums text-slate-900">
            {(score * 100).toFixed(0)}
          </span>
        </div>
      </div>

      {/* Acuity badge */}
      <span
        className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-sm font-semibold ${ACUITY_BG_LIGHT[acuityLevel]} ${ACUITY_TEXT_COLORS[acuityLevel]}`}
      >
        <span
          className={`h-2 w-2 rounded-full ${ACUITY_COLORS[acuityLevel]}`}
        />
        ESI {acuityLevel} — {label}
      </span>
    </div>
  );
}

function arcPath(r: number, sw: number): string {
  const cx = r + sw / 2;
  const cy = r + sw / 2;
  return `M ${cx - r} ${cy} A ${r} ${r} 0 0 1 ${cx + r} ${cy}`;
}

function arcColor(score: number): string {
  if (score >= 0.8) return "#dc2626";
  if (score >= 0.6) return "#f59e0b";
  if (score >= 0.4) return "#eab308";
  return "#10b981";
}
