"use client";
import { PlayCircle, X } from "lucide-react";
import { useEffect, useState } from "react";

import { api } from "@/lib/api";
import type { Scenario } from "@/lib/types";

import { DecisionBadge } from "./Badges";

const CATEGORY_LABELS: Record<string, string> = {
  safe: "Safe", hallucination: "Hallucination", privacy: "Privacy", bias: "Bias",
  combined: "Combined risks", multi_turn: "Multi-turn", low_confidence: "Low confidence",
  policy_specific: "Policy-specific",
};

export default function ScenarioPicker({ open, onClose, onSelect }: {
  open: boolean;
  onClose: () => void;
  onSelect: (s: Scenario) => void;
}) {
  const [scenarios, setScenarios] = useState<Scenario[]>([]);
  const [showAll, setShowAll] = useState(false);

  useEffect(() => {
    if (open) api<{ items: Scenario[] }>("/api/scenarios").then((r) => setScenarios(r.items)).catch(() => {});
  }, [open]);

  if (!open) return null;
  const featured = scenarios.filter((s) => s.featured);
  const list = showAll ? scenarios : featured;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 p-6" onClick={onClose}>
      <div className="max-h-[80vh] w-full max-w-2xl overflow-y-auto rounded-xl bg-white p-5 shadow-xl"
        onClick={(e) => e.stopPropagation()}>
        <div className="mb-4 flex items-center justify-between">
          <div>
            <h2 className="text-lg font-bold text-slate-900">Demo Mode — Select a Scenario</h2>
            <p className="text-xs text-slate-500">
              Pre-built interactions from the scenario library. Every result below is computed live by the pipeline.
            </p>
          </div>
          <button onClick={onClose} className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-100"><X className="h-5 w-5" /></button>
        </div>
        <div className="mb-3 flex gap-2">
          <button onClick={() => setShowAll(false)}
            className={!showAll ? "btn-primary !py-1.5" : "btn-secondary !py-1.5"}>Featured ({featured.length})</button>
          <button onClick={() => setShowAll(true)}
            className={showAll ? "btn-primary !py-1.5" : "btn-secondary !py-1.5"}>Full library ({scenarios.length})</button>
        </div>
        <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
          {list.map((s) => (
            <button key={s.id} onClick={() => { onSelect(s); onClose(); }}
              className="group flex flex-col gap-1.5 rounded-lg border border-slate-200 p-3 text-left transition hover:border-brand-400 hover:bg-brand-50/40">
              <div className="flex items-center justify-between gap-2">
                <span className="text-xs font-semibold uppercase tracking-wide text-slate-400">
                  {CATEGORY_LABELS[s.category] ?? s.category}
                </span>
                <DecisionBadge decision={s.expected_decision} />
              </div>
              <div className="flex items-center gap-1.5 text-sm font-semibold text-slate-800">
                <PlayCircle className="h-4 w-4 shrink-0 text-brand-500" />
                {s.featured_label ?? s.title}
              </div>
              <div className="line-clamp-2 text-xs text-slate-500">&ldquo;{s.prompt}&rdquo;</div>
              {s.conversation && <div className="text-[11px] font-medium text-violet-600">{s.conversation.length}-turn conversation</div>}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
