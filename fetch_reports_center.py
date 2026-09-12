"""
fetch_reports_center.py

Automates Oracle's public "Cloud Applications Readiness Reports Center"
to pull a structured feature listing (.xlsx) for the SCM pillar, for one
or more quarterly updates (26A, 26B, 26C, ...).

WHY THIS SOURCE: it's the same data Oracle's own "What's New" docs are
built from, but pre-structured into columns (Feature, Module, Product,
Pillar, Update, Date Added, Customer Action Required, Short Description).
That means almost no text-parsing on your end.

This is a client-rendered JS app, so we drive it with Playwright rather
than requests/BeautifulSoup.

SETUP:
    pip install playwright pandas openpyxl --break-system-packages
    playwright install chromium

USAGE:
    python fetch_reports_center.py --updates 26A 26B 26C --out ./data

NOTE: Oracle's UI selectors can change over time (it's a live app, not a
static page). If a selector below stops matching, open the app in a
normal browser, right-click the search box / filters, "Inspect", and
update the selectors accordingly. This is expected maintenance for any
scraper against a UI Oracle doesn't version.
"""

import argparse
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

READINESS_APP_URL = (
    "https://www.oracle.com/webfolder/technetwork/tutorials/tutorial/"
    "readiness/app/index.html"
)

# Oracle's Reports Center groups SCM under the "Supply Chain & Manufacturing"
# pillar. Adjust this string if Oracle renames the pillar in the UI.
PILLAR_SEARCH_TERM = "Supply Chain"


def fetch_update(page, update_code: str, out_dir: Path):
    """Select a pillar + a specific update in the Reports Center and
    download the resulting .xlsx feature listing."""

    # "networkidle" can hang indefinitely on pages with background polling
    # (e.g. analytics beacons), so we wait for the DOM instead and give the
    # JS app extra time via a longer timeout, then pause briefly for its
    # own rendering to finish.
    page.goto(READINESS_APP_URL, wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(6000)

    # DEBUG: capture what the page actually looks like once loaded, plus
    # a list of any iframes present. This is a temporary diagnostic step --
    # once selectors are confirmed working, this block can be removed.
    debug_dir = out_dir / "debug"
    debug_dir.mkdir(exist_ok=True)
    page.screenshot(path=str(debug_dir / f"screenshot_{update_code}.png"), full_page=True)
    frame_info = [f.url for f in page.frames]
    (debug_dir / f"frames_{update_code}.txt").write_text("\n".join(frame_info))
    print(f"Frames found: {frame_info}")

    # 1) Type into the combined pillar/product/module search box.
    # NOTE: The "placeholder" text is a custom attribute JET puts on the
    # <oj-select-many> element itself, not a real HTML placeholder on an
    # inner <input> -- confirmed from a timeout trying to locate one.
    # Rather than hunting for JET's internal (possibly shadow-DOM) input,
    # we click the component to focus it, then simulate real keystrokes.
    # Whatever internal field receives focus will get the typed text.
    select_component = page.locator("#cmbFullModules")
    select_component.click()
    page.wait_for_timeout(500)
    page.keyboard.type(PILLAR_SEARCH_TERM, delay=50)
    page.wait_for_timeout(1500)  # let the dropdown populate

    # DEBUG: capture the dropdown state right after typing, so we can see
    # the exact result text to match in step 2 instead of guessing.
    page.screenshot(path=str(debug_dir / f"after_search_{update_code}.png"), full_page=True)

    # 2) Pick the top-level pillar result (adjust text match if needed).
    page.get_by_text("Supply Chain & Manufacturing", exact=False).first.click()

    # 3) Open the Updates dropdown and select the requested release.
    page.get_by_text("Updates", exact=False).first.click()
    page.get_by_text(update_code, exact=False).first.click()

    # 4) Trigger the download.
    with page.expect_download() as download_info:
        page.get_by_role("button", name="Download").click()
    download = download_info.value

    out_path = out_dir / f"scm_features_{update_code}.xlsx"
    download.save_as(out_path)
    print(f"Saved {out_path}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--updates", nargs="+", required=True,
                         help="e.g. 26A 26B 26C")
    parser.add_argument("--out", default="./data")
    args = parser.parse_args()

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(accept_downloads=True)
        for update_code in args.updates:
            try:
                fetch_update(page, update_code, out_dir)
            except Exception as e:
                print(f"Failed for {update_code}: {e}")
            time.sleep(2)  # be polite between requests
        browser.close()


if __name__ == "__main__":
    main()
