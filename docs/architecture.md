# ControlPlane.ai — Architecture

## Component Map

```
frontend/  (Next.js + TypeScript + Tailwind + Recharts)
  app/            dashboard, analyzer, live-monitor, interactions(+detail),
                  review-queue, policies, simulator, knowledge-base,
                  analytics, audit-logs, settings
  components/     RiskPanel (scores/why/evidence/latency), ScenarioPicker,
                  Badges, KpiCard, Sidebar, Header (app + region switchers)
  lib/            typed API client, app context, formatting

backend/   (FastAPI + SQLAlchemy)
  app/api/        interactions, reviews, policies (+simulate), analytics, misc
  app/services/   pipeline.py   ← orchestration: pre-gate → generate → parallel
                                  detectors → aggregate → decide → persist
                  llm.py        ← provider abstraction (openai-compatible / mock)
                  scenarios.py  ← demo scenario library loader
  app/detectors/  pii.py, hallucination.py, bias.py, policy_violation.py, pregate.py
  app/rag/        kb.py         ← section-chunked markdown KB + TF-IDF retrieval
  app/scoring/    aggregator.py ← weighted score + max-risk override + confidence
  app/policy/     engine.py     ← thresholds → ALLOW/EDIT/FLAG/HUMAN_REVIEW/BLOCK
  app/database/   models.py (7 tables), seed.py (policies, docs, history)
  tests/          pii, grounding, policy engine, review/API flows

data/
  knowledge_base/    6 enterprise markdown documents (grounding corpus)
  demo_scenarios/    21-scenario library (safe / hallucination / privacy / bias /
                     combined / multi-turn / low-confidence / policy-specific)
```

## Request Lifecycle

1. **Pre-gate** (`pregate.py`) — input-only checks before any model call: prompt-injection phrases
   block immediately (saving cost/latency); sensitive-data requests mark the context so output
   detectors weigh harder; prior sensitive turns in the conversation raise an escalation level.
2. **Generation** — `llm.generate()` calls the configured OpenAI-compatible model, or in demo mode a
   deterministic mock that answers from scripted scenarios / knowledge-base retrieval.
3. **Parallel detection** — `asyncio.gather` runs all four detectors concurrently with per-detector
   timeouts. A detector exception yields a `DETECTOR_ERROR` result; the policy's fail-safe action
   (FLAG / HUMAN_REVIEW) applies instead of silently allowing.
4. **Aggregation** (`aggregator.py`) — weighted sum using the policy's risk weights, plus a
   maximum-risk override so one severe risk is never hidden by a low average; confidence is a
   contribution-weighted blend of detector confidences.
5. **Decision** (`engine.py`) — ordered evaluation:
   - critical overrides (privacy ≥ 95 → BLOCK; bias ≥ 90 in very-strict workflows → HUMAN_REVIEW),
   - abstention (unverifiable material claims at < 25% confidence → FLAG/HUMAN_REVIEW),
   - fail-safe for errored detectors,
   - per-risk thresholds → high/critical actions (bias never auto-blocks alone),
   - overall severity bands,
   - EDIT downgrade: privacy-only breaches under 95 are auto-redacted when the policy allows.
6. **Final output** — ALLOW passes the response through; EDIT delivers the redacted text; FLAG /
   HUMAN_REVIEW deliver a hold message and enqueue for review; BLOCK delivers a policy message.
7. **Persistence** — interaction, per-detector risk results, and audit events are written; flagged
   items appear in the review queue.
8. **Feedback loop** — reviewer verdicts (approve/edit/reject + true/false-positive labels) update
   the interaction, create feedback records and audit events, and drive the analytics FP-rate and
   override-rate metrics.

## Grounding (Hallucination) Detail

```
response → claim extraction (factual sentences: numbers / policy terms)
         → TF-IDF retrieval over section chunks of the knowledge base
         → per-claim comparison:
              high lexical overlap + conflicting numbers   → CONTRADICTED (risk 93, conf 0.92)
              high overlap, numbers consistent             → SUPPORTED    (risk 4)
              partial overlap                              → UNSUPPORTED  (risk 62, conf 0.5)
              no relevant evidence                         → UNVERIFIABLE (risk 55, conf 0.2 → abstain)
         → in live-LLM mode an AI judge refines each claim verdict against the retrieved evidence
```

Evidence (source document, section, matched text, per-claim status) is returned with every analysis
and rendered in the UI, satisfying the "show why" requirement.

## Demo Mode Honesty

`DEMO_MODE=true` (default) swaps only the *LLM-dependent* layers for deterministic ones: scripted
generation and skipped judge calls. The regex PII engine, bias heuristics, TF-IDF grounding against
the real seeded knowledge base, policy rules, aggregation and the decision engine run identically in
both modes — demo results are genuinely computed, not canned.

## Security Notes (prototype level)

- API keys only in `backend/.env`, read server-side; never sent to the browser.
- Frontend calls the backend over CORS-restricted origins.
- Input validation via Pydantic schemas; audit logging is structured and append-only at the API level.
- Not claimed: production-grade authn/authz, encryption at rest, tenant isolation.
