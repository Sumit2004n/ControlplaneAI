"use client";
import { Pause, Play } from "lucide-react";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";

import { DecisionBadge, RiskScore } from "@/components/Badges";
import { api } from "@/lib/api";
import { APPLICATIONS, RISK_TYPE_LABELS, appLabel, fmtMs, fmtTime } from "@/lib/format";
import type { InteractionSummary } from "@/lib/types";

const DECISIONS = ["ALLOW", "EDIT", "FLAG", "HUMAN_REVIEW", "BLOCK"];

export default function LiveMonitorPage() {
  const [items, setItems] = useState<InteractionSummary[]>([]);
  const [app, setApp] = useState(""); const [decision, setDecision] = useState("");
  const [minRisk, setMinRisk] = useState(0); const [live, setLive] = useState(true);
  const timer = useRef<ReturnType<typeof setInterval> | null>(null);

  const load = () => {
    const params = new URLSearchParams({ limit: "60" });
    if (app) params.set("application", app);
    if (decision) params.set("decision", decision);
    if (minRisk) params.set("min_risk", String(minRisk));
    api<{ items: InteractionSummary[] }>(`/api/interactions?${params}`).then((r) => setItems(r.items)).catch(() => {});
  };

  useEffect(() => {
    load();
    if (timer.current) clearInterval(timer.current);
    if (live) timer.current = setInterval(load, 4000);
    return () => { if (timer.current) clearInterval(timer.current); };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [app, decision, minRisk, live]);

  return (
    <div className="mx-auto max-w-[1200px] space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-slate-900">Live Monitor</h1>
          <p className="text-sm text-slate-500">Real-time feed of interactions passing through ControlPlane (refreshes every 4 s).</p>
        </div>
        <button className="btn-secondary" onClick={() => setLive(!live)}>
          {live ? <Pause className="h-4 w-4" /> : <Play className="h-4 w-4" />} {live ? "Pause" : "Resume"}
        </button>
      </div>

      <div className="card flex flex-wrap items-end gap-3 p-4">
        <div>
          <label className="label">Application</label>
          <select className="input !w-48" value={app} onChange={(e) => setApp(e.target.value)}>
            <option value="">All applications</option>
            {APPLICATIONS.map((a) => <option key={a.id} value={a.id}>{a.label}</option>)}
          </select>
        </div>
        <div>
          <label className="label">Decision</label>
          <select className="input !w-44" value={decision} onChange={(e) => setDecision(e.target.value)}>
            <option value="">All decisions</option>
            {DECISIONS.map((d) => <option key={d} value={d}>{d}</option>)}
          </select>
        </div>
        <div>
          <label className="label">Min risk: {minRisk}</label>
          <input type="range" min={0} max={100} value={minRisk} onChange={(e) => setMinRisk(Number(e.target.value))} className="w-44" />
        </div>
      </div>

      <div className="card overflow-hidden">
        <table className="w-full">
          <thead className="border-b border-slate-100 bg-slate-50/60">
            <tr>
              <th className="table-th">Time</th><th className="table-th">ID</th><th className="table-th">Application</th>
              <th className="table-th">Prompt</th><th className="table-th">Primary Risk</th>
              <th className="table-th">Risk</th><th className="table-th">Latency</th><th className="table-th">Decision</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-50">
            {items.map((i) => (
              <tr key={i.interaction_id} className="hover:bg-slate-50">
                <td className="table-td whitespace-nowrap font-mono text-xs">{fmtTime(i.timestamp)}</td>
                <td className="table-td whitespace-nowrap font-mono text-xs">
                  <Link href={`/interactions/${i.interaction_id}`} className="text-brand-600 hover:underline">{i.interaction_id}</Link>
                </td>
                <td className="table-td whitespace-nowrap text-xs">{appLabel(i.application)}</td>
                <td className="table-td max-w-xs truncate text-xs">{i.user_prompt}</td>
                <td className="table-td text-xs">{i.primary_risk ? RISK_TYPE_LABELS[i.primary_risk] ?? i.primary_risk : "—"}</td>
                <td className="table-td"><RiskScore score={i.overall_risk} /></td>
                <td className="table-td font-mono text-xs">{fmtMs(i.latency_ms)}</td>
                <td className="table-td"><DecisionBadge decision={i.decision} /></td>
              </tr>
            ))}
          </tbody>
        </table>
        {items.length === 0 && <div className="p-8 text-center text-sm text-slate-400">No interactions match the filters.</div>}
      </div>
    </div>
  );
}
