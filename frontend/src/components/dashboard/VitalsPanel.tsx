import type { Vitals } from "@/types/dashboard";

interface VitalsPanelProps {
  vitals: Vitals;
}

const NORMAL_HR = [60, 100] as const;
const NORMAL_SPO2 = 95;
const NORMAL_RR = [12, 20] as const;

export function VitalsPanel({ vitals }: VitalsPanelProps) {
  return (
    <div className="rounded-xl bg-white p-4 ring-1 ring-slate-200">
      <h3 className="mb-3 text-sm font-semibold text-slate-700">
        Vitals{" "}
        <span className="font-normal text-slate-400">
          ({(vitals.confidence * 100).toFixed(0)}% confidence)
        </span>
      </h3>

      <div className="grid grid-cols-2 gap-3">
        <VitalItem
          label="Heart Rate"
          value={`${vitals.heart_rate_bpm.toFixed(0)} bpm`}
          alert={
            vitals.heart_rate_bpm < NORMAL_HR[0] ||
            vitals.heart_rate_bpm > NORMAL_HR[1]
          }
        />
        <VitalItem
          label="SpO₂"
          value={
            vitals.spo2_percent != null
              ? `${vitals.spo2_percent.toFixed(0)}%`
              : "—"
          }
          alert={
            vitals.spo2_percent != null && vitals.spo2_percent < NORMAL_SPO2
          }
        />
        <VitalItem
          label="Respiratory Rate"
          value={
            vitals.respiratory_rate != null
              ? `${vitals.respiratory_rate.toFixed(0)} /min`
              : "—"
          }
          alert={
            vitals.respiratory_rate != null &&
            (vitals.respiratory_rate < NORMAL_RR[0] ||
              vitals.respiratory_rate > NORMAL_RR[1])
          }
        />
        <VitalItem
          label="Blood Pressure"
          value={
            vitals.blood_pressure
              ? `${vitals.blood_pressure.systolic.toFixed(0)}/${vitals.blood_pressure.diastolic.toFixed(0)}`
              : "—"
          }
          alert={
            vitals.blood_pressure != null &&
            (vitals.blood_pressure.systolic > 140 ||
              vitals.blood_pressure.systolic < 90)
          }
        />
      </div>
    </div>
  );
}

interface VitalItemProps {
  label: string;
  value: string;
  alert: boolean;
}

function VitalItem({ label, value, alert }: VitalItemProps) {
  return (
    <div
      className={`rounded-lg p-3 ${
        alert ? "bg-red-50 ring-1 ring-red-100" : "bg-slate-50"
      }`}
    >
      <p className="text-[11px] font-medium uppercase tracking-wider text-slate-400">
        {label}
      </p>
      <p
        className={`mt-0.5 text-lg font-bold tabular-nums ${
          alert ? "text-red-700" : "text-slate-900"
        }`}
      >
        {value}
      </p>
    </div>
  );
}
