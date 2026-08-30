"use client";
import { Save } from "lucide-react";
import { useEffect, useState } from "react";

import { api, put } from "@/lib/api";
import { RISK_TYPE_LABELS, appLabel } from "@/lib/format";
import type { Policy } from "@/lib/types";

const PROFILES = ["BALANCED", "STRICT", "VERY_STRICT"];
const ACTIONS = ["FLAG", "HUMAN_REVIEW", "BLOCK"];
const REGIONS = ["India", "EU", "US"];
const INDUSTRIES = ["Retail", "Technology", "Financial Services", "Healthcare", "General"];

export default function PoliciesPage() {
  const [policies, setPolicies] = useState<Policy[]>([]);
  const [selectedId, setSelectedId] = useState<string>("");
  const [draft, setDraft] = useState<Policy | null>(null);
  const [saved, setSaved] = useState(false);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api<{ items: Policy[] }>("/api/policies").then((r) => {
      setPolicies(r.items);
      if (r.items.length && !selectedId) { setSelectedId(r.items[0].id); setDraft(r.items[0]); }
    }).catch(() => {});
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function select(id: string) {
    setSelectedId(id);
    setDraft(policies.find((p) => p.id === id) ?? null);
    setSaved(false);
  }

  async function save() {
    if (!draft) return;
    setBusy(true);
    try {
      const { id, updated_at, ...body } = draft;
      const updated = await put<Policy>(`/api/policies/${id}`, body);
      setPolicies((ps) => ps.map((p) => (p.id === id ? updated : p)));
      setDraft(updated); setSaved(true);
      setTimeout(() => setSaved(false), 2500);
    } catch (e) { alert(String(e)); } finally { setBusy(false); }
  }

  const set = (patch: Partial<Policy>) => { setDraft((d) => (d ? { ...d, ...patch } : d)); setSaved(false); };

  return (
    <div className="mx-auto max-w-[1100px] space-y-4">
      <div>
        <h1 className="text-xl font-bold text-slate-900">Policy Management</h1>
        <p className="text-sm text-slate-500">
          Configurable governance layer: thresholds, weights and actions per application, region and risk appetite.
          Changes are versioned in the audit log. Threshold values are prototype assumptions.
        </p>
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <div className="space-y-2">
          {policies.map((p) => (
            <button key={p.id} onClick={() => select(p.id)}
              className={`card w-full p-4 text-left transition ${selectedId === p.id ? "ring-2 ring-brand-500" : "hover:border-slate-300"}`}>
              <div className="text-sm font-bold text-slate-900">{p.name}</div>
              <div className="text-xs text-slate-500">{appLabel(p.application_type)} · {p.region} · {p.industry}</div>
              <div className="mt-1.5 inline-block rounded-full bg-slate-100 px-2 py-0.5 text-[11px] font-semibold text-slate-600">
                {p.risk_profile.replace("_", " ")}
              </div>
            </button>
          ))}
        </div>

        {draft && (
          <div className="card space-y-5 p-5 lg:col-span-2">
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="label">Risk profile</label>
                <select className="input" value={draft.risk_profile} onChange={(e) => set({ risk_profile: e.target.value })}>
                  {PROFILES.map((p) => <option key={p}>{p}</option>)}
                </select>
              </div>
              <div>
                <label className="label">Region</label>
                <select className="input" value={draft.region} onChange={(e) => set({ region: e.target.value })}>
                  {REGIONS.map((r) => <option key={r}>{r}</option>)}
                </select>
              </div>
              <div>
                <label className="label">Industry</label>
                <select className="input" value={draft.industry} onChange={(e) => set({ industry: e.target.value })}>
                  {INDUSTRIES.map((i) => <option key={i}>{i}</option>)}
                </select>
              </div>
              <div>
                <label className="label">Fail-safe (detector failure)</label>
                <select className="input" value={draft.fail_safe} onChange={(e) => set({ fail_safe: e.target.value })}>
                  {ACTIONS.map((a) => <option key={a}>{a}</option>)}
                </select>
              </div>
            </div>

            <div>
              <div className="label">Risk thresholds (action triggers at or above)</div>
              <div className="space-y-4">
                {(["privacy", "hallucination", "bias", "policy"] as const).map((rt) => {
                  const key = `${rt}_threshold` as keyof Policy;
                  const value = draft[key] as number;
                  return (
                    <div key={rt}>
                      <div className="mb-1 flex justify-between text-sm">
                        <span className="font-medium text-slate-700">{RISK_TYPE_LABELS[rt]}</span>
                        <span className="font-bold tabular-nums text-slate-900">{value}</span>
                      </div>
                      <input type="range" min={10} max={100} value={value} className="w-full accent-brand-600"
                        onChange={(e) => set({ [key]: Number(e.target.value) } as Partial<Policy>)} />
                    </div>
                  );
                })}
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="label">High-risk action (50–74)</label>
                <select className="input" value={draft.high_risk_action} onChange={(e) => set({ high_risk_action: e.target.value })}>
                  {ACTIONS.map((a) => <option key={a}>{a}</option>)}
                </select>
              </div>
              <div>
                <label className="label">Critical-risk action (75+)</label>
                <select className="input" value={draft.critical_action} onChange={(e) => set({ critical_action: e.target.value })}>
                  {ACTIONS.map((a) => <option key={a}>{a}</option>)}
                </select>
              </div>
            </div>

            <label className="flex items-center gap-2 text-sm text-slate-700">
              <input type="checkbox" checked={draft.edit_enabled} onChange={(e) => set({ edit_enabled: e.target.checked })}
                className="h-4 w-4 accent-brand-600" />
              Allow automatic EDIT (redact personal data instead of blocking, when privacy is the only risk)
            </label>

            <div className="flex items-center justify-end gap-3 border-t border-slate-100 pt-4">
              {saved && <span className="text-sm font-medium text-emerald-600">Policy saved ✓</span>}
              <button className="btn-primary" onClick={save} disabled={busy}>
                <Save className="h-4 w-4" /> Save Policy
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
