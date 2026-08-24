"""Vercel entry point.

Vercel's Python runtime looks for an ASGI callable named `app` in a file under
api/. The application itself is unchanged - this only puts it where the
platform expects it, and pushes the repository root onto the path so
`app.config.ROOT` still resolves to the checkout rather than to api/.

Read this before relying on the deployment: Vercel functions get a read-only
filesystem apart from /tmp, and /tmp belongs to one instance and disappears
with it. SQLite therefore does not persist here. Retrieval and chat work,
because the index is rebuilt from knowledge/ on cold start, but a captured lead
lives only on whichever instance answered, and the run ledger the front page
reads is per-instance rather than a record of everything the app has done.
See docs/DEPLOY-VERCEL-RU.md.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app import db, rag  # noqa: E402
from app.main import app  # noqa: E402


def _warm() -> None:
    """Build the index at import rather than relying on the ASGI lifespan.

    A long-lived server runs lifespan once at boot and everything downstream
    can assume the database exists. Serverless adapters do not all run it, and
    an unindexed database answers every question with "I do not know" - a
    failure that looks like missing content rather than a missing startup hook.
    Module import happens exactly once per cold start, which is when this work
    belongs. The guards make it a no-op if the lifespan runs too.
    """
    db.init()
    if db.chunk_stats()["n"] == 0:
        rag.ingest_directory()
    from app import config
    if config.SEED_ON_START and db.metrics()["conversations"] == 0:
        from scripts.seed_demo import seed
        seed()


_warm()

__all__ = ["app"]
