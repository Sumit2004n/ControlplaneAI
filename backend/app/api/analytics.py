from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database.models import Feedback, Interaction, Review, RiskResult
from ..database.session import get_db
from ..services import llm

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


def _percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    values = sorted(values)
    idx = min(len(values) - 1, int(round(pct * (len(values) - 1))))
    return round(values[idx], 1)


@router.get("")
def analytics(days: int = 7, db: Session = Depends(get_db)):
    since = datetime.utcnow() - timedelta(days=days)
    interactions = db.query(Interaction).filter(Interaction.created_at >= since).all()
    total = len(interactions)

    decisions: dict[str, int] = {}
    severities = {"LOW": 0, "MEDIUM": 0, "HIGH": 0, "CRITICAL": 0}
    by_application: dict[str, dict] = {}
    latencies = []
    for i in interactions:
        decisions[i.decision] = decisions.get(i.decision, 0) + 1
        sev = "CRITICAL" if i.overall_risk >= 75 else "HIGH" if i.overall_risk >= 50 else "MEDIUM" if i.overall_risk >= 25 else "LOW"
        severities[sev] += 1
        latencies.append(i.latency_ms or 0)
        app_stats = by_application.setdefault(i.application, {"total": 0, "high_risk": 0, "blocked": 0, "avg_risk": 0.0})
        app_stats["total"] += 1
        app_stats["avg_risk"] += i.overall_risk
        if i.overall_risk >= 50:
            app_stats["high_risk"] += 1
        if i.decision == "BLOCK":
            app_stats["blocked"] += 1
    for stats in by_application.values():
        stats["avg_risk"] = round(stats["avg_risk"] / max(stats["total"], 1), 1)

    # Risk-type frequency (share of interactions where each risk was HIGH+)
    risk_freq: dict[str, int] = {}
    risk_rows = (db.query(RiskResult).join(Interaction)
                 .filter(Interaction.created_at >= since, RiskResult.score >= 50).all())
    for r in risk_rows:
        risk_freq[r.risk_type] = risk_freq.get(r.risk_type, 0) + 1

    # Feedback loop metrics (PRD sec 23)
    feedback = db.query(Feedback).all()
    reviewed = len(feedback)
    false_pos = sum(1 for f in feedback if f.is_false_positive)
    true_pos = reviewed - false_pos
    reviews = db.query(Review).count()
    overrides = db.query(Interaction).filter(Interaction.human_override.is_(True)).count()

    # Daily trend for charts
    trend: dict[str, dict] = {}
    for i in interactions:
        day = i.created_at.strftime("%Y-%m-%d")
        t = trend.setdefault(day, {"date": day, "total": 0, "flagged": 0, "blocked": 0, "avg_risk": 0.0})
        t["total"] += 1
        t["avg_risk"] += i.overall_risk
        if i.decision in ("FLAG", "HUMAN_REVIEW"):
            t["flagged"] += 1
        if i.decision == "BLOCK":
            t["blocked"] += 1
    trend_list = sorted(trend.values(), key=lambda t: t["date"])
    for t in trend_list:
        t["avg_risk"] = round(t["avg_risk"] / max(t["total"], 1), 1)

    llm_status = llm.status()
    return {
        "window_days": days,
        "kpis": {
            "total_interactions": total,
            "high_risk": severities["HIGH"] + severities["CRITICAL"],
            "blocked": decisions.get("BLOCK", 0),
            "flagged": decisions.get("FLAG", 0) + decisions.get("HUMAN_REVIEW", 0),
            "edited": decisions.get("EDIT", 0),
            "human_reviews": reviews,
            "pending_reviews": db.query(Interaction).filter(Interaction.review_status == "pending").count(),
        },
        "decision_distribution": decisions,
        "risk_distribution": severities,
        "risk_type_frequency": risk_freq,
        "by_application": by_application,
        "feedback": {
            "total_reviewed": reviewed,
            "true_positives": true_pos,
            "false_positives": false_pos,
            "false_positive_rate": round(100 * false_pos / reviewed, 1) if reviewed else 0.0,
            "human_override_rate": round(100 * overrides / max(total, 1), 1),
        },
        "latency": {
            "avg_ms": round(sum(latencies) / max(len(latencies), 1), 1),
            "p95_ms": _percentile(latencies, 0.95),
        },
        "cost_telemetry": {
            "mode": "Simulation mode" if llm_status["demo_mode"] else "Live",
            "llm_calls": llm_status["llm_calls"],
            "input_tokens": llm_status["input_tokens"],
            "output_tokens": llm_status["output_tokens"],
            "estimated_cost_usd": llm_status["estimated_cost_usd"],
        },
        "trend": trend_list,
    }
