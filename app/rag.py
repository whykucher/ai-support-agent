"""Retrieval: markdown -> chunks -> hybrid search (BM25 keyword + optional vectors).

The keyword half is always on. That is what makes demo mode work with zero API
keys, and in production it is the half that saves you when a customer types an
exact SKU or order number that an embedding model happily blurs away.
"""
import json
import math
import re
from collections import Counter
from pathlib import Path
from typing import Any

from . import config, db

HEADING_BOOST = 3  # how many times a heading token is counted vs a body token

# Cyrillic has to be in the character class or Russian input tokenises to
# nothing at all and the assistant silently answers every question with "I do
# not know" - which looks like a content problem and is not.
_WORD = re.compile(r"[a-zа-яё0-9]+")

_STOP_EN = {
    "the", "a", "an", "and", "or", "is", "are", "do", "does", "to", "of", "in",
    "for", "on", "it", "i", "you", "we", "my", "your", "can", "how", "what",
    "with", "at", "be", "have", "has", "will", "if", "this", "that", "from",
}

_STOP_RU = {
    "и", "в", "во", "не", "что", "он", "на", "я", "с", "со", "как", "а", "то",
    "все", "она", "так", "его", "но", "да", "ты", "к", "у", "же", "вы", "за",
    "бы", "по", "только", "её", "ее", "мне", "было", "вот", "от", "меня", "ещё",
    "еще", "нет", "о", "из", "ему", "когда", "ли", "если", "уже", "или", "ни",
    "быть", "был", "до", "вас", "вам", "там", "себя", "ей", "они", "тут", "где",
    "есть", "для", "мы", "тебя", "их", "чем", "была", "без", "чего", "раз",
    "тоже", "себе", "под", "будет", "тогда", "кто", "этот", "того", "потому",
    "этого", "какой", "ним", "здесь", "этом", "мой", "тем", "чтобы", "были",
    "куда", "зачем", "всех", "можно", "при", "об", "другой", "после", "над",
    "тот", "через", "эти", "нас", "про", "всего", "них", "какая", "эту", "моя",
    "этой", "перед", "том", "такой", "им", "более", "всю", "между", "надо",
    "сколько", "нужно", "ваш", "ваша", "ваши", "нам", "мною",
}

_STOP = _STOP_EN | _STOP_RU

# Longest first. Russian is heavily inflected: without this, "доставка",
# "доставки" and "доставку" are three unrelated words and a customer asking
# about delivery matches nothing.
_RU_ENDINGS = (
    "иями", "ями", "ами", "ого", "его", "ому", "ему", "ыми", "ими", "ться",
    "тся", "ых", "их", "ой", "ей", "ий", "ый", "ая", "яя", "ое", "ее", "ые",
    "ие", "ах", "ях", "ам", "ям", "ом", "ем", "ов", "ев", "ью", "ия", "ии",
    "а", "я", "ы", "и", "о", "е", "у", "ю", "ь", "й",
)

_CYRILLIC = re.compile(r"[а-яё]")


def _stem_ru(word: str) -> str:
    """Strip one inflectional ending, keeping at least four characters.

    The floor matters: without it "цена" collapses to "ц" and every short word
    in the corpus collides with every other.
    """
    for end in _RU_ENDINGS:
        # Three characters is enough after a short ending, so "цена"/"цены"
        # both reach "цен" and "оптом" reaches "опт" - without the second case
        # a customer asking to buy "оптом" never finds the wholesale section.
        # Endings of three or more need a longer stem left, or short words
        # collide with everything.
        floor = 3 if len(end) <= 2 else 4
        if word.endswith(end) and len(word) - len(end) >= floor:
            return word[: -len(end)]
    return word


def _stem_en(word: str) -> str:
    """Crude suffix stripping, applied identically to documents and queries.

    A stemmer only has to be *consistent*, not linguistically correct: both
    sides of the comparison go through it. Without this, "how much does it
    cost" misses a section that says "running costs" - the single most common
    question a prospect asks.
    """
    # Plurals first, so "cancellations" reaches the same place as "cancellation".
    if len(word) > 4 and word.endswith("ies"):
        word = word[:-3] + "y"
    elif len(word) > 4 and word.endswith(("ses", "xes", "zes", "ches", "shes")):
        word = word[:-2]
    elif len(word) > 3 and word.endswith("s") and not word.endswith("ss"):
        word = word[:-1]

    for suffix, keep in (("ing", 5), ("edly", 6), ("ed", 4), ("ly", 4)):
        if len(word) > keep and word.endswith(suffix):
            word = word[: -len(suffix)]
            break

    # Nominalisations: "can I cancel" has to reach a section headed
    # "cancellation". The four-character floor stops "station" -> "st".
    for suffix in ("ation", "ment", "ance", "ence"):
        if word.endswith(suffix) and len(word) - len(suffix) >= 4:
            word = word[: -len(suffix)]
            break

    if len(word) > 4 and word[-1] == word[-2] and word[-1] != "s":
        word = word[:-1]
    if len(word) > 4 and word.endswith("e"):
        word = word[:-1]
    return word


def tokenize(text: str) -> list[str]:
    """Lowercase, fold e-diaeresis, drop stopwords, stem by script.

    Russian writers use e for e-diaeresis about as often as not, so "sch-e-t"
    and "sch-yo-t" are the same word to a reader and two different words to an
    index. Folding one into the other on both sides costs one replace.
    """
    out: list[str] = []
    for w in _WORD.findall(text.lower().replace("ё", "е")):
        if w in _STOP or len(w) < 2:
            continue
        out.append(_stem_ru(w) if _CYRILLIC.search(w) else _stem_en(w))
    return out


