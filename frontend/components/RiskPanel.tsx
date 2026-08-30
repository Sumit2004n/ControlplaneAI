"use client";
import { AlertTriangle, CheckCircle2, HelpCircle, ShieldAlert, Timer } from "lucide-react";
import clsx from "clsx";

import { RISK_TYPE_LABELS, fmtMs, riskTextColor } from "@/lib/format";
import type { EvidenceItem, RiskOut } from "@/lib/types";

import { DecisionBadge, ScoreBar, SeverityBadge } from "./Badges";

const EVIDENCE_STATUS_STYLE: Record<string, string> = {
  SUPPORTED: "border-emerald-200 bg-emerald-50 text-emerald-800",
  CONTRADICTED: "border-red-200 bg-red-50 text-red-800",
  UNSUPPORTED: "border-orange-200 bg-orange-50 text-orange-800",
  UNVERIFIABLE: "border-slate-200 bg-slate-50 text-slate-600",
  DETECTED: "border-red-200 bg-red-50 text-red-800",
  VIOLATION: "border-red-200 bg-red-50 text-red-800",
  REQUIRES_REVIEW: "border-violet-200 bg-violet-50 text-violet-800",
  GENERALIZATION: "border-orange-200 bg-orange-50 text-orange-800",
  CAUSAL_ATTRIBUTE: "border-orange-200 bg-orange-50 text-orange-800",
};

export interface RiskPanelData {
  overall_risk: number;
  overall_confidence: number;
  severity: string;
  decision: string;
  reasons: string[];
  risks: Record<string, RiskOut>;
  latency_breakdown: Record<string, number>;
  abstained?: boolean;
  policy?: { name: string; risk_profile: string };
  pre_gate?: { action: string; reasons: string[] };
  thresholds?: Record<string, number>;
}

