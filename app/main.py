"""FastAPI service behind four surfaces.

    /        portfolio - the freelancer's own site, with its own live assistant
    /lab     working demonstrations: scrape, classify, clean
    /demo    the client-facing storefront the agent was built for
    /admin   operations dashboard across both sites

One engine, two knowledge bases, one run log. Run with:

    python -m uvicorn app.main:app --reload
"""
import time
import uuid
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator

import httpx
from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import config, db, lab, leads, llm, rag, sites


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    db.init()
    if db.chunk_stats()["n"] == 0:
        ingested = rag.ingest_directory()
        print(f"[startup] indexed {sum(ingested.values())} chunks "
              f"across {len(ingested)} file(s): {', '.join(ingested)}")
    if config.SEED_ON_START and db.metrics()["conversations"] == 0:
        from scripts.seed_demo import seed  # only needed on ephemeral hosts
        print(f"[startup] seeded demo traffic: {seed()} lead(s)")
    print(f"[startup] provider={config.LLM_PROVIDER} sites={', '.join(config.SITES)}")
    yield


app = FastAPI(
    title="AI Support & Lead Agent",
    version="2.0.0",
    description="RAG agents, lead scoring and n8n hand-off, with a working demo lab.",
    lifespan=lifespan,
)

# The widget is embedded on customer domains, so the chat endpoints are public
# by design. Lock this list down to the client's domains in production.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


# --- request models ---------------------------------------------------------

class ChatIn(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    conversation_id: str | None = None
    page_url: str = ""
    site: str = config.DEFAULT_SITE


class LeadIn(BaseModel):
    conversation_id: str
    name: str = Field(default="", max_length=120)
    email: str = Field(default="", max_length=200)
    phone: str = Field(default="", max_length=40)
    message: str = Field(default="", max_length=2000)
    page_url: str = ""
    site: str = config.DEFAULT_SITE


class ScrapeIn(BaseModel):
    url: str = Field(min_length=4, max_length=500)


class ClassifyIn(BaseModel):
    text: str = Field(min_length=1, max_length=4000)


class CleanIn(BaseModel):
    csv: str = Field(min_length=1, max_length=200_000)


# --- rate limiting ----------------------------------------------------------

_hits: dict[str, deque[float]] = defaultdict(deque)
RATE_LIMIT, RATE_WINDOW = 20, 60.0
# Fetching a remote page costs far more than answering from SQLite.
LAB_LIMIT, LAB_WINDOW = 8, 60.0


def _bucket(key: str, limit: int, window: float) -> None:
    now = time.time()
    q = _hits[key]
    while q and now - q[0] > window:
        q.popleft()
    if len(q) >= limit:
        raise HTTPException(429, "Too many requests, give it a minute.")
    q.append(now)


def rate_limit(request: Request) -> None:
    _bucket(request.client.host if request.client else "unknown", RATE_LIMIT, RATE_WINDOW)


def lab_limit(request: Request) -> None:
    host = request.client.host if request.client else "unknown"
    _bucket(f"lab:{host}", LAB_LIMIT, LAB_WINDOW)


def _clip(text: str, limit: int) -> str:
    """Trim on a word boundary - a log line ending mid-word looks broken."""
    text = " ".join(text.split())
    if len(text) <= limit:
        return text
    return text[:limit].rsplit(" ", 1)[0] + "…"


def require_admin(x_admin_token: str = Header(default="")) -> None:
    if x_admin_token != config.ADMIN_TOKEN:
        raise HTTPException(401, "Invalid admin token")


# --- public API -------------------------------------------------------------

@app.get("/api/health")
def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "provider": config.LLM_PROVIDER,
        "sites": {
            name: {**conf, "knowledge": db.chunk_stats(name)}
            for name, conf in config.SITES.items()
        },
        "knowledge": db.chunk_stats(),
        "n8n_configured": bool(config.N8N_WEBHOOK_URL),
    }