# --- ingestion --------------------------------------------------------------

def chunk_markdown(text: str, max_chars: int = 900) -> list[dict[str, Any]]:
    """Split on markdown headings, then pack paragraphs up to max_chars.

    Heading-aware splitting keeps a Q&A or policy section intact, which matters
    far more for answer quality than any clever overlap strategy.
    """
    chunks: list[dict[str, Any]] = []
    heading = ""
    buffer: list[str] = []

    def flush() -> None:
        body = "\n".join(buffer).strip()
        buffer.clear()
        if body:
            chunks.append({"heading": heading, "content": body, "tokens": len(body) // 4})

    for line in text.splitlines():
        if line.startswith("#"):
            flush()
            heading = line.lstrip("#").strip()
            continue
        buffer.append(line)
        if sum(len(x) for x in buffer) > max_chars and not line.strip():
            flush()
    flush()
    return chunks


def ingest_directory(directory: Path | None = None, *, embed: bool = True) -> dict[str, int]:
    """Index every .md/.txt under the knowledge folder.

    A first-level subdirectory is a site: knowledge/portfolio/*.md answers as
    the portfolio, knowledge/demo/*.md answers as the demo shop. Files sitting
    loose at the root fall back to DEFAULT_SITE so an existing flat folder keeps
    working without being reorganised.
    """
    from . import llm  # local import: keeps ingestion usable without a provider

    directory = directory or config.KNOWLEDGE_DIR
    result: dict[str, int] = {}
    for path in sorted(directory.glob("**/*")):
        if path.suffix.lower() not in {".md", ".txt"} or not path.is_file():
            continue
        rel = path.relative_to(directory)
        site = rel.parts[0] if len(rel.parts) > 1 else config.DEFAULT_SITE

        rows = chunk_markdown(path.read_text(encoding="utf-8"))
        if embed and config.LLM_PROVIDER != "demo":
            texts = [f"{r['heading']}\n{r['content']}" for r in rows]
            for row, vector in zip(rows, llm.embed(texts)):
                row["embedding"] = vector
        result[f"{site}/{path.name}"] = db.replace_chunks(site, path.name, rows)
    return result


# --- scoring ----------------------------------------------------------------

def _bm25(query_tokens: list[str], docs: list[list[str]]) -> list[float]:
    """BM25 with a coordination factor. ~45 lines beats a dependency here.

    The coordination factor is the part that matters in practice. Without it a
    short section that happens to contain one rare query word ("long" in a
    storage tip) outranks the shipping policy that actually answers "how long
    does shipping take" - BM25 rewards rare terms in short documents. Scaling by
    the share of query terms a chunk covers puts the real answer back on top.
    """
    k1, b = 1.5, 0.75
    n = len(docs)
    terms = set(query_tokens)
    if not n or not terms:
        return [0.0] * n

    avg_len = sum(len(d) for d in docs) / n
    df = Counter()
    for doc in docs:
        df.update(set(doc))

    scores = [0.0] * n
    matched = [0] * n
    for term in terms:
        if term not in df:
            continue
        idf = math.log(1 + (n - df[term] + 0.5) / (df[term] + 0.5))
        for i, doc in enumerate(docs):
            tf = doc.count(term)
            if not tf:
                continue
            scores[i] += idf * (tf * (k1 + 1)) / (tf + k1 * (1 - b + b * len(doc) / avg_len))
            matched[i] += 1

    return [s * (matched[i] / len(terms)) for i, s in enumerate(scores)]


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0


def _normalise(values: list[float]) -> list[float]:
    top = max(values, default=0.0)
    return [v / top for v in values] if top > 0 else [0.0] * len(values)


def search(query: str, site: str | None = None,
           k: int | None = None) -> list[dict[str, Any]]:
    """Hybrid retrieval inside one site. Returns chunks by blended relevance."""
    from . import llm

    k = k or config.TOP_K
    rows = db.site_chunks(site or config.DEFAULT_SITE)
    if not rows:
        return []

    # Headings are repeated so a term in "Shipping and delivery" outweighs the
    # same term buried in a paragraph - a cheap stand-in for field boosting.
    docs = [tokenize(r["heading"]) * HEADING_BOOST + tokenize(r["content"]) for r in rows]
    keyword = _normalise(_bm25(tokenize(query), docs))

    vector = [0.0] * len(rows)
    have_vectors = any(r["embedding"] for r in rows)
    if have_vectors and config.LLM_PROVIDER != "demo":
        try:
            q_vec = llm.embed([query])[0]
            vector = _normalise([
                _cosine(q_vec, json.loads(r["embedding"])) if r["embedding"] else 0.0
                for r in rows
            ])
        except Exception:  # noqa: BLE001 - retrieval must degrade, not crash the chat
            have_vectors = False

    # 50/50 when both signals exist; keyword-only otherwise.
    weight = 0.5 if have_vectors else 1.0
    ranked = sorted(
        (
            {
                "id": r["id"],
                "source": r["source"],
                "heading": r["heading"],
                "content": r["content"],
                "score": round(weight * keyword[i] + (1 - weight) * vector[i], 4),
            }
            for i, r in enumerate(rows)
        ),
        key=lambda c: c["score"],
        reverse=True,
    )
    return [c for c in ranked[:k] if c["score"] > 0.01]


def build_context(chunks: list[dict[str, Any]], budget: int = 4000) -> str:
    parts, used = [], 0
    for c in chunks:
        block = f"[{c['source']} > {c['heading'] or 'general'}]\n{c['content']}"
        if used + len(block) > budget:
            break
        parts.append(block)
        used += len(block)
    return "\n\n---\n\n".join(parts)
