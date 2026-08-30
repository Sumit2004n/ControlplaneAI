"use client";
import Link from "next/link";
import { useEffect, useState } from "react";

import { api } from "@/lib/api";
import { fmtTime } from "@/lib/format";
import type { AuditEntry } from "@/lib/types";

const EVENTS = ["", "DECISION_MADE", "REVIEW_REQUESTED", "HUMAN_REVIEW", "POLICY_UPDATED", "POLICY_CREATED", "FEEDBACK_RECORDED"];

export default function AuditLogsPage() {
  const [items, setItems] = useState<AuditEntry[]>([]);
  const [total, setTotal] = useState(0);
  const [event, setEvent] = useState("");
  const [offset, setOffset] = useState(0);

  useEffect(() => {
    const params = new URLSearchParams({ limit: "40", offset: String(offset) });
    if (event) params.set("event", event);
    api<{ total: number; items: AuditEntry[] }>(`/api/audit-logs?${params}`)
      .then((r) => { setItems(r.items); setTotal(r.total); }).catch(() => {});
  }, [event, offset]);

  return (
    <div className="mx-auto max-w-[1100px] space-y-4">
      <div className="flex items-end justify-between">
        <div>
          <h1 className="text-xl font-bold text-slate-900">Audit Logs</h1>
          <p className="text-sm text-slate-500">Immutable trail of every ControlPlane decision, review and policy change ({total} events).</p>
        </div>
        <select className="input !w-56" value={event} onChange={(e) => { setEvent(e.target.value); setOffset(0); }}>
          {EVENTS.map((e) => <option key={e} value={e}>{e === "" ? "All events" : e.replace(/_/g, " ")}</option>)}
        </select>
      </div>

      <div className="card divide-y divide-slate-50">
        {items.map((a) => (
          <div key={a.id} className="flex items-start gap-4 p-4">
            <div className="w-36 shrink-0 font-mono text-xs text-slate-400">{fmtTime(a.timestamp)}</div>
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-2 text-sm">
                <span className="font-semibold text-slate-800">{a.event.replace(/_/g, " ")}</span>
                <span className="text-xs text-slate-400">by {a.actor}</span>
                {a.interaction_id && (
                  <Link href={`/interactions/${a.interaction_id}`} className="font-mono text-xs text-brand-600 hover:underline">
                    {a.interaction_id}
                  </Link>
                )}
              </div>
              <pre className="mt-1 max-w-full overflow-x-auto rounded bg-slate-50 p-2 text-[10px] leading-relaxed text-slate-500">
                {JSON.stringify(a.meta)}
              </pre>
            </div>
          </div>
        ))}
      </div>

      <div className="flex justify-end gap-2">
        <button className="btn-secondary" disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - 40))}>Previous</button>
        <button className="btn-secondary" disabled={offset + 40 >= total} onClick={() => setOffset(offset + 40)}>Next</button>
      </div>
    </div>
  );
}
