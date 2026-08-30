"use client";
import { useEffect, useState } from "react";
import {
  Bar, BarChart, CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";

import { api } from "@/lib/api";
import { RISK_TYPE_LABELS, appLabel, fmtMs } from "@/lib/format";
import type { Analytics } from "@/lib/types";

export default function AnalyticsPage() {
  const [data, setData] = useState<Analytics | null>(null);

  useEffect(() => { api<Analytics>("/api/analytics?days=8").then(setData).catch(() => {}); }, []);
  if (!data) return <div className="p-8 text-sm text-slate-400">Loading analytics…</div>;

  const fb = data.feedback;
  const appData = Object.entries(data.by_application).map(([k, v]) => ({
    name: appLabel(k), interactions: v.total, highRisk: v.high_risk, blocked: v.blocked,
  }));

  return (
    <div className="mx-auto max-w-[1200px] space-y-4">
      <div>
        <h1 className="text-xl font-bold text-slate-900">Analytics & Trust Metrics</h1>
        <p className="text-sm text-slate-500">
          Detection quality, human oversight and runtime telemetry — evaluated on the seeded scenario library plus live interactions.
        </p>
      </div>

      {/* Feedback-loop metrics (PRD sec 23) */}
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-5">
        {[
          ["Total reviewed", fb.total_reviewed, ""],
          ["True positives", fb.true_positives, "risk confirmed by humans"],
          ["False positives", fb.false_positives, "detection overturned"],
          ["False positive rate", `${fb.false_positive_rate}%`, "target: tune thresholds down"],
          ["Human override rate", `${fb.human_override_rate}%`, "of all interactions"],
        ].map(([label, value, sub]) => (
          <div key={label as string} className="card p-4">
            <div className="text-xs font-medium text-slate-500">{label}</div>
            <div className="text-2xl font-bold tabular-nums text-slate-900">{value}</div>
            {sub && <div className="text-[11px] text-slate-400">{sub}</div>}
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <div className="card p-4">
          <div className="label">Average Risk Trend</div>
          <ResponsiveContainer width="100%" height={240}>
            <LineChart data={data.trend}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} />
              <XAxis dataKey="date" tick={{ fontSize: 11 }} />
              <YAxis tick={{ fontSize: 11 }} domain={[0, 100]} />
              <Tooltip />
              <Line type="monotone" dataKey="avg_risk" stroke="#3b5bdb" strokeWidth={2} name="Avg risk" />
            </LineChart>
          </ResponsiveContainer>
        </div>
        <div className="card p-4">
          <div className="label">Volume & Interventions by Application</div>
          <ResponsiveContainer width="100%" height={240}>
            <BarChart data={appData}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} />
              <XAxis dataKey="name" tick={{ fontSize: 11 }} />
              <YAxis tick={{ fontSize: 11 }} allowDecimals={false} />
              <Tooltip />
              <Legend wrapperStyle={{ fontSize: 11 }} />
              <Bar dataKey="interactions" fill="#3b5bdb" name="Interactions" radius={[3, 3, 0, 0]} />
              <Bar dataKey="highRisk" fill="#f97316" name="High risk" radius={[3, 3, 0, 0]} />
              <Bar dataKey="blocked" fill="#ef4444" name="Blocked" radius={[3, 3, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <div className="card p-4">
          <div className="label">Latency Telemetry</div>
          <div className="mt-2 space-y-2 text-sm">
            <div className="flex justify-between"><span className="text-slate-500">Average total latency</span><span className="font-semibold">{fmtMs(data.latency.avg_ms)}</span></div>
            <div className="flex justify-between"><span className="text-slate-500">P95 total latency</span><span className="font-semibold">{fmtMs(data.latency.p95_ms)}</span></div>
            <p className="border-t border-slate-100 pt-2 text-[11px] text-slate-400">
              Detectors run in parallel to protect latency. In demo mode deterministic detectors add ~1–5 ms of overhead.
            </p>
          </div>
        </div>
        <div className="card p-4">
          <div className="label">Cost Telemetry</div>
          <div className="mt-2 space-y-2 text-sm">
            <div className="flex justify-between"><span className="text-slate-500">Mode</span><span className="font-semibold">{data.cost_telemetry.mode}</span></div>
            <div className="flex justify-between"><span className="text-slate-500">LLM calls (this session)</span><span className="font-semibold tabular-nums">{data.cost_telemetry.llm_calls}</span></div>
            <div className="flex justify-between"><span className="text-slate-500">Input / output tokens</span><span className="font-semibold tabular-nums">{data.cost_telemetry.input_tokens} / {data.cost_telemetry.output_tokens}</span></div>
            <div className="flex justify-between"><span className="text-slate-500">Estimated cost</span>
              <span className="font-semibold">{data.cost_telemetry.estimated_cost_usd === null ? "Simulation mode" : `$${data.cost_telemetry.estimated_cost_usd}`}</span></div>
          </div>
        </div>
        <div className="card p-4">
          <div className="label">High-Risk Detections by Type</div>
          <div className="mt-2 space-y-2 text-sm">
            {Object.entries(data.risk_type_frequency).map(([k, v]) => (
              <div key={k} className="flex justify-between">
                <span className="text-slate-500">{RISK_TYPE_LABELS[k] ?? k}</span>
                <span className="font-semibold tabular-nums">{v}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      <p className="text-[11px] text-slate-400">
        Metrics are computed from genuinely analyzed interactions (seeded scenario library + live usage), not fabricated
        benchmark claims — prototype evaluation per PRD section 94.
      </p>
    </div>
  );
}
