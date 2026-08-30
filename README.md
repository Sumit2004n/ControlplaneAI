# ControlPlane.ai — Enterprise AI Governance & Runtime Risk Control Plane

**Accenture Innovation Challenge 2026 · Round 2 Prototype · Track 1**

**PDF / submission copy:** [docs/SUBMISSION_README.md](docs/SUBMISSION_README.md) — 

**Business proposal PDF:** [docs/BUSINESS_PROPOSAL.md](docs/BUSINESS_PROPOSAL.md) / [docs/ControlPlane_AI_Business_Proposal.pdf](docs/ControlPlane_AI_Business_Proposal.pdf)

**Business proposal PPT:** [docs/ControlPlane_AI_Business_Proposal.pptx](docs/ControlPlane_AI_Business_Proposal.pptx)

ControlPlane.ai is a policy-aware control layer that sits between enterprise AI applications and their
users. Every AI interaction is intercepted, analyzed by four parallel risk detectors, scored against a
configurable per-application policy, and only then **allowed, edited, flagged for human review, or
blocked** — with full explainability, evidence, audit trails and a human feedback loop.

> Don't ask "Is this AI response safe?" Ask: **"Safe for whom, in which application, under which policy,
> with what evidence, at what confidence — and what should the enterprise do about it?"**

---

## 1. Product Overview

Enterprises run many AI systems at once — customer chatbots, employee copilots, decision-support tools —
and each has a different risk tolerance, latency budget and regulatory context. A one-size-fits-all
safety checker over-flags some flows (alert fatigue) and under-protects others (liability).

ControlPlane.ai demonstrates:

| Capability | Where to see it |
|---|---|
| Runtime interception (pre-gate + post-generation checks) | Analyzer |
| PII / privacy detection (regex + entity spans + LLM secondary check) | Analyzer → PII Leak scenario |
| Hallucination / grounding via retrieval verification (claim → evidence → SUPPORTED / CONTRADICTED / UNSUPPORTED / UNVERIFIABLE) | Analyzer → Hallucination scenario |
| Bias detection (protected-attribute heuristics + AI-as-judge), always routed to humans | Analyzer → Bias scenario |
| Policy-violation rules (data protection, decision oversight, overclaiming) | Analyzer → any privacy scenario |
| Weighted risk aggregation with critical overrides + confidence | Risk panel on every analysis |
| Tiered decisions: ALLOW / EDIT (auto-redaction) / FLAG / HUMAN REVIEW / BLOCK | Everywhere |
| Abstention when evidence is unavailable (no fake certainty) | Low Confidence scenario |
| Multi-turn conversational risk escalation | Multi-turn Escalation scenario |
| Configurable policies per application, region, industry, risk appetite | Policies page |
| What-if Policy Simulator — same output, different policy, different decision | Policy Simulator page |
| Human review queue with approve / edit / reject + TP/FP labels | Review Queue |
| Feedback loop metrics (false-positive rate, override rate) | Analytics |
| Immutable audit trail for every decision, review and policy change | Audit Logs |
| Latency + cost telemetry, parallel detector execution | Analytics, risk panel |
| Guaranteed-working **demo mode** (no API key, no network) | Default configuration |

## 2. Architecture

```
USER → AI APPLICATION → PRE-GATE (input check, injection, sensitive requests)
     → LLM (real or deterministic mock)
     → CONTROLPLANE: [ PII | HALLUCINATION/RAG | BIAS | POLICY ]  ← run in parallel
     → RISK AGGREGATOR (policy weights + max-risk override + confidence)
     → POLICY ENGINE (thresholds per application/region → ALLOW/EDIT/FLAG/HUMAN_REVIEW/BLOCK)
     → FINAL OUTPUT to user  +  AUDIT LOG  →  REVIEW QUEUE → FEEDBACK → ANALYTICS
```

- **Backend:** Python + FastAPI + SQLAlchemy (SQLite by default; point `DATABASE_URL` at PostgreSQL to switch).
- **Grounding:** markdown knowledge base chunked by section, TF-IDF retrieval in-process (OpenAI embeddings in live mode), deterministic numeric-contradiction and lexical-support rules, LLM judge refinement in live mode.
- **LLM abstraction:** `LLM_PROVIDER` / `LLM_MODEL` / `LLM_BASE_URL` — any OpenAI-compatible API, or the built-in deterministic mock.
- **Frontend:** Next.js + TypeScript + Tailwind + Recharts.
- **Deterministic first:** regex, thresholds, policy rules, risk aggregation and decision logic are deterministic; LLMs are used only where semantic reasoning adds value (generation, claim extraction, secondary judging, never as the sole source of quantitative truth).

See [docs/architecture.md](docs/architecture.md) for the full component walkthrough.

