"""End-to-end check with no server and no API keys.

    python -m scripts.smoke_test

Exercises every surface: both knowledge bases, retrieval quality, chat, intent
scoring, lead capture, the run log, all three lab tools, SSRF refusal, admin
auth and the four pages. Exit code 0 means the whole thing works on this
machine. Network is only needed for the one live-scrape check, which is skipped
rather than failed when offline.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient  # noqa: E402

from app import config, db  # noqa: E402
from app.main import app  # noqa: E402

CHECKS: list[tuple[str, bool, str]] = []
SKIPPED: list[str] = []


def check(label: str, ok: bool, detail: str = "") -> None:
    CHECKS.append((label, ok, detail))
    print(f"  {'PASS' if ok else 'FAIL'}  {label}" + (f"  -> {detail}" if detail else ""))


def skip(label: str, why: str) -> None:
    SKIPPED.append(label)
    print(f"  SKIP  {label}  -> {why}")


def main() -> int:
    print(f"provider = {config.LLM_PROVIDER}\n")
    with TestClient(app) as client:
        admin = {"X-Admin-Token": config.ADMIN_TOKEN}

        # --- 1. health and both knowledge bases -----------------------------
        health = client.get("/api/health").json()
        check("health endpoint", health.get("status") == "ok", health.get("provider", ""))
        for site in ("portfolio", "demo"):
            n = health["sites"][site]["knowledge"]["n"]
            check(f"knowledge indexed: {site}", n > 0, f"{n} sections")

        # --- 2. retrieval quality, per site ---------------------------------
        from app import rag
        expected = [
            ("portfolio", "what do you charge", "pricing"),
            ("portfolio", "when should I not hire you", "not to hire"),
            ("portfolio", "which AI models do you use", "technology"),
            ("portfolio", "how do we start", "start"),
            ("demo", "how long does shipping take", "shipping"),
            ("demo", "wholesale discount for 200 lb", "wholesale"),
            ("demo", "can I cancel my subscription", "subscription"),
            ("demo", "I want a refund for an opened bag", "returns"),
        ]
        for site, query, want in expected:
            top = rag.search(query, site)
            head = top[0]["heading"].lower() if top else ""
            check(f'retrieval [{site}] "{query[:30]}"', want in head, head or "no hits")

        # --- 3. the two knowledge bases stay apart --------------------------
        check("sites are isolated",
              not rag.search("wholesale coffee roast profile", "portfolio"),
              "portfolio knows nothing about coffee")

        # --- 4. chat on the portfolio ---------------------------------------
        r = client.post("/api/chat", json={"message": "What do you charge for a pilot?",
                                           "site": "portfolio"}).json()
        check("portfolio chat answers", bool(r.get("answer")), r.get("sources", [""])[0])
        check("portfolio detects buying intent", r["lead_score"] >= config.HANDOFF_SCORE,
              f"score={r['lead_score']} intent={r['intent']}")
        conv_p = r["conversation_id"]
        check("portfolio conversation is tagged", r["site"] == "portfolio")

        # --- 5. chat on the demo --------------------------------------------
        r1 = client.post("/api/chat", json={"message": "How long does US shipping take?",
                                            "site": "demo"}).json()
        check("demo chat answers", bool(r1.get("answer")), ", ".join(r1.get("sources", [])[:2]))
        check("support question scores low", r1["lead_score"] < 40, f"score={r1['lead_score']}")
        conv = r1["conversation_id"]

        r2 = client.post("/api/chat", json={
            "message": "I need wholesale pricing for my cafe, about 80 lb a month",
            "conversation_id": conv, "site": "demo"}).json()
        check("demo detects buying intent", r2["lead_score"] >= config.HANDOFF_SCORE,
              f"score={r2['lead_score']}")
        check("lead form triggered", r2["show_lead_form"] is True)

        r3 = client.post("/api/chat", json={"message": "Reach me at buyer@example.com",
                                            "conversation_id": conv, "site": "demo"}).json()
        check("inline contact captured", r3.get("lead") is not None)

        # --- 6. lead form ----------------------------------------------------
        r4 = client.post("/api/lead", json={
            "conversation_id": conv_p, "name": "Test Buyer",
            "email": "test@example.com", "message": "smoke test", "site": "portfolio"})
        check("lead form endpoint", r4.status_code == 200 and "lead_id" in r4.json())

        # --- 7. the run log ---------------------------------------------------
        runs = client.get("/api/runs?limit=50").json()
        kinds = {run["kind"] for run in runs["runs"]}
        check("run log is public", "runs" in runs and len(runs["runs"]) > 0,
              f"{len(runs['runs'])} rows")
        check("chat answers are logged", "chat.answer" in kinds)
        check("lead capture is logged", "lead.capture" in kinds)

        # --- 8. lab: classifier ------------------------------------------------
        c = client.post("/api/lab/classify", json={
            "text": "We need a quote for invoice automation, budget $3000, "
                    "call me on +1 415 555 0123"}).json()
        check("lab classify: intent", c["intent"] == "buying", f"score={c['lead_score']}")
        check("lab classify: entities", len(c["entities"]["phones"]) >= 1
              and len(c["entities"]["amounts"]) >= 1,
              f"{c['entities']['amounts']} {c['entities']['phones']}")
        c2 = client.post("/api/lab/classify", json={
            "text": "my order arrived broken and I want to reorder two more"}).json()
        check("lab classify: complaint outranks purchase", c2["intent"] == "complaint",
              c2["intent"])

        # --- 9. lab: CSV cleaner -----------------------------------------------
        messy = ("Name,Email,Phone\n"
                 "John Doe,  JOHN@Example.COM ,+1 (415) 555-0100\n"
                 "john doe,john@example.com,+14155550100\n"
                 "\n"
                 "Jane Roe,jane@example.com,+1 415 555 0111\n"
                 "Ragged Row,bad-email\n")
        cl = client.post("/api/lab/clean", json={"csv": messy}).json()
        check("lab clean: deduplicates", cl["duplicates_removed"] == 1)
        check("lab clean: drops blank rows", cl["blank_rows_removed"] == 1)
        check("lab clean: pads ragged rows", cl["ragged_rows_padded"] == 1)
        check("lab clean: flags bad emails", cl["invalid_emails"] == 1)
        check("lab clean: returns a file", cl["csv"].startswith("Name,Email,Phone"))

        # --- 10. lab: scraper safety --------------------------------------------
        for bad in ("http://localhost:8000", "http://127.0.0.1/admin",
                    "file:///etc/passwd", "http://169.254.169.254/latest/meta-data"):
            code = client.post("/api/lab/scrape", json={"url": bad}).status_code
            check(f"scraper refuses {bad[:34]}", code == 400, f"HTTP {code}")

        # --- 11. lab: a real fetch (skipped offline) -----------------------------
        live = client.post("/api/lab/scrape", json={"url": "https://example.com"})
        if live.status_code == 200:
            d = live.json()
            check("lab scrape: real page", d["title"] == "Example Domain"
                  and d["status"] == 200, f"{d['words']} words in {d['duration_ms']}ms")
        else:
            skip("lab scrape: real page", f"no network (HTTP {live.status_code})")

        # --- 12. admin surface ---------------------------------------------------
        check("admin requires token", client.get("/api/metrics").status_code == 401)
        m = client.get("/api/metrics", headers=admin)
        check("metrics endpoint", m.status_code == 200 and "by_site" in m.json(),
              f"{m.json()['all']['leads']} leads")
        check("metrics per site", set(m.json()["by_site"]) == set(config.SITES))
        focus = client.get("/api/metrics?site=portfolio", headers=admin).json()["focus"]
        check("metrics can focus one site", focus is not None
              and focus["leads"] <= m.json()["all"]["leads"])
        kb = client.get("/api/knowledge", headers=admin).json()
        check("knowledge browser", len(kb["sections"]) > 0 and len(kb["sites"]) == 2,
              f"{len(kb['sections'])} sections across {kb['sites']}")
        check("leads listing", bool(client.get("/api/leads", headers=admin).json()["leads"]))

        # --- 13. pages ------------------------------------------------------------
        for path, marker in [("/", "This page is the demo"),
                             ("/lab", "Page scraper"),
                             ("/demo", "FIRST CRACK"),
                             ("/admin", "Run log")]:
            resp = client.get(path)
            check(f"page {path}", resp.status_code == 200 and marker in resp.text)
        check("widget served", client.get("/static/widget.js").status_code == 200)

    failed = [c for c in CHECKS if not c[1]]
    print(f"\n{len(CHECKS) - len(failed)}/{len(CHECKS)} checks passed"
          + (f", {len(SKIPPED)} skipped" if SKIPPED else ""))
    if failed:
        print("failed: " + ", ".join(c[0] for c in failed))
    return 1 if failed else 0


if __name__ == "__main__":
    db.init()
    raise SystemExit(main())
