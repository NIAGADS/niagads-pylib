"""Optional end-to-end smoke test against the test-only API harness and Next.js.

Requires Playwright and Chromium. Start serve_prototype.py and the frontend first.
Run: python browser_smoke.py --url http://127.0.0.1:3010
"""

import argparse
from pathlib import Path

from playwright.sync_api import sync_playwright


def submit(page, question):
    """Send a question through the real browser/proxy/agent/tool stream."""
    page.get_by_label("Your question").fill(question)
    page.get_by_role("button", name="Ask NIAGADS", exact=True).click()
    page.locator("article").last.get_by_text("MOCK DATA:", exact=False).wait_for(
        timeout=60000
    )
    page.get_by_role("button", name="Stop response", exact=True).wait_for(
        state="detached", timeout=60000
    )


def main():
    """Check rendered evidence, mobile behavior, and deferred capabilities."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:3010")
    args = parser.parse_args()
    with sync_playwright() as playwright:
        executable = "/usr/bin/chromium" if Path("/usr/bin/chromium").exists() else None
        browser = playwright.chromium.launch(
            executable_path=executable,
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto(args.url, wait_until="networkidle", timeout=90000)
        submit(page, "Show a dashboard for the test gene")
        page.get_by_text("Show source chart", exact=True).click()
        page.locator('[aria-label="Association counts by track"] svg').wait_for(
            timeout=60000
        )
        assert "test-track-a" in page.locator("main").inner_text()
        assert page.get_by_role("cell", name="1200", exact=True).count() >= 1
        print("PASS desktop: real tool stream, NIAGADS table/chart, source counts")

        page.set_viewport_size({"width": 390, "height": 844})
        page.wait_for_function(
            "document.documentElement.scrollWidth <= window.innerWidth",
            timeout=5000,
        )
        assert not page.evaluate(
            "document.documentElement.scrollWidth > window.innerWidth"
        )
        assert page.get_by_role("region", name="Evidence table", exact=False).evaluate(
            "element => element.scrollWidth > element.clientWidth"
        )
        print("PASS mobile: chart and horizontally scrollable evidence table")

        page.get_by_role("button", name="New session", exact=True).click()
        assert page.get_by_text("MOCK DATA:", exact=False).count() == 0
        submit(page, "Show the test gene evidence")
        assert "test-gene" in page.locator("main").inner_text()
        assert page.get_by_text("Show source chart", exact=True).count() == 0
        print("PASS report: gene records do not offer association charts")

        submit(page, "Show a dashboard for the test gene")
        assert page.get_by_text("MOCK DATA:", exact=False).count() == 2
        print("PASS follow-up: conversation continues with text-only history")

        for question in (
            "Find test transcript associations",
            "Find genes for a test phenotype",
        ):
            page.get_by_role("button", name="New session", exact=True).click()
            submit(page, question)
            page.get_by_text("Result status: unsupported", exact=True).wait_for(
                timeout=30000
            )
        print("PASS missing capabilities: transcript region and phenotype retrieval")

        page.reload(wait_until="domcontentloaded")
        assert page.get_by_text("MOCK DATA:", exact=False).count() == 0
        assert not errors, errors
        print("PASS session: reset/reload clears history; no browser runtime errors")
        browser.close()


if __name__ == "__main__":
    main()
