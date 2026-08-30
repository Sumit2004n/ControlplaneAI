"""ControlPlane orchestration pipeline (PRD sections 8-10, 50).

pre-gate -> (generation) -> parallel detectors -> risk aggregation ->
policy decision -> final output + audit trail. Independent detectors run
concurrently to protect latency; each stage is timed.
"""
import asyncio
import time
from datetime import datetime

from sqlalchemy.orm import Session

from ..database.models import AuditLog, Interaction, Policy, RiskResult
from ..detectors.base import DetectionContext, RiskOutput
from ..detectors.bias import BiasDetector
from ..detectors.hallucination import HallucinationDetector
from ..detectors.pii import PIIDetector
from ..detectors.policy_violation import PolicyViolationDetector
from ..detectors.pregate import pre_gate
from ..policy.engine import BLOCK_MESSAGE, decide
from ..scoring.aggregator import aggregate
from . import llm

DETECTORS = {
    "privacy": PIIDetector(),
    "hallucination": HallucinationDetector(),
    "bias": BiasDetector(),
    "policy": PolicyViolationDetector(),
}

DETECTOR_TIMEOUT_S = 20.0


def resolve_policy(db: Session, application: str, region: str | None, policy_id: str | None) -> Policy:
    if policy_id:
        policy = db.get(Policy, policy_id)
        if policy:
            return policy
    q = db.query(Policy).filter(Policy.application_type == application)
    if region:
        regional = q.filter(Policy.region == region).first()
        if regional:
            return regional
    policy = q.first()
    if policy:
        return policy
    policy = db.query(Policy).first()
    if policy is None:
        raise RuntimeError("No policies configured")
    return policy


async def _run_detector(name: str, detector, ctx: DetectionContext) -> RiskOutput:
    t0 = time.perf_counter()
    try:
        return await asyncio.wait_for(detector.analyze(ctx), timeout=DETECTOR_TIMEOUT_S)
    except Exception as exc:  # fail-safe path (PRD sec 52-53)
        return RiskOutput(
            risk_type=name, score=0, confidence=0, status="DETECTOR_ERROR", error=True,
            reasons=[f"{name} detector unavailable ({type(exc).__name__}) — fail-safe policy applies"],
            latency_ms=(time.perf_counter() - t0) * 1000,
        )


