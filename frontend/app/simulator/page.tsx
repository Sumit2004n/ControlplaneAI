"use client";
import { FlaskConical, Loader2 } from "lucide-react";
import { useEffect, useState } from "react";

import { DecisionBadge, RiskScore } from "@/components/Badges";
import { api, post } from "@/lib/api";
import { RISK_TYPE_LABELS, appLabel } from "@/lib/format";
import type { Policy, Scenario } from "@/lib/types";

interface SimResult {
  policy: Policy;
  overall_risk: number;
  decision: string;
  reasons: string[];
  risks: Record<string, number>;
}

const DEFAULT_PROMPT = "Should we approve this customer's request?";
const DEFAULT_RESPONSE =
  "The customer request should probably be rejected, although the available records are incomplete and the repayment history could not be verified.";

export default function SimulatorPage() {
  const [prompt, setPrompt] = useState(DEFAULT_PROMPT);
  const [response, setResponse] = useState(DEFAULT_RESPONSE);
  const [results, setResults] = useState<SimResult[]>([]);
  const [scenarios, setScenarios] = useState<Scenario[]>([]);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api<{ items: Scenario[] }>("/api/scenarios").then((r) => setScenarios(r.items)).catch(() => {});
  }, []);

  async function run() {
    setBusy(true);
    try {
      const r = await post<{ results: SimResult[] }>("/api/policies/simulate", { prompt, response, policy_ids: [] });
      setResults(r.results);
    } catch (e) { alert(String(e)); } finally { setBusy(false); }
  }

  return (
    <div className="mx-auto max-w-[1200px] space-y-4">
      <div>
        <h1 className="text-xl font-bold text-slate-900">What-if Policy Simulator</h1>
        <p className="text-sm text-slate-500">
          The central ControlPlane demonstration: the <span className="font-semibold">same AI output</span> evaluated
          under every policy — same risks, different governance decision.
        </p>
      </div>

      <div className="card space-y-3 p-4">
        <div className="flex flex-wrap items-end gap-3">
          <div className="min-w-64 flex-1">
            <label className="label">Load from scenario library</label>
            <select className="input" defaultValue="" onChange={(e) => {
              const s = scenarios.find((x) => x.id === e.target.value);
              if (s) { setPrompt(s.prompt); setResponse(s.response); setResults([]); }
            }}>
              <option value="" disabled>Select a scenario…</option>
              {scenarios.filter((s) => !s.conversation).map((s) => <option key={s.id} value={s.id}>{s.title}</option>)}
            </select>
          </div>
          <button className="btn-primary" onClick={run} disabled={busy || !response.trim()}>
            {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <FlaskConical className="h-4 w-4" />}
            Run under all policies
          </button>
        </div>
        <div>
          <label className="label">User prompt</label>
          <input className="input" value={prompt} onChange={(e) => setPrompt(e.target.value)} />
        </div>
        <div>
          <label className="label">AI response to evaluate</label>
          <textarea className="input h-24 resize-none" value={response} onChange={(e) => setResponse(e.target.value)} />
        </div>
      </div>

      {results.length > 0 && (
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
          {results.map((r) => (
            <div key={r.policy.id} className="card p-4">
              <div className="mb-1 flex items-start justify-between gap-2">
                <div>
                  <div className="text-sm font-bold text-slate-900">{r.policy.name}</div>
                  <div className="text-xs text-slate-500">
                    {appLabel(r.policy.application_type)} · {r.policy.risk_profile.replace("_", " ")} · {r.policy.region}
                  </div>
                </div>
                <DecisionBadge decision={r.decision} />
              </div>
              <div className="my-3 flex items-baseline gap-2">
                <RiskScore score={r.overall_risk} size="lg" />
                <span className="text-xs text-slate-400">overall risk</span>
              </div>
              <div className="space-y-1 text-xs text-slate-600">
                {Object.entries(r.risks).map(([k, v]) => (
                  <div key={k} className="flex justify-between">
                    <span>{RISK_TYPE_LABELS[k] ?? k}</span>
                    <span className="font-semibold tabular-nums">{Math.round(v)}</span>
                  </div>
                ))}
              </div>
              <div className="mt-3 border-t border-slate-100 pt-2">
                <div className="label !mb-1">Why</div>
                <ul className="list-inside list-disc space-y-1 text-[11px] text-slate-500">
                  {r.reasons.slice(0, 4).map((reason, i) => <li key={i}>{reason}</li>)}
                </ul>
              </div>
            </div>
          ))}
        </div>
      )}

      {results.length > 0 && (
        <div className="rounded-lg border border-brand-200 bg-brand-50 p-4 text-sm text-brand-900">
          <span className="font-semibold">Same model output. Different policy. Different control decision.</span> Risk
          scores are identical across columns — only the governance configuration changes the outcome.
        </div>
      )}
    </div>
  );
}
