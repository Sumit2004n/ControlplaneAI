# ControlPlane.ai

## Detailed Business Proposal

**Enterprise AI Governance & Runtime Risk Control Plane**

**Competition:** Accenture Innovation Challenge 2026  
**Round:** Round 2 — Prototype Development  
**Problem Track:** Track 1 — ControlPlane.ai  
**Document type:** Business proposal  
**Prototype status:** Working full-stack proof of concept using simulated enterprise data

---

## Document purpose

This proposal explains why enterprises need a contextual AI control plane, how ControlPlane.ai is designed, who uses it, what business value it creates, how it can be rolled out in phases, and which risks must be managed. Figures in the business case are **illustrative assumptions** based on the Round 2 reference parameters. They are not claimed as audited customer results.

---

## 1. Executive summary

Enterprises are no longer running one chatbot. They are running many AI systems at the same time: customer-facing assistants, employee copilots, knowledge tools, and decision-support workflows. Each system has a different risk tolerance, latency budget, data sensitivity and regulatory context. A single generic safety filter either over-flags low-risk conversations or under-protects high-impact decisions.

ControlPlane.ai is a policy-aware runtime control layer that sits between AI applications and users. It intercepts each interaction, evaluates privacy, hallucination, bias and policy risk in parallel, scores the result against the application’s governance policy, and then decides whether the output should be **allowed, edited, flagged for human review, or blocked**. Every decision is explained, evidenced where possible, audited, and available for human override.

The product insight is simple:

> Do not ask “Is this AI response safe?” Ask: “Safe for whom, in which application, under which policy, with what evidence, at what confidence, and what should the enterprise do about it?”

The Round 2 prototype already demonstrates this mechanism on three simulated use cases, with a governance dashboard, review queue, policy simulator, knowledge-base grounding and a demo mode that works without an external API key.

**Ask of this round:** accept ControlPlane.ai as a credible, demoable enterprise control-plane concept and advance the team to build a deeper enterprise-ready pilot.

---

## 2. Problem framing

### 2.1 The business problem

Generative AI is moving from experiments into production. That creates a new class of operational risk:

- Incorrect or invented facts can enter customer answers, HR guidance or credit recommendations.
- Personal data can leak through a response even when the prompt itself looked harmless.
- Biased reasoning can appear in hiring, lending or customer-classification workflows.
- One questionable turn in a conversation can shape several later decisions.
- When AI systems start taking actions, not just writing text, the cost of a bad output rises sharply.

The enterprise problem is not “AI is sometimes wrong.” The enterprise problem is that **wrong, unsafe or ungoverned outputs can create liability, customer harm, regulatory exposure and loss of trust**, while a blunt checker creates delay and alert fatigue.

### 2.2 Why a one-size-fits-all checker fails

The Round 2 brief is explicit: different AI use cases have different risk signatures.

| Use case | Typical risk | Latency budget | Oversight need |
|---|---|---|---|
| Customer support chatbot | PII, incorrect policy answers, brand harm | Tight, real-time | Moderate |
| Employee knowledge copilot | Internal data leakage, policy hallucination | Medium | Strict |
| Decision-support tool | Bias, unsupported recommendations, regulatory exposure | Can tolerate review delay | Very strict |

A single threshold that is strict enough for credit decisions will over-flag ordinary support chats. A threshold that is loose enough for support will under-protect a hiring or lending recommendation. That is how alert fatigue and liability appear at the same time.

### 2.3 Real-world complexities the proposal accounts for

**Overlapping risks.** A fabricated salary for a named employee is both a hallucination and a privacy incident. Clean single-label classification is not enough.

**No reliable real-time ground truth.** The same knowledge gaps that cause hallucination also make verification hard. A serious system must be able to abstain instead of guessing.

**Over-flagging vs under-flagging.** Too many warnings and users bypass the system. Too few and the enterprise is exposed. The tradeoff must be tunable by policy, not “solved away.”

