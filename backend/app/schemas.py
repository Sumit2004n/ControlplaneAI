"""Pydantic request/response schemas (PRD sections 43, 45, 46)."""
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class HistoryTurn(BaseModel):
    role: str = "user"
    content: str = ""


class AnalyzeRequest(BaseModel):
    application: str
    prompt: str
    response: str
    conversation_history: list[HistoryTurn] = Field(default_factory=list)
    conversation_id: str | None = None
    region: str | None = None
    policy_id: str | None = None
    scenario_id: str | None = None


class GenerateAnalyzeRequest(BaseModel):
    application: str
    prompt: str
    conversation_history: list[HistoryTurn] = Field(default_factory=list)
    conversation_id: str | None = None
    region: str | None = None
    policy_id: str | None = None
    scenario_id: str | None = None


class RiskOut(BaseModel):
    risk_type: str
    score: float
    confidence: float
    severity: str
    status: str = ""
    reasons: list[str] = Field(default_factory=list)
    evidence: list[dict[str, Any]] = Field(default_factory=list)
    latency_ms: float = 0


class AnalysisOut(BaseModel):
    interaction_id: str
    application: str
    region: str
    policy: dict[str, Any]
    risks: dict[str, RiskOut]
    overall_risk: float
    overall_confidence: float
    severity: str
    decision: str
    reasons: list[str]
    evidence: list[dict[str, Any]]
    final_response: str
    ai_response: str
    user_prompt: str
    latency_ms: float
    latency_breakdown: dict[str, Any]
    review_status: str
    abstained: bool = False
    pre_gate: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime | None = None


class ReviewRequest(BaseModel):
    reviewer: str = "Demo Reviewer"
    decision: str  # APPROVE / EDIT / REJECT
    edited_response: str | None = None
    label: str | None = None  # TRUE_POSITIVE / FALSE_POSITIVE
    comment: str | None = None


class FeedbackRequest(BaseModel):
    interaction_id: str
    prediction: str
    human_label: str
    is_false_positive: bool = False
    comment: str | None = None


class PolicyIn(BaseModel):
    name: str
    application_type: str
    region: str = "India"
    industry: str = "General"
    risk_profile: str = "BALANCED"
    privacy_threshold: int = 70
    hallucination_threshold: int = 75
    bias_threshold: int = 70
    policy_threshold: int = 65
    low_risk_threshold: int = 25
    weights: dict[str, float] = Field(
        default_factory=lambda: {"privacy": 0.35, "hallucination": 0.30, "bias": 0.20, "policy": 0.15}
    )
    high_risk_action: str = "FLAG"
    critical_action: str = "BLOCK"
    edit_enabled: bool = False
    fail_safe: str = "FLAG"


class SimulateRequest(BaseModel):
    prompt: str
    response: str
    policy_ids: list[str] = Field(default_factory=list)  # empty = all policies
