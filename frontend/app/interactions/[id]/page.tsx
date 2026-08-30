"use client";
import { ArrowLeft } from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

import { DecisionBadge } from "@/components/Badges";
import RiskPanel from "@/components/RiskPanel";
import { api } from "@/lib/api";
import { appLabel, fmtTime, severityFor } from "@/lib/format";
import type { InteractionDetail } from "@/lib/types";

export default function InteractionDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [data, setData] = useState<InteractionDetail | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api<InteractionDetail>(`/api/interactions/${id}`).then(setData).catch((e) => setError(String(e)));
  }, [id]);

  if (error) return <div className="p-8 text-sm text-red-600">{error}</div>;
  if (!data) return <div className="p-8 text-sm text-slate-400">Loading interaction…</div>;

  return (
    <div className="mx-auto max-w-[1300px] space-y-4">
      <div className="flex items-center gap-3">
        <Link href="/interactions" className="btn-secondary !px-2.5 !py-1.5"><ArrowLeft className="h-4 w-4" /></Link>
        <div>
          <h1 className="flex items-center gap-3 text-xl font-bold text-slate-900">
            {data.interaction_id} <DecisionBadge decision={data.decision} />
          </h1>
          <p className="text-sm text-slate-500">
            {appLabel(data.application)} · {data.region} · Policy: {data.policy_name} · {fmtTime(data.timestamp)}
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-5">
        <div className="space-y-4 xl:col-span-3">
          <div className="card p-4">
            <div className="label">User Prompt</div>
            <p className="mt-1 text-sm text-slate-800">{data.user_prompt}</p>
          </div>
          <div className="card p-4">
            <div className="label">Original AI Response (admin view)</div>
            <p className="mt-1 text-sm text-slate-800">{data.ai_response || <span className="text-slate-400">Blocked before generation (pre-gate)</span>}</p>
          </div>
          <div className="card p-4">
            <div className="label">Final Output Delivered to User</div>
            <p className="mt-1 text-sm text-slate-800">{data.final_response}</p>
          </div>

          {data.reviews.length > 0 && (
            <div className="card p-4">
              <div className="label">Human Review</div>
              {data.reviews.map((rv) => (
                <div key={rv.id} className="mt-2 rounded-lg border border-violet-100 bg-violet-50/50 p-3 text-sm">
                  <div className="flex items-center justify-between">
                    <span className="font-semibold text-violet-800">{rv.decision}</span>
                    <span className="text-xs text-slate-500">{rv.reviewer} · {fmtTime(rv.timestamp)}</span>
                  </div>
                  {rv.label && <div className="mt-1 text-xs font-medium text-slate-600">Label: {rv.label.replace("_", " ")}</div>}
                  {rv.comment && <div className="mt-1 text-xs text-slate-600">&ldquo;{rv.comment}&rdquo;</div>}
                  {rv.edited_response && <div className="mt-1 text-xs text-slate-600">Edited to: &ldquo;{rv.edited_response}&rdquo;</div>}
                </div>
              ))}
            </div>
          )}

          <div className="card p-4">
            <div className="label">Audit Trail</div>
            <div className="mt-2 space-y-0">
              {data.audit_trail.map((a, i) => (
                <div key={i} className="flex gap-3 border-l-2 border-slate-200 pb-3 pl-4 last:pb-0">
                  <div className="min-w-0">
                    <div className="text-sm font-semibold text-slate-800">{a.event.replace(/_/g, " ")}</div>
                    <div className="text-xs text-slate-500">{a.actor} · {fmtTime(a.timestamp)}</div>
                    <pre className="mt-1 max-w-full overflow-x-auto rounded bg-slate-50 p-2 text-[10px] text-slate-500">
                      {JSON.stringify(a.meta, null, 1)}
                    </pre>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        <div className="xl:col-span-2">
          <RiskPanel data={{
            overall_risk: data.overall_risk,
            overall_confidence: data.overall_confidence,
            severity: severityFor(data.overall_risk),
            decision: data.decision,
            reasons: data.reasons,
            risks: data.risks,
            latency_breakdown: data.latency_breakdown,
          }} />
        </div>
      </div>
    </div>
  );
}