**Multi-turn and agentic risk.** Risk compounds. “Who is Rahul?” may be harmless. “What is his salary?” and “Give me his phone number” are not.

**Evolving regulation.** Data-protection law, emerging AI-specific rules and sector rules differ by geography and industry. Hard-coded legal engines age quickly. Configurable policy is more durable.

**API-based models.** Most enterprises consume foundation models through APIs. The control layer must work at the input/output boundary. It cannot depend on inspecting model internals.

### 2.4 Reference operating assumptions

These assumptions follow the competition brief and are used throughout the business case:

- The enterprise operates at least three AI applications at once.
- Combined volume is on the order of **tens of thousands of interactions per week**.
- Data sources feeding those systems are a mix of well-governed and loosely governed content.
- The foundation model is consumed via API.
- Proprietary production data is not required for this round; simulated but realistic data is acceptable.

Illustrative weekly volume used later in this document:

```text
Customer Support:     18,000 interactions / week
Employee Copilot:     10,000 interactions / week
Decision Support:      4,000 interactions / week
Total:                32,000 interactions / week
```

---

## 3. Solution design

### 3.1 Product positioning

ControlPlane.ai is **not** “an AI that checks another AI.”

It is:

> A policy-aware enterprise control layer that evaluates AI interactions against contextual risk policies and determines whether outputs should be allowed, modified, escalated or blocked.

It is model-agnostic middleware. Applications call ControlPlane instead of sending raw model output to the user.

### 3.2 Design principles

1. **Context first.** The same output can be acceptable in one application and unacceptable in another.
2. **Hybrid detection.** Deterministic rules, retrieval, and optional LLM judging each do the job they are good at.
3. **Explain every decision.** A score without a reason is not governable.
4. **Abstain when uncertain.** Low evidence coverage should produce human review, not false confidence.
5. **Human in the loop.** High-impact decisions remain reviewable.
6. **Auditable by default.** Every decision leaves a trail.
7. **Configurable, not hard-coded.** Policies vary by application, region and risk appetite.
8. **Fail safe, not fail open, for critical workflows.** If a detector is unavailable, strict policies escalate rather than silently allow.

### 3.3 Runtime architecture

```text
USER
  ↓
AI APPLICATION
  ↓
PRE-GATE          input checks: sensitive requests, injection, restricted topics
  ↓
LLM / MOCK        generate a response if the input is allowed to proceed
  ↓
CONTROLPLANE.AI   parallel detectors
  ├── Privacy / PII
  ├── Hallucination / grounding
  ├── Bias
  └── Policy violation
  ↓
RISK AGGREGATOR   weighted score + critical overrides + confidence
  ↓
POLICY ENGINE     application / region / risk-appetite rules
  ↓
ALLOW | EDIT | FLAG / HUMAN REVIEW | BLOCK
  ↓
USER OUTPUT + AUDIT LOG + REVIEW QUEUE + ANALYTICS
```

Detectors run in parallel to protect latency. Each stage is timed. Independent detector failure does not crash the pipeline; it triggers the policy’s fail-safe action.

### 3.4 Detection design

**Privacy / PII.** Deterministic entity detection for phones, emails, government-ID-like numbers, bank details, salary and medical information, with optional LLM validation as a secondary layer. Supports auto-redaction for EDIT.

**Hallucination / grounding.** Claim extraction, retrieval against approved enterprise documents, then comparison. Each claim is labelled SUPPORTED, CONTRADICTED, UNSUPPORTED or UNVERIFIABLE. This is more credible than asking another model “is this hallucinated?”

**Bias.** Heuristics for protected attributes used as decision criteria, with optional LLM-as-judge refinement. The product language is “potential bias,” and high-impact bias is routed to humans.

**Policy.** Configurable enterprise rules: sensitive-data disclosure, decision-oversight requirements, overclaiming, and application-scope limits. Example: an employee copilot should not make a customer credit decision.

