"use client";
import Link from "next/link";
import { useEffect, useState } from "react";

import { DecisionBadge, RiskScore } from "@/components/Badges";
import { api } from "@/lib/api";
import { APPLICATIONS, appLabel, fmtTime } from "@/lib/format";
import type { InteractionSummary } from "@/lib/types";

const PAGE = 25;

export default function InteractionsPage() {
  const [items, setItems] = useState<InteractionSummary[]>([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [app, setApp] = useState("");

  useEffect(() => {
    const params = new URLSearchParams({ limit: String(PAGE), offset: String(offset) });
    if (app) params.set("application", app);
    api<{ total: number; items: InteractionSummary[] }>(`/api/interactions?${params}`)
      .then((r) => { setItems(r.items); setTotal(r.total); }).catch(() => {});
  }, [offset, app]);

  return (
    <div className="mx-auto max-w-[1200px] space-y-4">
      <div className="flex items-end justify-between">
        <div>
          <h1 className="text-xl font-bold text-slate-900">Interactions</h1>
          <p className="text-sm text-slate-500">Complete history of analyzed AI interactions ({total} total).</p>
        </div>
        <select className="input !w-52" value={app} onChange={(e) => { setApp(e.target.value); setOffset(0); }}>
          <option value="">All applications</option>
          {APPLICATIONS.map((a) => <option key={a.id} value={a.id}>{a.label}</option>)}
        </select>
      </div>

      <div className="card overflow-hidden">
        <table className="w-full">
          <thead className="border-b border-slate-100 bg-slate-50/60">
            <tr>
              <th className="table-th">ID</th><th className="table-th">Time</th><th className="table-th">Application</th>
              <th className="table-th">Prompt</th><th className="table-th">Risk</th>
              <th className="table-th">Decision</th><th className="table-th">Review</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-50">
            {items.map((i) => (
              <tr key={i.interaction_id} className="hover:bg-slate-50">
                <td className="table-td whitespace-nowrap font-mono text-xs">
                  <Link href={`/interactions/${i.interaction_id}`} className="text-brand-600 hover:underline">{i.interaction_id}</Link>
                </td>
                <td className="table-td whitespace-nowrap text-xs">{fmtTime(i.timestamp)}</td>
                <td className="table-td whitespace-nowrap text-xs">{appLabel(i.application)}</td>
                <td className="table-td max-w-sm truncate text-xs">{i.user_prompt}</td>
                <td className="table-td"><RiskScore score={i.overall_risk} /></td>
                <td className="table-td"><DecisionBadge decision={i.decision} /></td>
                <td className="table-td text-xs">
                  {i.review_status === "pending" && <span className="font-medium text-orange-600">Pending</span>}
                  {i.review_status === "reviewed" && <span className="text-slate-500">{i.human_decision}{i.human_override ? " (override)" : ""}</span>}
                  {i.review_status === "none" && <span className="text-slate-300">—</span>}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="flex items-center justify-between text-sm text-slate-500">
        <span>Showing {offset + 1}–{Math.min(offset + PAGE, total)} of {total}</span>
        <div className="flex gap-2">
          <button className="btn-secondary" disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - PAGE))}>Previous</button>
          <button className="btn-secondary" disabled={offset + PAGE >= total} onClick={() => setOffset(offset + PAGE)}>Next</button>
        </div>
      </div>
    </div>
  );
}
