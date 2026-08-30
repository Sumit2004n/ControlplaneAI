"""Pre-generation gate (PRD section 9).

Lightweight input check before the LLM is called: sensitive-data requests,
prompt-injection indicators and restricted topics. Injection blocks before
generation (saves cost and latency); sensitive requests proceed but mark the
context so output detectors weigh the interaction more heavily.
"""
import re

SENSITIVE_REQUEST = re.compile(
    r"(?i)\b(phone number|mobile number|contact number|personal (?:number|phone|email|address)|"
    r"home address|salary|compensation|ctc|medical|health record|diagnos\w+|bank (?:account|details)|"
    r"account number|aadhaar|pan number|credit card)\b"
)
INJECTION = re.compile(
    r"(?i)\b(ignore (?:all )?(?:previous|prior|your) instructions|disregard (?:the )?system prompt|"
    r"pretend (?:you are|to be)|jailbreak|developer mode|act as (?:an? )?unrestricted)\b"
)
RESTRICTED = re.compile(r"(?i)\b(how to hack|make a (?:bomb|weapon)|steal (?:credentials|passwords))\b")


def pre_gate(prompt: str, history: list[dict] | None = None) -> dict:
    reasons: list[str] = []
    action = "PROCEED"
    risk = 0

    if INJECTION.search(prompt):
        return {"action": "BLOCK", "risk": 95, "sensitive_request": False, "escalation_level": 0,
                "reasons": ["Prompt-injection indicators detected — request blocked before generation"]}
    if RESTRICTED.search(prompt):
        return {"action": "BLOCK", "risk": 92, "sensitive_request": False, "escalation_level": 0,
                "reasons": ["Restricted topic requested — request blocked before generation"]}

    sensitive = bool(SENSITIVE_REQUEST.search(prompt))
    if sensitive:
        risk = 60
        reasons.append("Prompt requests potentially sensitive personal data — output checks tightened")

    # Multi-turn escalation: count prior sensitive requests in this conversation
    escalation = 0
    for turn in history or []:
        if turn.get("role", "user") == "user" and SENSITIVE_REQUEST.search(turn.get("content", "")):
            escalation += 1
    if escalation > 0:
        risk = min(90, risk + 10 * escalation)
        reasons.append(f"Conversation contains {escalation} earlier sensitive request(s) — escalation monitored")

    if not reasons:
        reasons.append("No input risks detected")
    return {"action": action, "risk": risk, "sensitive_request": sensitive,
            "escalation_level": escalation, "reasons": reasons}