### 3.5 Decision design

Each detector returns a score, confidence, severity, reasons and evidence.

Overall risk is a weighted combination of privacy, hallucination, bias and policy scores. Weights come from the selected application policy.

Critical overrides prevent a severe individual risk from being hidden by averaging:

```text
Privacy >= 95                         → BLOCK
Bias >= 90 in very-strict workflows   → HUMAN REVIEW
Evidence confidence < 25%             → ABSTAIN / HUMAN REVIEW
Detector unavailable                  → fail-safe FLAG / HUMAN REVIEW
```

Final actions:

| Decision | When it is used | What the user sees |
|---|---|---|
| ALLOW | Low contextual risk | Original AI response |
| EDIT | Risk can be auto-sanitized | Redacted or rewritten response |
| FLAG | Meaningful but not catastrophic risk | Held for review |
| HUMAN REVIEW | High-impact or low-confidence case | Held for review |
| BLOCK | Critical privacy or policy violation | Safe policy message |

Admin users still see the original model output, evidence and audit trail.

### 3.6 Seeded policy profiles

These values are prototype assumptions and are editable:

| Application | Profile | Privacy | Hallucination | Bias | High-risk action | Critical action |
|---|---|---|---|---|---|---|
| Customer Support | Balanced | 70 | 75 | 70 | FLAG | BLOCK |
| Employee Copilot | Strict | 40 | 55 | 50 | FLAG | BLOCK |
| Decision Support | Very strict | 30 | 40 | 35 | HUMAN REVIEW | BLOCK |

The Policy Simulator is the commercial proof of the concept: the same model output can produce FLAG, BLOCK and HUMAN REVIEW depending only on the policy.

### 3.7 What is already built in the prototype

- Working FastAPI control plane and Next.js governance dashboard
- Four detectors plus pre-gate
- Knowledge-base grounding
- Three application policies
- Analyzer, live monitor, review queue, analytics, audit logs
- 21 demo scenarios
- Demo mode that works without an API key
- Automated tests for detectors, policy decisions and review flow

The prototype is intentionally not a production platform. It is a functional demonstration of the core mechanism.

---

## 4. Target users

ControlPlane.ai is sold to the enterprise, but used by four roles.

### 4.1 AI Governance Manager / Responsible AI lead

**Need:** one place to see risk, set policy, prove oversight and produce audit evidence.

**Primary surfaces:** Dashboard, Policies, Analytics, Audit Logs.

**Value:** can show leadership and auditors that AI use is observable and controllable, not informal.

### 4.2 AI Application Owner / product manager

**Need:** understand why outputs are blocked, tune the application risk profile, watch false positives and latency.

**Primary surfaces:** Analyzer, Application monitoring, Policy Simulator.

**Value:** can raise or lower thresholds without rewriting the model or the app.

### 4.3 Human Reviewer / operations specialist

**Need:** a queue of flagged cases with reasons, evidence and a simple approve / edit / reject action.

**Primary surfaces:** Review Queue, Interaction detail.

**Value:** spends time only on uncertain or high-impact cases, not every conversation.

### 4.4 Enterprise end user

**Need:** fast, trustworthy answers with as few unnecessary warnings as possible.

**Primary surface:** the original AI application. ControlPlane is mostly invisible unless a response is edited, held or blocked.

**Value:** safer answers without turning every chat into a compliance exercise.

### 4.5 Buying committee

Typical buyers:

- Chief Risk Officer
- Chief Information Security Officer
- Head of AI / AI Centre of Excellence
- Data Protection Officer
- Line-of-business owners in support, HR, finance or credit

The product is strongest where AI is already in production, the organisation is regulated or brand-sensitive, and there is no single owner of “AI safety” across applications.

### 4.6 Target segments

**Near-term**

