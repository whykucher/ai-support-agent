"""Capture the portfolio screenshots by driving the real app in a real browser.

    python -m scripts.screenshots                 # against http://127.0.0.1:8010
    python -m scripts.screenshots --base <url>    # or against the deployed site

Writes docs/screenshots/*.png at 2x for crisp uploads. Regenerate these after
any UI change instead of re-cropping by hand - that is the whole point.

Requires:  pip install playwright  &&  playwright install chromium
"""
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

OUT = ROOT / "docs" / "screenshots"
WIDTH, HEIGHT = 1440, 900

SHIPPING_Q = "How fast is shipping, and do you deliver to Canada?"
WHOLESALE_Q = "I run a cafe and need wholesale pricing for about 80 lb a month"


def main() -> int:
    from playwright.sync_api import sync_playwright

    parser = argparse.ArgumentParser(description="Capture portfolio screenshots")
    parser.add_argument("--base", default="http://127.0.0.1:8010")
    parser.add_argument("--token", default="demo-admin-token")
    args = parser.parse_args()
    base = args.base.rstrip("/")

    OUT.mkdir(parents=True, exist_ok=True)
    shots: list[tuple[str, str]] = []

    with sync_playwright() as p:
        browser = p.chromium.launch()
        # Pin locale/timezone: the dashboard formats dates with the browser
        # locale, and screenshots aimed at English-speaking clients should not
        # come out in whatever locale this machine happens to run.
        ctx = browser.new_context(
            viewport={"width": WIDTH, "height": HEIGHT},
            device_scale_factor=2,
            locale="en-US",
            timezone_id="America/Los_Angeles",
        )
        page = ctx.new_page()

        # --- 1. grounded answer with source chips ---------------------------
        page.goto(base, wait_until="networkidle")
        page.evaluate("localStorage.removeItem('nw_conversation_id')")
        page.reload(wait_until="networkidle")

        page.click(".nw-launcher")
        page.fill("#nw-input", SHIPPING_Q)
        page.press("#nw-input", "Enter")
        page.wait_for_selector(".nw-sources", timeout=30_000)
        page.wait_for_timeout(600)
        page.screenshot(path=OUT / "01-grounded-answer.png")
        shots.append(("01-grounded-answer.png", "Answer built from the knowledge base, with the source sections shown"))

        # --- 2. buying intent detected, lead form appears -------------------
        page.fill("#nw-input", WHOLESALE_Q)
        page.press("#nw-input", "Enter")
        page.wait_for_selector(".nw-lead", timeout=30_000)
        page.wait_for_timeout(600)
        page.screenshot(path=OUT / "02-lead-capture.png")
        shots.append(("02-lead-capture.png", "Buying intent detected - the bot stops answering and starts qualifying"))

        # Submit the lead so the dashboard shot has a fresh row to show.
        page.fill("#nw-l-name", "Marta Iversen")
        page.fill("#nw-l-email", "marta@harborlanecafe.example")
        page.click("#nw-l-send")
        page.wait_for_selector(".nw-done", timeout=30_000)

        # --- 3. ops dashboard with a transcript open ------------------------
        page.goto(f"{base}/admin", wait_until="networkidle")
        page.evaluate("t => localStorage.setItem('nw_admin_token', t)", args.token)
        page.reload(wait_until="networkidle")
        page.wait_for_selector("#leads tr", timeout=30_000)
        page.click("#leads tr:first-child")
        page.wait_for_selector("#tx .msg", timeout=30_000)
        page.wait_for_timeout(600)
        page.screenshot(path=OUT / "03-ops-dashboard.png")
        shots.append(("03-ops-dashboard.png", "Ops dashboard: deflection rate, captured leads, delivery status, transcripts"))

        # --- 4. the widget on a phone ---------------------------------------
        mobile = browser.new_context(
            viewport={"width": 390, "height": 844},
            device_scale_factor=3,
            is_mobile=True,
            has_touch=True,
            locale="en-US",
            timezone_id="America/Los_Angeles",
        )
        mpage = mobile.new_page()
        mpage.goto(base, wait_until="networkidle")
        mpage.click(".nw-launcher")
        mpage.fill("#nw-input", "Can I pause my subscription for a month?")
        mpage.press("#nw-input", "Enter")
        mpage.wait_for_selector(".nw-sources", timeout=30_000)
        mpage.wait_for_timeout(600)
        mpage.screenshot(path=OUT / "04-mobile.png")
        shots.append(("04-mobile.png", "Same widget on a phone - no separate mobile build"))

        mobile.close()
        browser.close()

    print(f"wrote {len(shots)} screenshots to {OUT}")
    for name, caption in shots:
        size_kb = (OUT / name).stat().st_size // 1024
        print(f"  {name:26} {size_kb:>5} KB   {caption}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
