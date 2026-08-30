from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database.models import AuditLog, Policy
from ..database.session import get_db
from ..schemas import PolicyIn, SimulateRequest
from ..services.pipeline import run_analysis

router = APIRouter(prefix="/api/policies", tags=["policies"])


def _policy_out(p: Policy) -> dict:
    return {
        "id": p.id, "name": p.name, "application_type": p.application_type,
        "region": p.region, "industry": p.industry, "risk_profile": p.risk_profile,
        "privacy_threshold": p.privacy_threshold, "hallucination_threshold": p.hallucination_threshold,
        "bias_threshold": p.bias_threshold, "policy_threshold": p.policy_threshold,
        "low_risk_threshold": p.low_risk_threshold, "weights": p.weights,
        "high_risk_action": p.high_risk_action, "critical_action": p.critical_action,
        "edit_enabled": p.edit_enabled, "fail_safe": p.fail_safe,
        "updated_at": p.updated_at.isoformat() if p.updated_at else None,
    }


@router.get("")
def list_policies(db: Session = Depends(get_db)):
    return {"items": [_policy_out(p) for p in db.query(Policy).all()]}


@router.post("")
def create_policy(req: PolicyIn, db: Session = Depends(get_db)):
    pid = "pol-" + req.name.lower().replace(" ", "-")[:48]
    if db.get(Policy, pid):
        raise HTTPException(400, "Policy with this name already exists")
    p = Policy(id=pid, **req.model_dump())
    db.add(p)
    db.add(AuditLog(event="POLICY_CREATED", actor="governance-admin", meta={"policy_id": pid, "name": req.name}))
    db.commit()
    return _policy_out(p)


@router.put("/{policy_id}")
def update_policy(policy_id: str, req: PolicyIn, db: Session = Depends(get_db)):
    p = db.get(Policy, policy_id)
    if not p:
        raise HTTPException(404, "Policy not found")
    changes = {}
    for field, value in req.model_dump().items():
        if getattr(p, field) != value:
            changes[field] = {"from": getattr(p, field), "to": value}
            setattr(p, field, value)
    db.add(AuditLog(event="POLICY_UPDATED", actor="governance-admin",
                    meta={"policy_id": policy_id, "changes": changes}))
    db.commit()
    return _policy_out(p)


@router.post("/simulate")
async def simulate(req: SimulateRequest, db: Session = Depends(get_db)):
    """What-if Policy Simulator (PRD sec 34): same AI response evaluated
    under multiple policies, decisions compared side by side. Nothing persists."""
    policies = db.query(Policy).all()
    if req.policy_ids:
        policies = [p for p in policies if p.id in req.policy_ids]
    results = []
    for p in policies:
        analysis = await run_analysis(
            db, application=p.application_type, prompt=req.prompt, response=req.response,
            policy_id=p.id, persist=False,
        )
        results.append({
            "policy": _policy_out(p),
            "overall_risk": analysis["overall_risk"],
            "decision": analysis["decision"],
            "reasons": analysis["reasons"],
            "risks": {k: v["score"] for k, v in analysis["risks"].items()},
        })
    return {"prompt": req.prompt, "response": req.response, "results": results}
