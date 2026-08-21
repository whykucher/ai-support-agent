"""LLM layer: one interface, three backends (demo / Anthropic / OpenAI-compatible).

Every call returns the same structured envelope, so swapping providers - or
falling back to demo mode when a key expires - never changes downstream code.
Raw HTTP via httpx instead of vendor SDKs keeps the dependency list at five
packages and makes OpenRouter / DeepSeek / Ollama work by changing one env var.
"""
import json
import re
from typing import Any

import httpx

from . import config

TIMEOUT = httpx.Timeout(30.0, connect=10.0)

SYSTEM_PROMPT = """You are {agent}, the support assistant for {company}.

Rules:
1. Answer ONLY from the CONTEXT below. If the context does not contain the
   answer, say you do not have that detail and offer to pass the question to a
   human - never invent policies, prices, or delivery dates.
2. Be concise: two to four sentences, no filler, no "as an AI".
3. Match the customer's language.
4. If the customer shows buying intent (pricing for volume, wholesale, custom
   orders, integrations, "how do I get started"), answer their question first,
   then ask for the one detail sales needs next.

Reply with JSON only, no markdown fence:
{{"answer": str,
  "intent": "question" | "pricing" | "buying" | "support" | "complaint" | "other",
  "lead_score": int 0-100,
  "handoff": bool,
  "ask_for_contact": bool}}

lead_score reflects commercial value of this conversation: a shipping-status
question is 0-20, general pricing 40-60, wholesale or integration intent 70-100.
Set handoff when a human must take over (complaint, refund, anything you cannot
answer from context)."""

USER_TEMPLATE = """CONTEXT:
{context}

CUSTOMER: {question}"""


# --- demo backend -----------------------------------------------------------

# "subscription" deliberately absent: someone asking to pause or cancel one is
# a retention question, not a purchase, and scoring it as buying intent made the
# bot pitch a sales call at an existing customer.
_BUY_WORDS = ("wholesale", "bulk", "volume", "reseller", "quote", "invoice",
              "b2b", "contract", "partnership", "integrate",
              "api", "custom", "office", "corporate")

# The portfolio sells project work, so its buying signals are different ones.
_BUY_WORDS_PORTFOLIO = ("hire", "budget", "quote", "project", "engage", "start",
                        "available", "availability", "retainer", "contract",
                        "proposal", "scope", "timeline", "deadline", "cost",
                        "price", "pricing", "rate", "charge", "pilot",
                        "how much", "estimate", "package", "deposit", "invoice")

_PRICE_WORDS = ("price", "cost", "how much", "discount", "pricing", "cheap")
_ANGRY_WORDS = ("refund", "broken", "damaged", "late", "never arrived",
                "complaint", "wrong item", "cancel")

# Russian equivalents. These are matched as substrings against the lowercased
# question, so each entry is a stem rather than a word form: "цен" catches
# цена, цены, цену and ценам without a morphology library.
_BUY_WORDS_RU = ("опт", "объём", "объем", "парти", "счёт", "счет", "договор",
                 "юрлиц", "юридическ", "интеграц", "api", "корпоратив",
                 "сотруднич", "коммерческ предлож", "подключ")

_BUY_WORDS_PORTFOLIO_RU = ("нанят", "наня", "бюджет", "проект", "заказ",
                           "смет", "срок", "дедлайн", "сколько сто", "стоимост",
                           "цен", "тариф", "пилот", "сопровожд", "договор",
                           "счёт", "счет", "свободн", "занят", "начать",
                           "приступ", "оценит")

_PRICE_WORDS_RU = ("цен", "стоимост", "сколько сто", "сколько буд", "скидк",
                   "дешев", "дешёв", "тариф", "прайс", "рассрочк")

_ANGRY_WORDS_RU = ("верните", "вернуть деньги", "возврат", "брак", "сломал",
                   "повредил", "опозда", "задерж", "жалоб", "не пришл",
                   "не приш", "отмен", "обман")

# What the assistant offers next once it detects commercial interest.
_FOLLOW_UP = {
    "demo": " Want me to have our wholesale team send you a quote?",
    "portfolio": " If you tell me what the task is, I can pass it to Nikita with"
                 " your details and he will come back within a business day.",
    "portfolio-ru": " Опишите задачу в двух словах — передам Леониду вместе с"
                    " вашими контактами, он вернётся в течение рабочего дня.",
    "ru-agency": " Оставьте контакты — стратег позвонит и разберёт вашу ситуацию"
                 " за 30 минут, бесплатно.",
    "ru-shop": " Напишите рост и обхваты — подскажем размер до того, как вы"
               " оформите заказ.",
    "ru-school": " Оставьте контакты — запишем вас на бесплатную консультацию.",
}

# Everything the demo backend says in its own voice, rather than quoting a
# document. Keyed by the language on the site's config entry.
_PHRASES = {
    "en": {
        "unknown": "I do not have that in {company}'s knowledge base yet. "
                   "Leave your email and you will get a proper answer today.",
        "sorry": "Sorry about that - I am handing this to a human agent now. ",
    },
    "ru": {
        # No company name here on purpose: the registry stores it already
        # quoted, and Russian would need it in the genitive anyway.
        "unknown": "Этого пока нет в моей базе знаний. Оставьте почту, "
                   "и вы получите нормальный ответ сегодня.",
        "sorry": "Извините за это — передаю вопрос живому сотруднику. ",
    },
}


def _is_portfolio(site: str) -> bool:
    """The portfolio sells project work; the demo businesses sell products.

    Checked by name in two places, and there are two portfolios now, so it is
    worth one function rather than two string comparisons that drift apart.
    """
    return site in ("portfolio", "portfolio-ru")


