"""Central configuration. All values come from environment / backend/.env."""
import os
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parent.parent   # backend/
ROOT_DIR = BACKEND_DIR.parent                           # repo root
DATA_DIR = ROOT_DIR / "data"
KNOWLEDGE_BASE_DIR = DATA_DIR / "knowledge_base"
SCENARIOS_FILE = DATA_DIR / "demo_scenarios" / "scenarios.json"

load_dotenv(BACKEND_DIR / ".env")


def _bool(value: str | None, default: bool) -> bool:
    if value is None or value.strip() == "":
        return default
    return value.strip().lower() in ("1", "true", "yes", "on")


DEMO_MODE = _bool(os.getenv("DEMO_MODE"), True)
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai").strip().lower()
LLM_API_KEY = os.getenv("LLM_API_KEY", "").strip()
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini").strip()
LLM_EMBEDDING_MODEL = os.getenv("LLM_EMBEDDING_MODEL", "text-embedding-3-small").strip()
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "").strip() or None

DATABASE_URL = os.getenv("DATABASE_URL", "").strip() or f"sqlite:///{(BACKEND_DIR / 'controlplane.db').as_posix()}"

CORS_ORIGINS = [o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",") if o.strip()]

# Demo mode is forced when no API key is configured, so the prototype can never
# fail during judging because of a missing key / network outage (PRD sec 42).
LLM_AVAILABLE = LLM_PROVIDER == "openai" and bool(LLM_API_KEY)
EFFECTIVE_DEMO_MODE = DEMO_MODE or not LLM_AVAILABLE
