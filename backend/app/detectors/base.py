"""Common detector interface (PRD sections 11, 45, 77)."""
from dataclasses import dataclass, field
from typing import Any


def severity_for(score: float) -> str:
    """PRD section 47 severity bands."""
    if score >= 75:
        return "CRITICAL"
    if score >= 50:
        return "HIGH"
    if score >= 25:
        return "MEDIUM"
    return "LOW"


@dataclass
class DetectionContext:
    prompt: str
    response: str
    application: str
    region: str = "India"
    history: list[dict] = field(default_factory=list)
    policy: Any = None
    sensitive_request: bool = False       # set by the pre-gate
    escalation_level: int = 0             # multi-turn sensitive-request count


@dataclass
class RiskOutput:
    risk_type: str
    score: float = 0.0
    confidence: float = 0.9
    status: str = "OK"
    reasons: list[str] = field(default_factory=list)
    evidence: list[dict] = field(default_factory=list)
    latency_ms: float = 0.0
    error: bool = False

    @property
    def severity(self) -> str:
        return severity_for(self.score)

    def to_dict(self) -> dict:
        return {
            "risk_type": self.risk_type,
            "score": round(self.score, 1),
            "confidence": round(self.confidence, 2),
            "severity": self.severity,
            "status": self.status,
            "reasons": self.reasons,
            "evidence": self.evidence,
            "latency_ms": round(self.latency_ms, 1),
        }


class BaseDetector:
    name = "base"

    async def analyze(self, ctx: DetectionContext) -> RiskOutput:  # pragma: no cover
        raise NotImplementedError
