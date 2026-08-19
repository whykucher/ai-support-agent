"""FastAPI service: chat widget backend + lead capture + admin API.

Run:  python -m uvicorn app.main:app --reload
"""
import time
import uuid
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import config, db, leads, llm, rag

@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    db.init()
    if db.chunk_stats()["n"] == 0:
        ingested = rag.ingest_directory()
        print(f"[startup] indexed {sum(ingested.values())} chunks "
              f"from {len(ingested)} file(s)")
    if config.SEED_ON_START and db.metrics()["conversations"] == 0:
        from scripts.seed_demo import seed  # only needed on ephemeral hosts
        print(f"[startup] seeded demo traffic: {seed()} lead(s)")
    print(f"[startup] provider={config.LLM_PROVIDER} company={config.COMPANY_NAME}")
    yield


app = FastAPI(
    title="AI Support & Lead Agent",
    version="1.0.0",
    description="RAG support bot with lead scoring and n8n hand-off.",
    lifespan=lifespan,
)

# The widget is embedded on the customer's own domain, so the chat endpoints are
# public by design. Lock this list down to the client's domains in production.
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


class LeadIn(BaseModel):
    conversation_id: str
    name: str = Field(default="", max_length=120)
    email: str = Field(default="", max_length=200)
    phone: str = Field(default="", max_length=40)
    message: str = Field(default="", max_length=2000)
    page_url: str = ""


# --- rate limiting ----------------------------------------------------------

_hits: dict[str, deque[float]] = defaultdict(deque)
RATE_LIMIT, RATE_WINDOW = 20, 60.0


def rate_limit(request: Request) -> None:
    key = request.client.host if request.client else "unknown"
    now = time.time()
    bucket = _hits[key]
    while bucket and now - bucket[0] > RATE_WINDOW:
        bucket.popleft()
    if len(bucket) >= RATE_LIMIT:
        raise HTTPException(429, "Too many messages, slow down a moment.")
    bucket.append(now)


def require_admin(x_admin_token: str = Header(default="")) -> None:
    if x_admin_token != config.ADMIN_TOKEN:
        raise HTTPException(401, "Invalid admin token")


# --- public API -------------------------------------------------------------

@app.get("/api/health")
def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "provider": config.LLM_PROVIDER,
        "company": config.COMPANY_NAME,
        "agent": config.AGENT_NAME,
        "knowledge": db.chunk_stats(),
        "n8n_configured": bool(config.N8N_WEBHOOK_URL),
    }


@app.post("/api/chat", dependencies=[Depends(rate_limit)])
def chat(payload: ChatIn) -> dict[str, Any]:
    started = time.perf_counter()
    conv_id = payload.conversation_id or uuid.uuid4().hex[:16]
    db.touch_conversation(conv_id, payload.page_url)

    history = db.history(conv_id, limit=8)
    db.add_message(conv_id, "user", payload.message)

    chunks = rag.search(payload.message)
    context = rag.build_context(chunks)
    result = llm.answer(payload.message, chunks, context, history)

    latency_ms = int((time.perf_counter() - started) * 1000)
    # Rank order, deduped - these become the "where this came from" chips in the
    # widget, so the most relevant section has to be the one shown first.
    sources: list[str] = []
    for c in chunks:
        label = c["heading"] or c["source"].rsplit(".", 1)[0]
        if label not in sources:
            sources.append(label)
    db.add_message(conv_id, "assistant", result["answer"], intent=result["intent"],
                   sources=sources, latency_ms=latency_ms)
    db.set_lead_score(conv_id, result["lead_score"], result["handoff"])

    # A contact typed straight into the chat is a lead, no form required.
    found = leads.extract_contacts(payload.message)
    captured = None
    if found["email"] or found["phone"]:
        captured = leads.capture(
            conv_id, email=found["email"], phone=found["phone"],
            message=payload.message, intent=result["intent"],
            lead_score=max(result["lead_score"], config.HANDOFF_SCORE),
            source_page=payload.page_url,
        )

    return {
        "conversation_id": conv_id,
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
    db.touch_conversation(payload.conversation_id, payload.page_url)
    return leads.capture(
        payload.conversation_id,
        name=payload.name, email=payload.email, phone=payload.phone,
        message=payload.message, intent="form",
        lead_score=max(config.HANDOFF_SCORE, 70),
        source_page=payload.page_url,
    )


# --- admin API --------------------------------------------------------------

@app.get("/api/metrics", dependencies=[Depends(require_admin)])
def metrics() -> dict[str, Any]:
    return db.metrics()


@app.get("/api/leads", dependencies=[Depends(require_admin)])
def list_leads(limit: int = 50) -> dict[str, Any]:
    return {"leads": db.recent_leads(min(limit, 200))}


@app.get("/api/conversations/{conv_id}", dependencies=[Depends(require_admin)])
def transcript(conv_id: str) -> dict[str, Any]:
    return {"conversation_id": conv_id, "messages": db.history(conv_id, limit=100)}


@app.post("/api/reindex", dependencies=[Depends(require_admin)])
def reindex() -> dict[str, Any]:
    return {"indexed": rag.ingest_directory()}


@app.post("/api/leads/retry", dependencies=[Depends(require_admin)])
def retry() -> dict[str, Any]:
    return {"resent": leads.retry_undelivered()}


# --- demo site --------------------------------------------------------------

WEB = config.ROOT / "web"
app.mount("/static", StaticFiles(directory=WEB), name="static")


@app.get("/")
def storefront() -> FileResponse:
    return FileResponse(WEB / "index.html")


@app.get("/admin")
def admin() -> FileResponse:
    return FileResponse(WEB / "admin.html")


@app.exception_handler(HTTPException)
def http_error(_: Request, exc: HTTPException) -> JSONResponse:
    return JSONResponse({"error": exc.detail}, status_code=exc.status_code)
