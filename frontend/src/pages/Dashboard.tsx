import { useCallback, useEffect, useState } from "react";

import { CdsCardDisplay } from "@/components/dashboard/CdsCardDisplay";
import { FactorsPanel } from "@/components/dashboard/FactorsPanel";
import { PatientQueue } from "@/components/dashboard/PatientQueue";
import { RiskGauge } from "@/components/dashboard/RiskGauge";
import { SymptomPanel } from "@/components/dashboard/SymptomPanel";
import { VitalsPanel } from "@/components/dashboard/VitalsPanel";
import { getPatientQueue, getTriageResult } from "@/lib/mock-data";
import type { PatientQueueItem, TriageResultData } from "@/types/dashboard";

const QUEUE_POLL_INTERVAL = 15_000;

/**
 * Simulated clinician dashboard.
 *
 * Layout: left sidebar with patient queue, right main area with
 * the selected patient's triage details, CDS cards, and reasoning.
 */
export function Dashboard() {
  const [patients, setPatients] = useState<PatientQueueItem[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [result, setResult] = useState<TriageResultData | null>(null);

  useEffect(() => {
    const load = () => setPatients(getPatientQueue());
    load();
    const id = setInterval(load, QUEUE_POLL_INTERVAL);
    return () => clearInterval(id);
  }, []);

  useEffect(() => {
    const first = patients[0];
    if (!selectedId && first) {
      setSelectedId(first.id);
    }
  }, [selectedId, patients]);

  useEffect(() => {
    if (selectedId) {
      setResult(getTriageResult(selectedId));
    }
  }, [selectedId]);

  const handleSelect = useCallback((id: string) => {
    setSelectedId(id);
  }, []);

  return (
    <div className="flex flex-1 overflow-hidden">
      {/* Sidebar */}
      <div className="w-72 flex-shrink-0 lg:w-80">
        <PatientQueue
          patients={patients}
          selectedId={selectedId}
          onSelect={handleSelect}
        />
      </div>

      {/* Main content */}
      <div className="flex-1 overflow-y-auto bg-slate-50 p-6">
        {result ? (
          <PatientDetail result={result} />
        ) : (
          <EmptyState />
        )}
      </div>
    </div>
  );
}

function PatientDetail({ result }: { result: TriageResultData }) {
  const { patient, risk, vitals, symptoms, cds_cards, errors } = result;

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">{patient.name}</h1>
          <p className="text-sm text-slate-500">
            {patient.age} y/o {patient.sex} · Arrived{" "}
            {new Date(patient.arrived_at).toLocaleTimeString("en-US", {
              hour: "2-digit",
              minute: "2-digit",
            })}
          </p>
        </div>
        <StatusPill status={patient.status} />
      </div>

      {/* Partial result warning */}
      {errors.length > 0 && (
        <div className="rounded-xl border border-amber-200 bg-amber-50 p-3">
          <p className="text-sm font-medium text-amber-800">
            Partial Assessment
          </p>
          <ul className="mt-1 space-y-0.5">
            {errors.map((e, i) => (
              <li key={i} className="text-xs text-amber-700">
                &bull; {e}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Top row: Risk gauge + Vitals */}
      <div className="grid gap-4 lg:grid-cols-2">
        <div className="flex items-center justify-center rounded-xl bg-white p-6 ring-1 ring-slate-200">
          <RiskGauge score={risk.score} acuityLevel={risk.acuity_level} />
        </div>
        {vitals && <VitalsPanel vitals={vitals} />}
      </div>

      {/* CDS Cards */}
      <CdsCardDisplay cards={cds_cards} />

      {/* Bottom row: Symptoms + Factors */}
      <div className="grid gap-4 lg:grid-cols-2">
        {symptoms && <SymptomPanel symptoms={symptoms} />}
        <FactorsPanel
          factors={risk.contributing_factors}
          reasoning={risk.reasoning}
          similarCasesCount={risk.similar_cases_count}
        />
      </div>
    </div>
  );
}

function EmptyState() {
  return (
    <div className="flex flex-1 items-center justify-center">
      <div className="text-center">
        <svg
          className="mx-auto h-12 w-12 text-slate-300"
          fill="none"
          viewBox="0 0 24 24"
          strokeWidth={1}
          stroke="currentColor"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M15.75 6a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0zM4.501 20.118a7.5 7.5 0 0114.998 0A17.933 17.933 0 0112 21.75c-2.676 0-5.216-.584-7.499-1.632z"
          />
        </svg>
        <p className="mt-3 text-sm font-medium text-slate-500">
          Select a patient from the queue
        </p>
        <p className="text-xs text-slate-400">
          Triage details and CDS cards will appear here
        </p>
      </div>
    </div>
  );
}

function StatusPill({ status }: { status: PatientQueueItem["status"] }) {
  const styles = {
    waiting:
      "bg-slate-100 text-slate-600 ring-slate-200",
    in_review:
      "bg-amber-50 text-amber-700 ring-amber-200",
    completed:
      "bg-accent-50 text-accent-700 ring-accent-200",
  };

  const labels = {
    waiting: "Waiting",
    in_review: "In Review",
    completed: "Completed",
  };

  return (
    <span
      className={`inline-flex items-center rounded-full px-3 py-1 text-xs font-medium ring-1 ${styles[status]}`}
    >
      {labels[status]}
    </span>
  );
}
