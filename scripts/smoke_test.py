"""End-to-end check with no server and no API keys.

    python -m scripts.smoke_test

Exercises: indexing -> retrieval -> chat -> lead capture -> admin API.
Exit code 0 means the whole pipeline works on this machine.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient  # noqa: E402

from app import config, db  # noqa: E402
from app.main import app  # noqa: E402

CHECKS: list[tuple[str, bool, str]] = []


def check(label: str, ok: bool, detail: str = "") -> None:
    CHECKS.append((label, ok, detail))
    print(f"  {'PASS' if ok else 'FAIL'}  {label}" + (f"  -> {detail}" if detail else ""))


def main() -> int:
    print(f"provider = {config.LLM_PROVIDER}\n")
    with TestClient(app) as client:
        health = client.get("/api/health").json()
        check("health endpoint", health.get("status") == "ok", health.get("provider", ""))
        check("knowledge indexed", health["knowledge"]["n"] > 0,
              f"{health['knowledge']['n']} chunks")

        # 1. A plain support question should be answered from the knowledge base.
        r1 = client.post("/api/chat", json={"message": "How long does US shipping take?"})
        d1 = r1.json()
        check("chat responds", r1.status_code == 200 and bool(d1.get("answer")))
        check("answer is grounded", bool(d1.get("sources")), ", ".join(d1.get("sources", [])[:2]))
        check("support question scores low", d1["lead_score"] < 40, f"score={d1['lead_score']}")

        conv = d1["conversation_id"]

        # 2. A commercial question should score high and trigger the lead form.
        r2 = client.post("/api/chat", json={
            "message": "I need wholesale pricing for my cafe, about 80 lb a month",
            "conversation_id": conv})
        d2 = r2.json()
        check("buying intent detected", d2["lead_score"] >= config.HANDOFF_SCORE,
              f"score={d2['lead_score']} intent={d2['intent']}")
        check("lead form triggered", d2["show_lead_form"] is True)

        # 3. A contact typed into the chat is captured without any form.
        r3 = client.post("/api/chat", json={
            "message": "Reach me at buyer@example.com", "conversation_id": conv})
        check("inline contact captured", r3.json().get("lead") is not None)

        # 4. Explicit form submission.
        r4 = client.post("/api/lead", json={
            "conversation_id": conv, "name": "Test Buyer",
            "email": "test@example.com", "message": "smoke test"})
        check("lead form endpoint", r4.status_code == 200 and "lead_id" in r4.json())

        # 5. Admin surface.
        bad = client.get("/api/metrics")
        check("admin requires token", bad.status_code == 401)
        good = client.get("/api/metrics", headers={"X-Admin-Token": config.ADMIN_TOKEN})
        check("metrics endpoint", good.status_code == 200 and good.json()["leads"] >= 2,
              f"{good.json().get('leads')} leads")

        listing = client.get("/api/leads", headers={"X-Admin-Token": config.ADMIN_TOKEN})
        check("leads listing", listing.status_code == 200 and listing.json()["leads"])

        # 6. Static demo site.
        check("storefront served", client.get("/").status_code == 200)
        check("widget served", client.get("/static/widget.js").status_code == 200)

        # 7. Retrieval quality: the right section has to win, not just any section.
        from app import rag
        expected = [
            ("How long does shipping take?", "shipping"),
            ("wholesale discount for 200 lb a month", "wholesale"),
            ("can I cancel my subscription", "subscription"),
            ("I want a refund for an opened bag", "returns"),
            ("what grind ratio for french press", "brewing"),
            ("how much is a single origin bag", "pricing"),
        ]
        for query, want in expected:
            top = rag.search(query)
            head = top[0]["heading"].lower() if top else ""
            check(f'retrieval: "{query[:34]}"', want in head, head or "no hits")

    failed = [c for c in CHECKS if not c[1]]
    print(f"\n{len(CHECKS) - len(failed)}/{len(CHECKS)} checks passed")
    if failed:
        print("failed: " + ", ".join(c[0] for c in failed))
    return 1 if failed else 0


if __name__ == "__main__":
    db.init()
    raise SystemExit(main())
