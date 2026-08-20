"""Working demonstrations, not mockups.

Three of the jobs clients actually ask for, each running for real on the server
and each needing no API key:

* `scrape`   - fetch a page and pull out the structured bits
* `classify` - score a message for intent and extract the entities in it
* `clean`    - deduplicate and normalise a pasted CSV

Everything is stdlib plus httpx, which is already a dependency. No BeautifulSoup,
no pandas: on inputs this size they buy nothing and cost two more packages.
"""
import csv
import io
import ipaddress
import re
import socket
import time
from html.parser import HTMLParser
from typing import Any
from urllib.parse import urljoin, urlparse

import httpx

from . import db

MAX_BYTES = 900_000
FETCH_TIMEOUT = httpx.Timeout(12.0, connect=6.0)
USER_AGENT = "Mozilla/5.0 (compatible; PortfolioLabBot/1.0; +demo)"

EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]{2,}")
PHONE_RE = re.compile(r"(?:\+?\d[\d\s().-]{8,17}\d)")
# Anchored decimals so a sentence-ending full stop is not read as part of the
# amount: "$3,000." must extract as "$3,000", not "$3,000.".
MONEY_RE = re.compile(
    r"(?:[$€£]\s?\d[\d,]*(?:\.\d{1,2})?"
    r"|\d[\d,]*(?:\.\d{1,2})?\s?(?:USD|EUR|GBP|usd|eur|gbp))")
DATE_RE = re.compile(
    r"\b(?:\d{4}-\d{2}-\d{2}|\d{1,2}[./]\d{1,2}[./]\d{2,4}"
    r"|(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{1,2})\b")
URGENT_RE = re.compile(r"\b(urgent|asap|immediately|today|right now|deadline)\b", re.I)


# --- URL safety -------------------------------------------------------------

class UnsafeURL(ValueError):
    """Raised for anything we refuse to fetch."""


def assert_fetchable(url: str) -> str:
    """Reject anything that is not a public http(s) address.

    This endpoint takes a URL from the internet and fetches it from inside the
    server, which is exactly the shape of an SSRF hole. Resolving the host first
    and refusing private, loopback, link-local and reserved ranges closes the
    obvious version of it.
    """
    parsed = urlparse(url if "://" in url else f"https://{url}")
    if parsed.scheme not in {"http", "https"}:
        raise UnsafeURL("Only http and https addresses can be fetched.")
    if not parsed.hostname:
        raise UnsafeURL("That does not look like a web address.")

    try:
        infos = socket.getaddrinfo(parsed.hostname, None)
    except socket.gaierror as exc:
        raise UnsafeURL(f"Could not resolve {parsed.hostname}.") from exc

    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if (ip.is_private or ip.is_loopback or ip.is_link_local
                or ip.is_reserved or ip.is_multicast):
            raise UnsafeURL("That address is on a private network, so it is not fetched.")

    return parsed.geturl()


# --- scraping ---------------------------------------------------------------

