import { BrowserRouter, Route, Routes } from "react-router-dom";

import { AppLayout } from "@/components/layout/AppLayout";
import { KioskLanding } from "@/pages/KioskLanding";
import { NotFound } from "@/pages/NotFound";
import { TriageCapture } from "@/pages/TriageCapture";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<AppLayout />}>
          <Route index element={<KioskLanding />} />
          <Route path="triage" element={<TriageCapture />} />
          <Route path="*" element={<NotFound />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
