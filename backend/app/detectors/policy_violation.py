"""Policy violation detector (PRD section 16).

Deterministic checks against configurable enterprise rules: sensitive-data
disclosure rules, decision-oversight rules for regulated workflows, and
overclaiming rules. Application- and region-aware.
"""
import re
import time

from .base import BaseDetector, DetectionContext, RiskOutput
from .pii import detect_entities

RECOMMENDATION = re.compile(
    r"(?i)\b(should (?:probably )?be (?:approved|rejected|denied|extended)|recommend(?:s|ed)?|"
    r"approve the|reject the|deny the|can (?:likely )?be extended|should (?:not )?(?:approve|reject|hire|shortlist))\b"
)
EVIDENCE_LANGUAGE = re.compile(
    r"(?i)\b(according to|based on (?:the )?(?:documented|verified|published)|per the .{0,30}polic|credit bureau score|repayment history)\b"
)
UNCERTAINTY_LANGUAGE = re.compile(
    r"(?i)\b(incomplete|could not be verified|missing|partial records|not verified|unverified|although)\b"
)
OVERCLAIM = re.compile(r"(?i)\b(guarantee[ds]?|definitely will|100 percent certain|assured returns?)\b")

SENSITIVE_ENTITY_TYPES = {"PHONE_NUMBER", "AADHAAR", "PAN", "CREDIT_CARD", "BANK_ACCOUNT", "SALARY_INFO", "MEDICAL_INFO"}

CUSTOMER_DECISION_TOPIC = re.compile(
    r"(?i)\b(customer|credit limit|credit bureau|repayment history|loan|default|payment risk)\b"
)
EMPLOYEE_HR_TOPIC = re.compile(
    r"(?i)\b(employee|annual leave|sick leave|salary|compensation|medical|hr policy|personal phone)\b"
)
SUPPORT_TOPIC = re.compile(r"(?i)\b(refund|cancellation|warranty|support ticket|customer support)\b")


class PolicyViolationDetector(BaseDetector):
    name = "policy"

    async def analyze(self, ctx: DetectionContext) -> RiskOutput:
        t0 = time.perf_counter()
        text = ctx.response
        combined = f"{ctx.prompt}\n{text}"
        score = 0.0
        reasons: list[str] = []
        evidence: list[dict] = []

        # Rule 0 — application scope. This is what makes the same output behave
        # differently across Customer Support, Employee Copilot and Decision Support.
        if ctx.application == "employee_copilot" and CUSTOMER_DECISION_TOPIC.search(combined):
            score = max(score, 82.0)
            reasons.append(
                "Application-scope policy: Employee Copilot must not make customer credit or repayment decisions"
            )
            evidence.append({"source": "AI Governance Policy", "section": "Human Review Rules",
                             "status": "VIOLATION", "match": "customer decision topic in employee copilot"})
        elif ctx.application == "customer_support" and EMPLOYEE_HR_TOPIC.search(combined):
            score = max(score, 72.0)
            reasons.append(
                "Application-scope policy: Customer Support must not answer employee HR or personal-data questions"
            )
            evidence.append({"source": "AI Governance Policy", "section": "Sensitive Data Rules",
                             "status": "VIOLATION", "match": "employee/HR topic in customer support"})
        elif ctx.application == "decision_support" and (SUPPORT_TOPIC.search(combined) or EMPLOYEE_HR_TOPIC.search(combined)):
            score = max(score, 58.0)
            reasons.append(
                "Application-scope policy: Decision Support should route operational support or HR-policy answers to the owning application"
            )
            evidence.append({"source": "AI Governance Policy", "section": "AI Usage Rules",
                             "status": "REQUIRES_REVIEW", "match": "out-of-scope operational topic"})

        # Rule 1 — sensitive data disclosure (Employee Data Protection / AI Governance)
        entities = detect_entities(text)
        sensitive = [e for e in entities if e["type"] in SENSITIVE_ENTITY_TYPES]
        if sensitive:
            score = max(score, 90.0)
            kinds = sorted({e["type"] for e in sensitive})
            reasons.append(
                "Employee/Customer Data Protection Policy prohibits disclosure of: " + ", ".join(kinds)
            )
            evidence.append({"source": "Employee Data Protection Policy", "section": "Prohibited Disclosures",
                             "status": "VIOLATION", "match": ", ".join(e["value"] for e in sensitive[:4])})
            if ctx.region == "EU":
                score = min(100.0, score + 5)
                reasons.append("EU regional profile applies stricter personal-data handling")

        # Rule 2 — decision recommendations need documented evidence + human oversight
        rec = RECOMMENDATION.search(text)
        if rec:
            uncertain = bool(UNCERTAINTY_LANGUAGE.search(text))
            unsupported = uncertain or not EVIDENCE_LANGUAGE.search(text)
            if ctx.application == "decision_support" and unsupported:
                score = max(score, 72.0)
                reasons.append("AI Governance Policy: decision recommendations require documented evidence and human approval")
                evidence.append({"source": "Financial Policy", "section": "Credit Decisions",
                                 "status": "REQUIRES_REVIEW", "match": rec.group(0)})
            elif uncertain:
                score = max(score, 68.0)
                reasons.append("Recommendation is based on admittedly incomplete or unverified information")
                evidence.append({"source": "AI Governance Policy", "section": "Human Review Rules",
                                 "status": "REQUIRES_REVIEW", "match": rec.group(0)})
            elif ctx.application == "decision_support":
                score = max(score, 40.0)
                reasons.append("Decision recommendation detected — human approval required before use")

        # Rule 3 — overclaiming / forward-looking guarantees
        oc = OVERCLAIM.search(text)
        if oc:
            score = max(score, 55.0)
            reasons.append("Financial Policy prohibits guarantees and unverified forward-looking claims")
            evidence.append({"source": "Financial Policy", "section": "Forward-Looking Statements",
                             "status": "VIOLATION", "match": oc.group(0)})

        return RiskOutput(
            risk_type="policy",
            score=score,
            confidence=0.95 if score >= 50 else 0.9,
            status="POLICY_VIOLATION" if score >= 70 else ("POLICY_CAUTION" if score >= 40 else "COMPLIANT"),
            reasons=reasons or ["No enterprise policy rules triggered"],
            evidence=evidence,
            latency_ms=(time.perf_counter() - t0) * 1000,
        )
