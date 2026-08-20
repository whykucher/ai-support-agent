"""Capture the portfolio screenshots by driving the real app in a real browser.

    python -m scripts.screenshots                 # against http://127.0.0.1:8010
    python -m scripts.screenshots --base <url>    # or against the deployed site

Writes docs/screenshots/*.png at 2x. Regenerate after any UI change instead of
re-cropping by hand - that is the whole point of scripting it.

Requires:  pip install -r requirements-dev.txt  &&  playwright install chromium
"""
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

OUT = ROOT / "docs" / "screenshots"
WIDTH, HEIGHT = 1440, 950


def main() -> int:
    from playwright.sync_api import sync_playwright

    parser = argparse.ArgumentParser(description="Capture portfolio screenshots")
    parser.add_argument("--base", default="http://127.0.0.1:8010")
    parser.add_argument("--token", default="demo-admin-token")
    args = parser.parse_args()
    base = args.base.rstrip("/")

    OUT.mkdir(parents=True, exist_ok=True)
    shots: list[tuple[str, str]] = []

    def shot(page, name: str, caption: str) -> None:
        page.screenshot(path=OUT / name)
        shots.append((name, caption))

    with sync_playwright() as p:
        browser = p.chromium.launch()
        # Pin locale and timezone: the dashboard formats dates with the browser
        # locale, and screenshots aimed at English-speaking clients should not
        # come out in whatever locale this machine happens to run.
        ctx = browser.new_context(
            viewport={"width": WIDTH, "height": HEIGHT},
            device_scale_factor=2, locale="en-US",
            timezone_id="America/Los_Angeles",
        )
        page = ctx.new_page()

        # --- 1. the portfolio as a visitor first meets it -------------------
        page.goto(base, wait_until="networkidle")
        page.evaluate("localStorage.clear()")
        page.reload(wait_until="networkidle")
        page.wait_for_timeout(2600)   # let the two lanes finish drawing
        shot(page, "00-portfolio.png",
             "Portfolio hero: the same enquiry by hand and by agent")

        # --- 2. the assistant answering, with the run log beside it ---------
        page.click(".asks button")
        page.wait_for_selector(".nw-msg.bot", state="visible", timeout=30_000)
        page.wait_for_timeout(6_500)  # the feed polls every 5s
        page.locator("#live").scroll_into_view_if_needed()
        page.wait_for_timeout(600)
        shot(page, "01-live-agent.png",
             "Ask a question and watch it land in the live run log")

        # --- 3. the lab, mid-result ------------------------------------------
        page.goto(f"{base}/lab", wait_until="networkidle")
        page.click("#cl-go")
        page.wait_for_selector("#cl-out .stats", timeout=30_000)
        page.locator("#classify").scroll_into_view_if_needed()
        page.wait_for_timeout(600)
        shot(page, "02-lab-classify.png",
             "Message classifier: intent, score, entities, routing")

        page.click("#cs-go")
        page.wait_for_selector("#cs-out .stats", timeout=30_000)
        page.locator("#clean").scroll_into_view_if_needed()
        page.wait_for_timeout(600)
        shot(page, "03-lab-clean.png",
             "CSV cleaner: dedupe, normalise, flag, hand the file back")

        # --- 4. the client-facing demo ---------------------------------------
        page.goto(f"{base}/demo", wait_until="networkidle")
        page.wait_for_timeout(2600)
        shot(page, "04-client-demo.png", "The storefront the agent was built for")

        page.click(".nw-launcher")
        page.fill("#nw-input",
                  "I run a cafe and need wholesale pricing for about 80 lb a month")
        page.press("#nw-input", "Enter")
        page.wait_for_selector(".nw-lead", timeout=30_000)
        page.wait_for_timeout(600)
        shot(page, "05-lead-capture.png",
             "Buying intent detected: the bot stops answering and starts qualifying")

        # --- 5. operations ----------------------------------------------------
        page.goto(f"{base}/admin", wait_until="networkidle")
        page.evaluate("t => { localStorage.setItem('nw_admin_token', t);"
                      " localStorage.setItem('nw_admin_site', ''); }", args.token)
        page.reload(wait_until="networkidle")
        page.wait_for_selector("#leads tr", timeout=30_000)
        page.click("#leads tr:first-child")
        page.wait_for_selector("#tx .msg", timeout=30_000)
        page.wait_for_timeout(600)
        shot(page, "06-ops-leads.png",
             "Ops: leads across both sites, with the transcript behind each")

        page.click("[data-tab=runs]")
        page.wait_for_timeout(700)
        shot(page, "07-ops-runs.png",
             "Ops: every automation the app has performed")

        # --- 6. the widget on a phone ------------------------------------------
        mobile = browser.new_context(
            viewport={"width": 390, "height": 844}, device_scale_factor=3,
            is_mobile=True, has_touch=True, locale="en-US",
            timezone_id="America/Los_Angeles",
        )
        mpage = mobile.new_page()
        mpage.goto(base, wait_until="networkidle")
        mpage.click(".nw-launcher")
        mpage.fill("#nw-input", "How long does a project take?")
        mpage.press("#nw-input", "Enter")
        mpage.wait_for_selector(".nw-sources", state="visible", timeout=30_000)
        mpage.wait_for_timeout(600)
        shot(mpage, "08-mobile.png", "Same widget on a phone, no separate build")

        mobile.close()
        browser.close()

    print(f"wrote {len(shots)} screenshots to {OUT}")
    for name, caption in shots:
        size_kb = (OUT / name).stat().st_size // 1024
        print(f"  {name:24} {size_kb:>5} KB   {caption}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
