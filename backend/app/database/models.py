"""Database schema per PRD section 44 (interactions, risk_results, policies,
reviews, feedback, audit_logs, documents)."""
from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .session import Base

DISPLAY_ID_BASE = 10000


def display_id(pk: int) -> str:
    return f"INT-{DISPLAY_ID_BASE + pk}"


def pk_from_display(did: str) -> int:
    return int(did.replace("INT-", "")) - DISPLAY_ID_BASE


class Interaction(Base):
    __tablename__ = "interactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    application: Mapped[str] = mapped_column(String(64), index=True)
    region: Mapped[str] = mapped_column(String(32), default="India")
    user_prompt: Mapped[str] = mapped_column(Text)
    ai_response: Mapped[str] = mapped_column(Text, default="")
    final_response: Mapped[str] = mapped_column(Text, default="")
    conversation_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)

    overall_risk: Mapped[float] = mapped_column(Float, default=0)
    overall_confidence: Mapped[float] = mapped_column(Float, default=0)
    decision: Mapped[str] = mapped_column(String(24), index=True)  # ALLOW/EDIT/FLAG/HUMAN_REVIEW/BLOCK
    reasons: Mapped[list] = mapped_column(JSON, default=list)

    policy_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    policy_name: Mapped[str | None] = mapped_column(String(128), nullable=True)

    latency_ms: Mapped[float] = mapped_column(Float, default=0)
    latency_breakdown: Mapped[dict] = mapped_column(JSON, default=dict)

    review_status: Mapped[str] = mapped_column(String(16), default="none", index=True)  # none/pending/reviewed
    human_decision: Mapped[str | None] = mapped_column(String(24), nullable=True)
    human_override: Mapped[bool] = mapped_column(Boolean, default=False)
    source: Mapped[str] = mapped_column(String(16), default="live")  # live/seed
    scenario_id: Mapped[str | None] = mapped_column(String(64), nullable=True)

    risk_results: Mapped[list["RiskResult"]] = relationship(back_populates="interaction", cascade="all, delete-orphan")
    reviews: Mapped[list["Review"]] = relationship(back_populates="interaction", cascade="all, delete-orphan")

    @property
    def interaction_id(self) -> str:
        return display_id(self.id)


class RiskResult(Base):
    __tablename__ = "risk_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    interaction_pk: Mapped[int] = mapped_column(ForeignKey("interactions.id"), index=True)
    risk_type: Mapped[str] = mapped_column(String(32))  # privacy/hallucination/bias/policy
    score: Mapped[float] = mapped_column(Float)
    confidence: Mapped[float] = mapped_column(Float)
    severity: Mapped[str] = mapped_column(String(16))  # LOW/MEDIUM/HIGH/CRITICAL
    status: Mapped[str] = mapped_column(String(32), default="")
    reasons: Mapped[list] = mapped_column(JSON, default=list)
    evidence: Mapped[list] = mapped_column(JSON, default=list)
    latency_ms: Mapped[float] = mapped_column(Float, default=0)

    interaction: Mapped[Interaction] = relationship(back_populates="risk_results")


class Policy(Base):
    __tablename__ = "policies"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(128))
    application_type: Mapped[str] = mapped_column(String(64), index=True)
    region: Mapped[str] = mapped_column(String(32), default="India")
    industry: Mapped[str] = mapped_column(String(64), default="General")
    risk_profile: Mapped[str] = mapped_column(String(32))  # BALANCED/STRICT/VERY_STRICT

    privacy_threshold: Mapped[int] = mapped_column(Integer, default=70)
    hallucination_threshold: Mapped[int] = mapped_column(Integer, default=75)
    bias_threshold: Mapped[int] = mapped_column(Integer, default=70)
    policy_threshold: Mapped[int] = mapped_column(Integer, default=65)
    low_risk_threshold: Mapped[int] = mapped_column(Integer, default=25)

    weights: Mapped[dict] = mapped_column(JSON, default=dict)
    high_risk_action: Mapped[str] = mapped_column(String(24), default="FLAG")
    critical_action: Mapped[str] = mapped_column(String(24), default="BLOCK")
    edit_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    fail_safe: Mapped[str] = mapped_column(String(24), default="FLAG")  # action when a detector fails
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Review(Base):
    __tablename__ = "reviews"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    interaction_pk: Mapped[int] = mapped_column(ForeignKey("interactions.id"), index=True)
    reviewer: Mapped[str] = mapped_column(String(64), default="Demo Reviewer")
    decision: Mapped[str] = mapped_column(String(16))  # APPROVE/EDIT/REJECT
    edited_response: Mapped[str | None] = mapped_column(Text, nullable=True)
    label: Mapped[str | None] = mapped_column(String(24), nullable=True)  # TRUE_POSITIVE/FALSE_POSITIVE
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    interaction: Mapped[Interaction] = relationship(back_populates="reviews")


class Feedback(Base):
    __tablename__ = "feedback"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    interaction_pk: Mapped[int] = mapped_column(ForeignKey("interactions.id"), index=True)
    prediction: Mapped[str] = mapped_column(String(24))
    human_label: Mapped[str] = mapped_column(String(24))
    is_false_positive: Mapped[bool] = mapped_column(Boolean, default=False)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    interaction_pk: Mapped[int | None] = mapped_column(ForeignKey("interactions.id"), nullable=True, index=True)
    event: Mapped[str] = mapped_column(String(64), index=True)
    actor: Mapped[str] = mapped_column(String(64), default="controlplane")
    meta: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(128))
    category: Mapped[str] = mapped_column(String(64))
    version: Mapped[str] = mapped_column(String(16), default="1.0")
    status: Mapped[str] = mapped_column(String(16), default="ACTIVE")
    last_updated: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    content: Mapped[str] = mapped_column(Text)
