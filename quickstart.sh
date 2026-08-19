#!/usr/bin/env bash
# One-command start on macOS/Linux.  Usage:  ./quickstart.sh [--seed] [--port 8000]
set -euo pipefail
cd "$(dirname "$0")"

PORT=8000
SEED=0
while [ $# -gt 0 ]; do
  case "$1" in
    --seed) SEED=1; shift ;;
    --port) PORT="$2"; shift 2 ;;
    *) echo "unknown option: $1"; exit 1 ;;
  esac
done

[ -d .venv ] || { echo "creating virtualenv..."; python3 -m venv .venv; }
PY=.venv/bin/python

echo "installing dependencies..."
"$PY" -m pip install --quiet --upgrade pip
"$PY" -m pip install --quiet -r requirements.txt

[ -f .env ] || { cp .env.example .env; echo "created .env (demo mode, no API key needed)"; }

echo "indexing knowledge base..."
"$PY" -m scripts.ingest --no-embed

[ "$SEED" = "1" ] && "$PY" -m scripts.seed_demo

echo
echo "storefront  http://127.0.0.1:$PORT/"
echo "dashboard   http://127.0.0.1:$PORT/admin   (token: demo-admin-token)"
echo

exec "$PY" -m uvicorn app.main:app --host 127.0.0.1 --port "$PORT"
