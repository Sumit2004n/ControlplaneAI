"""Demo scenario library loader (PRD sections 38-39)."""
import json
from functools import lru_cache

from ..config import SCENARIOS_FILE


@lru_cache(maxsize=1)
def load_scenarios() -> list[dict]:
    if not SCENARIOS_FILE.exists():
        return []
    data = json.loads(SCENARIOS_FILE.read_text(encoding="utf-8"))
    return data.get("scenarios", [])


def get_scenario(scenario_id: str) -> dict | None:
    for s in load_scenarios():
        if s["id"] == scenario_id:
            return s
    return None


def match_scenario_by_prompt(prompt: str) -> dict | None:
    """Fuzzy match a free-text prompt to a scripted scenario (mock provider)."""
    p = prompt.strip().lower()
    best, best_score = None, 0.0
    for s in load_scenarios():
        sp = s["prompt"].strip().lower()
        if sp == p:
            return s
        s_tokens, p_tokens = set(sp.split()), set(p.split())
        if not p_tokens:
            continue
        score = len(s_tokens & p_tokens) / max(len(s_tokens | p_tokens), 1)
        if score > best_score:
            best, best_score = s, score
    return best if best_score >= 0.6 else None
