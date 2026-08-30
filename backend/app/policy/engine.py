"""Policy decision engine (PRD sections 18-19, 49, 53, 80, 83).

Maps detector outputs + the application's policy to one of
ALLOW / EDIT / FLAG / HUMAN_REVIEW / BLOCK, with deterministic explanations,
critical-risk overrides, abstention on low-confidence material claims and a
configurable fail-safe when a detector errors.
"""
from dataclasses import dataclass, field

from ..detectors.base import RiskOutput
from ..detectors.pii import detect_entities, redact

ACTION_RANK = {"ALLOW": 0, "EDIT": 1, "FLAG": 2, "HUMAN_REVIEW": 3, "BLOCK": 4}

BLOCK_MESSAGE = ("This response cannot be provided because it violates the applicable AI safety policy. "
                 "The interaction has been logged for governance review.")
FLAG_MESSAGE = "This response requires human review before it can be released. A reviewer has been notified."


@dataclass
class Decision:
    decision: str
    reasons: list[str] = field(default_factory=list)
    triggered: list[str] = field(default_factory=list)
    abstained: bool = False
    final_response: str = ""


def _threshold_for(policy, risk_type: str) -> int:
    return {
        "privacy": policy.privacy_threshold,
        "hallucination": policy.hallucination_threshold,
        "bias": policy.bias_threshold,
        "policy": policy.policy_threshold,
    }.get(risk_type, 70)


def _action_for(risk_type: str, score: float, policy) -> str:
    """Tiered action for a triggered risk. Potential bias is never auto-blocked
    on its own — it is routed to a human because bias detection cannot prove
    real-world discrimination (PRD sec 15, 58, 80)."""
    high, critical = policy.high_risk_action, policy.critical_action
    if risk_type == "bias":
        high = "HUMAN_REVIEW" if policy.risk_profile == "VERY_STRICT" else "FLAG"
        critical = "FLAG" if policy.risk_profile == "BALANCED" else "HUMAN_REVIEW"
    return critical if score >= 75 else high


def decide(outputs: dict[str, RiskOutput], overall: float, confidence: float,
           policy, application: str, response: str) -> Decision:
    reasons: list[str] = []
    triggered: list[str] = []
    candidates: list[str] = ["ALLOW"]
    abstained = False

    privacy = outputs.get("privacy")
    bias = outputs.get("bias")
    hall = outputs.get("hallucination")

    # ---- Critical safety overrides (PRD sec 80) ----
    if privacy and privacy.score >= 95:
        candidates.append("BLOCK")
        triggered.append("privacy")
        reasons.append(f"Critical override: privacy risk {privacy.score:.0f} >= 95 — sensitive PII must be blocked")
    if bias and bias.score >= 90 and policy.risk_profile == "VERY_STRICT":
        candidates.append("HUMAN_REVIEW")
        triggered.append("bias")
        reasons.append(f"Critical override: potential bias {bias.score:.0f} >= 90 in a very-strict workflow requires human review")

    # ---- Abstention: low-confidence material claims (PRD sec 14, 48-49) ----
    if hall and hall.status == "UNVERIFIABLE" and hall.confidence < 0.25:
        abstained = True
        candidates.append("HUMAN_REVIEW" if policy.risk_profile == "VERY_STRICT" else "FLAG")
        if "hallucination" not in triggered:
            triggered.append("hallucination")
        reasons.append(
            f"Abstention: claim verification not possible (evidence unavailable, confidence {hall.confidence:.0%}) — "
            "ControlPlane abstains instead of guessing"
        )

    # ---- Detector failure fail-safe (PRD sec 52-53) ----
    for rtype, out in outputs.items():
        if out.error:
            candidates.append(policy.fail_safe)
            reasons.append(f"Fail-safe: {rtype} detector unavailable — policy adopts {policy.fail_safe} instead of silently allowing")

    # ---- Per-risk policy thresholds ----
    for rtype, out in outputs.items():
        threshold = _threshold_for(policy, rtype)
        if out.score >= threshold:
            if rtype not in triggered:
                triggered.append(rtype)
            action = _action_for(rtype, out.score, policy)
            candidates.append(action)
            reasons.append(
                f"{rtype.capitalize()} risk {out.score:.0f} exceeded the '{policy.name}' threshold of {threshold} "
                f"({policy.risk_profile} profile) -> {action}"
            )

    # ---- Overall risk bands (use the dominant risk's action mapping) ----
    dominant = max(outputs, key=lambda t: outputs[t].score) if outputs else "policy"
    if overall >= 75:
        candidates.append(_action_for(dominant, overall, policy))
        reasons.append(f"Overall contextual risk {overall:.0f} is CRITICAL under the {policy.risk_profile} profile")
    elif overall >= 50:
        candidates.append(_action_for(dominant, overall, policy))
        reasons.append(f"Overall contextual risk {overall:.0f} is HIGH under the {policy.risk_profile} profile")

    final = max(candidates, key=lambda a: ACTION_RANK.get(a, 0))

    # ---- EDIT downgrade: privacy-only breach that can be auto-sanitized ----
    if (policy.edit_enabled and privacy is not None and "privacy" in triggered
            and privacy.score < 95
            and all(t == "privacy" for t in triggered)
            and ACTION_RANK.get(final, 0) in (ACTION_RANK["FLAG"], ACTION_RANK["HUMAN_REVIEW"], ACTION_RANK["BLOCK"])):
        entities = detect_entities(response)
        if entities:
            final = "EDIT"
            reasons.append("Auto-edit applied: detected personal data was redacted instead of blocking (policy allows EDIT)")

    if final == "ALLOW" and not reasons:
        reasons.append(f"Overall risk {overall:.0f} is below the '{policy.name}' low-risk threshold ({policy.low_risk_threshold}) — allowed")

    # ---- Final output to the end user (PRD sec 83) ----
    if final == "ALLOW":
        final_response = response
    elif final == "EDIT":
        final_response = redact(response, detect_entities(response))
    elif final in ("FLAG", "HUMAN_REVIEW"):
        final_response = FLAG_MESSAGE
    else:
        final_response = BLOCK_MESSAGE

    return Decision(decision=final, reasons=reasons, triggered=triggered,
                    abstained=abstained, final_response=final_response)
