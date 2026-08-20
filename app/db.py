"""SQLite storage: knowledge chunks, conversations, messages, leads, run log.

Two things worth knowing before reading further.

**Sites.** One engine serves several knowledge bases - the portfolio answers
questions about the freelancer, the demo answers questions about a coffee
roaster - so almost every table carries a `site` column and every query is
scoped by it. That is cheaper and far easier to reason about than running two
deployments, and it is the same shape a real multi-client install would take.

**Runs.** Every automation the app performs writes a row to `runs`. The public
activity feed and the admin log both read from it, which means the site is
never claiming an automation happened - it is showing the ledger.
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
    site        TEXT    NOT NULL DEFAULT 'demo',
    source      TEXT    NOT NULL,
    heading     TEXT    NOT NULL DEFAULT '',
    content     TEXT    NOT NULL,
    tokens      INTEGER NOT NULL DEFAULT 0,
    embedding   TEXT,
    created_at  REAL    NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_chunks_site ON chunks(site);

CREATE TABLE IF NOT EXISTS conversations (
    id          TEXT    PRIMARY KEY,
    site        TEXT    NOT NULL DEFAULT 'demo',
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
    created_at      REAL    NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_messages_conv ON messages(conversation_id);

CREATE TABLE IF NOT EXISTS leads (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    site            TEXT    NOT NULL DEFAULT 'demo',
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

CREATE TABLE IF NOT EXISTS runs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    site        TEXT    NOT NULL DEFAULT 'demo',
    kind        TEXT    NOT NULL,
    status      TEXT    NOT NULL DEFAULT 'ok',
    summary     TEXT    NOT NULL DEFAULT '',
    detail      TEXT    NOT NULL DEFAULT '{}',
    duration_ms INTEGER NOT NULL DEFAULT 0,
    created_at  REAL    NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_runs_created ON runs(created_at DESC);
"""

# Columns added after the first release. SQLite has no "ADD COLUMN IF NOT
# EXISTS", so this runs once against whatever shape the database already has.
MIGRATIONS = [
    ("chunks", "site", "TEXT NOT NULL DEFAULT 'demo'"),
    ("conversations", "site", "TEXT NOT NULL DEFAULT 'demo'"),
    ("leads", "site", "TEXT NOT NULL DEFAULT 'demo'"),
]


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
        for table, column, decl in MIGRATIONS:
            cols = {r["name"] for r in conn.execute(f"PRAGMA table_info({table})")}
            if column not in cols:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {decl}")


# --- knowledge base ---------------------------------------------------------

