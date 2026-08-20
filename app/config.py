"""Runtime configuration. Everything is env-driven so the same image runs in demo and prod."""
import os
from pathlib import Path
from typing import Any

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

# --- Sites ------------------------------------------------------------------
# One engine, several knowledge bases. A site is a folder under knowledge/ plus
# an entry below. Adding a client is a folder and a dict - no new deployment,
# no forked code.
DEFAULT_SITE = os.getenv("DEFAULT_SITE", "portfolio")

OWNER_NAME = os.getenv("OWNER_NAME", "Nikita Denisov")
OWNER_EMAIL = os.getenv("OWNER_EMAIL", "hentajp5@gmail.com")

# Entries marked `vertical` also appear in the industry picker on the portfolio,
# which is rendered from this dict rather than from hand-written HTML.
#
# `pipeline` describes what actually gets wired, not a promised outcome. There
# are deliberately no percentages: I have not measured these businesses, they
# are illustrative builds, and an invented saving is the one thing that would
# make the rest of the page untrustworthy.
SITES: dict[str, dict[str, Any]] = {
    "portfolio": {
        "company": OWNER_NAME,
        "agent": "Ada",
        "label": "Portfolio assistant",
        "accent": "#A96417",
        "greeting": "I answer from Nikita's own notes: scope, pricing, timelines, "
                    "and what he turns down. What would you like to know?",
        "vertical": False,
    },
    "demo": {
        "company": os.getenv("COMPANY_NAME", "Northwind Coffee Co."),
        "agent": os.getenv("AGENT_NAME", "Nora"),
        "label": "Northwind Support",
        "accent": "#6E7F4E",
        "greeting": "Hi! I can help with orders, shipping, subscriptions and "
                    "wholesale. What do you need?",
        "vertical": True,
        "industry": "E-commerce",
        "tagline": "Specialty coffee roaster, ships direct",
        "pain": "Forty shipping and returns questions a day, and the one wholesale "
                "enquiry worth real money sits in the same inbox as the rest.",
        "pipeline": [
            "Answer shipping, returns and subscription questions from the policy docs",
            "Score every conversation; wholesale and bulk intent flags as hot",
            "Push hot leads to Slack and the CRM with the full transcript",
            "Log the rest and send a follow-up email the next day",
        ],
        "questions": [
            "How fast is shipping to Canada?",
            "What is your wholesale price for 80 lb a month?",
            "Can I pause my subscription?",
        ],
    },
    "clinic": {
        "company": "Brightwater Dental",
        "agent": "Rowan",
        "label": "Brightwater Dental",
        "accent": "#2F7D91",
        "greeting": "I can help with appointments, prices, insurance and what to "
                    "do in a dental emergency. What do you need?",
        "vertical": True,
        "industry": "Dental clinic",
        "tagline": "Five chairs, about 340 patients a month",
        "pain": "Reception answers the same price and availability questions all "
                "day, and misses calls while doing it. Every missed call is a "
                "patient who rings the practice down the road.",
        "pipeline": [
            "Answer prices, hours, insurance and emergency questions around the clock",
            "Recognise pain and urgency, and route those to the on-call slot list",
            "Capture new-patient enquiries with the details reception would ask for",
            "Send the registration form and add the follow-up to the practice CRM",
        ],
        "questions": [
            "How much is a new patient check-up?",
            "I have severe toothache, can I be seen today?",
            "Do you take Bupa insurance?",
        ],
    },
    "realty": {
        "company": "Kestrel Property",
        "agent": "Elin",
        "label": "Kestrel Property",
        "accent": "#4A6FA5",
        "greeting": "I can help with fees, valuations, viewings and lettings. "
                    "Buying, selling or renting?",
        "vertical": True,
        "industry": "Estate agency",
        "tagline": "Four negotiators, about 25 sales a month",
        "pain": "Portal enquiries arrive at all hours and go cold overnight. "
                "Negotiators spend mornings re-asking budget and position instead "
                "of booking viewings.",
        "pipeline": [
            "Answer fee, process and local market questions from the office notes",
            "Qualify buyers on budget, area, position and mortgage readiness",
            "Book the valuation or viewing straight into the diary",
            "Hand a scored, qualified lead to the right negotiator within seconds",
        ],
        "questions": [
            "What is your commission for selling a house?",
            "I want to book a free valuation",
            "What fees do tenants pay?",
        ],
    },
    "fitness": {
        "company": "Ironhouse Strength",
        "agent": "Mica",
        "label": "Ironhouse Strength",
        "accent": "#C4553A",
        "greeting": "I can help with memberships, classes, freezing and personal "
                    "training. What do you want to know?",
        "vertical": True,
        "industry": "Gym and studio",
        "tagline": "480 members, eight lifting platforms",
        "pain": "Staff are on the gym floor, not at a desk. Membership and "
                "cancellation questions pile up across three channels and get "
                "answered inconsistently.",
        "pipeline": [
            "Answer price, class, freeze and cancellation questions from one source",
            "Spot trial and corporate enquiries and treat them as leads, not FAQs",
            "Book the free intro session into the coach's calendar",
            "Flag cancellation intent to a human before the member walks",
        ],
        "questions": [
            "How much is a full membership?",
            "Can I freeze my membership while injured?",
            "Do you do corporate rates for my company?",
        ],
    },
    "garage": {
        "company": "Lockwood Auto",
        "agent": "Sam",
        "label": "Lockwood Auto",
        "accent": "#7A6A4F",
        "greeting": "I can help with servicing, MOTs, prices, warranty and "
                    "booking. What is the car doing?",
        "vertical": True,
        "industry": "Auto repair",
        "tagline": "Six ramps, eight technicians, MOT centre",
        "pain": "The phone rings while technicians are under cars. Callers want a "
                "price and a date, and the answer is on a whiteboard nobody can "
                "read from the ramp.",
        "pipeline": [
            "Quote standard servicing, MOT and diagnostics from the live price list",
            "Answer the warranty question that stops people using an independent",
            "Take the booking with registration, mileage and courtesy car need",
            "Route fleet enquiries to the manager instead of the booking queue",
        ],
        "questions": [
            "How much is a full service and MOT?",
            "Will servicing here void my manufacturer warranty?",
            "Do you have a courtesy car available?",
        ],
    },
    "legal": {
        "company": "Marsden Law",
        "agent": "Iris",
        "label": "Marsden Law",
        "accent": "#5C5470",
        "greeting": "I can explain how the firm works: fees, first consultations "
                    "and which areas we cover. I cannot give legal advice.",
        "vertical": True,
        "industry": "Law firm",
        "tagline": "Six solicitors, four practice areas",
        "pain": "Solicitors bill by the hour, so unqualified enquiries are "
                "expensive. Half the calls are matters the firm does not take, and "
                "finding that out costs twenty minutes each time.",
        "pipeline": [
            "Explain fees, fixed prices and the consultation process",
            "Screen the matter type and say plainly when the firm cannot act",
            "Collect the facts a fee earner needs before the first call",
            "Book the free consultation and start the conflict check",
        ],
        "questions": [
            "What do you charge for a will?",
            "How long do I have to bring an unfair dismissal claim?",
            "Do you handle immigration cases?",
        ],
    },
}


def verticals() -> dict[str, dict[str, Any]]:
    """Sites that appear in the industry picker, in declared order."""
    return {k: v for k, v in SITES.items() if v.get("vertical")}


def site_conf(site: str | None) -> dict[str, Any]:
    """Never raise on an unknown site - fall back rather than 500 a chat."""
    return SITES.get(site or DEFAULT_SITE, SITES[DEFAULT_SITE])


# Kept for backwards compatibility with the demo-only entry points.
COMPANY_NAME = SITES["demo"]["company"]
AGENT_NAME = SITES["demo"]["agent"]
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
