"""Startup seeding (PRD sections 18, 35, 85): policies, knowledge documents,
and a genuinely-computed interaction history so no dashboard is ever empty.

Historical interactions are produced by actually running the ControlPlane
pipeline over the scenario library (not fabricated numbers), then spread over
the past 7 days.
"""
import random
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from ..config import KNOWLEDGE_BASE_DIR
from ..services.scenarios import load_scenarios
from .models import AuditLog, Document, Feedback, Interaction, Policy, Review

SEED_POLICIES = [
    dict(
        id="pol-customer-support", name="Customer Support Policy",
        application_type="customer_support", region="India", industry="Retail",
        risk_profile="BALANCED",
        privacy_threshold=70, hallucination_threshold=75, bias_threshold=70,
        policy_threshold=65, low_risk_threshold=25,
        weights={"privacy": 0.35, "hallucination": 0.30, "bias": 0.20, "policy": 0.15},
        high_risk_action="FLAG", critical_action="BLOCK",
        edit_enabled=True, fail_safe="FLAG",
    ),
    dict(
        id="pol-employee-copilot", name="Employee Copilot Policy",
        application_type="employee_copilot", region="India", industry="Technology",
        risk_profile="STRICT",
        privacy_threshold=40, hallucination_threshold=55, bias_threshold=50,
        policy_threshold=45, low_risk_threshold=25,
        weights={"privacy": 0.40, "hallucination": 0.30, "bias": 0.10, "policy": 0.20},
        high_risk_action="FLAG", critical_action="BLOCK",
        edit_enabled=False, fail_safe="FLAG",
    ),
    dict(
        id="pol-decision-support", name="Decision Support Policy",
        application_type="decision_support", region="India", industry="Financial Services",
        risk_profile="VERY_STRICT",
        privacy_threshold=30, hallucination_threshold=40, bias_threshold=35,
        policy_threshold=40, low_risk_threshold=20,
        weights={"privacy": 0.25, "hallucination": 0.30, "bias": 0.30, "policy": 0.15},
        high_risk_action="HUMAN_REVIEW", critical_action="BLOCK",
        edit_enabled=False, fail_safe="HUMAN_REVIEW",
    ),
]


def seed_policies(db: Session) -> None:
    for p in SEED_POLICIES:
        if not db.get(Policy, p["id"]):
            db.add(Policy(**p))
    db.commit()


def seed_documents(db: Session) -> None:
    if db.query(Document).count() > 0:
        return
    categories = {
        "hr_policy": ("HR Policy", "Human Resources", "3.1"),
        "customer_refund_policy": ("Customer Refund Policy", "Customer Operations", "2.4"),
        "product_documentation": ("Product Documentation — AtlasCRM Pro", "Product", "5.2"),
        "employee_data_policy": ("Employee Data Protection Policy", "Compliance", "1.8"),
        "financial_policy": ("Financial Policy", "Finance", "4.0"),
        "ai_governance_policy": ("AI Governance Policy", "Governance", "2.1"),
    }
    for path in sorted(KNOWLEDGE_BASE_DIR.glob("*.md")):
        name, category, version = categories.get(path.stem, (path.stem.title(), "General", "1.0"))
        db.add(Document(id=path.stem, name=name, category=category, version=version,
                        status="ACTIVE", content=path.read_text(encoding="utf-8")))
    db.commit()


async def seed_history(db: Session) -> None:
    if db.query(Interaction).count() > 0:
        return
    from ..services.pipeline import run_analysis  # local import to avoid cycles

    rng = random.Random(42)
    now = datetime.utcnow()
    scenarios = load_scenarios()

    for repeat in range(3):
        for s in scenarios:
            offset_hours = rng.uniform(2, 24 * 7)
            created = now - timedelta(hours=offset_hours)
            if s.get("conversation"):
                history: list[dict] = []
                for turn in s["conversation"]:
                    await run_analysis(
                        db, application=s["application"], prompt=turn["prompt"],
                        response=turn["response"], history=list(history),
                        conversation_id=f"seed-{s['id']}-{repeat}",
                        scenario_id=s["id"], source="seed", created_at=created,
                    )
                    history.append({"role": "user", "content": turn["prompt"]})
                    history.append({"role": "assistant", "content": turn["response"]})
                    created += timedelta(minutes=1)
            else:
                await run_analysis(
                    db, application=s["application"], prompt=s["prompt"], response=s["response"],
                    scenario_id=s["id"], source="seed", created_at=created,
                )

    # Review a share of the flagged items so feedback metrics are populated
    pending = (db.query(Interaction)
               .filter(Interaction.review_status == "pending", Interaction.source == "seed")
               .order_by(Interaction.created_at).all())
    reviewers = ["A. Mehta", "S. Iyer", "Governance Bot"]
    for idx, i in enumerate(pending):
        if idx % 3 == 2:
            continue  # leave ~1/3 pending for the live demo queue
        is_fp = idx % 5 == 0  # ~20% false positives for a realistic FP rate
        decision = "APPROVE" if is_fp else ("REJECT" if i.overall_risk >= 75 else "EDIT" if idx % 4 == 1 else "REJECT")
        reviewer = reviewers[idx % len(reviewers)]
        edited = None
        if decision == "EDIT":
            edited = "The requested information is available through the appropriate official channel."
        db.add(Review(interaction_pk=i.id, reviewer=reviewer, decision=decision,
                      edited_response=edited,
                      label="FALSE_POSITIVE" if is_fp else "TRUE_POSITIVE",
                      comment="Verified against source documents" if is_fp else "Risk confirmed on review",
                      created_at=i.created_at + timedelta(hours=1)))
        db.add(Feedback(interaction_pk=i.id, prediction=i.decision, human_label=decision,
                        is_false_positive=is_fp,
                        comment="Reviewer feedback (seeded)",
                        created_at=i.created_at + timedelta(hours=1)))
        db.add(AuditLog(interaction_pk=i.id, event="HUMAN_REVIEW", actor=reviewer,
                        created_at=i.created_at + timedelta(hours=1),
                        meta={"original_decision": i.decision, "human_decision": decision,
                              "label": "FALSE_POSITIVE" if is_fp else "TRUE_POSITIVE"}))
        i.review_status = "reviewed"
        i.human_decision = decision
        i.human_override = is_fp or decision == "EDIT"
    db.commit()


async def seed_all(db: Session) -> None:
    seed_policies(db)
    seed_documents(db)
    await seed_history(db)
