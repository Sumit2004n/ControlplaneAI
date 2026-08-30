"use client";
import { Globe2, MonitorSmartphone } from "lucide-react";

import { useApp } from "@/lib/context";
import { APPLICATIONS, REGIONS } from "@/lib/format";
import { StatusDot } from "./Badges";

export default function Header() {
  const { application, setApplication, region, setRegion, demoMode, backendUp } = useApp();
  return (
    <header className="flex items-center justify-between border-b border-slate-200 bg-white px-6 py-3">
      <div className="flex items-center gap-4">
        <StatusDot ok={backendUp} label={backendUp ? "ControlPlane Active" : "Backend offline — start the FastAPI server"} />
        {demoMode !== null && (
          <span className={`rounded-full border px-2.5 py-0.5 text-[11px] font-semibold ${
            demoMode ? "border-sky-200 bg-sky-50 text-sky-700" : "border-emerald-200 bg-emerald-50 text-emerald-700"}`}>
            {demoMode ? "DEMO MODE — deterministic, offline" : "LIVE LLM MODE"}
          </span>
        )}
      </div>
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-1.5">
          <MonitorSmartphone className="h-4 w-4 text-slate-400" />
          <select value={application} onChange={(e) => setApplication(e.target.value)}
            className="rounded-lg border border-slate-300 bg-white px-2.5 py-1.5 text-sm font-medium text-slate-700 focus:outline-none">
            {APPLICATIONS.map((a) => <option key={a.id} value={a.id}>{a.label}</option>)}
          </select>
        </div>
        <div className="flex items-center gap-1.5">
          <Globe2 className="h-4 w-4 text-slate-400" />
          <select value={region} onChange={(e) => setRegion(e.target.value)}
            className="rounded-lg border border-slate-300 bg-white px-2.5 py-1.5 text-sm font-medium text-slate-700 focus:outline-none">
            {REGIONS.map((r) => <option key={r} value={r}>{r}</option>)}
          </select>
        </div>
      </div>
    </header>
  );
}
