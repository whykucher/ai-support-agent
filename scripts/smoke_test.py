"""End-to-end check with no server and no API keys.

    python -m scripts.smoke_test

Exercises every surface: all eleven knowledge bases in both languages,
retrieval quality, tenant isolation, every question the industry picker advertises, chat and scoring, lead
capture, the run log, all three lab tools, SSRF refusal, admin auth and the four
pages, English and Russian. Exit code 0 means the whole thing works on this
machine. Network is only needed for the one live-scrape check, which is skipped
rather than failed when offline.
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Windows consoles default to a legacy codepage, and half of what this script
# prints is now Russian. Without this the run dies on a rouble sign in a passing
# check rather than on anything being wrong.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):  # already wrapped, or not a real tty
        pass

# Windows consoles still default to a legacy codepage, and half the checks now
# print Russian. Without this the suite dies on a rouble sign rather than on a
# real failure.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):  # already utf-8, or not a real tty
        pass

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
        for site in config.SITES:
            n = health["sites"][site]["knowledge"]["n"]
            check(f"knowledge indexed: {site}", n > 0, f"{n} sections")

        # --- 1b. every industry the page advertises actually works ----------
        verticals = config.verticals()
        check("industry picker has content", len(verticals) >= 5,
              f"{len(verticals)} verticals")
        for key, conf in verticals.items():
            shape_ok = (len(conf["pipeline"]) == 4 and len(conf["questions"]) == 3
                        and conf.get("accent", "").startswith("#"))
            check(f"vertical shape: {key}", shape_ok, conf["industry"])

        from app import rag as _rag
        for key, conf in verticals.items():
            # Every question the page offers must return something. An advertised
            # question that produces "I do not know" is worse than not offering it.
            answered = sum(1 for q in conf["questions"] if _rag.search(q, key))
            check(f"advertised questions answered: {key}",
                  answered == len(conf["questions"]),
                  f"{answered}/{len(conf['questions'])}")

        # Isolation is about provenance, not scores: BM25 is normalised, so the
        # top hit is always 1.0. What matters is which file it came out of.
        cross = _rag.search("coffee wholesale roast subscription", "saas")
        check("no cross-tenant leakage",
              all("latchkey" in c["source"] for c in cross),
              f"saas answered from {cross[0]['source'] if cross else 'nothing'}")

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
        check("every site is separately indexed",
              len({tuple(sorted(c["heading"] for c in rag.search("pricing", s)))
                   for s in ("agency", "saas", "recruiting")}) == 3,
              "three industries, three different answers to the same word")

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
        check("knowledge browser",
              len(kb["sections"]) > 0 and set(kb["sites"]) == set(config.SITES),
              f"{len(kb['sections'])} sections across {len(kb['sites'])} sites")
        check("leads listing", bool(client.get("/api/leads", headers=admin).json()["leads"]))

        # --- 12b. the standalone business sites ------------------------------
        from app import sites as _sites
        for key, page in _sites.PAGES.items():
            resp = client.get(f"/b/{key}")
            check(f"business page /b/{key}", resp.status_code == 200)

            payload = client.get(f"/api/site/{key}")
            d = payload.json() if payload.status_code == 200 else {}
            shape = (payload.status_code == 200
                     and d["page"]["brand"] == page["brand"]
                     and len(d["page"]["sections"]) >= 2
                     and len(d["page"]["stats"]) == 4
                     and d["assistant"]["questions"]
                     and d["knowledge"]["n"] > 0)
            check(f"site payload {key}", shape,
                  f"{page['brand']} · {d.get('knowledge', {}).get('n', 0)} sections")

        # Every business must look like a different company, not a recoloured
        # template: distinct palette, typeface and hero layout.
        themes = [p["theme"] for p in _sites.PAGES.values()]
        check("each business has its own palette",
              len({t["bg"] for t in themes}) == len(themes))
        check("each business has its own typeface",
              len({t["display"] for t in themes}) == len(themes))
        check("hero layouts vary",
              len({p["layout"] for p in _sites.PAGES.values()}) >= 3,
              ", ".join(sorted({p["layout"] for p in _sites.PAGES.values()})))

        check("unknown business 404s", client.get("/b/nope").status_code == 404)
        check("unknown site payload 404s", client.get("/api/site/nope").status_code == 404)

        # --- 12c. the Russian side ------------------------------------------
        # A half-translated site is worse than an English one, so these check
        # the seams: routing, language scoping, and that the assistant actually
        # answers in Russian rather than falling back to the English templates.
        cyrillic = re.compile(r"[а-яё]", re.I)
        latin = re.compile(r"[a-z]", re.I)

        for key, conf in config.SITES.items():
            if conf.get("lang") != "ru":
                continue
            for q in conf.get("questions", []):
                a = client.post("/api/chat", json={"message": q, "site": key})
                ans = a.json().get("answer", "") if a.status_code == 200 else ""
                # Compared as counts, not presence: a Russian answer may still
                # contain "SEO" or "n8n" without being an English answer.
                russian = (len(cyrillic.findall(ans)) >
                           len(latin.findall(ans)))
                check(f"{key} answers «{q[:28]}…» in Russian", russian,
                      ans[:60])

        # The two portfolios must not list each other's demo businesses.
        en_page = client.get("/").text
        ru_page = client.get("/ru").text
        check("/ru serves the Russian portfolio",
              client.get("/ru").status_code == 200
              and "Леонид Денисов" in ru_page)
        check("Russian portfolio does not carry the English name",
              "Nikita" not in ru_page)
        # Matched loosely: the two pages render their pickers differently, and
        # the invariant is the language filter, not the variable it is on.
        check("each portfolio filters the picker by language",
              'lang === "en"' in en_page and 'lang === "ru"' in ru_page)

        # These faces ship no Cyrillic. If one is ever set on the Russian page
        # the headings silently fall back to a system font, which is the kind of
        # breakage that looks like a browser problem rather than a bug.
        latin_only = ("Bricolage", "Anton", "Fraunces", "Instrument+Serif")
        check("Russian portfolio uses a Cyrillic display face",
              not any(f in ru_page for f in latin_only) and "Geologica" in ru_page)

        ru_payload = client.get("/api/site/ru-shop").json()
        check("Russian business payload points home to /ru",
              ru_payload["lang"] == "ru" and ru_payload["home"] == "/ru"
              and ru_payload["owner"] == config.OWNER_NAME_RU)
        check("English business payload points home to /",
              client.get("/api/site/saas").json()["home"] == "/")

        # Company names are stored already quoted; anything adding its own
        # prints ««Лоскут»».
        unknown = client.post("/api/chat", json={
            "message": "Продаёте ли вы велосипеды?", "site": "ru-shop"}).json()
        check("Russian fallback has no doubled guillemets",
              "««" not in unknown["answer"] and
              len(cyrillic.findall(unknown["answer"])) > 10,
              unknown["answer"][:60])

        # A buying word inside a negated question is not buying intent. This
        # shipped scoring "when should I NOT hire you" at 80/100 and pitching a
        # sales call in reply, which the execution chain on the front page
        # displays in full.
        for site, q in (("portfolio", "When should I not hire you?"),
                        ("portfolio-ru", "Когда вас не надо нанимать?")):
            d = client.post("/api/chat", json={"message": q, "site": site}).json()
            check(f"{site} does not read a negated question as buying",
                  d["intent"] != "buying" and not d["show_lead_form"],
                  f"{d['intent']} {d['lead_score']}/100")
        for site, q in (("portfolio", "I want to hire you for a project"),
                        ("portfolio-ru", "Хочу нанять вас на проект")):
            d = client.post("/api/chat", json={"message": q, "site": site}).json()
            check(f"{site} still reads real buying intent", d["intent"] == "buying",
                  f"{d['intent']} {d['lead_score']}/100")

        check("Russian portfolio asks its own tenant",
              'site: "portfolio-ru"' in ru_page and 'site: "portfolio"' in en_page)

        check("widget carries a Russian string table",
              "Спросите что угодно" in client.get("/static/widget.js").text)

        # --- 13. pages ------------------------------------------------------------
        for path, marker in [("/", "Execution chain"),
                             ("/ru", "Цепочка выполнения"),
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
