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
        page.wait_for_timeout(1200)
        shot(page, "00-portfolio.png",
             "The hero is the execution chain, waiting for a question")

        # --- 2. a real question run through the real chain ------------------
        # Seed 1 is commercial, so the router fires and the whole chain settles.
        page.click("#seeds button:nth-child(1)")
        page.wait_for_selector("#result:not([hidden])", timeout=30_000)
        page.wait_for_timeout(900)
        shot(page, "01-live-agent.png",
             "One question, five stages, every value read back from the request")

        # --- 2b. the same chain declining to route ----------------------------
        # Seed 3 is not a lead, and the Route node says so instead of firing.
        page.click("#seeds button:nth-child(3)")
        page.wait_for_timeout(2200)
        page.screenshot(path=OUT / "01b-not-routed.png")
        shots.append(("01b-not-routed.png",
                      "Below the threshold the router deliberately does not fire"))

        # --- 2c. the standalone business sites --------------------------------
        for key, label in [("agency", "Halyard Digital, performance marketing"),
                           ("realty", "Kestrel Property, estate agency"),
                           ("saas", "Latchkey, field-service SaaS")]:
            page.goto(f"{base}/b/{key}", wait_until="networkidle")
            page.wait_for_timeout(2200)
            shot(page, f"01c-site-{key}.png",
                 f"A whole site, not a card: {label}")

        # --- 2d. the Russian side ---------------------------------------------
        # Its own context: the run log prints relative times and the pages are
        # laid out for Cyrillic, so capturing them under en-US would show a
        # visitor something no Russian visitor would ever see.
        ru = browser.new_context(
            viewport={"width": WIDTH, "height": HEIGHT},
            device_scale_factor=2, locale="ru-RU",
            timezone_id="Europe/Moscow",
        )
        rupage = ru.new_page()

        rupage.goto(f"{base}/ru", wait_until="networkidle")
        rupage.evaluate("localStorage.clear()")
        rupage.reload(wait_until="networkidle")
        rupage.wait_for_timeout(1200)
        shot(rupage, "09-portfolio-ru.png",
             "Русская версия на том же движке: цепочка ждёт вопроса")

        rupage.click("#seeds button:nth-child(1)")
        rupage.wait_for_selector("#result:not([hidden])", timeout=30_000)
        rupage.wait_for_timeout(900)
        shot(rupage, "10-live-agent-ru.png",
             "Один вопрос, пять стадий, все значения из настоящего запроса")

        for key, label in [("ru-agency", "«Полдень», перформанс-маркетинг"),
                           ("ru-shop", "«Лоскут», магазин одежды из льна"),
                           ("ru-school", "«Ступень», онлайн-школа")]:
            rupage.goto(f"{base}/b/{key}", wait_until="networkidle")
            rupage.wait_for_timeout(2200)
            shot(rupage, f"11-site-{key}.png", f"Отдельный сайт: {label}")

        # The lead form on a Russian business, in Russian.
        rupage.goto(f"{base}/b/ru-shop", wait_until="networkidle")
        rupage.wait_for_timeout(1500)
        rupage.click(".nw-launcher")
        rupage.fill("#nw-input",
                    "Хочу закупить оптом партию рубашек, работаете с юрлицами?")
        rupage.press("#nw-input", "Enter")
        rupage.wait_for_selector(".nw-lead", timeout=30_000)
        rupage.wait_for_timeout(600)
        shot(rupage, "12-lead-capture-ru.png",
             "Замечено намерение купить: бот переходит к сбору контактов")

        ru.close()

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

        # --- 5b. the rebuilt portfolio on a phone --------------------------------
        # The chain is five wide on a desktop and has to stack without a
        # horizontal scrollbar, which is the failure mode of any node graph.
        narrow = browser.new_context(
            viewport={"width": 390, "height": 844}, device_scale_factor=3,
            is_mobile=True, has_touch=True, locale="en-US",
            timezone_id="America/Los_Angeles",
        )
        npage = narrow.new_page()
        npage.goto(base, wait_until="networkidle")
        npage.click("#seeds button:nth-child(1)")
        npage.wait_for_selector("#result:not([hidden])", timeout=30_000)
        npage.wait_for_timeout(700)
        shot(npage, "08b-portfolio-mobile.png",
             "The same chain stacked on a phone")
        narrow.close()

        # --- 6. the widget on a phone ------------------------------------------
        mobile = browser.new_context(
            viewport={"width": 390, "height": 844}, device_scale_factor=3,
            is_mobile=True, has_touch=True, locale="en-US",
            timezone_id="America/Los_Angeles",
        )
        mpage = mobile.new_page()
        mpage.goto(f"{base}/b/agency", wait_until="networkidle")
        mpage.click(".nw-launcher")
        mpage.fill("#nw-input", "How much do you charge to manage Google Ads?")
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
