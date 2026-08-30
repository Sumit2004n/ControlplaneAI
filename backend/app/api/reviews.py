from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database.models import AuditLog, Feedback, Interaction, Review, pk_from_display
from ..database.session import get_db
from ..policy.engine import BLOCK_MESSAGE
from ..schemas import ReviewRequest

router = APIRouter(prefix="/api/reviews", tags=["reviews"])


@router.get("")
def review_queue(status: str = "pending", limit: int = 100, db: Session = Depends(get_db)):
    q = db.query(Interaction)
    if status != "all":
        q = q.filter(Interaction.review_status == status)
    else:
        q = q.filter(Interaction.review_status.in_(["pending", "reviewed"]))
    items = q.order_by(Interaction.created_at.desc()).limit(limit).all()
    return {
        "items": [
            {
                "interaction_id": i.interaction_id,
                "application": i.application,
                "user_prompt": i.user_prompt,
                "ai_response": i.ai_response,
                "overall_risk": i.overall_risk,
                "decision": i.decision,
                "policy_name": i.policy_name,
                "review_status": i.review_status,
                "human_decision": i.human_decision,
                "reasons": i.reasons,
                "primary_risk": max(i.risk_results, key=lambda r: r.score).risk_type if i.risk_results else None,
                "risk_scores": {r.risk_type: r.score for r in i.risk_results},
                "timestamp": i.created_at.isoformat(),
            }
            for i in items
        ]
    }


@router.post("/{interaction_id}")
def submit_review(interaction_id: str, req: ReviewRequest, db: Session = Depends(get_db)):
    if req.decision not in ("APPROVE", "EDIT", "REJECT"):
        raise HTTPException(400, "decision must be APPROVE, EDIT or REJECT")
    try:
        pk = pk_from_display(interaction_id)
    except ValueError:
        raise HTTPException(404, "Invalid interaction id")
    i = db.get(Interaction, pk)
    if not i:
        raise HTTPException(404, "Interaction not found")

    review = Review(interaction_pk=pk, reviewer=req.reviewer, decision=req.decision,
                    edited_response=req.edited_response, label=req.label, comment=req.comment)
    db.add(review)

    original_decision = i.decision
    i.review_status = "reviewed"
    i.human_decision = req.decision
    if req.decision == "APPROVE":
        i.final_response = i.ai_response
        i.human_override = original_decision in ("FLAG", "HUMAN_REVIEW", "BLOCK")
    elif req.decision == "EDIT":
        i.final_response = req.edited_response or i.final_response
        i.human_override = True
    else:  # REJECT
        i.final_response = BLOCK_MESSAGE
        i.human_override = original_decision not in ("BLOCK",)

    label = req.label or ("FALSE_POSITIVE" if req.decision == "APPROVE" else "TRUE_POSITIVE")
    db.add(Feedback(
        interaction_pk=pk, prediction=original_decision, human_label=req.decision,
        is_false_positive=(label == "FALSE_POSITIVE"), comment=req.comment,
    ))
    db.add(AuditLog(
        interaction_pk=pk, event="HUMAN_REVIEW", actor=req.reviewer,
        meta={"original_decision": original_decision, "human_decision": req.decision,
              "label": label, "comment": req.comment or ""},
    ))
    db.commit()
    return {"ok": True, "interaction_id": interaction_id, "original_decision": original_decision,
            "human_decision": req.decision, "label": label, "human_override": i.human_override}
