from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import config
from ..database.models import AuditLog, Document, Feedback, Interaction, pk_from_display
from ..database.session import get_db
from ..schemas import FeedbackRequest
from ..services import llm
from ..services.scenarios import load_scenarios

router = APIRouter(prefix="/api", tags=["misc"])


@router.get("/health")
def health():
    s = llm.status()
    return {"status": "ok", "controlplane": "ACTIVE", "demo_mode": s["demo_mode"],
            "provider": s["provider"], "model": s["model"]}


@router.get("/scenarios")
def scenarios():
    return {"items": load_scenarios()}


@router.get("/audit-logs")
def audit_logs(event: str | None = None, limit: int = 100, offset: int = 0,
               db: Session = Depends(get_db)):
    q = db.query(AuditLog)
    if event:
        q = q.filter(AuditLog.event == event)
    total = q.count()
    rows = q.order_by(AuditLog.created_at.desc()).offset(offset).limit(min(limit, 300)).all()
    return {"total": total, "items": [
        {"id": a.id, "event": a.event, "actor": a.actor, "meta": a.meta,
         "interaction_id": f"INT-{10000 + a.interaction_pk}" if a.interaction_pk else None,
         "timestamp": a.created_at.isoformat()} for a in rows
    ]}


@router.post("/feedback")
def submit_feedback(req: FeedbackRequest, db: Session = Depends(get_db)):
    try:
        pk = pk_from_display(req.interaction_id)
    except ValueError:
        raise HTTPException(404, "Invalid interaction id")
    if not db.get(Interaction, pk):
        raise HTTPException(404, "Interaction not found")
    db.add(Feedback(interaction_pk=pk, prediction=req.prediction, human_label=req.human_label,
                    is_false_positive=req.is_false_positive, comment=req.comment))
    db.add(AuditLog(interaction_pk=pk, event="FEEDBACK_RECORDED", actor="reviewer",
                    meta={"human_label": req.human_label, "is_false_positive": req.is_false_positive}))
    db.commit()
    return {"ok": True}


@router.get("/documents")
def documents(db: Session = Depends(get_db)):
    docs = db.query(Document).all()
    return {"items": [
        {"id": d.id, "name": d.name, "category": d.category, "version": d.version,
         "status": d.status, "last_updated": d.last_updated.isoformat()} for d in docs
    ]}


@router.get("/documents/{doc_id}")
def document(doc_id: str, db: Session = Depends(get_db)):
    d = db.get(Document, doc_id)
    if not d:
        raise HTTPException(404, "Document not found")
    return {"id": d.id, "name": d.name, "category": d.category, "version": d.version,
            "status": d.status, "last_updated": d.last_updated.isoformat(), "content": d.content}