- Mid-to-large enterprises already using multiple LLM applications
- Financial services, insurance, telecom, retail, IT services and shared-services operations
- Organisations under GDPR-like, DPDP-like or sector AI-risk pressure

**Later**

- Public sector and healthcare, after stronger identity, access control and data-residency features
- Multi-model and agentic estates that need tool-call governance, not only text checking

India, EU and US regional profiles in the prototype are configuration examples, not legal-compliance engines.

---

## 5. Business case and impact

### 5.1 Value thesis

ControlPlane.ai creates value in five ways:

1. **Loss avoidance.** Fewer privacy leaks, fewer ungrounded high-impact recommendations, fewer biased decision traces.
2. **Operating efficiency.** Humans review only flagged cases, not every AI interaction.
3. **Trust and adoption.** Business teams are more willing to scale AI if there is a visible control layer.
4. **Audit readiness.** Every decision has a reason, a policy version and a log.
5. **Reuse.** One control plane can govern many applications instead of building a checker per bot.

### 5.2 Illustrative operating model

Assume 32,000 interactions per week and these **prototype-style** interception rates, based on a mixed portfolio of support, internal copilot and decision support:

```text
ALLOW:          78%
EDIT:            6%
FLAG / REVIEW:  11%
BLOCK:           5%
```

That implies, illustratively:

```text
Weekly interactions:                 32,000
Auto-released (ALLOW + EDIT):        26,880
Human-reviewed:                       3,520
Blocked:                              1,600
```

Without a control plane, two failure modes are common:

- **No checking:** high-impact errors reach users.
- **Manual review of everything:** 32,000 items/week is not operable.

ControlPlane.ai is designed for the middle path: automatic handling of clear cases, human attention on the uncertain remainder.

### 5.3 Cost of inaction (illustrative)

These are directional planning figures, not claims of a specific customer loss:

| Risk event | Why it happens | Illustrative impact |
|---|---|---|
| Customer PII in chat | Model recites stored or inferred personal data | Regulatory notification, customer complaint, brand damage |
| Wrong HR or product policy | Hallucinated leave, refund or warranty rule | Wrong employee/customer action, rework, disputes |
| Biased hiring or credit language | Protected attribute used as a reason | Legal exposure, internal investigation, model shutdown |
| Alert fatigue | Generic checker flags too much | Users bypass controls; residual risk returns |
| No audit trail | Tooling only logs the chat, not the decision | Weak response to auditors, customers or regulators |

Even a small number of serious incidents per year can exceed the cost of a governance layer. The business case is therefore primarily **risk-adjusted**, not “this will increase chatbot conversion by X%.”

### 5.4 Efficiency impact (illustrative)

If an organisation currently samples 20% of AI conversations manually for quality and risk:

```text
32,000 × 20% = 6,400 reviews / week
```

If ControlPlane.ai concentrates review on the 11% flagged set:

```text
32,000 × 11% = 3,520 reviews / week
```

That is a **reduction of about 2,880 reviews per week**, while increasing coverage of the actually risky cases. Remaining ALLOW traffic can still be sampled for quality, but the default operating model is no longer “spot-check and hope.”

This also reduces the hidden cost of users ignoring warnings. EDIT and FLAG exist specifically so the system does not jump from “do nothing” to “block everything.”

### 5.5 Latency and cost impact

The prototype measures component latency because governance that adds seconds of delay will be bypassed.

Design choice:

- Cheap deterministic checks always run.
- Retrieval runs against a bounded enterprise corpus.
- LLM-as-judge is used as a secondary mechanism, not the only mechanism.
- Independent detectors run in parallel.

In demo mode, detector overhead is milliseconds. In live LLM mode, generation remains the dominant cost; ControlPlane should add a bounded overhead, not a second full conversation.

Token and estimated-cost telemetry exist so a sceptical stakeholder can see the control-plane tax, not only the risk metrics.

### 5.6 Strategic impact