def _demo_reply(question: str, chunks: list[dict[str, Any]],
                site: str | None = None) -> dict[str, Any]:
    """Deterministic, no network. Good enough to demo the whole pipeline."""
    site = site or config.DEFAULT_SITE
    conf = config.site_conf(site)
    ru = conf.get("lang", "en") == "ru"
    phrases = _PHRASES["ru" if ru else "en"]

    if _is_portfolio(site):
        buy_words = _BUY_WORDS_PORTFOLIO_RU if ru else _BUY_WORDS_PORTFOLIO
    else:
        buy_words = _BUY_WORDS_RU if ru else _BUY_WORDS
    angry_words = _ANGRY_WORDS_RU if ru else _ANGRY_WORDS
    price_words = _PRICE_WORDS_RU if ru else _PRICE_WORDS
    q = question.lower()

    if not _is_portfolio(site) and any(w in q for w in angry_words):
        intent, score, handoff = "complaint", 25, True
    elif any(w in q for w in buy_words):
        intent, score, handoff = "buying", 80, False
    elif any(w in q for w in price_words):
        intent, score, handoff = "pricing", 50, False
    elif chunks:
        intent, score, handoff = "question", 10, False
    else:
        intent, score, handoff = "other", 10, True

    if not chunks:
        answer = phrases["unknown"].format(company=conf["company"])
    else:
        body = " ".join(chunks[0]["content"].split())
        if len(body) > 420:
            body = body[:420].rsplit(" ", 1)[0] + "..."
        answer = body
        if intent == "buying":
            answer += _FOLLOW_UP.get(site, "")
        elif intent == "complaint":
            answer = phrases["sorry"] + answer

    return {
        "answer": answer,
        "intent": intent,
        "lead_score": score,
        "handoff": handoff,
        "ask_for_contact": score >= config.HANDOFF_SCORE or handoff,
        "model": "demo-retrieval",
    }


# --- provider calls ---------------------------------------------------------

def _anthropic_chat(system: str, messages: list[dict[str, str]]) -> str:
    resp = httpx.post(
        f"{config.ANTHROPIC_BASE_URL}/v1/messages",
        headers={
            "x-api-key": config.ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": config.ANTHROPIC_MODEL,
            "max_tokens": 700,
            "system": system,
            "messages": messages,
        },
        timeout=TIMEOUT,
    )
    resp.raise_for_status()
    return "".join(b.get("text", "") for b in resp.json().get("content", []))


def _openai_chat(system: str, messages: list[dict[str, str]]) -> str:
    resp = httpx.post(
        f"{config.OPENAI_BASE_URL}/chat/completions",
        headers={
            "Authorization": f"Bearer {config.OPENAI_API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": config.OPENAI_MODEL,
            "temperature": 0.2,
            "response_format": {"type": "json_object"},
            "messages": [{"role": "system", "content": system}, *messages],
        },
        timeout=TIMEOUT,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


def embed(texts: list[str]) -> list[list[float]]:
    """Embeddings always go through an OpenAI-compatible endpoint."""
    if config.LLM_PROVIDER == "demo" or not config.OPENAI_API_KEY:
        return [[] for _ in texts]
    resp = httpx.post(
        f"{config.OPENAI_BASE_URL}/embeddings",
        headers={
            "Authorization": f"Bearer {config.OPENAI_API_KEY}",
            "Content-Type": "application/json",
        },
        json={"model": config.EMBEDDING_MODEL, "input": texts},
        timeout=TIMEOUT,
    )
    resp.raise_for_status()
    return [item["embedding"] for item in resp.json()["data"]]


def _parse_envelope(raw: str, fallback: str) -> dict[str, Any]:
    """Models sometimes wrap JSON in prose or a fence. Recover instead of failing."""
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if match:
        try:
            data = json.loads(match.group(0))
            return {
                "answer": str(data.get("answer") or fallback).strip(),
                "intent": str(data.get("intent", "other")),
                "lead_score": max(0, min(100, int(data.get("lead_score", 0) or 0))),
                "handoff": bool(data.get("handoff", False)),
                "ask_for_contact": bool(data.get("ask_for_contact", False)),
            }
        except (ValueError, TypeError):
            pass
    return {"answer": raw.strip() or fallback, "intent": "other",
            "lead_score": 0, "handoff": False, "ask_for_contact": False}


def answer(question: str, chunks: list[dict[str, Any]], context: str,
           history: list[dict[str, str]], site: str | None = None) -> dict[str, Any]:
    """Main entry point. Never raises - a broken provider falls back to demo mode."""
    conf = config.site_conf(site)
    if config.LLM_PROVIDER == "demo":
        return _demo_reply(question, chunks, site)

    system = SYSTEM_PROMPT.format(agent=conf["agent"], company=conf["company"])
    messages = [
        *history[-6:],
        {"role": "user", "content": USER_TEMPLATE.format(
            context=context or "(no matching documents)", question=question)},
    ]
    try:
        if config.LLM_PROVIDER == "anthropic":
            raw = _anthropic_chat(system, messages)
            model = config.ANTHROPIC_MODEL
        else:
            raw = _openai_chat(system, messages)
            model = config.OPENAI_MODEL
    except Exception as exc:  # noqa: BLE001 - a live widget must always reply
        result = _demo_reply(question, chunks, site)
        result["model"] = f"demo-fallback ({type(exc).__name__})"
        return result

    result = _parse_envelope(raw, "Let me get a human to confirm that for you.")
    result["model"] = model
    return result
