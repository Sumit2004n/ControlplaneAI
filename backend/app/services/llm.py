"""LLM provider abstraction (PRD sections 41-42).

- provider "openai": any OpenAI-compatible API (base URL configurable).
- provider "mock" / DEMO_MODE=true: deterministic, offline behavior so the
  prototype can never fail during judging.

The LLM is never the sole source of quantitative truth: judges return
structured JSON that supplements deterministic detector logic (PRD sec 40).
"""
import json
import re
import time

from .. import config
from ..rag.kb import get_kb
from .scenarios import get_scenario


class Telemetry:
    """Simple runtime counters for the analytics page (PRD sec 54-55)."""

    def __init__(self) -> None:
        self.llm_calls = 0
        self.input_tokens = 0
        self.output_tokens = 0

    def record(self, usage) -> None:
        self.llm_calls += 1
        if usage is not None:
            self.input_tokens += getattr(usage, "prompt_tokens", 0) or 0
            self.output_tokens += getattr(usage, "completion_tokens", 0) or 0

    def estimated_cost_usd(self) -> float:
        # gpt-4o-mini list price approximation: $0.15 / 1M input, $0.60 / 1M output
        return round(self.input_tokens * 0.15 / 1e6 + self.output_tokens * 0.60 / 1e6, 4)


telemetry = Telemetry()
_client = None


def demo_active() -> bool:
    return config.EFFECTIVE_DEMO_MODE


def _get_client():
    global _client
    if _client is None:
        from openai import AsyncOpenAI

        kwargs = {"api_key": config.LLM_API_KEY}
        if config.LLM_BASE_URL:
            kwargs["base_url"] = config.LLM_BASE_URL
        _client = AsyncOpenAI(**kwargs)
    return _client


# ---------------------------------------------------------------- generation

def _mock_generate(prompt: str, application: str, scenario_id: str | None) -> str:
    """Deterministic response generation for demo mode."""
    scenario = get_scenario(scenario_id) if scenario_id else None
    if scenario is not None:
        return scenario["response"]

    # Ground free-text questions in the knowledge base so demo mode still
    # behaves like a real assistant.
    results = get_kb().search(prompt, k=1)
    if results:
        chunk, cosine, overlap = results[0]
        if cosine + overlap >= 0.45:
            sentences = re.split(r"(?<=[.!?])\s+", chunk.text)
            answer = " ".join(sentences[:2])
            return f"According to the {chunk.doc_name} ({chunk.section}): {answer}"
    return (
        "I could not find verified information about that in the company knowledge base, "
        "so I cannot give a confident answer."
    )


async def generate(prompt: str, application: str, history: list[dict] | None = None,
                   scenario_id: str | None = None) -> str:
    if demo_active():
        return _mock_generate(prompt, application, scenario_id)

    client = _get_client()
    messages = [{
        "role": "system",
        "content": (
            f"You are the enterprise AI assistant for the '{application}' application. "
            "Answer the user's question concisely and professionally."
        ),
    }]
    for turn in (history or [])[-8:]:
        role = turn.get("role", "user")
        messages.append({"role": "assistant" if role == "assistant" else "user",
                         "content": turn.get("content", "")})
    messages.append({"role": "user", "content": prompt})
    resp = await client.chat.completions.create(model=config.LLM_MODEL, messages=messages, temperature=0.3)
    telemetry.record(resp.usage)
    return resp.choices[0].message.content or ""


# ------------------------------------------------------------------- judging

async def judge_json(system: str, user: str) -> dict | None:
    """AI-as-judge secondary mechanism. Returns None in demo mode (callers
    fall back to deterministic logic)."""
    if demo_active():
        return None
    try:
        client = _get_client()
        resp = await client.chat.completions.create(
            model=config.LLM_MODEL,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
            temperature=0,
            response_format={"type": "json_object"},
        )
        telemetry.record(resp.usage)
        return json.loads(resp.choices[0].message.content or "{}")
    except Exception:
        return None  # fail-safe: deterministic layer still decides


def status() -> dict:
    return {
        "demo_mode": demo_active(),
        "provider": "mock" if demo_active() else config.LLM_PROVIDER,
        "model": "deterministic-mock" if demo_active() else config.LLM_MODEL,
        "llm_calls": telemetry.llm_calls,
        "input_tokens": telemetry.input_tokens,
        "output_tokens": telemetry.output_tokens,
        "estimated_cost_usd": None if demo_active() else telemetry.estimated_cost_usd(),
        "started_at": _STARTED_AT,
    }


_STARTED_AT = time.time()
