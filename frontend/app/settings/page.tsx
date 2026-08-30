"use client";
import { useEffect, useState } from "react";

import { api } from "@/lib/api";

interface Health { status: string; controlplane: string; demo_mode: boolean; provider: string; model: string }

export default function SettingsPage() {
  const [health, setHealth] = useState<Health | null>(null);
  const [err, setErr] = useState(false);

  useEffect(() => { api<Health>("/api/health").then(setHealth).catch(() => setErr(true)); }, []);

  return (
    <div className="mx-auto max-w-[800px] space-y-4">
      <div>
        <h1 className="text-xl font-bold text-slate-900">Settings & System Status</h1>
        <p className="text-sm text-slate-500">Runtime configuration is controlled via environment variables in <code className="rounded bg-slate-100 px-1">backend/.env</code>.</p>
      </div>

      <div className="card p-5">
        <div className="label">Runtime</div>
        {err && <p className="text-sm text-red-600">Backend unreachable — start it with <code className="rounded bg-slate-100 px-1">uvicorn app.main:app --port 8000</code> from the backend folder.</p>}
        {health && (
          <div className="mt-2 space-y-2 text-sm">
            <div className="flex justify-between"><span className="text-slate-500">ControlPlane status</span><span className="font-semibold text-emerald-600">{health.controlplane}</span></div>
            <div className="flex justify-between"><span className="text-slate-500">Mode</span>
              <span className="font-semibold">{health.demo_mode ? "DEMO MODE (deterministic, offline)" : "LIVE LLM MODE"}</span></div>
            <div className="flex justify-between"><span className="text-slate-500">LLM provider</span><span className="font-semibold">{health.provider}</span></div>
            <div className="flex justify-between"><span className="text-slate-500">Model</span><span className="font-semibold">{health.model}</span></div>
          </div>
        )}
      </div>

      <div className="card p-5 text-sm leading-relaxed text-slate-600">
        <div className="label">Switching to a real LLM</div>
        <ol className="mt-1 list-inside list-decimal space-y-1">
          <li>Copy <code className="rounded bg-slate-100 px-1">.env.example</code> to <code className="rounded bg-slate-100 px-1">backend/.env</code></li>
          <li>Set <code className="rounded bg-slate-100 px-1">DEMO_MODE=false</code> and <code className="rounded bg-slate-100 px-1">LLM_API_KEY=sk-…</code></li>
          <li>Restart the backend. Generation, claim extraction and AI-as-judge layers switch to the configured model; deterministic layers stay active.</li>
        </ol>
        <p className="mt-2 text-[11px] text-slate-400">API keys live only on the server and are never exposed to this frontend.</p>
      </div>

      <div className="card p-5 text-sm text-slate-600">
        <div className="label">Prototype limitations (stated per PRD sec 93)</div>
        <ul className="mt-1 list-inside list-disc space-y-1 text-xs">
          <li>Simulated enterprise data; risk scores are prototype estimates.</li>
          <li>Bias detection identifies potential bias; it cannot prove real-world discrimination.</li>
          <li>Hallucination verification depends on evidence being present in the knowledge base.</li>
          <li>Regional profiles are governance configuration, not legal compliance engines.</li>
          <li>Production deployment would require enterprise security controls (SSO, RBAC, encryption).</li>
          <li>Human oversight remains necessary for high-impact decisions.</li>
        </ul>
      </div>
    </div>
  );
}
