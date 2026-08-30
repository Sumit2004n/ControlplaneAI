"use client";
import { Activity, AlertOctagon, ClipboardCheck, Gauge, ShieldAlert, Timer } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";
import {
  Bar, BarChart, CartesianGrid, Cell, Legend, Line, LineChart, Pie, PieChart,
  ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";

import { DecisionBadge, RiskScore } from "@/components/Badges";
import KpiCard from "@/components/KpiCard";
import { api } from "@/lib/api";
import { RISK_TYPE_LABELS, appLabel, decisionLabel, fmtMs, fmtTime } from "@/lib/format";
import type { Analytics, InteractionSummary } from "@/lib/types";

const DECISION_COLORS: Record<string, string> = {
  ALLOW: "#10b981", EDIT: "#f59e0b", FLAG: "#f97316", HUMAN_REVIEW: "#8b5cf6", BLOCK: "#ef4444",
};
const SEVERITY_COLORS: Record<string, string> = {
  LOW: "#10b981", MEDIUM: "#f59e0b", HIGH: "#f97316", CRITICAL: "#ef4444",
};

export default function DashboardPage() {
  const [data, setData] = useState<Analytics | null>(null);
  const [recent, setRecent] = useState<InteractionSummary[]>([]);

  useEffect(() => {
    api<Analytics>("/api/analytics?days=8").then(setData).catch(() => {});
    api<{ items: InteractionSummary[] }>("/api/interactions?min_risk=50&limit=8")
      .then((r) => setRecent(r.items)).catch(() => {});
  }, []);

  if (!data) return <div className="p-8 text-sm text-slate-400">Loading governance dashboard…</div>;

  const decisionData = Object.entries(data.decision_distribution).map(([name, value]) => ({ name: decisionLabel(name), key: name, value }));
  const severityData = ["LOW", "MEDIUM", "HIGH", "CRITICAL"].map((s) => ({ name: s, value: data.risk_distribution[s] ?? 0 }));
  const riskTypeData = Object.entries(data.risk_type_frequency).map(([k, v]) => ({ name: RISK_TYPE_LABELS[k] ?? k, value: v }));

  return (
    <div className="mx-auto max-w-[1400px] space-y-4">
      <div>
        <h1 className="text-xl font-bold text-slate-900">Governance Dashboard</h1>
        <p className="text-sm text-slate-500">Runtime risk posture across all AI applications (last {data.window_days} days).</p>
      </div>

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-6">
        <KpiCard label="Interactions" value={data.kpis.total_interactions} icon={Activity} />
        <KpiCard label="High Risk" value={data.kpis.high_risk} icon={ShieldAlert} tone="orange" />
        <KpiCard label="Blocked" value={data.kpis.blocked} icon={AlertOctagon} tone="red" />
        <KpiCard label="Human Reviews" value={data.kpis.human_reviews} sub={`${data.kpis.pending_reviews} pending`} icon={ClipboardCheck} tone="violet" />
        <KpiCard label="False Positive Rate" value={`${data.feedback.false_positive_rate}%`} sub={`${data.feedback.total_reviewed} reviewed`} icon={Gauge} tone="green" />
        <KpiCard label="Avg Latency" value={fmtMs(data.latency.avg_ms)} sub={`p95 ${fmtMs(data.latency.p95_ms)}`} icon={Timer} />
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <div className="card p-4">
          <div className="label">Decision Distribution</div>
          <ResponsiveContainer width="100%" height={220}>
            <PieChart>
              <Pie data={decisionData} dataKey="value" nameKey="name" innerRadius={45} outerRadius={75} paddingAngle={2}>
                {decisionData.map((d) => <Cell key={d.key} fill={DECISION_COLORS[d.key] ?? "#94a3b8"} />)}
              </Pie>
              <Tooltip />
              <Legend wrapperStyle={{ fontSize: 11 }} />
            </PieChart>
          </ResponsiveContainer>
        </div>
        <div className="card p-4">
          <div className="label">Risk Severity Distribution</div>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={severityData}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} />
              <XAxis dataKey="name" tick={{ fontSize: 11 }} />
              <YAxis tick={{ fontSize: 11 }} allowDecimals={false} />
              <Tooltip />
              <Bar dataKey="value" radius={[4, 4, 0, 0]}>
                {severityData.map((d) => <Cell key={d.name} fill={SEVERITY_COLORS[d.name]} />)}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
        <div className="card p-4">
          <div className="label">High-Risk Detections by Type</div>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={riskTypeData} layout="vertical">
              <CartesianGrid strokeDasharray="3 3" horizontal={false} />
              <XAxis type="number" tick={{ fontSize: 11 }} allowDecimals={false} />
              <YAxis type="category" dataKey="name" tick={{ fontSize: 11 }} width={90} />
              <Tooltip />
              <Bar dataKey="value" fill="#3b5bdb" radius={[0, 4, 4, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <div className="card p-4 lg:col-span-2">
          <div className="label">Interactions & Interventions Trend</div>
          <ResponsiveContainer width="100%" height={220}>
            <LineChart data={data.trend}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} />
              <XAxis dataKey="date" tick={{ fontSize: 11 }} />
              <YAxis tick={{ fontSize: 11 }} allowDecimals={false} />
              <Tooltip />
              <Legend wrapperStyle={{ fontSize: 11 }} />
              <Line type="monotone" dataKey="total" stroke="#3b5bdb" strokeWidth={2} dot={false} name="Interactions" />
              <Line type="monotone" dataKey="blocked" stroke="#ef4444" strokeWidth={2} dot={false} name="Blocked" />
              <Line type="monotone" dataKey="flagged" stroke="#f97316" strokeWidth={2} dot={false} name="Flagged" />
            </LineChart>
          </ResponsiveContainer>
        </div>
        <div className="card p-4">
          <div className="label">By Application</div>
          <div className="mt-2 space-y-3">
            {Object.entries(data.by_application).map(([app, s]) => (
              <div key={app} className="rounded-lg border border-slate-100 p-3">
                <div className="flex items-center justify-between text-sm font-semibold text-slate-800">
                  {appLabel(app)}
                  <span className="text-xs font-normal text-slate-400">{s.total} interactions</span>
                </div>
                <div className="mt-1 flex gap-4 text-xs text-slate-500">
                  <span>avg risk <span className="font-semibold text-slate-700">{s.avg_risk}</span></span>
                  <span>high risk <span className="font-semibold text-orange-600">{s.high_risk}</span></span>
                  <span>blocked <span className="font-semibold text-red-600">{s.blocked}</span></span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="card overflow-hidden">
        <div className="flex items-center justify-between px-4 pt-4">
          <div className="label !mb-0">Recent High-Risk Incidents</div>
          <Link href="/interactions" className="text-xs font-medium text-brand-600 hover:underline">View all →</Link>
        </div>
        <table className="mt-2 w-full">
          <thead className="border-b border-slate-100">
            <tr>
              <th className="table-th">Time</th><th className="table-th">Application</th>
              <th className="table-th">Prompt</th><th className="table-th">Risk</th><th className="table-th">Decision</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-50">
            {recent.map((i) => (
              <tr key={i.interaction_id} className="hover:bg-slate-50">
                <td className="table-td whitespace-nowrap text-xs">{fmtTime(i.timestamp)}</td>
                <td className="table-td whitespace-nowrap">{appLabel(i.application)}</td>
                <td className="table-td max-w-md truncate">
                  <Link href={`/interactions/${i.interaction_id}`} className="hover:text-brand-600 hover:underline">{i.user_prompt}</Link>
                </td>
                <td className="table-td"><RiskScore score={i.overall_risk} /></td>
                <td className="table-td"><DecisionBadge decision={i.decision} /></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