def replace_chunks(site: str, source: str, rows: list[dict[str, Any]]) -> int:
    """Re-ingest one source file atomically, within its site."""
    now = time.time()
    with connect() as conn:
        conn.execute("DELETE FROM chunks WHERE site = ? AND source = ?", (site, source))
        conn.executemany(
            "INSERT INTO chunks (site, source, heading, content, tokens, embedding,"
            " created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            [
                (
                    site,
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


def site_chunks(site: str) -> list[sqlite3.Row]:
    with connect() as conn:
        return conn.execute(
            "SELECT id, source, heading, content, embedding FROM chunks WHERE site = ?",
            (site,),
        ).fetchall()


def chunk_stats(site: str | None = None) -> dict[str, Any]:
    where, params = ("WHERE site = ?", (site,)) if site else ("", ())
    with connect() as conn:
        row = conn.execute(
            f"SELECT COUNT(*) AS n, COUNT(embedding) AS vectorised,"
            f" COUNT(DISTINCT source) AS sources FROM chunks {where}",
            params,
        ).fetchone()
    return dict(row)


def knowledge_index() -> list[dict[str, Any]]:
    """Per-site, per-file, per-section listing for the admin knowledge browser."""
    with connect() as conn:
        rows = conn.execute(
            "SELECT site, source, heading, LENGTH(content) AS chars,"
            " embedding IS NOT NULL AS vectorised"
            " FROM chunks ORDER BY site, source, id"
        ).fetchall()
    return [dict(r) for r in rows]


def sites() -> list[str]:
    with connect() as conn:
        return [r[0] for r in conn.execute("SELECT DISTINCT site FROM chunks ORDER BY site")]


# --- conversations ----------------------------------------------------------

def touch_conversation(conv_id: str, site: str, page_url: str = "") -> None:
    now = time.time()
    with connect() as conn:
        conn.execute(
            "INSERT INTO conversations (id, site, started_at, last_seen, page_url)"
            " VALUES (?, ?, ?, ?, ?)"
            " ON CONFLICT(id) DO UPDATE SET last_seen = excluded.last_seen",
            (conv_id, site, now, now, page_url),
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
            "INSERT INTO leads (site, conversation_id, name, email, phone, message,"
            " intent, lead_score, source_page, created_at)"
            " VALUES (:site, :conversation_id, :name, :email, :phone, :message,"
            " :intent, :lead_score, :source_page, :created_at)",
            {
                "site": kw.get("site", "demo"),
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


def recent_leads(limit: int = 50, site: str | None = None) -> list[dict[str, Any]]:
    where, params = ("WHERE site = ?", [site]) if site else ("", [])
    with connect() as conn:
        rows = conn.execute(
            f"SELECT * FROM leads {where} ORDER BY created_at DESC LIMIT ?",
            (*params, limit),
        ).fetchall()
    return [dict(r) for r in rows]


# --- run log ----------------------------------------------------------------

def add_run(kind: str, *, site: str = "demo", status: str = "ok", summary: str = "",
            detail: dict[str, Any] | None = None, duration_ms: int = 0) -> int:
    """Record one automation execution. Never raises: a failure to log must not
    take down the thing being logged."""
    try:
        with connect() as conn:
            cur = conn.execute(
                "INSERT INTO runs (site, kind, status, summary, detail, duration_ms,"
                " created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (site, kind, status, summary[:200],
                 json.dumps(detail or {}, ensure_ascii=False)[:2000],
                 duration_ms, time.time()),
            )
        return int(cur.lastrowid)
    except Exception:  # noqa: BLE001
        return 0


def recent_runs(limit: int = 30, site: str | None = None) -> list[dict[str, Any]]:
    where, params = ("WHERE site = ?", [site]) if site else ("", [])
    with connect() as conn:
        rows = conn.execute(
            f"SELECT * FROM runs {where} ORDER BY created_at DESC LIMIT ?",
            (*params, limit),
        ).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        try:
            d["detail"] = json.loads(d["detail"])
        except ValueError:
            d["detail"] = {}
        out.append(d)
    return out


def run_counts() -> dict[str, int]:
    with connect() as conn:
        rows = conn.execute(
            "SELECT kind, COUNT(*) AS n FROM runs GROUP BY kind ORDER BY n DESC"
        ).fetchall()
    return {r["kind"]: r["n"] for r in rows}


# --- metrics ----------------------------------------------------------------

def metrics(site: str | None = None) -> dict[str, Any]:
    # Build one predicate and reuse it, rather than splicing fragments per query.
    scoped = " AND site = ?" if site else ""
    joined = " AND c.site = ?" if site else ""
    p = [site] if site else []

    with connect() as conn:
        one = lambda sql, args=(): conn.execute(sql, args).fetchone()[0]  # noqa: E731
        convs = one(f"SELECT COUNT(*) FROM conversations WHERE 1=1{scoped}", p)
        handed = one(
            f"SELECT COUNT(*) FROM conversations WHERE handed_off = 1{scoped}", p)
        leads = one(f"SELECT COUNT(*) FROM leads WHERE 1=1{scoped}", p)
        runs = one(f"SELECT COUNT(*) FROM runs WHERE 1=1{scoped}", p)
        msgs = one(
            "SELECT COUNT(*) FROM messages m JOIN conversations c"
            f" ON c.id = m.conversation_id WHERE m.role = 'user'{joined}", p)
        latency = conn.execute(
            "SELECT AVG(m.latency_ms) FROM messages m JOIN conversations c"
            " ON c.id = m.conversation_id"
            f" WHERE m.role = 'assistant' AND m.latency_ms > 0{joined}", p).fetchone()[0]
    # "Deflected" = conversations the bot closed out without escalating.
    deflected = round(100 * (convs - handed) / convs) if convs else 0
    return {
        "conversations": convs,
        "user_messages": msgs,
        "leads": leads,
        "handoffs": handed,
        "runs": runs,
        "deflection_rate": deflected,
        "avg_latency_ms": round(latency or 0),
        "knowledge": chunk_stats(site),
    }