@app.post("/api/chat", dependencies=[Depends(rate_limit)])
def chat(payload: ChatIn) -> dict[str, Any]:
    started = time.perf_counter()
    site = payload.site if payload.site in config.SITES else config.DEFAULT_SITE
    conv_id = payload.conversation_id or uuid.uuid4().hex[:16]
    db.touch_conversation(conv_id, site, payload.page_url)

    history = db.history(conv_id, limit=8)
    db.add_message(conv_id, "user", payload.message)

    chunks = rag.search(payload.message, site)
    context = rag.build_context(chunks)
    result = llm.answer(payload.message, chunks, context, history, site)

    latency_ms = int((time.perf_counter() - started) * 1000)
    # Rank order, deduped - these become the "where this came from" chips.
    sources: list[str] = []
    for c in chunks:
        label = c["heading"] or c["source"].rsplit(".", 1)[0]
        if label not in sources:
            sources.append(label)

    db.add_message(conv_id, "assistant", result["answer"], intent=result["intent"],
                   sources=sources, latency_ms=latency_ms)
    db.set_lead_score(conv_id, result["lead_score"], result["handoff"])
    db.add_run("chat.answer", site=site, summary=_clip(result["answer"], 110),
               detail={"intent": result["intent"], "score": result["lead_score"],
                       "sources": sources[:3], "model": result.get("model", "")},
               duration_ms=latency_ms)

    # A contact typed straight into the chat is a lead, no form required.
    found = leads.extract_contacts(payload.message)
    captured = None
    if found["email"] or found["phone"]:
        captured = leads.capture(
            conv_id, site=site, email=found["email"], phone=found["phone"],
            message=payload.message, intent=result["intent"],
            lead_score=max(result["lead_score"], config.HANDOFF_SCORE),
            source_page=payload.page_url,
        )

    return {
        "conversation_id": conv_id,
        "site": site,
        "answer": result["answer"],
        "intent": result["intent"],
        "lead_score": result["lead_score"],
        "handoff": result["handoff"],
        "show_lead_form": bool(
            result.get("ask_for_contact")
            or result["handoff"]
            or result["lead_score"] >= config.HANDOFF_SCORE
        ) and not captured,
        "sources": sources,
        "latency_ms": latency_ms,
        "model": result.get("model", config.LLM_PROVIDER),
        "lead": captured,
    }


@app.post("/api/lead", dependencies=[Depends(rate_limit)])
def submit_lead(payload: LeadIn) -> dict[str, Any]:
    if not payload.email and not payload.phone:
        raise HTTPException(422, "Provide an email or a phone number")
    site = payload.site if payload.site in config.SITES else config.DEFAULT_SITE
    db.touch_conversation(payload.conversation_id, site, payload.page_url)
    return leads.capture(
        payload.conversation_id, site=site,
        name=payload.name, email=payload.email, phone=payload.phone,
        message=payload.message, intent="form",
        lead_score=max(config.HANDOFF_SCORE, 70),
        source_page=payload.page_url,
    )


@app.get("/api/site/{site}")
def site_payload(site: str) -> dict[str, Any]:
    """Brand, theme and copy for one demo business, plus its assistant config.

    The business pages are rendered from this rather than hand-written, so a new
    demo is a knowledge folder, a config entry and a content dict - never a new
    HTML file to keep in sync with five others."""
    page = sites.page(site)
    if page is None or site not in config.SITES:
        raise HTTPException(404, "No such business")
    conf = config.SITES[site]
    return {
        "site": site,
        "home": "/",
        "owner": config.OWNER_NAME,
        "page": page,
        "fonts": sites.FONTS,
        "assistant": {
            "label": conf["label"],
            "agent": conf["agent"],
            "greeting": conf["greeting"],
            "questions": conf.get("questions", []),
            "company": conf["company"],
        },
        "knowledge": db.chunk_stats(site),
    }


