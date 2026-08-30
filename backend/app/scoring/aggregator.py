"""Contextual risk aggregation (PRD sections 17, 79).

Weighted scoring with a maximum-risk override so a severe individual risk is
never hidden by a low average.
"""
from ..detectors.base import RiskOutput

DEFAULT_WEIGHTS = {"privacy": 0.35, "hallucination": 0.30, "bias": 0.20, "policy": 0.15}


def aggregate(outputs: dict[str, RiskOutput], weights: dict[str, float] | None = None) -> tuple[float, float]:
    """Returns (overall_risk 0-100, overall_confidence 0-1)."""
    w = {**DEFAULT_WEIGHTS, **(weights or {})}
    total_w = sum(w.get(t, 0.0) for t in outputs) or 1.0
    weighted = sum(o.score * w.get(t, 0.0) for t, o in outputs.items()) / total_w

    top = max((o.score for o in outputs.values()), default=0.0)
    # Maximum-risk override: a single severe risk dominates the average
    if top >= 90:
        overall = max(weighted, top - 4)
    elif top >= 75:
        overall = max(weighted, top - 10)
    elif top >= 50:
        overall = max(weighted, top - 20)
    else:
        overall = weighted
    overall = round(min(100.0, max(0.0, overall)), 1)

    # Confidence: weight each detector's confidence by how much it contributes
    contrib = [(o.score + 10, o.confidence) for o in outputs.values()]
    denom = sum(c for c, _ in contrib) or 1.0
    confidence = round(sum(c * conf for c, conf in contrib) / denom, 2)
    return overall, confidence
