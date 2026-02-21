import { BrowserRouter, Route, Routes } from "react-router-dom";

import { AppLayout } from "@/components/layout/AppLayout";
import { KioskLanding } from "@/pages/KioskLanding";
import { NotFound } from "@/pages/NotFound";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<AppLayout />}>
          <Route index element={<KioskLanding />} />
          {/* Phase 15+ routes */}
          <Route path="triage" element={<TriagePlaceholder />} />
          <Route path="*" element={<NotFound />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

function TriagePlaceholder() {
  return (
    <div className="flex flex-1 items-center justify-center p-6">
      <div className="kiosk-card max-w-md text-center">
        <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-accent-100">
          <svg
            className="h-7 w-7 text-accent-600"
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
        </div>
        <h2 className="text-xl font-semibold text-slate-900">
          Capture Module
        </h2>
        <p className="mt-2 text-sm text-slate-500">
          Webcam and microphone capture will be available in the next phase.
          This screen will guide patients through the intake process.
        </p>
      </div>
    </div>
  );
}
