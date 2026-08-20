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
    "agency": {
        "company": "Halyard Digital",
        "agent": "Wren",
        "label": "Halyard Digital",
        "accent": "#3E6B8C",
        "greeting": "I can cover retainers, pricing, onboarding, reporting and "
                    "who we are a bad fit for. What are you looking at?",
        "vertical": True,
        "industry": "Marketing agency",
        "tagline": "Eleven people, roster capped at eighteen clients",
        "pain": "Inbound enquiries arrive from four channels and half of them are "
                "brands too small for the retainer. Founders spend discovery calls "
                "discovering the budget does not exist.",
        "pipeline": [
            "Answer scope, retainer and minimum-spend questions before a call is booked",
            "Qualify on ad spend, channels and timeline, and say so when it is too small",
            "Book the discovery call straight into the strategist's calendar",
            "Push the brief and the qualifying answers into the CRM with the transcript",
        ],
        "questions": [
            "How much do you charge to manage Google Ads?",
            "Is there a minimum contract length?",
            "Can you guarantee a specific ROAS?",
        ],
    },
    "saas": {
        "company": "Latchkey",
        "agent": "Juno",
        "label": "Latchkey Support",
        "accent": "#4C6EA8",
        "greeting": "I can help with plans, the trial, integrations, security and "
                    "migration. What do you need to know?",
        "vertical": True,
        "industry": "B2B SaaS",
        "tagline": "Field service scheduling, 1,400 companies",
        "pain": "Support answers the same twelve pricing and integration questions "
                "all day, while the enterprise security questionnaire that would "
                "close a five-figure deal waits three days in the same queue.",
        "pipeline": [
            "Deflect plan, trial, integration and cancellation questions from the docs",
            "Spot enterprise signals - SSO, SOC 2, procurement, seat counts - and escalate",
            "Route security questionnaires to the security inbox, not to support",
            "Nudge trials that have stalled and hand warm ones to sales with context",
        ],
        "questions": [
            "How much is the Growth plan per user?",
            "Are you SOC 2 compliant and where is data hosted?",
            "Can I cancel any time?",
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
        "industry": "Real estate",
        "tagline": "Four negotiators, about 25 sales a month",
        "pain": "Portal enquiries arrive at all hours and go cold overnight. "
                "Negotiators spend mornings re-asking budget and position instead "
                "of booking viewings.",
        "pipeline": [
            "Answer commission, process and local market questions from the office notes",
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
    "coaching": {
        "company": "Northlight Coaching",
        "agent": "Tess",
        "label": "Northlight Coaching",
        "accent": "#8A5A7A",
        "greeting": "I can explain the programmes, prices, payment plans and "
                    "whether this is the right fit. What are you weighing up?",
        "vertical": True,
        "industry": "Coaching and courses",
        "tagline": "Two coaches, about 40 clients a year",
        "pain": "Most enquiries are people deciding whether the programme is for "
                "them at all. Answering that well takes a real conversation, and "
                "there are only two coaches to have them.",
        "pipeline": [
            "Answer programme, price, payment plan and refund questions in full",
            "Help someone self-select in or out before they book a call",
            "Book the free discovery call and send the pre-call questions",
            "Hold waitlist enquiries for the next cohort and follow up when it opens",
        ],
        "questions": [
            "How much is the group programme?",
            "Do you offer payment plans?",
            "Is this right for me if I was promoted last month?",
        ],
    },
    "recruiting": {
        "company": "Havenridge Talent",
        "agent": "Kit",
        "label": "Havenridge Talent",
        "accent": "#4F7A63",
        "greeting": "I can cover fees, the replacement guarantee, how the process "
                    "runs, and what happens if you are applying. Hiring or looking?",
        "vertical": True,
        "industry": "Recruiting agency",
        "tagline": "Seven consultants, 143 placements last year",
        "pain": "Two audiences in one inbox. Hiring managers want fees and "
                "timelines; candidates want a reply. Consultants answer both by "
                "hand and the candidates are the ones who wait.",
        "pipeline": [
            "Answer fee, guarantee and process questions for hiring companies",
            "Reply to every candidate the same day, including the rejections",
            "Split the two audiences and route each to the right consultant",
            "Take the role brief and open it in the ATS with the salary band attached",
        ],
        "questions": [
            "What is your fee for a permanent placement?",
            "What happens if the hire leaves after a month?",
            "Do you charge candidates anything?",
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
