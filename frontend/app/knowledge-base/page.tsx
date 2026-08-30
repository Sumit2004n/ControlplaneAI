"use client";
import { BookOpen, FileText } from "lucide-react";
import { useEffect, useState } from "react";

import { api } from "@/lib/api";
import { fmtTime } from "@/lib/format";
import type { DocumentMeta } from "@/lib/types";

export default function KnowledgeBasePage() {
  const [docs, setDocs] = useState<DocumentMeta[]>([]);
  const [active, setActive] = useState<DocumentMeta | null>(null);

  useEffect(() => {
    api<{ items: DocumentMeta[] }>("/api/documents").then((r) => setDocs(r.items)).catch(() => {});
  }, []);

  async function open(id: string) {
    const d = await api<DocumentMeta>(`/api/documents/${id}`);
    setActive(d);
  }

  return (
    <div className="mx-auto max-w-[1200px] space-y-4">
      <div>
        <h1 className="text-xl font-bold text-slate-900">Knowledge Base</h1>
        <p className="text-sm text-slate-500">
          Approved enterprise documents used by the grounding engine for retrieval verification (RAG).
          Factual claims in AI responses are checked against these sources.
        </p>
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <div className="space-y-2">
          {docs.map((d) => (
            <button key={d.id} onClick={() => open(d.id)}
              className={`card flex w-full items-start gap-3 p-4 text-left transition ${active?.id === d.id ? "ring-2 ring-brand-500" : "hover:border-slate-300"}`}>
              <FileText className="mt-0.5 h-5 w-5 shrink-0 text-brand-500" />
              <div className="min-w-0">
                <div className="truncate text-sm font-semibold text-slate-900">{d.name}</div>
                <div className="text-xs text-slate-500">{d.category} · v{d.version}</div>
                <div className="mt-1 flex items-center gap-2 text-[11px] text-slate-400">
                  <span className="rounded-full bg-emerald-50 px-1.5 py-0.5 font-semibold text-emerald-600">{d.status}</span>
                  Updated {fmtTime(d.last_updated)}
                </div>
              </div>
            </button>
          ))}
        </div>
        <div className="lg:col-span-2">
          {active ? (
            <div className="card p-5">
              <div className="mb-3 border-b border-slate-100 pb-3">
                <h2 className="text-lg font-bold text-slate-900">{active.name}</h2>
                <p className="text-xs text-slate-500">{active.category} · version {active.version}</p>
              </div>
              <pre className="whitespace-pre-wrap font-sans text-sm leading-relaxed text-slate-700">{active.content}</pre>
            </div>
          ) : (
            <div className="card flex h-full min-h-[300px] flex-col items-center justify-center text-slate-400">
              <BookOpen className="mb-2 h-8 w-8" />
              <p className="text-sm">Select a document to view its contents.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
