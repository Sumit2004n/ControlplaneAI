from types import SimpleNamespace

from app.detectors.base import RiskOutput
from app.policy.engine import decide
from app.scoring.aggregator import aggregate


def make_policy(**overrides):
    base = dict(
        id="pol-test", name="Test Policy", risk_profile="BALANCED",
        privacy_threshold=70, hallucination_threshold=75, bias_threshold=70,
        policy_threshold=65, low_risk_threshold=25,
        high_risk_action="FLAG", critical_action="BLOCK",
        edit_enabled=False, fail_safe="FLAG", weights=None,
    )
    base.update(overrides)
    return SimpleNamespace(**base)


def outputs(privacy=0, hallucination=0, bias=0, policy=0, **kw):
    return {
        "privacy": RiskOutput(risk_type="privacy", score=privacy, confidence=0.9),
        "hallucination": RiskOutput(risk_type="hallucination", score=hallucination, confidence=0.8,
                                    status=kw.get("hall_status", "OK")),
        "bias": RiskOutput(risk_type="bias", score=bias, confidence=0.8),
        "policy": RiskOutput(risk_type="policy", score=policy, confidence=0.9),
    }


def run(outs, policy, response="Sample response."):
    overall, conf = aggregate(outs, None)
    return decide(outs, overall, conf, policy, policy.name, response)


def test_low_risk_allows():
    d = run(outputs(privacy=5, hallucination=8), make_policy())
    assert d.decision == "ALLOW"


def test_medium_risk_flags():
    d = run(outputs(hallucination=62), make_policy(hallucination_threshold=55))
    assert d.decision == "FLAG"


def test_critical_pii_blocks():
    d = run(outputs(privacy=97), make_policy())
    assert d.decision == "BLOCK"


def test_same_output_different_policy_different_decision():
    outs = outputs(bias=68)
    balanced = run(outs, make_policy(bias_threshold=70))
    strict = run(outputs(bias=68), make_policy(bias_threshold=35, risk_profile="VERY_STRICT",
                                               high_risk_action="HUMAN_REVIEW"))
    assert balanced.decision != strict.decision
    assert strict.decision in ("HUMAN_REVIEW", "BLOCK")


def test_abstention_on_unverifiable_low_confidence():
    outs = outputs(hallucination=55, hall_status="UNVERIFIABLE")
    outs["hallucination"].confidence = 0.2
    d = run(outs, make_policy(hallucination_threshold=75))
    assert d.abstained is True
    assert d.decision in ("FLAG", "HUMAN_REVIEW")


def test_edit_downgrade_for_redactable_privacy():
    outs = outputs(privacy=88)
    d = run(outs, make_policy(edit_enabled=True, privacy_threshold=70),
            response="Her phone number is 9876543210.")
    assert d.decision == "EDIT"
    assert "9876543210" not in d.final_response


def test_detector_failure_fail_safe():
    outs = outputs()
    outs["hallucination"].error = True
    d = run(outs, make_policy(fail_safe="FLAG"))
    assert d.decision == "FLAG"