async def run_analysis(
    db: Session,
    *,
    application: str,
    prompt: str,
    response: str | None = None,
    history: list[dict] | None = None,
    conversation_id: str | None = None,
    region: str | None = None,
    policy_id: str | None = None,
    scenario_id: str | None = None,
    persist: bool = True,
    source: str = "live",
    created_at: datetime | None = None,
) -> dict:
    t_total = time.perf_counter()
    history = history or []
    policy = resolve_policy(db, application, region, policy_id)
    region = region or policy.region
    latency: dict = {}

    # ---- Pre-gate (input) ----
    t0 = time.perf_counter()
    gate = pre_gate(prompt, history)
    latency["pre_gate_ms"] = round((time.perf_counter() - t0) * 1000, 1)

    generated = False
    if gate["action"] == "BLOCK":
        response = ""
        ai_response = ""
        outputs: dict[str, RiskOutput] = {}
        overall, confidence = float(gate["risk"]), 0.9
        decision_obj = None
        decision = "BLOCK"
        reasons = gate["reasons"] + [f"Blocked at the pre-gate before any model call (policy '{policy.name}')"]
        final_response = BLOCK_MESSAGE
        abstained = False
        latency["generation_ms"] = 0.0
        latency["detectors_ms"] = 0.0
        risks_payload: dict = {}
        evidence_payload: list = []
    else:
        # ---- Generation (if no response supplied) ----
        t0 = time.perf_counter()
        if response is None:
            response = await llm.generate(prompt, application, history, scenario_id)
            generated = True
        ai_response = response
        latency["generation_ms"] = round((time.perf_counter() - t0) * 1000, 1)

        # ---- Parallel detectors ----
        ctx = DetectionContext(
            prompt=prompt, response=response, application=application, region=region,
            history=history, policy=policy,
            sensitive_request=gate["sensitive_request"], escalation_level=gate["escalation_level"],
        )
        t0 = time.perf_counter()
        results = await asyncio.gather(*(_run_detector(n, d, ctx) for n, d in DETECTORS.items()))
        outputs = {name: out for name, out in zip(DETECTORS.keys(), results)}
        latency["detectors_ms"] = round((time.perf_counter() - t0) * 1000, 1)
        for name, out in outputs.items():
            latency[f"detector_{name}_ms"] = round(out.latency_ms, 1)

        # ---- Aggregate + decide ----
        t0 = time.perf_counter()
        overall, confidence = aggregate(outputs, policy.weights or None)
        decision_obj = decide(outputs, overall, confidence, policy, application, response)
        latency["decision_ms"] = round((time.perf_counter() - t0) * 1000, 1)

        decision = decision_obj.decision
        reasons = decision_obj.reasons
        final_response = decision_obj.final_response
        abstained = decision_obj.abstained
        if gate["sensitive_request"] or gate["escalation_level"]:
            reasons = gate["reasons"] + reasons

        risks_payload = {name: out.to_dict() for name, out in outputs.items()}
        evidence_payload = [ev for out in outputs.values() for ev in out.evidence]

    latency["total_ms"] = round((time.perf_counter() - t_total) * 1000, 1)
    review_status = "pending" if decision in ("FLAG", "HUMAN_REVIEW") else "none"
    severity = "CRITICAL" if overall >= 75 else "HIGH" if overall >= 50 else "MEDIUM" if overall >= 25 else "LOW"

    interaction_id = "INT-PREVIEW"
    timestamp = created_at or datetime.utcnow()
    if persist:
        interaction = Interaction(
            application=application, region=region, user_prompt=prompt,
            ai_response=ai_response, final_response=final_response,
            conversation_id=conversation_id, created_at=timestamp,
            overall_risk=overall, overall_confidence=confidence,
            decision=decision, reasons=reasons,
            policy_id=policy.id, policy_name=policy.name,
            latency_ms=latency["total_ms"], latency_breakdown=latency,
            review_status=review_status, source=source, scenario_id=scenario_id,
        )
        db.add(interaction)
        db.flush()
        for name, out in outputs.items():
            db.add(RiskResult(
                interaction_pk=interaction.id, risk_type=name, score=out.score,
                confidence=out.confidence, severity=out.severity, status=out.status,
                reasons=out.reasons, evidence=out.evidence, latency_ms=out.latency_ms,
            ))
        db.add(AuditLog(
            interaction_pk=interaction.id, event="DECISION_MADE", actor="controlplane",
            created_at=timestamp,
            meta={
                "decision": decision, "overall_risk": overall, "policy": policy.name,
                "policy_id": policy.id, "application": application, "region": region,
                "risks": {n: o.score for n, o in outputs.items()},
                "generated": generated, "pre_gate": gate["action"],
            },
        ))
        if review_status == "pending":
            db.add(AuditLog(interaction_pk=interaction.id, event="REVIEW_REQUESTED",
                            actor="controlplane", created_at=timestamp,
                            meta={"reason": "Decision requires human review"}))
        db.commit()
        interaction_id = interaction.interaction_id

    return {
        "interaction_id": interaction_id,
        "application": application,
        "region": region,
        "policy": {"id": policy.id, "name": policy.name, "risk_profile": policy.risk_profile,
                   "region": policy.region, "industry": policy.industry},
        "risks": risks_payload,
        "overall_risk": overall,
        "overall_confidence": confidence,
        "severity": severity,
        "decision": decision,
        "reasons": reasons,
        "evidence": evidence_payload,
        "final_response": final_response,
        "ai_response": ai_response,
        "user_prompt": prompt,
        "latency_ms": latency["total_ms"],
        "latency_breakdown": latency,
        "review_status": review_status,
        "abstained": abstained,
        "pre_gate": gate,
        "timestamp": timestamp.isoformat(),
    }
