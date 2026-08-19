"""Lead extraction and outbound delivery to n8n.

The bot captures contacts two ways: the customer types them mid-conversation
(regex), or the widget shows an inline form once lead_score crosses the
threshold. Both land in the same table and the same webhook payload.
"""
import hashlib
import hmac
import json
import re
import time
from typing import Any

import httpx

from . import config, db

EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]{2,}")
# Deliberately loose: international formats vary, and a false positive costs
# nothing here (a human reviews the lead) while a miss costs a customer.
PHONE_RE = re.compile(r"(?:\+?\d[\d\s().-]{7,17}\d)")


def extract_contacts(text: str) -> dict[str, str]:
    email = EMAIL_RE.search(text)
    phone = PHONE_RE.search(EMAIL_RE.sub("", text))
    return {
        "email": email.group(0) if email else "",
        "phone": phone.group(0).strip() if phone else "",
    }


def _sign(body: bytes) -> str:
    return hmac.new(config.N8N_WEBHOOK_SECRET.encode(), body, hashlib.sha256).hexdigest()


def deliver(lead_id: int, payload: dict[str, Any]) -> bool:
    """POST the lead to n8n. Failure is recorded, not raised - the lead is already
    safe in SQLite and /api/leads/retry can replay it."""
    if not config.N8N_WEBHOOK_URL:
        db.mark_delivered(lead_id, False, "N8N_WEBHOOK_URL not configured")
        return False

    body = json.dumps(payload, ensure_ascii=False).encode()
    headers = {"Content-Type": "application/json"}
    if config.N8N_WEBHOOK_SECRET:
        headers["X-Signature"] = _sign(body)

    try:
        resp = httpx.post(config.N8N_WEBHOOK_URL, content=body, headers=headers,
                          timeout=httpx.Timeout(10.0))
        resp.raise_for_status()
    except Exception as exc:  # noqa: BLE001
        db.mark_delivered(lead_id, False, f"{type(exc).__name__}: {exc}")
        return False

    db.mark_delivered(lead_id, True)
    return True


def capture(conversation_id: str, *, name: str = "", email: str = "", phone: str = "",
            message: str = "", intent: str = "", lead_score: int = 0,
            source_page: str = "") -> dict[str, Any]:
    """Persist a lead, then push it downstream."""
    lead_id = db.add_lead(
        conversation_id=conversation_id, name=name, email=email, phone=phone,
        message=message, intent=intent, lead_score=lead_score, source_page=source_page,
    )
    payload = {
        "lead_id": lead_id,
        "conversation_id": conversation_id,
        "name": name,
        "email": email,
        "phone": phone,
        "message": message,
        "intent": intent,
        "lead_score": lead_score,
        "priority": "hot" if lead_score >= config.HANDOFF_SCORE else "warm",
        "source_page": source_page,
        "company": config.COMPANY_NAME,
        "captured_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "transcript": db.history(conversation_id, limit=20),
    }
    delivered = deliver(lead_id, payload)
    return {"lead_id": lead_id, "delivered": delivered, "priority": payload["priority"]}


def retry_undelivered(limit: int = 20) -> int:
    """Replay leads that failed to reach n8n (webhook was down, secret rotated...)."""
    sent = 0
    for lead in db.recent_leads(limit=200):
        if lead["delivered"] or sent >= limit:
            continue
        payload = {
            **{k: lead[k] for k in ("name", "email", "phone", "message", "intent",
                                    "lead_score", "conversation_id", "source_page")},
            "lead_id": lead["id"],
            "replay": True,
            "transcript": db.history(lead["conversation_id"], limit=20),
        }
        if deliver(lead["id"], payload):
            sent += 1
    return sent
