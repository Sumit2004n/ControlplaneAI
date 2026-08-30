"use client";
import { Bot, Eraser, Loader2, Send, Sparkles, User } from "lucide-react";
import clsx from "clsx";
import { useState } from "react";

import { DecisionBadge } from "@/components/Badges";
import RiskPanel from "@/components/RiskPanel";
import ScenarioPicker from "@/components/ScenarioPicker";
import { post } from "@/lib/api";
import { useApp } from "@/lib/context";
import { appLabel } from "@/lib/format";
import type { Analysis, Scenario } from "@/lib/types";

interface Turn { prompt: string; analysis: Analysis }

export default function AnalyzerPage() {
  const { application, setApplication, region } = useApp();
  const [turns, setTurns] = useState<Turn[]>([]);
  const [selected, setSelected] = useState<number>(-1);
  const [prompt, setPrompt] = useState("");
  const [mode, setMode] = useState<"generate" | "provide">("generate");
  const [providedResponse, setProvidedResponse] = useState("");
  const [busy, setBusy] = useState(false);
  const [pickerOpen, setPickerOpen] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const historyFrom = (list: Turn[]) =>
    list.flatMap((t) => [
      { role: "user", content: t.prompt },
      { role: "assistant", content: t.analysis.ai_response },
    ]);

  async function runTurn(opts: {
    prompt: string; response?: string; scenarioId?: string;
    app?: string; baseTurns?: Turn[];
  }): Promise<Turn[]> {
    const base = opts.baseTurns ?? turns;
    const body = {
      application: opts.app ?? application,
      prompt: opts.prompt,
      conversation_history: historyFrom(base),
      region,
      scenario_id: opts.scenarioId,
      ...(opts.response !== undefined ? { response: opts.response } : {}),
    };
    const endpoint = opts.response !== undefined
      ? "/api/interactions/analyze"
      : "/api/interactions/generate-and-analyze";
    const analysis = await post<Analysis>(endpoint, body);
    const next = [...base, { prompt: opts.prompt, analysis }];
    setTurns(next);
    setSelected(next.length - 1);
    return next;
  }

  async function handleSend() {
    if (!prompt.trim() || busy) return;
    setBusy(true); setError(null);
    try {
      await runTurn({
        prompt: prompt.trim(),
        response: mode === "provide" ? providedResponse.trim() : undefined,
      });
      setPrompt(""); setProvidedResponse("");
    } catch (e) { setError(String(e)); } finally { setBusy(false); }
  }

  async function handleScenario(s: Scenario) {
    setBusy(true); setError(null);
    setApplication(s.application);
    setTurns([]); setSelected(-1);
    try {
      if (s.conversation) {
        let acc: Turn[] = [];
        for (const turn of s.conversation) {
          acc = await runTurn({
            prompt: turn.prompt, response: turn.response,
            scenarioId: s.id, app: s.application, baseTurns: acc,
          });
        }
      } else {
        await runTurn({ prompt: s.prompt, response: s.response, scenarioId: s.id, app: s.application, baseTurns: [] });
      }
    } catch (e) { setError(String(e)); } finally { setBusy(false); }
  }

  const current = selected >= 0 ? turns[selected]?.analysis : null;

  return (
    <div className="mx-auto max-w-[1400px]">
      <div className="mb-4 flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-slate-900">Live Interaction Analyzer</h1>
          <p className="text-sm text-slate-500">
            Application: <span className="font-medium text-slate-700">{appLabel(application)}</span> ·
            Region: <span className="font-medium text-slate-700"> {region}</span> —
            every response passes through the ControlPlane pipeline before reaching the user.
          </p>
        </div>
        <div className="flex gap-2">
          <button className="btn-secondary" onClick={() => { setTurns([]); setSelected(-1); }}>
            <Eraser className="h-4 w-4" /> Clear
          </button>
          <button className="btn-primary" onClick={() => setPickerOpen(true)}>
            <Sparkles className="h-4 w-4" /> Demo Mode
          </button>
        </div>
      </div>

      {error && <div className="mb-3 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</div>}

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-5">
        {/* Conversation column */}
        <div className="xl:col-span-3">
          <div className="card flex min-h-[480px] flex-col">
            <div className="flex-1 space-y-4 overflow-y-auto p-4">
              {turns.length === 0 && (
                <div className="flex h-full min-h-[360px] flex-col items-center justify-center text-center text-slate-400">
                  <Bot className="mb-2 h-10 w-10" />
                  <p className="text-sm font-medium">Ask a question or pick a demo scenario.</p>
                  <p className="mt-1 max-w-sm text-xs">
                    The AI response is intercepted, checked by four detectors in parallel,
                    scored against the active policy, and only then released, edited, flagged or blocked.
                  </p>
                </div>
              )}
              {turns.map((t, i) => (
                <div key={i} className="space-y-2">
                  <div className="flex justify-end">
                    <div className="max-w-[80%] rounded-2xl rounded-tr-sm bg-brand-600 px-4 py-2.5 text-sm text-white">
                      <div className="mb-0.5 flex items-center gap-1 text-[10px] font-semibold uppercase tracking-wide text-brand-100">
                        <User className="h-3 w-3" /> User
                      </div>
                      {t.prompt}
                    </div>
                  </div>
                  <div className="flex justify-start">
                    <button onClick={() => setSelected(i)}
                      className={clsx(
                        "max-w-[85%] rounded-2xl rounded-tl-sm border px-4 py-2.5 text-left text-sm transition",
                        selected === i ? "border-brand-400 bg-brand-50/60 ring-1 ring-brand-300" : "border-slate-200 bg-white hover:border-slate-300",
                      )}>
                      <div className="mb-1 flex items-center justify-between gap-3">
                        <span className="flex items-center gap-1 text-[10px] font-semibold uppercase tracking-wide text-slate-400">
                          <Bot className="h-3 w-3" /> AI via ControlPlane · risk {Math.round(t.analysis.overall_risk)}
                        </span>
                        <DecisionBadge decision={t.analysis.decision} />
                      </div>
                      <div className="text-slate-700">{t.analysis.final_response}</div>
                      {t.analysis.decision !== "ALLOW" && t.analysis.ai_response && t.analysis.ai_response !== t.analysis.final_response && (
                        <div className="mt-2 rounded-lg border border-dashed border-red-200 bg-red-50/60 p-2 text-xs text-red-700">
                          <span className="font-semibold">Original model output (admin view): </span>
                          {t.analysis.ai_response}
                        </div>
                      )}
                    </button>
                  </div>
                </div>
              ))}
              {busy && <div className="flex items-center gap-2 text-sm text-slate-400"><Loader2 className="h-4 w-4 animate-spin" /> Running ControlPlane checks…</div>}
            </div>

            {/* Composer */}
            <div className="border-t border-slate-200 p-3">
              <div className="mb-2 flex gap-2 text-xs">
                <button onClick={() => setMode("generate")}
                  className={clsx("rounded-full px-3 py-1 font-medium", mode === "generate" ? "bg-brand-600 text-white" : "bg-slate-100 text-slate-600")}>
                  Generate AI response
                </button>
                <button onClick={() => setMode("provide")}
                  className={clsx("rounded-full px-3 py-1 font-medium", mode === "provide" ? "bg-brand-600 text-white" : "bg-slate-100 text-slate-600")}>
                  Provide AI response to check
                </button>
              </div>
              {mode === "provide" && (
                <textarea className="input mb-2 h-20 resize-none" placeholder="Paste the AI response to be analyzed…"
                  value={providedResponse} onChange={(e) => setProvidedResponse(e.target.value)} />
              )}
              <div className="flex gap-2">
                <input className="input" placeholder="User prompt…" value={prompt}
                  onChange={(e) => setPrompt(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && handleSend()} />
                <button className="btn-primary shrink-0" disabled={busy || !prompt.trim() || (mode === "provide" && !providedResponse.trim())}
                  onClick={handleSend}>
                  {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />} Analyze
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* Risk analysis column */}
        <div className="xl:col-span-2">
          {current ? (
            <RiskPanel data={{ ...current, policy: current.policy }} />
          ) : (
            <div className="card flex h-full min-h-[480px] items-center justify-center p-6 text-center text-sm text-slate-400">
              Risk analysis appears here after an interaction is analyzed.<br />
              Click any AI message to inspect its verdict.
            </div>
          )}
        </div>
      </div>

      <ScenarioPicker open={pickerOpen} onClose={() => setPickerOpen(false)} onSelect={handleScenario} />
    </div>
  );
}
