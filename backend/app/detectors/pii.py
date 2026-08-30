"""PII / privacy detector (PRD section 12).

Layer 1: deterministic regex entity detection (primary, never skipped).
Layer 2: LLM classification as secondary validation (real mode only).
Produces redaction spans used by the EDIT action.
"""
import re
import time

from ..services import llm
from .base import BaseDetector, DetectionContext, RiskOutput

# (entity_type, compiled regex, base risk weight, human reason)
ENTITY_PATTERNS: list[tuple[str, re.Pattern, int, str]] = [
    ("PHONE_NUMBER", re.compile(r"(?:\+91[\s-]?)?\b[6-9]\d{9}\b"), 95, "Personal phone number detected"),
    ("EMAIL", re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b"), 72, "Email address detected"),
    ("AADHAAR", re.compile(r"\b\d{4}[\s-]\d{4}[\s-]\d{4}\b"), 98, "Aadhaar-like government ID detected"),
    ("PAN", re.compile(r"\b[A-Z]{5}\d{4}[A-Z]\b"), 92, "PAN-like government ID detected"),
    ("CREDIT_CARD", re.compile(r"\b\d{4}[\s-]\d{4}[\s-]\d{4}[\s-]\d{4}\b"), 97, "Credit-card-like number detected"),
    ("BANK_ACCOUNT", re.compile(r"(?i)\baccount\s+(?:no\.?|number)?\s*:?\s*\d{9,18}\b"), 93, "Bank-account-like information detected"),
    ("EMPLOYEE_ID", re.compile(r"\bEMP[-\s]?\d{3,6}\b"), 65, "Employee ID detected"),
]

SALARY_PATTERN = re.compile(
    r"(?i)(?:salary|earns?|ctc|compensation)\b[^.\n]{0,40}?"
    r"(?:(?:₹|rs\.?|inr)\s*\d[\d,.]*|\d[\d,.]*\s*(?:lakh|lakhs|lpa|crore|rupees|k\b))"
)
SALARY_AMOUNT = re.compile(r"(?i)(?:₹|rs\.?|inr)\s*\d[\d,.]*\s*(?:lakh|lakhs|crore)|\b\d+\s*(?:lakh|lakhs)\s*(?:rupees)?")

MEDICAL_TERMS = re.compile(
    r"(?i)\b(depression|anxiety|diabetes|cancer|hiv|aids|asthma|bipolar|schizophrenia|"
    r"medical condition|surgery|therapy|chemotherapy|diagnos\w+|treated for|treatment for)\b"
)
PERSON_CONTEXT = re.compile(r"(?i)\b(he|she|his|her|their|employee|customer|candidate)\b|\b[A-Z][a-z]{2,}\b")


def detect_entities(text: str) -> list[dict]:
    """Deterministic entity detection with spans (also used by the pre-gate)."""
    entities: list[dict] = []
    seen_spans: list[tuple[int, int]] = []

    def overlaps(start: int, end: int) -> bool:
        return any(not (end <= s or start >= e) for s, e in seen_spans)

    for etype, pattern, weight, reason in ENTITY_PATTERNS:
        for m in pattern.finditer(text):
            if overlaps(m.start(), m.end()):
                continue
            seen_spans.append((m.start(), m.end()))
            entities.append({"type": etype, "value": m.group(), "start": m.start(),
                             "end": m.end(), "weight": weight, "reason": reason})

    for m in SALARY_PATTERN.finditer(text):
        if not overlaps(m.start(), m.end()):
            seen_spans.append((m.start(), m.end()))
            entities.append({"type": "SALARY_INFO", "value": m.group(), "start": m.start(),
                             "end": m.end(), "weight": 88, "reason": "Salary / compensation information detected"})
    for m in SALARY_AMOUNT.finditer(text):
        if not overlaps(m.start(), m.end()):
            seen_spans.append((m.start(), m.end()))
            entities.append({"type": "SALARY_INFO", "value": m.group(), "start": m.start(),
                             "end": m.end(), "weight": 85, "reason": "Salary-like amount detected"})

    for m in MEDICAL_TERMS.finditer(text):
        window = text[max(0, m.start() - 120):m.end() + 40]
        if PERSON_CONTEXT.search(window) and not overlaps(m.start(), m.end()):
            seen_spans.append((m.start(), m.end()))
            entities.append({"type": "MEDICAL_INFO", "value": m.group(), "start": m.start(),
                             "end": m.end(), "weight": 90, "reason": "Medical / health information about a person detected"})
    return entities


def redact(text: str, entities: list[dict]) -> str:
    """Replace detected spans, producing the EDIT-action sanitized response."""
    result = text
    for ent in sorted(entities, key=lambda e: e["start"], reverse=True):
        result = result[:ent["start"]] + f"[REDACTED-{ent['type']}]" + result[ent["end"]:]
    return result


class PIIDetector(BaseDetector):
    name = "privacy"

    async def analyze(self, ctx: DetectionContext) -> RiskOutput:
        t0 = time.perf_counter()
        entities = detect_entities(ctx.response)

        score = 0.0
        reasons: list[str] = []
        if entities:
            score = max(e["weight"] for e in entities)
            score = min(100.0, score + 2.0 * (len(entities) - 1))
            reasons = sorted({e["reason"] for e in entities})

        # Multi-turn escalation: repeated sensitive requests raise privacy risk
        if ctx.escalation_level > 0 and (entities or ctx.sensitive_request):
            boost = min(10, 4 * ctx.escalation_level)
            score = min(100.0, score + boost)
            reasons.append(
                f"Conversation escalation: {ctx.escalation_level} prior sensitive request(s) in this conversation"
            )

        confidence = 0.96 if entities else 0.9

        # Secondary LLM validation (real mode only) for entities regex misses
        if not llm.demo_active():
            verdict = await llm.judge_json(
                "You are a privacy analyst. Respond with JSON: "
                '{"contains_pii": bool, "entities": [string], "risk_0_100": number}',
                f"Does this text disclose personal information about a specific person?\n\n{ctx.response}",
            )
            if verdict and verdict.get("contains_pii") and score < 60:
                score = max(score, min(float(verdict.get("risk_0_100", 70)), 90.0))
                reasons.append("LLM privacy judge flagged personal information: "
                               + ", ".join(map(str, verdict.get("entities", [])[:4])))
                confidence = 0.75

        evidence = [{"source": "PII detector", "entity": e["type"], "match": e["value"],
                     "claim": e["reason"], "status": "DETECTED"} for e in entities]
        return RiskOutput(
            risk_type="privacy",
            score=score,
            confidence=confidence,
            status="PII_DETECTED" if entities else "CLEAN",
            reasons=reasons or ["No personal information detected"],
            evidence=evidence,
            latency_ms=(time.perf_counter() - t0) * 1000,
        )
