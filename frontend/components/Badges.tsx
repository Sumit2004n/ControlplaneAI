import clsx from "clsx";

import { DECISION_STYLES, SEVERITY_STYLES, decisionLabel, riskBarColor, riskTextColor } from "@/lib/format";
import type { Decision } from "@/lib/types";

export function DecisionBadge({ decision, className }: { decision: string; className?: string }) {
  return (
    <span className={clsx(
      "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold",
      DECISION_STYLES[decision as Decision] ?? "bg-slate-100 text-slate-700 border-slate-200",
      className,
    )}>
      {decisionLabel(decision)}
    </span>
  );
}

export function SeverityBadge({ severity }: { severity: string }) {
  return (
    <span className={clsx(
      "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold",
      SEVERITY_STYLES[severity] ?? "bg-slate-100 text-slate-700 border-slate-200",
    )}>
      {severity}
    </span>
  );
}

export function RiskScore({ score, size = "md" }: { score: number; size?: "md" | "lg" }) {
  return (
    <span className={clsx("font-bold tabular-nums", riskTextColor(score), size === "lg" ? "text-3xl" : "text-sm")}>
      {Math.round(score)}
    </span>
  );
}

export function ScoreBar({ score, threshold }: { score: number; threshold?: number }) {
  return (
    <div className="relative h-2 w-full overflow-hidden rounded-full bg-slate-100">
      <div className={clsx("h-full rounded-full transition-all", riskBarColor(score))}
        style={{ width: `${Math.max(2, Math.min(100, score))}%` }} />
      {threshold !== undefined && (
        <div className="absolute top-0 h-full w-0.5 bg-slate-500" style={{ left: `${threshold}%` }}
          title={`Policy threshold: ${threshold}`} />
      )}
    </div>
  );
}

export function StatusDot({ ok, label }: { ok: boolean; label: string }) {
  return (
    <span className="inline-flex items-center gap-1.5 text-xs font-medium text-slate-600">
      <span className={clsx("h-2 w-2 rounded-full", ok ? "bg-emerald-500" : "bg-red-500")} />
      {label}
    </span>
  );
}
