"""SQLite storage: knowledge chunks (with vectors), conversations, messages, leads.

One file, no external services - deliberate. A support bot for an SMB handles a
few thousand chunks; a dedicated vector DB would be operational cost without a
payoff. Swapping in pgvector/Qdrant later only touches rag.search().
"""
import json
import sqlite3
import time
from contextlib import contextmanager
from typing import Any, Iterator

from . import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS chunks (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    source      TEXT    NOT NULL,
    heading     TEXT    NOT NULL DEFAULT '',
    content     TEXT    NOT NULL,
    tokens      INTEGER NOT NULL DEFAULT 0,
    embedding   TEXT,
    created_at  REAL    NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_chunks_source ON chunks(source);

CREATE TABLE IF NOT EXISTS conversations (
    id          TEXT    PRIMARY KEY,
    started_at  REAL    NOT NULL,
    last_seen   REAL    NOT NULL,
    page_url    TEXT    NOT NULL DEFAULT '',
    lead_score  INTEGER NOT NULL DEFAULT 0,
    handed_off  INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS messages (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id TEXT    NOT NULL,
    role            TEXT    NOT NULL,
    content         TEXT    NOT NULL,
    intent          TEXT    NOT NULL DEFAULT '',
    sources         TEXT    NOT NULL DEFAULT '[]',
    latency_ms      INTEGER NOT NULL DEFAULT 0,
    created_at      REAL    NOT NULL,
    FOREIGN KEY (conversation_id) REFERENCES conversations(id)
);
CREATE INDEX IF NOT EXISTS idx_messages_conv ON messages(conversation_id);

CREATE TABLE IF NOT EXISTS leads (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id TEXT    NOT NULL,
    name            TEXT    NOT NULL DEFAULT '',
    email           TEXT    NOT NULL DEFAULT '',
    phone           TEXT    NOT NULL DEFAULT '',
    message         TEXT    NOT NULL DEFAULT '',
    intent          TEXT    NOT NULL DEFAULT '',
    lead_score      INTEGER NOT NULL DEFAULT 0,
    source_page     TEXT    NOT NULL DEFAULT '',
    delivered       INTEGER NOT NULL DEFAULT 0,
    delivery_error  TEXT    NOT NULL DEFAULT '',
    created_at      REAL    NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_leads_created ON leads(created_at DESC);
"""


@contextmanager
def connect() -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(config.DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init() -> None:
    with connect() as conn:
        conn.executescript(SCHEMA)


# --- knowledge base ---------------------------------------------------------

def replace_chunks(source: str, rows: list[dict[str, Any]]) -> int:
    """Re-ingest one source file atomically."""
    now = time.time()
    with connect() as conn:
        conn.execute("DELETE FROM chunks WHERE source = ?", (source,))
        conn.executemany(
            "INSERT INTO chunks (source, heading, content, tokens, embedding, created_at)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            [
                (
                    source,
                    r.get("heading", ""),
                    r["content"],
                    r.get("tokens", 0),
                    json.dumps(r["embedding"]) if r.get("embedding") else None,
                    now,
                )
                for r in rows
            ],
        )
    return len(rows)


def all_chunks() -> list[sqlite3.Row]:
    with connect() as conn:
        return conn.execute(
            "SELECT id, source, heading, content, embedding FROM chunks"
        ).fetchall()


def chunk_stats() -> dict[str, Any]:
    with connect() as conn:
        row = conn.execute(
            "SELECT COUNT(*) AS n, COUNT(embedding) AS vectorised,"
            " COUNT(DISTINCT source) AS sources FROM chunks"
        ).fetchone()
    return dict(row)


# --- conversations ----------------------------------------------------------

def touch_conversation(conv_id: str, page_url: str = "") -> None:
    now = time.time()
    with connect() as conn:
        conn.execute(
            "INSERT INTO conversations (id, started_at, last_seen, page_url)"
            " VALUES (?, ?, ?, ?)"
            " ON CONFLICT(id) DO UPDATE SET last_seen = excluded.last_seen",
            (conv_id, now, now, page_url),
        )


def add_message(conv_id: str, role: str, content: str, *, intent: str = "",
                sources: list[str] | None = None, latency_ms: int = 0) -> None:
    with connect() as conn:
        conn.execute(
            "INSERT INTO messages (conversation_id, role, content, intent, sources,"
            " latency_ms, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (conv_id, role, content, intent, json.dumps(sources or []),
             latency_ms, time.time()),
        )


def history(conv_id: str, limit: int = 10) -> list[dict[str, str]]:
    with connect() as conn:
        rows = conn.execute(
            "SELECT role, content FROM messages WHERE conversation_id = ?"
            " ORDER BY id DESC LIMIT ?",
            (conv_id, limit),
        ).fetchall()
    return [{"role": r["role"], "content": r["content"]} for r in reversed(rows)]


def set_lead_score(conv_id: str, score: int, handed_off: bool) -> None:
    with connect() as conn:
        conn.execute(
            "UPDATE conversations SET lead_score = MAX(lead_score, ?),"
            " handed_off = MAX(handed_off, ?) WHERE id = ?",
            (score, int(handed_off), conv_id),
        )


# --- leads ------------------------------------------------------------------

def add_lead(**kw: Any) -> int:
    with connect() as conn:
        cur = conn.execute(
            "INSERT INTO leads (conversation_id, name, email, phone, message, intent,"
            " lead_score, source_page, created_at)"
            " VALUES (:conversation_id, :name, :email, :phone, :message, :intent,"
            " :lead_score, :source_page, :created_at)",
            {
                "conversation_id": kw.get("conversation_id", ""),
                "name": kw.get("name", ""),
                "email": kw.get("email", ""),
                "phone": kw.get("phone", ""),
                "message": kw.get("message", ""),
                "intent": kw.get("intent", ""),
                "lead_score": kw.get("lead_score", 0),
                "source_page": kw.get("source_page", ""),
                "created_at": time.time(),
            },
        )
    return int(cur.lastrowid)


def mark_delivered(lead_id: int, ok: bool, error: str = "") -> None:
    with connect() as conn:
        conn.execute(
            "UPDATE leads SET delivered = ?, delivery_error = ? WHERE id = ?",
            (int(ok), error[:500], lead_id),
        )


def recent_leads(limit: int = 50) -> list[dict[str, Any]]:
    with connect() as conn:
        rows = conn.execute(
            "SELECT * FROM leads ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
    return [dict(r) for r in rows]


def metrics() -> dict[str, Any]:
    with connect() as conn:
        convs = conn.execute("SELECT COUNT(*) FROM conversations").fetchone()[0]
        msgs = conn.execute(
            "SELECT COUNT(*) FROM messages WHERE role = 'user'").fetchone()[0]
        leads = conn.execute("SELECT COUNT(*) FROM leads").fetchone()[0]
        handed = conn.execute(
            "SELECT COUNT(*) FROM conversations WHERE handed_off = 1").fetchone()[0]
        latency = conn.execute(
            "SELECT AVG(latency_ms) FROM messages"
            " WHERE role = 'assistant' AND latency_ms > 0").fetchone()[0]
    # "Deflected" = conversations the bot closed out without escalating to a human.
    deflected = round(100 * (convs - handed) / convs) if convs else 0
    return {
        "conversations": convs,
        "user_messages": msgs,
        "leads": leads,
        "handoffs": handed,
        "deflection_rate": deflected,
        "avg_latency_ms": round(latency or 0),
        "knowledge": chunk_stats(),
    }