For Accenture and similar system integrators, the product is also a **repeatable offer**:

- Assess the client’s AI estate
- Define application-specific policies
- Connect knowledge sources
- Insert the control plane in front of existing LLM APIs
- Operate a review queue and reporting layer

That maps naturally onto responsible-AI, risk, data-protection and AI-transformation programmes rather than a one-off chatbot build.

### 5.7 What we will not claim

- We will not claim a real-world accuracy percentage that was not measured on production data.
- We will not claim full GDPR, DPDP, HIPAA or EU AI Act compliance from the prototype.
- We will not claim that bias detection proves discrimination.
- We will not claim that hallucination detection works without evidence.

Credibility is part of the business case.

---

## 6. Go-to-market and implementation approach

### 6.1 Insertion model

ControlPlane.ai is inserted as middleware:

```text
Existing AI app  →  ControlPlane API  →  Foundation model API
                              ↓
                        User-safe output
```

The client does not need to replace the model. They change the integration point.

### 6.2 Commercial shape (proposal, not a price list)

A practical packaging for a later pilot:

- **Platform subscription** by volume band and number of applications
- **Policy and integration services** for onboarding the first three use cases
- **Optional managed review operations** if the client cannot staff a queue immediately

This is a software-plus-services motion, which fits enterprise buying behaviour better than a pure self-serve API.

### 6.3 First-client success criteria

A 90-day pilot would be considered successful if:

- At least three applications are on-boarded with distinct policies
- Every decision is explainable and logged
- Reviewers can clear the queue within the agreed SLA
- False-positive rate is measured and used to tune thresholds
- Application owners can show a before/after sample of risky outputs that were edited, flagged or blocked
- Added latency remains within the agreed budget for each use case

---

## 7. Phased roadmap

### Phase 0 — Now: Round 2 prototype

**Objective:** prove the core mechanism with simulated data.

**Scope already delivered:**

- Intercept, detect, score, decide, explain
- Three application policies
- PII, hallucination, bias and policy detectors
- Human review, audit, analytics
- Policy simulator
- Offline demo mode

**Exit criteria:** a judge can run the 5–7 minute demo and understand the product insight.

### Phase 1 — 0 to 3 months: design partner pilot

**Objective:** run ControlPlane.ai against one real enterprise’s three AI applications in a controlled environment.

Work:

- Replace simulated documents with the client’s approved knowledge sources
- Connect the actual model API
- Add authentication, role-based access, environment isolation
- Tune thresholds with the client’s risk and legal teams
- Measure false positives / false negatives on labelled samples
- Define reviewer operating procedures

Success: one production-adjacent pilot with evidence that policy-specific decisions reduce ungoverned high-risk outputs without freezing low-risk traffic.

### Phase 2 — 3 to 9 months: enterprise production

**Objective:** make the control plane operable as a shared enterprise service.

Work:

- SSO, RBAC, secrets management, encryption, retention controls
- Connectors for SharePoint, Confluence, policy repositories and ticket systems
- Streaming and batch audit modes
- Threshold suggestions from reviewer labels
- Broader regional / industry policy packs as configuration, still not “legal autopilot”
- Cost, latency and model-call dashboards for FinOps and SRE

Success: multiple applications share one control plane; governance, security and application teams have distinct roles.

### Phase 3 — 9 to 18 months: agent and multi-model control

**Objective:** govern actions, not only text.

Work:

- Intercept tool calls: email send, CRM update, payment, case closure
- Multi-model routing and per-model risk profiles
- Policy simulation before deployment of a new use case
- Cross-application risk intelligence
- Optional on-prem / VPC deployment for data-sensitive clients

Success: ControlPlane.ai is the standard gate in front of both copilots and agents.

### Phase 4 — 18 months+: platform scale

**Objective:** become the enterprise standard for runtime AI governance.

Work:

- Marketplace of detector and policy modules
- Automated policy optimisation with human approval
- Sector playbooks (banking, telecom, public sector)
- Independent assurance reports and evaluation harnesses
- Partner-led delivery through system integrators

This phase is directional. It depends on Phase 1–2 evidence, not on prototype metrics.

---

## 8. Key risks and mitigations

| Risk | Why it matters | Mitigation |
|---|---|---|
| Over-flagging / alert fatigue | Users ignore or bypass the system | Tiered actions (ALLOW / EDIT / FLAG / BLOCK); per-application thresholds; reviewer feedback used to retune; Policy Simulator before rollout |
| Under-flagging / missed harm | Liability, customer harm, regulatory exposure | Critical overrides for severe PII; fail-closed options for strict apps; human review for high-impact bias and low-confidence material claims |
| No ground truth for hallucination | False “this is hallucinated” labels destroy trust | Retrieval against approved documents; explicit UNVERIFIABLE / abstain path; never treat an LLM judge as sole quantitative truth |
| Detector quality is imperfect | Bias and privacy are hard problems | Hybrid stack: regex + retrieval + optional LLM judge; language is “potential bias”; humans remain in the loop |
| Added latency | Product teams will route around the gateway | Parallel detectors; cheap prefilters first; per-use-case latency budgets; skip expensive checks where policy allows |
| Policy configuration complexity | Wrong thresholds recreate one-size-fits-all | Seeded profiles (Balanced / Strict / Very Strict); simulator; governance owner plus application-owner split |
| Regulatory over-claim | Saying “GDPR compliant” without a legal engine creates legal risk | Regional profiles are configuration only; legal review stays human; limitations are stated in product and proposal |
| Integration friction | Enterprises already have bots and vendors | API-layer insertion; model-agnostic design; no requirement to own or fine-tune the foundation model |
| Demo / prototype misunderstood as production | Judges or clients over-read the current build | Clear limitations, simulated data, SQLite/demo mode, no production-security claim |
| Key-person / model-provider outage | Live LLM mode can fail during a demo or outage | Default demo mode; fail-safe decisions; safe fallback messages |
| Change management | Risk, legal, IT and business disagree on thresholds | Shared dashboard, audit evidence, and a review queue that makes disagreements operational rather than theoretical |
| Data handling in the control plane | The checker itself becomes a sensitive-data store | Minimise retention, hash or restrict raw logs in production, keep keys server-side, no secrets in the frontend |
| Agentic expansion too early | Tool-call governance is harder than text governance | Roadmap sequences text control first, then action interception after the pilot proves the decision model |

---

## 9. Why this can win as a Round 2 concept

The competition does not ask for a production platform. It asks for a complete solution design and a working prototype of the core mechanism.

ControlPlane.ai is strong on that brief because it shows:

- Multiple use cases, not one chatbot
- Multiple risk types, including overlap
- Evidence-aware hallucination checks
- Uncertainty handling
- Policy as configuration
- Human oversight
- Audit and feedback
- A live prototype that can be demonstrated without proprietary data

The business proposal and the prototype tell the same story: enterprises do not need a perfect oracle. They need a **control plane** that makes AI use observable, explainable, policy-aware and interruptible.

---

## 10. Closing recommendation

**Build the control plane before the next wave of AI applications is too large to govern.**

Recommended next step after Round 2:

1. Keep the current prototype as the demo and design artefact.
2. Select one design-partner enterprise with three live AI use cases.
3. Replace simulated documents with approved sources.
4. Run a 90-day policy-tuning pilot with measured false-positive rate, latency and reviewer load.
5. Only then productise identity, connectors and agent-action interception.

That sequence matches both the technical reality and the enterprise buying cycle.

---

**End of business proposal**

*ControlPlane.ai — Accenture Innovation Challenge 2026, Round 2, Track 1. All operating volumes, interception rates and efficiency figures in this document are illustrative planning assumptions, not audited customer results.*
