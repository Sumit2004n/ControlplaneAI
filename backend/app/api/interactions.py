from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database.models import AuditLog, Interaction, pk_from_display
from ..database.session import get_db
from ..schemas import AnalyzeRequest, GenerateAnalyzeRequest
from ..services.pipeline import run_analysis

router = APIRouter(prefix="/api/interactions", tags=["interactions"])


@router.post("/analyze")
async def analyze(req: AnalyzeRequest, db: Session = Depends(get_db)):
    return await run_analysis(
        db,
        application=req.application,
        prompt=req.prompt,
        response=req.response,
        history=[t.model_dump() for t in req.conversation_history],
        conversation_id=req.conversation_id,
        region=req.region,
        policy_id=req.policy_id,
        scenario_id=req.scenario_id,
    )


@router.post("/generate-and-analyze")
async def generate_and_analyze(req: GenerateAnalyzeRequest, db: Session = Depends(get_db)):
    return await run_analysis(
        db,
        application=req.application,
        prompt=req.prompt,
        response=None,
        history=[t.model_dump() for t in req.conversation_history],
        conversation_id=req.conversation_id,
        region=req.region,
        policy_id=req.policy_id,
        scenario_id=req.scenario_id,
    )


def _summary(i: Interaction) -> dict:
    return {
        "interaction_id": i.interaction_id,
        "application": i.application,
        "region": i.region,
        "user_prompt": i.user_prompt,
        "decision": i.decision,
        "overall_risk": i.overall_risk,
        "overall_confidence": i.overall_confidence,
        "policy_name": i.policy_name,
        "review_status": i.review_status,
        "human_decision": i.human_decision,
        "human_override": i.human_override,
        "latency_ms": i.latency_ms,
        "timestamp": i.created_at.isoformat(),
        "primary_risk": max(i.risk_results, key=lambda r: r.score).risk_type if i.risk_results else None,
        "risk_scores": {r.risk_type: r.score for r in i.risk_results},
    }


@router.get("")
def list_interactions(
    application: str | None = None,
    decision: str | None = None,
    review_status: str | None = None,
    min_risk: float | None = None,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    q = db.query(Interaction)
    if application:
        q = q.filter(Interaction.application == application)
    if decision:
        q = q.filter(Interaction.decision == decision)
    if review_status:
        q = q.filter(Interaction.review_status == review_status)
    if min_risk is not None:
        q = q.filter(Interaction.overall_risk >= min_risk)
    total = q.count()
    items = q.order_by(Interaction.created_at.desc()).offset(offset).limit(min(limit, 200)).all()
    return {"total": total, "items": [_summary(i) for i in items]}


@router.get("/{interaction_id}")
def get_interaction(interaction_id: str, db: Session = Depends(get_db)):
    try:
        pk = pk_from_display(interaction_id)
    except ValueError:
        raise HTTPException(404, "Invalid interaction id")
    i = db.get(Interaction, pk)
    if not i:
        raise HTTPException(404, "Interaction not found")
    audit = db.query(AuditLog).filter(AuditLog.interaction_pk == pk).order_by(AuditLog.created_at).all()
    return {
        **_summary(i),
        "ai_response": i.ai_response,
        "final_response": i.final_response,
        "conversation_id": i.conversation_id,
        "reasons": i.reasons,
        "policy_id": i.policy_id,
        "latency_breakdown": i.latency_breakdown,
        "source": i.source,
        "scenario_id": i.scenario_id,
        "risks": {
            r.risk_type: {
                "risk_type": r.risk_type, "score": r.score, "confidence": r.confidence,
                "severity": r.severity, "status": r.status, "reasons": r.reasons,
                "evidence": r.evidence, "latency_ms": r.latency_ms,
            } for r in i.risk_results
        },
        "reviews": [
            {"id": rv.id, "reviewer": rv.reviewer, "decision": rv.decision, "label": rv.label,
             "comment": rv.comment, "edited_response": rv.edited_response,
             "timestamp": rv.created_at.isoformat()} for rv in i.reviews
        ],
        "audit_trail": [
            {"event": a.event, "actor": a.actor, "meta": a.meta, "timestamp": a.created_at.isoformat()}
            for a in audit
        ],
    }
