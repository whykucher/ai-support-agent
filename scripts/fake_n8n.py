"""A stand-in for n8n: accepts the lead webhook, verifies the signature, prints it.

    python -m scripts.fake_n8n              # listens on http://127.0.0.1:5999

Then point the app at it and restart:

    N8N_WEBHOOK_URL=http://127.0.0.1:5999/webhook/lead-intake

Why this exists: n8n needs Docker, and on a client call you rarely want to boot
it just to prove leads leave the building. This shows the outbound half of the
integration - signature and all - in one terminal window.
"""
import hashlib
import hmac
import json
import os
import sys
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

SECRET = os.getenv("N8N_WEBHOOK_SECRET", "")
received = 0


class Handler(BaseHTTPRequestHandler):
    def do_POST(self) -> None:  # noqa: N802 - name fixed by BaseHTTPRequestHandler
        global received
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length)

        signature_state = "not checked (no secret set)"
        if SECRET:
            expected = hmac.new(SECRET.encode(), raw, hashlib.sha256).hexdigest()
            got = self.headers.get("X-Signature", "")
            if not hmac.compare_digest(expected, got):
                print("  !! REJECTED: bad signature")
                self.send_response(401)
                self.end_headers()
                self.wfile.write(b'{"error":"bad signature"}')
                return
            signature_state = "verified"

        try:
            lead = json.loads(raw)
        except ValueError:
            lead = {"raw": raw.decode("utf-8", "replace")}

        received += 1
        stamp = datetime.now().strftime("%H:%M:%S")
        print(f"\n[{stamp}] lead #{received}  signature: {signature_state}")
        print(f"  {lead.get('priority', '?').upper():5} score={lead.get('lead_score')} "
              f"intent={lead.get('intent')}")
        print(f"  {lead.get('name') or '(no name)'} <{lead.get('email') or '-'}> "
              f"{lead.get('phone') or ''}".rstrip())
        print(f"  page: {lead.get('source_page') or '-'}")
        turns = lead.get("transcript") or []
        if turns:
            print(f"  transcript: {len(turns)} message(s), first: "
                  f"{turns[0].get('content', '')[:70]}...")

        body = json.dumps({"ok": True, "lead_id": lead.get("lead_id")}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_: object) -> None:
        """Silence the default one-line-per-request access log."""


def main() -> int:
    port = int(os.getenv("FAKE_N8N_PORT", "5999"))
    print(f"fake n8n listening on http://127.0.0.1:{port}/webhook/lead-intake")
    print(f"signature checking: {'on' if SECRET else 'off (set N8N_WEBHOOK_SECRET)'}")
    print("Ctrl+C to stop\n")
    try:
        HTTPServer(("127.0.0.1", port), Handler).serve_forever()
    except KeyboardInterrupt:
        print(f"\nstopped after {received} lead(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