class PageParser(HTMLParser):
    """Pulls the parts of a page a client usually wants, and nothing else."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title = ""
        self.meta: dict[str, str] = {}
        self.headings: list[dict[str, str]] = []
        self.links: list[dict[str, str]] = []
        self.text_parts: list[str] = []
        self._tag: str | None = None
        self._href: str | None = None
        self._buf: list[str] = []
        self._skip = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        a = {k: (v or "") for k, v in attrs}
        if tag in {"script", "style", "noscript", "svg"}:
            self._skip += 1
        elif tag == "meta":
            key = (a.get("name") or a.get("property") or "").lower()
            if key in {"description", "og:title", "og:description", "og:site_name",
                       "author", "keywords"} and a.get("content"):
                self.meta[key] = a["content"].strip()[:400]
        elif tag in {"h1", "h2", "h3", "title"}:
            self._tag, self._buf = tag, []
        elif tag == "a" and a.get("href"):
            self._tag, self._href, self._buf = "a", a["href"], []

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "noscript", "svg"}:
            self._skip = max(0, self._skip - 1)
            return
        if tag != self._tag:
            return
        text = " ".join("".join(self._buf).split())[:200]
        if tag == "title":
            self.title = text
        elif tag in {"h1", "h2", "h3"} and text:
            self.headings.append({"level": tag, "text": text})
        elif tag == "a" and text and self._href:
            self.links.append({"text": text, "href": self._href})
        self._tag, self._href, self._buf = None, None, []

    def handle_data(self, data: str) -> None:
        if self._skip:
            return
        if self._tag:
            self._buf.append(data)
        stripped = data.strip()
        if stripped:
            self.text_parts.append(stripped)


def scrape(url: str) -> dict[str, Any]:
    """Fetch one page and return the structured parts of it."""
    started = time.perf_counter()
    safe = assert_fetchable(url)

    with httpx.Client(follow_redirects=True, timeout=FETCH_TIMEOUT,
                      headers={"User-Agent": USER_AGENT}) as client:
        resp = client.get(safe)
        resp.raise_for_status()
        html = resp.text[:MAX_BYTES]

    parser = PageParser()
    parser.feed(html)

    body = " ".join(parser.text_parts)
    internal, external = [], []
    host = urlparse(str(resp.url)).netloc
    for link in parser.links:
        absolute = urljoin(str(resp.url), link["href"])
        (internal if urlparse(absolute).netloc == host else external).append(
            {"text": link["text"], "href": absolute})

    result = {
        "url": str(resp.url),
        "status": resp.status_code,
        "title": parser.title or parser.meta.get("og:title", ""),
        "description": parser.meta.get("description") or parser.meta.get("og:description", ""),
        "site_name": parser.meta.get("og:site_name", ""),
        "headings": parser.headings[:25],
        "emails": sorted(set(EMAIL_RE.findall(body)))[:15],
        "phones": sorted({p.strip() for p in PHONE_RE.findall(body)})[:10],
        "links": {
            "internal": len(internal),
            "external": len(external),
            "sample": (internal[:5] + external[:5])[:8],
        },
        "words": len(body.split()),
        "html_bytes": len(html),
        "duration_ms": int((time.perf_counter() - started) * 1000),
    }
    db.add_run("lab.scrape", site="portfolio", summary=f"Scraped {host}",
               detail={"url": result["url"], "headings": len(result["headings"]),
                       "emails": len(result["emails"]), "words": result["words"]},
               duration_ms=result["duration_ms"])
    return result


# --- classification ---------------------------------------------------------

_INTENTS: list[tuple[str, tuple[str, ...], int]] = [
    ("complaint", ("refund", "broken", "damaged", "not working", "complaint",
                   "disappointed", "cancel my", "terrible"), 20),
    ("buying", ("quote", "pricing", "how much", "budget", "hire", "proposal",
                "wholesale", "bulk", "contract", "invoice", "get started",
                "sign up", "purchase", "order"), 80),
    ("support", ("how do i", "where is", "cannot", "can't", "help me",
                 "not sure how", "reset", "login", "error"), 15),
    ("scheduling", ("call", "meeting", "available", "schedule", "book a",
                    "calendar", "next week"), 60),
]


def classify(text: str) -> dict[str, Any]:
    """Score one message the way the live agent scores conversations."""
    started = time.perf_counter()
    low = text.lower()

    # A complaint outranks everything, even a purchase in the same message:
    # "your last order arrived broken, and I want to reorder" is a person who
    # needs a human first. Otherwise the highest-value match wins.
    matches = [(name, base, [w for w in words if w in low])
               for name, words, base in _INTENTS]
    matches = [m for m in matches if m[2]]
    complaint = next((m for m in matches if m[0] == "complaint"), None)
    best = complaint or (max(matches, key=lambda m: m[1]) if matches else None)
    intent, score, hits = best or ("question", 10, [])

    urgent = bool(URGENT_RE.search(text))
    if urgent and intent in {"buying", "scheduling"}:
        score = min(100, score + 10)

    entities = {
        "emails": sorted(set(EMAIL_RE.findall(text))),
        "phones": sorted({p.strip() for p in PHONE_RE.findall(EMAIL_RE.sub("", text))}),
        "amounts": sorted(set(MONEY_RE.findall(text))),
        "dates": sorted(set(DATE_RE.findall(text))),
    }
    if entities["emails"] or entities["phones"]:
        score = min(100, score + 15)

    # Cyrillic vs Latin is enough of a language signal for routing purposes.
    cyrillic = len(re.findall(r"[Ѐ-ӿ]", text))
    latin = len(re.findall(r"[A-Za-z]", text))
    language = "ru" if cyrillic > latin else "en"

    result = {
        "intent": intent,
        "lead_score": score,
        "priority": "hot" if score >= 60 else "warm" if score >= 30 else "cold",
        "urgent": urgent,
        "language": language,
        "matched_terms": hits[:6],
        "entities": entities,
        "route": {
            "buying": "Sales channel + CRM, immediately",
            "scheduling": "Calendar link, then sales",
            "complaint": "Human agent, skip the bot",
            "support": "Knowledge base answer, no hand-off",
            "question": "Knowledge base answer, no hand-off",
        }[intent],
        "duration_ms": int((time.perf_counter() - started) * 1000),
    }
    db.add_run("lab.classify", site="portfolio",
               summary=f"Classified as {intent} ({score})",
               detail={"intent": intent, "score": score, "language": language},
               duration_ms=result["duration_ms"])
    return result


# --- CSV clean-up -----------------------------------------------------------

def _normalise_cell(value: str, header: str) -> str:
    v = " ".join(value.split())
    h = header.lower()
    if "mail" in h:
        return v.lower()
    if "phone" in h or "tel" in h:
        digits = re.sub(r"[^\d+]", "", v)
        return digits
    if h in {"name", "company", "city", "country"}:
        return v.title() if v.isupper() or v.islower() else v
    return v


def clean_csv(raw: str) -> dict[str, Any]:
    """Trim, normalise and deduplicate a pasted table, and say what changed."""
    started = time.perf_counter()
    text = raw.strip()
    if not text:
        raise ValueError("Paste some rows first.")

    dialect_delim = "\t" if text.count("\t") > text.count(",") else ","
    rows = list(csv.reader(io.StringIO(text), delimiter=dialect_delim))
    if len(rows) < 2:
        raise ValueError("Needs a header row and at least one data row.")

    header = [h.strip() or f"column_{i+1}" for i, h in enumerate(rows[0])]
    width = len(header)

    seen: set[tuple[str, ...]] = set()
    cleaned: list[list[str]] = []
    duplicates = blanks = padded = 0

    for row in rows[1:]:
        if not any(c.strip() for c in row):
            blanks += 1
            continue
        if len(row) != width:
            padded += 1
            row = (row + [""] * width)[:width]
        norm = [_normalise_cell(c, header[i]) for i, c in enumerate(row)]
        key = tuple(v.lower() for v in norm)
        if key in seen:
            duplicates += 1
            continue
        seen.add(key)
        cleaned.append(norm)

    out = io.StringIO()
    writer = csv.writer(out, lineterminator="\n")
    writer.writerow(header)
    writer.writerows(cleaned)

    invalid_emails = 0
    for i, h in enumerate(header):
        if "mail" in h.lower():
            invalid_emails = sum(
                1 for r in cleaned if r[i] and not EMAIL_RE.fullmatch(r[i]))

    result = {
        "columns": header,
        "rows_in": len(rows) - 1,
        "rows_out": len(cleaned),
        "duplicates_removed": duplicates,
        "blank_rows_removed": blanks,
        "ragged_rows_padded": padded,
        "invalid_emails": invalid_emails,
        "preview": cleaned[:8],
        "csv": out.getvalue(),
        "duration_ms": int((time.perf_counter() - started) * 1000),
    }
    db.add_run("lab.clean", site="portfolio",
               summary=f"Cleaned {result['rows_in']} rows to {result['rows_out']}",
               detail={k: result[k] for k in
                       ("rows_in", "rows_out", "duplicates_removed", "blank_rows_removed")},
               duration_ms=result["duration_ms"])
    return result