@app.get("/api/runs")
def runs(limit: int = 20, site: str | None = None) -> dict[str, Any]:
    """Public: the activity feed on the portfolio reads this. It is a ledger of
    what the app actually did, which is why it is safe to show visitors."""
    return {"runs": db.recent_runs(min(limit, 50), site), "counts": db.run_counts()}


# --- the lab: working demonstrations ----------------------------------------

@app.post("/api/lab/scrape", dependencies=[Depends(lab_limit)])
def lab_scrape(payload: ScrapeIn) -> dict[str, Any]:
    try:
        return lab.scrape(payload.url)
    except lab.UnsafeURL as exc:
        raise HTTPException(400, str(exc)) from exc
    except httpx.HTTPError as exc:
        raise HTTPException(502, f"Could not fetch that page: {type(exc).__name__}") from exc


@app.post("/api/lab/classify", dependencies=[Depends(lab_limit)])
def lab_classify(payload: ClassifyIn) -> dict[str, Any]:
    return lab.classify(payload.text)


@app.post("/api/lab/clean", dependencies=[Depends(lab_limit)])
def lab_clean(payload: CleanIn) -> dict[str, Any]:
    try:
        return lab.clean_csv(payload.csv)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


# --- admin API --------------------------------------------------------------

@app.get("/api/metrics", dependencies=[Depends(require_admin)])
def metrics(site: str | None = None) -> dict[str, Any]:
    return {
        "all": db.metrics(),
        "by_site": {name: db.metrics(name) for name in config.SITES},
        "runs": db.run_counts(),
        "focus": db.metrics(site) if site else None,
    }


@app.get("/api/leads", dependencies=[Depends(require_admin)])
def list_leads(limit: int = 50, site: str | None = None) -> dict[str, Any]:
    return {"leads": db.recent_leads(min(limit, 200), site)}


@app.get("/api/knowledge", dependencies=[Depends(require_admin)])
def knowledge() -> dict[str, Any]:
    return {"sections": db.knowledge_index(), "sites": db.sites()}


@app.get("/api/conversations/{conv_id}", dependencies=[Depends(require_admin)])
def transcript(conv_id: str) -> dict[str, Any]:
    return {"conversation_id": conv_id, "messages": db.history(conv_id, limit=100)}


@app.post("/api/reindex", dependencies=[Depends(require_admin)])
def reindex() -> dict[str, Any]:
    started = time.perf_counter()
    indexed = rag.ingest_directory()
    ms = int((time.perf_counter() - started) * 1000)
    db.add_run("knowledge.reindex", site="portfolio",
               summary=f"Reindexed {sum(indexed.values())} sections",
               detail=indexed, duration_ms=ms)
    return {"indexed": indexed, "duration_ms": ms}


@app.post("/api/leads/retry", dependencies=[Depends(require_admin)])
def retry() -> dict[str, Any]:
    sent = leads.retry_undelivered()
    db.add_run("lead.retry", site="portfolio", summary=f"Replayed {sent} lead(s)")
    return {"resent": sent}


# --- pages ------------------------------------------------------------------

WEB = config.ROOT / "web"
app.mount("/static", StaticFiles(directory=WEB), name="static")


def _page(name: str) -> FileResponse:
    return FileResponse(WEB / name)


@app.get("/")
def portfolio() -> FileResponse:
    return _page("portfolio.html")


@app.get("/lab")
def lab_page() -> FileResponse:
    return _page("lab.html")


@app.get("/demo")
def storefront() -> FileResponse:
    return _page("index.html")


@app.get("/b/{site}")
def business(site: str) -> FileResponse:
    """One template, themed per business at runtime."""
    if not sites.has_page(site):
        raise HTTPException(404, "No such business")
    return _page("business.html")


@app.get("/admin")
def admin() -> FileResponse:
    return _page("admin.html")


@app.exception_handler(HTTPException)
def http_error(_: Request, exc: HTTPException) -> JSONResponse:
    return JSONResponse({"error": exc.detail}, status_code=exc.status_code)