export default function RiskPanel({ data }: { data: RiskPanelData }) {
  const risks = Object.values(data.risks ?? {});
  return (
    <div className="space-y-4">
      {/* Overall verdict */}
      <div className="card p-4">
        <div className="flex items-start justify-between">
          <div>
            <div className="label">Overall Contextual Risk</div>
            <div className="flex items-baseline gap-2">
              <span className={clsx("text-4xl font-bold tabular-nums", riskTextColor(data.overall_risk))}>
                {Math.round(data.overall_risk)}
              </span>
              <span className="text-sm text-slate-400">/ 100</span>
            </div>
            <div className="mt-1 text-xs text-slate-500">
              Confidence {Math.round(data.overall_confidence * 100)}%
              {data.policy && <> · Policy: <span className="font-medium">{data.policy.name}</span> ({data.policy.risk_profile})</>}
            </div>
          </div>
          <div className="flex flex-col items-end gap-1.5">
            <DecisionBadge decision={data.decision} className="!px-3 !py-1 !text-sm" />
            <SeverityBadge severity={data.severity} />
            {data.abstained && (
              <span className="inline-flex items-center gap-1 rounded-full border border-slate-300 bg-slate-100 px-2 py-0.5 text-[11px] font-semibold text-slate-600">
                <HelpCircle className="h-3 w-3" /> ABSTAINED
              </span>
            )}
          </div>
        </div>
        <div className="mt-3"><ScoreBar score={data.overall_risk} /></div>
      </div>

      {/* Per-risk scores */}
      <div className="card p-4">
        <div className="label">Risk Breakdown</div>
        <div className="mt-2 space-y-3">
          {risks.map((r) => (
            <div key={r.risk_type}>
              <div className="mb-1 flex items-center justify-between text-sm">
                <span className="font-medium text-slate-700">{RISK_TYPE_LABELS[r.risk_type] ?? r.risk_type}</span>
                <span className="flex items-center gap-2">
                  <span className="text-[11px] text-slate-400">conf {Math.round(r.confidence * 100)}%</span>
                  <span className={clsx("font-bold tabular-nums", riskTextColor(r.score))}>{Math.round(r.score)}</span>
                </span>
              </div>
              <ScoreBar score={r.score} threshold={data.thresholds?.[r.risk_type]} />
            </div>
          ))}
        </div>
      </div>

      {/* Why? — explainability (PRD sec 26-27) */}
      <div className="card p-4">
        <div className="label flex items-center gap-1.5">
          <ShieldAlert className="h-3.5 w-3.5" /> Why this decision?
        </div>
        <ul className="mt-2 space-y-1.5">
          {data.reasons.map((reason, i) => (
            <li key={i} className="flex gap-2 text-sm text-slate-700">
              <span className="mt-0.5 shrink-0">
                {data.decision === "ALLOW"
                  ? <CheckCircle2 className="h-4 w-4 text-emerald-500" />
                  : <AlertTriangle className="h-4 w-4 text-orange-500" />}
              </span>
              {reason}
            </li>
          ))}
        </ul>
      </div>

      {/* Evidence */}
      <EvidenceList risks={risks} />

      {/* Pipeline timeline + latency (PRD sec 31, 50) */}
      <div className="card p-4">
        <div className="label flex items-center gap-1.5"><Timer className="h-3.5 w-3.5" /> Pipeline & Latency</div>
        <div className="mt-2 space-y-1">
          {[
            ["Pre-gate (input check)", data.latency_breakdown?.pre_gate_ms],
            ["AI generation", data.latency_breakdown?.generation_ms],
            ["Detectors (parallel)", data.latency_breakdown?.detectors_ms],
            ["  Privacy / PII", data.latency_breakdown?.detector_privacy_ms],
            ["  Hallucination / grounding", data.latency_breakdown?.detector_hallucination_ms],
            ["  Bias", data.latency_breakdown?.detector_bias_ms],
            ["  Policy rules", data.latency_breakdown?.detector_policy_ms],
            ["Risk aggregation + decision", data.latency_breakdown?.decision_ms],
          ].map(([labelText, ms]) =>
            ms === undefined ? null : (
              <div key={labelText as string}
                className={clsx("flex items-center justify-between text-xs",
                  (labelText as string).startsWith("  ") ? "pl-4 text-slate-400" : "text-slate-600")}>
                <span>{(labelText as string).trim()}</span>
                <span className="font-mono">{fmtMs(ms as number)}</span>
              </div>
            ),
          )}
          <div className="mt-1 flex items-center justify-between border-t border-slate-100 pt-1.5 text-xs font-semibold text-slate-800">
            <span>Total</span>
            <span className="font-mono">{fmtMs(data.latency_breakdown?.total_ms ?? 0)}</span>
          </div>
        </div>
      </div>
    </div>
  );
}

export function EvidenceList({ risks }: { risks: RiskOut[] }) {
  const items: (EvidenceItem & { risk_type: string })[] = risks.flatMap((r) =>
    (r.evidence ?? []).map((ev) => ({ ...ev, risk_type: r.risk_type })),
  );
  if (items.length === 0) return null;
  return (
    <div className="card p-4">
      <div className="label">Evidence</div>
      <div className="mt-2 space-y-2">
        {items.map((ev, i) => (
          <div key={i} className={clsx("rounded-lg border p-2.5 text-xs",
            EVIDENCE_STATUS_STYLE[ev.status ?? ""] ?? "border-slate-200 bg-slate-50 text-slate-700")}>
            <div className="mb-1 flex items-center justify-between gap-2">
              <span className="font-semibold">{ev.status ?? "EVIDENCE"}</span>
              <span className="truncate text-[11px] opacity-70">
                {ev.source}{ev.section && ev.section !== "—" ? ` · ${ev.section}` : ""}
              </span>
            </div>
            {ev.claim && <div className="italic">&ldquo;{ev.claim}&rdquo;</div>}
            {ev.match && ev.match !== ev.claim && (
              <div className="mt-1 border-t border-current/10 pt-1 opacity-80">{ev.match}</div>
            )}
            {ev.detail && <div className="mt-1 font-medium">{ev.detail}</div>}
          </div>
        ))}
      </div>
    </div>
  );
}
