"""Fill the database with realistic traffic so the dashboard has something to show.

Useful for portfolio screenshots and for demoing to a client before their own
data exists.

    python -m scripts.seed_demo
"""
import random
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import config, db, leads, llm, rag  # noqa: E402

CONVERSATIONS: list[tuple[list[str], dict[str, str] | None]] = [
    (["How fast is shipping to Canada?",
      "Do I pay customs on that?"], None),
    (["My order says delivered but nothing arrived",
      "It has been four days"], None),
    (["What is your return policy on opened bags?"], None),
    (["I run a cafe and need wholesale pricing for about 60 lb a month",
      "Do you loan grinders?"],
     {"name": "Marta Iversen", "email": "marta@harborlanecafe.example"}),
    (["Can I pause my subscription for a month?"], None),
    (["We want office coffee service for a 40 person studio",
      "What does onboarding look like?"],
     {"name": "Devin Okafor", "email": "devin@studionorth.example"}),
    (["Which roast is best for espresso?"], None),
    (["Do you offer private label roasting?",
      "Minimum order?"],
     {"name": "Priya Raman", "email": "priya@ridgelinehotels.example",
      "phone": "+1 415 555 0193"}),
    (["The bag arrived damaged, I want a refund"], None),
    (["Do you have an API for placing orders automatically?"],
     {"name": "Tom Berger", "email": "tom@beanstack.example"}),
]

PAGES = ["/", "/wholesale", "/subscribe", "/coffee/harbor-blend"]


def seed() -> int:
    """Write the sample conversations. Returns the number of leads created."""
    db.init()
    if db.chunk_stats()["n"] == 0:
        rag.ingest_directory()

    now = time.time()
    created = 0

    for offset, (turns, contact) in enumerate(CONVERSATIONS):
        conv_id = f"seed{offset:02d}{random.randint(1000, 9999)}"
        page = random.choice(PAGES)
        db.touch_conversation(conv_id, page)
        # Spread the traffic over the last three days.
        started = now - random.uniform(0, 3 * 86400)

        intent = "question"
        score = 0
        for turn in turns:
            db.add_message(conv_id, "user", turn)
            chunks = rag.search(turn)
            result = llm.answer(turn, chunks, rag.build_context(chunks), [])
            db.add_message(
                conv_id, "assistant", result["answer"], intent=result["intent"],
                sources=[c["source"] for c in chunks],
                latency_ms=random.randint(380, 1600),
            )
            intent, score = result["intent"], max(score, result["lead_score"])
            db.set_lead_score(conv_id, result["lead_score"], result["handoff"])

        if contact:
            db.add_lead(
                conversation_id=conv_id,
                name=contact.get("name", ""),
                email=contact.get("email", ""),
                phone=contact.get("phone", ""),
                message=turns[0],
                intent=intent,
                lead_score=max(score, 70),
                source_page=page,
            )
            created += 1

        # Backdate so the dashboard shows a spread instead of one timestamp.
        with db.connect() as conn:
            conn.execute("UPDATE conversations SET started_at = ?, last_seen = ?"
                         " WHERE id = ?", (started, started + 240, conv_id))
            conn.execute("UPDATE messages SET created_at = ? WHERE conversation_id = ?",
                         (started, conv_id))
            conn.execute("UPDATE leads SET created_at = ? WHERE conversation_id = ?",
                         (started + 300, conv_id))

    return created


def main() -> int:
    created = seed()
    m = db.metrics()
    print(f"seeded {len(CONVERSATIONS)} conversations, {created} leads "
          f"(provider={config.LLM_PROVIDER})")
    print(f"  deflection {m['deflection_rate']}% · avg {m['avg_latency_ms']} ms")
    print(f"  open http://{config.HOST}:{config.PORT}/admin")
    if config.N8N_WEBHOOK_URL:
        print(f"  replaying to n8n: {leads.retry_undelivered()} lead(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
