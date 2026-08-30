import pytest

from app.detectors.base import DetectionContext
from app.detectors.hallucination import HallucinationDetector, extract_claims


def _ctx(response: str, application: str = "employee_copilot") -> DetectionContext:
    return DetectionContext(prompt="", response=response, application=application)


def test_claim_extraction_finds_factual_sentences():
    claims = extract_claims("Employees receive 45 annual leaves every year. Thank you!")
    assert len(claims) == 1
    assert "45" in claims[0]


@pytest.mark.asyncio
async def test_supported_claim_low_risk():
    out = await HallucinationDetector().analyze(
        _ctx("Employees receive 20 annual leave days per calendar year."))
    assert out.status == "SUPPORTED"
    assert out.score < 25


@pytest.mark.asyncio
async def test_contradicted_claim_high_risk():
    out = await HallucinationDetector().analyze(
        _ctx("Employees receive 45 annual leaves every year."))
    assert out.status == "CONTRADICTED"
    assert out.score >= 75
    assert any(ev["status"] == "CONTRADICTED" for ev in out.evidence)


@pytest.mark.asyncio
async def test_no_evidence_returns_uncertainty():
    out = await HallucinationDetector().analyze(
        _ctx("The company emitted approximately 4200 tonnes of carbon dioxide in Q2."))
    assert out.status in ("UNVERIFIABLE", "UNSUPPORTED")
    assert out.confidence <= 0.5
