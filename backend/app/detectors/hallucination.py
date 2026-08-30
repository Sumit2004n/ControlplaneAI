"""Hallucination / grounding detector (PRD sections 13-14, 36).

Hybrid pipeline — never just "ask an LLM if it's hallucinated":
  1. Extract factual claims from the response (deterministic sentence rules;
     LLM extraction refines in real mode).
  2. Retrieve evidence chunks from the enterprise knowledge base.
  3. Compare claim vs evidence: numeric-conflict + lexical-support rules
     (LLM judge refines the comparison in real mode).
  4. Label each claim SUPPORTED / CONTRADICTED / UNSUPPORTED / UNVERIFIABLE.
  5. Report confidence; abstain instead of guessing when evidence is missing.
"""
import re
import time

from ..rag.kb import content_tokens, extract_numbers, get_kb
from ..services import llm
from .base import BaseDetector, DetectionContext, RiskOutput

FACTUAL_HINTS = re.compile(
    r"(?i)\b(polic\w+|refund|warranty|leave|leaves|salary|price[ds]?|pricing|storage|uptime|sla|"
    r"expense|approv\w+|limit|receive[sd]?|entitled|includes?|per (?:year|month|user)|percent|"
    r"days?|weeks?|months?|rupees|lakh|tonnes?|emissions?|rate|default)\b"
)
OPINION_HINTS = re.compile(r"(?i)\b(i think|maybe|perhaps|hello|thank you|you're welcome)\b")


def extract_claims(response: str) -> list[str]:
    """Deterministic claim extraction: factual sentences (numbers or policy terms)."""
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", response) if s.strip()]
    claims = []
    for s in sentences:
        if OPINION_HINTS.search(s):
            continue
        has_number = bool(re.search(r"\d", s))
        if (has_number or FACTUAL_HINTS.search(s)) and len(s.split()) >= 4:
            claims.append(s)
    return claims


def _grade_claim(claim: str, kb) -> dict:
    """Deterministic claim-vs-evidence comparison."""
    results = kb.search(claim, k=2)
    claim_content = {t for t in content_tokens(claim) if not t.isdigit()}
    claim_numbers = extract_numbers(claim)

    if not results or not claim_content:
        return {"claim": claim, "status": "UNVERIFIABLE", "risk": 55, "confidence": 0.2,
                "source": None, "section": None, "match": None, "coverage": 0.0,
                "detail": "No relevant evidence found in the knowledge base"}

    chunk, cosine, overlap = results[0]
    coverage = round(min(1.0, overlap), 2)
    chunk_numbers = extract_numbers(chunk.text)

    if overlap >= 0.45 and claim_numbers and chunk_numbers and not (claim_numbers & chunk_numbers):
        return {"claim": claim, "status": "CONTRADICTED", "risk": 93, "confidence": 0.92,
                "source": chunk.doc_name, "section": chunk.section, "match": chunk.text[:220],
                "coverage": coverage,
                "detail": (f"Claim states {', '.join(sorted(claim_numbers))} but evidence states "
                           f"{', '.join(sorted(chunk_numbers))}")}
    if overlap >= 0.5 and (not claim_numbers or (claim_numbers & chunk_numbers) or not chunk_numbers):
        return {"claim": claim, "status": "SUPPORTED", "risk": 4, "confidence": 0.88,
                "source": chunk.doc_name, "section": chunk.section, "match": chunk.text[:220],
                "coverage": coverage, "detail": "Claim is consistent with enterprise documentation"}
    if overlap >= 0.28:
        return {"claim": claim, "status": "UNSUPPORTED", "risk": 62, "confidence": 0.5,
                "source": chunk.doc_name, "section": chunk.section, "match": chunk.text[:220],
                "coverage": coverage, "detail": "Partially related evidence found but the claim is not confirmed"}
    return {"claim": claim, "status": "UNVERIFIABLE", "risk": 55, "confidence": 0.2,
            "source": None, "section": None, "match": None, "coverage": coverage,
            "detail": "No sufficiently relevant evidence found in the knowledge base"}


class HallucinationDetector(BaseDetector):
    name = "hallucination"

    async def analyze(self, ctx: DetectionContext) -> RiskOutput:
        t0 = time.perf_counter()
        kb = get_kb()
        claims = extract_claims(ctx.response)

        if not claims:
            return RiskOutput(
                risk_type="hallucination", score=3, confidence=0.9, status="NO_FACTUAL_CLAIMS",
                reasons=["No verifiable factual claims detected in the response"],
                latency_ms=(time.perf_counter() - t0) * 1000,
            )

        graded = [_grade_claim(c, kb) for c in claims]

        # Real mode: LLM judge refines the deterministic comparison per claim
        if not llm.demo_active():
            for g in graded:
                if g["match"] is None:
                    continue
                verdict = await llm.judge_json(
                    "You verify claims against evidence. Respond with JSON: "
                    '{"status": "SUPPORTED"|"CONTRADICTED"|"UNSUPPORTED", "confidence_0_1": number, "detail": string}',
                    f"Claim: {g['claim']}\n\nEvidence ({g['source']} - {g['section']}): {g['match']}",
                )
                if verdict and verdict.get("status") in ("SUPPORTED", "CONTRADICTED", "UNSUPPORTED"):
                    g["status"] = verdict["status"]
                    g["confidence"] = max(0.1, min(1.0, float(verdict.get("confidence_0_1", g["confidence"]))))
                    g["risk"] = {"SUPPORTED": 4, "CONTRADICTED": 93, "UNSUPPORTED": 62}[verdict["status"]]
                    g["detail"] = str(verdict.get("detail", g["detail"]))[:220]

        worst = max(graded, key=lambda g: g["risk"])
        score = float(worst["risk"])
        statuses = [g["status"] for g in graded]
        n_bad = sum(1 for s in statuses if s != "SUPPORTED")
        if n_bad > 1:
            score = min(100.0, score + 2.0 * (n_bad - 1))

        avg_coverage = round(sum(g["coverage"] for g in graded) / len(graded), 2)
        status = worst["status"]
        confidence = worst["confidence"]

        reasons = []
        for g in graded:
            if g["status"] == "CONTRADICTED":
                reasons.append(f"CONTRADICTED — \"{g['claim'][:90]}\" conflicts with {g['source']} ({g['section']}): {g['detail']}")
            elif g["status"] == "UNSUPPORTED":
                reasons.append(f"UNSUPPORTED — \"{g['claim'][:90]}\" could not be confirmed against {g['source']}")
            elif g["status"] == "UNVERIFIABLE":
                reasons.append(f"UNVERIFIABLE — no evidence available for \"{g['claim'][:90]}\" (verification not possible)")
        if not reasons:
            reasons.append(f"All {len(graded)} factual claim(s) supported by enterprise documents")

        evidence = [{
            "claim": g["claim"], "status": g["status"], "source": g["source"] or "Knowledge base",
            "section": g["section"] or "—", "match": g["match"] or "No relevant evidence found",
            "coverage": g["coverage"], "detail": g["detail"],
        } for g in graded]

        return RiskOutput(
            risk_type="hallucination", score=score, confidence=confidence, status=status,
            reasons=reasons, evidence=evidence,
            latency_ms=(time.perf_counter() - t0) * 1000,
        )
