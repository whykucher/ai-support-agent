"""Vercel entry point.

Vercel's Python runtime looks for an ASGI or WSGI callable named `app` in a
file under api/. The application itself is unchanged - this only puts it where
the platform expects to find it, and pushes the repository root onto the path
so `app.config.ROOT` still resolves to the checkout rather than to api/.

Read this before relying on the deployment: Vercel functions get a read-only
filesystem apart from /tmp, and /tmp belongs to one instance and disappears
with it. SQLite therefore does not persist here. Retrieval and chat work,
because the index is rebuilt from knowledge/ on cold start, but a captured
lead lives only on whichever instance answered, and the run ledger the front
page reads is per-instance rather than a record of everything the app has
done. See docs/DEPLOY-VERCEL-RU.md.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.main import app  # noqa: E402

__all__ = ["app"]
