"""Runtime configuration. Everything is env-driven so the same image runs in demo and prod."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _load_dotenv() -> None:
    env_file = ROOT / ".env"
    if not env_file.exists():
        return
    for raw in env_file.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_dotenv()


def _bool(name: str, default: bool = False) -> bool:
    return os.getenv(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


# --- LLM provider -----------------------------------------------------------
# "demo"      - no API key needed, keyword retrieval + templated answers
# "anthropic" - Claude
# "openai"    - GPT / any OpenAI-compatible endpoint (OpenRouter, DeepSeek, Ollama)
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "demo").strip().lower()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-5")
ANTHROPIC_BASE_URL = os.getenv("ANTHROPIC_BASE_URL", "https://api.anthropic.com")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")

# --- Business logic ---------------------------------------------------------
COMPANY_NAME = os.getenv("COMPANY_NAME", "Northwind Coffee Co.")
AGENT_NAME = os.getenv("AGENT_NAME", "Nora")
TOP_K = int(os.getenv("TOP_K", "4"))
HANDOFF_SCORE = int(os.getenv("HANDOFF_SCORE", "60"))  # lead_score >= this -> notify sales

# --- Integrations -----------------------------------------------------------
# Point this at your n8n Webhook node to fan out into CRM / Slack / Sheets / email.
N8N_WEBHOOK_URL = os.getenv("N8N_WEBHOOK_URL", "")
N8N_WEBHOOK_SECRET = os.getenv("N8N_WEBHOOK_SECRET", "")

# --- Infra ------------------------------------------------------------------
DB_PATH = Path(os.getenv("DB_PATH", ROOT / "data" / "app.db"))
KNOWLEDGE_DIR = Path(os.getenv("KNOWLEDGE_DIR", ROOT / "knowledge"))
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "demo-admin-token")
HOST = os.getenv("HOST", "127.0.0.1")
PORT = int(os.getenv("PORT", "8000"))
DEBUG = _bool("DEBUG", False)

# Free hosting tiers give you no persistent disk, so the database is wiped on
# every redeploy and the dashboard would greet a prospective client with zeros.
# With this on, an empty database is filled with sample traffic at startup.
SEED_ON_START = _bool("SEED_ON_START", False)

DB_PATH.parent.mkdir(parents=True, exist_ok=True)
