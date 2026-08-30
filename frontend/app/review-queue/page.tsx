"use client";
import { Check, Pencil, X } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";

import { DecisionBadge, RiskScore } from "@/components/Badges";
import { api, post } from "@/lib/api";
import { RISK_TYPE_LABELS, appLabel, fmtTime } from "@/lib/format";
import type { ReviewItem } from "@/lib/types";

export default function ReviewQueuePage() {
  const [tab, setTab] = useState<"pending" | "reviewed">("pending");
  const [items, setItems] = useState<ReviewItem[]>([]);
  const [active, setActive] = useState<ReviewItem | null>(null);

  const load = () =>
    api<{ items: ReviewItem[] }>(`/api/reviews?status=${tab}`).then((r) => setItems(r.items)).catch(() => {});
  useEffect(() => { load(); /* eslint-disable-line react-hooks/exhaustive-deps */ }, [tab]);

  return (
    <div className="mx-auto max-w-[1200px] space-y-4">
      <div>
        <h1 className="text-xl font-bold text-slate-900">Human Review Queue</h1>
        <p className="text-sm text-slate-500">Flagged interactions awaiting human judgment. Reviewer decisions feed the feedback loop and analytics.</p>
      </div>

      <div className="flex gap-2">
        <button onClick={() => setTab("pending")} className={tab === "pending" ? "btn-primary" : "btn-secondary"}>Pending</button>
        <button onClick={() => setTab("reviewed")} className={tab === "reviewed" ? "btn-primary" : "btn-secondary"}>Reviewed</button>
      </div>

      <div className="card overflow-hidden">
        <table className="w-full">
          <thead className="border-b border-slate-100 bg-slate-50/60">
            <tr>
              <th className="table-th">ID</th><th className="table-th">Application</th><th className="table-th">Prompt</th>
              <th className="table-th">Primary Issue</th><th className="table-th">Risk</th>
              <th className="table-th">Decision</th><th className="table-th">Age</th><th className="table-th"></th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-50">
            {items.map((i) => (
              <tr key={i.interaction_id} className="hover:bg-slate-50">
                <td className="table-td font-mono text-xs">
                  <Link href={`/interactions/${i.interaction_id}`} className="text-brand-600 hover:underline">{i.interaction_id}</Link>
                </td>
                <td className="table-td whitespace-nowrap text-xs">{appLabel(i.application)}</td>
                <td className="table-td max-w-xs truncate text-xs">{i.user_prompt}</td>
                <td className="table-td text-xs">{i.primary_risk ? RISK_TYPE_LABELS[i.primary_risk] : "—"}</td>
                <td className="table-td"><RiskScore score={i.overall_risk} /></td>
                <td className="table-td"><DecisionBadge decision={i.decision} /></td>
                <td className="table-td whitespace-nowrap text-xs text-slate-400">{fmtTime(i.timestamp)}</td>
                <td className="table-td">
                  {tab === "pending"
                    ? <button className="btn-primary !px-3 !py-1.5 text-xs" onClick={() => setActive(i)}>Review</button>
                    : <span className="text-xs font-medium text-slate-500">{i.human_decision}</span>}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {items.length === 0 && <div className="p-8 text-center text-sm text-slate-400">Queue is empty.</div>}
      </div>

      {active && <ReviewModal item={active} onClose={() => setActive(null)} onDone={() => { setActive(null); load(); }} />}
    </div>
  );
}

function ReviewModal({ item, onClose, onDone }: { item: ReviewItem; onClose: () => void; onDone: () => void }) {
  const [label, setLabel] = useState<"TRUE_POSITIVE" | "FALSE_POSITIVE">("TRUE_POSITIVE");
  const [comment, setComment] = useState("");
  const [edited, setEdited] = useState(item.ai_response);
  const [editing, setEditing] = useState(false);
  const [busy, setBusy] = useState(false);

  async function submit(decision: "APPROVE" | "EDIT" | "REJECT") {
    setBusy(true);
    try {
      await post(`/api/reviews/${item.interaction_id}`, {
        reviewer: "Demo Reviewer", decision, label, comment: comment || undefined,
        edited_response: decision === "EDIT" ? edited : undefined,
      });
      onDone();
    } catch (e) { alert(String(e)); } finally { setBusy(false); }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 p-6" onClick={onClose}>
      <div className="max-h-[85vh] w-full max-w-2xl overflow-y-auto rounded-xl bg-white p-5 shadow-xl" onClick={(e) => e.stopPropagation()}>
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-lg font-bold text-slate-900">Review {item.interaction_id}</h2>
          <DecisionBadge decision={item.decision} />
        </div>

        <div className="space-y-3 text-sm">
          <div><div className="label">Application / Policy</div>{appLabel(item.application)} · {item.policy_name}</div>
          <div><div className="label">User Prompt</div><div className="rounded-lg bg-slate-50 p-3">{item.user_prompt}</div></div>
          <div><div className="label">AI Response (held)</div><div className="rounded-lg bg-slate-50 p-3">{item.ai_response}</div></div>
          <div>
            <div className="label">Why it was flagged</div>
            <ul className="list-inside list-disc space-y-1 text-xs text-slate-600">
              {item.reasons.map((r, i) => <li key={i}>{r}</li>)}
            </ul>
          </div>
          <div>
            <div className="label">Detection quality label</div>
            <div className="flex gap-2">
              <button onClick={() => setLabel("TRUE_POSITIVE")}
                className={label === "TRUE_POSITIVE" ? "btn-primary !py-1.5 text-xs" : "btn-secondary !py-1.5 text-xs"}>
                True positive (risk confirmed)
              </button>
              <button onClick={() => setLabel("FALSE_POSITIVE")}
                className={label === "FALSE_POSITIVE" ? "btn-primary !py-1.5 text-xs" : "btn-secondary !py-1.5 text-xs"}>
                False positive (detection wrong)
              </button>
            </div>
          </div>
          <div>
            <div className="label">Reviewer comment</div>
            <textarea className="input h-16 resize-none" value={comment} onChange={(e) => setComment(e.target.value)}
              placeholder="Optional justification (stored in the audit trail)…" />
          </div>
          {editing && (
            <div>
              <div className="label">Edited response to release</div>
              <textarea className="input h-24 resize-none" value={edited} onChange={(e) => setEdited(e.target.value)} />
            </div>
          )}
        </div>

        <div className="mt-4 flex justify-end gap-2">
          <button className="btn-secondary" disabled={busy} onClick={() => submit("REJECT")}>
            <X className="h-4 w-4 text-red-500" /> Reject
          </button>
          {!editing ? (
            <button className="btn-secondary" onClick={() => setEditing(true)}><Pencil className="h-4 w-4 text-amber-500" /> Edit</button>
          ) : (
            <button className="btn-secondary" disabled={busy} onClick={() => submit("EDIT")}>
              <Pencil className="h-4 w-4 text-amber-500" /> Release edited
            </button>
          )}
          <button className="btn-primary" disabled={busy} onClick={() => submit("APPROVE")}>
            <Check className="h-4 w-4" /> Approve original
          </button>
        </div>
      </div>
    </div>
  );
}