## 3. Quick Start (demo mode — no API key needed)

Prerequisites: Python 3.11+, Node 18+.

**Backend** (terminal 1):

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn app.main:app --port 8000
```

**Frontend** (terminal 2):

```powershell
cd frontend
npm install
npm run dev
```

Open **http://localhost:3000**. On first start the backend seeds 3 policies, 6 knowledge-base
documents and a fully-computed interaction history (the dashboard is never empty). Interactive API
docs: http://localhost:8000/docs

### Running with a real LLM

1. Copy `.env.example` to `backend/.env`
2. Set `DEMO_MODE=false`, `LLM_API_KEY=sk-…` (and optionally `LLM_MODEL`, `LLM_BASE_URL`)
3. Restart the backend. Generation, claim extraction and AI-as-judge layers switch to the real model;
   all deterministic layers stay active. Keys live only on the server.

## 4. The 5–7 Minute Demo Flow

1. **Analyzer → Demo Mode → Safe Customer Query** — risk ~1, ALLOW.
2. **Hallucination** — "45 annual leaves" is CONTRADICTED by HR Policy (20 days) with the evidence excerpt shown → BLOCK.
3. **PII Leak** — phone number detected → risk 95+ → BLOCK; original output visible only in admin view.
4. **Auto-Edit (Redaction)** — email in a customer-support answer → EDIT: delivered with `[REDACTED-EMAIL]`.
5. **Bias** — gender-based hiring reasoning → HUMAN REVIEW (never auto-blocked: bias needs human judgment).
6. **Low Confidence / Abstain** — no evidence for carbon emissions → ControlPlane abstains instead of guessing.
7. **Multi-turn Escalation** — watch risk climb 1 → 1 → 86 → 95 as an innocent chat drifts into PII harvesting.
8. **Policy Simulator** — the same response: FLAG under Customer Support, HUMAN REVIEW under Decision Support. *Same model output, different policy, different decision.*
9. **Review Queue** — approve a flagged case as a false positive → audit trail and Analytics FP-rate update.
10. **Dashboard / Audit Logs** — every decision above is logged and visible.

## 5. Tests

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest            # 21 unit/API tests
.\.venv\Scripts\python.exe check_scenarios.py    # all 21 scenarios vs expected decisions
```

Covers: PII detection, grounding (supported / contradicted / no-evidence), policy decisions,
EDIT redaction, abstention, detector fail-safe, review workflow, feedback and the policy simulator.

## 6. API Summary

| Endpoint | Purpose |
|---|---|
| `POST /api/interactions/analyze` | Analyze a provided AI response |
| `POST /api/interactions/generate-and-analyze` | Generate a response, then analyze it |
| `GET /api/interactions` / `GET /api/interactions/{id}` | History and full decision detail |
| `GET /api/reviews` / `POST /api/reviews/{id}` | Review queue and reviewer verdicts |
| `GET/POST/PUT /api/policies`, `POST /api/policies/simulate` | Policy CRUD + what-if simulator |
| `GET /api/analytics` | KPIs, FP rate, latency and cost telemetry |
| `GET /api/audit-logs`, `POST /api/feedback` | Audit trail and feedback capture |
| `GET /api/documents`, `GET /api/scenarios`, `GET /api/health` | Knowledge base, scenario library, status |

## 7. Stated Assumptions

- Three simulated applications (customer support / employee copilot / decision support) stand in for an enterprise AI portfolio; threshold values in the seeded policies are prototype assumptions and fully configurable.
- The knowledge base is a simulated set of six enterprise documents; all employee/customer data is fictional.
- The foundation model is consumed via API only — ControlPlane inspects inputs/outputs, not model internals.

## 8. Limitations (stated deliberately)

1. Simulated enterprise data; risk scores are prototype estimates evaluated on the seeded scenario library, not benchmarked real-world accuracy.
2. Bias detection flags *potential* bias; it cannot prove real-world discrimination — hence mandatory human routing.
3. Hallucination verification depends on evidence existing in the knowledge base; when it doesn't, the system abstains rather than pretending to know.
4. Regional profiles (India / EU / US) demonstrate configurable governance, not legal compliance engines.
5. Production deployment would additionally require SSO, RBAC, encryption at rest, rate limiting and hardened infrastructure.
6. Human oversight remains necessary for high-impact decisions.

## 9. Roadmap

- **Phase 1 (this prototype):** four detectors, policy engine, human review, audit, analytics, demo mode.
- **Phase 2 (enterprise pilot):** real knowledge connectors, SSO/RBAC, threshold auto-tuning from feedback labels, model evaluation harness.
- **Phase 3 (scale):** multi-model routing, AI-agent action governance (tool-call interception), streaming-time checks, regulatory policy packs, cross-enterprise risk intelligence.
