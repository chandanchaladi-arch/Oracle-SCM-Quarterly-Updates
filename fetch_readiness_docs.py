"""
fetch_readiness_docs.py

Scrapes the public, no-login Oracle Help Center "What's New" readiness
pages for Oracle Fusion Cloud SCM modules, for a given quarterly update
(e.g. "26a", "26b"). These pages carry the full prose Oracle's xlsx
Feature Listing doesn't include: capability overview, setup considerations,
tips, and role/privilege requirements.

URL PATTERN (confirmed working, no auth required):
    https://docs.oracle.com/en/cloud/saas/readiness/scm/{release}/{module_code}{release}/toc.htm

IMPORTANT: toc.htm is a table-of-contents / navigation page, not content.
It lists links to the actual chapter pages (one per feature area). This
script fetches toc.htm first to discover those chapter links, then fetches
each chapter page and pulls the real prose from there. (An earlier version
of this script parsed toc.htm's own headings directly, which only ever
produced a single fake "feature" per module titled "Table of Contents"
with no body -- that's simply what toc.htm's own heading says.)

SETUP:
    pip install requests beautifulsoup4 --break-system-packages

USAGE:
    python fetch_readiness_docs.py --release 26a --out ./data

MAINTAINING THE MODULE MAP:
    Oracle doesn't publish a machine-readable index of module codes, so
    MODULE_CODES below is a starting set built from confirmed URLs. To
    extend coverage to every SCM module:
      1. Go to https://docs.oracle.com/en/cloud/saas/readiness/ in a browser
      2. Navigate: Supply Chain & Manufacturing -> pick a module -> Latest
      3. Copy the module_code segment from the resulting URL
      4. Add it to MODULE_CODES below
    This is a one-time-per-module setup cost, not a recurring one --
    Oracle rarely renames these codes.
"""

import argparse
import json
import time
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

BASE = "https://docs.oracle.com/en/cloud/saas/readiness/scm"

# module_code -> friendly name. Extend this as you confirm more modules
# (see docstring above for how to find each code).
MODULE_CODES = {
    "mfg": "Manufacturing",
    "proc": "Procurement",
    "order": "Order Management",
    "plm": "Product Lifecycle Management",
    "scp": "Supply Planning",
    # TODO: add the rest as you confirm them, e.g.:
    # "inv":       "Inventory Management",
    # "log":       "Logistics",
    # "wms":       "Warehouse Management",
    # "mrp":       "Material Requirements Planning",
    # "transport": "Transportation Management",
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (internal release-tracking tool; contact: you@yourcompany.com)"
}

# Safety cap so a malformed/huge TOC can't turn one module into hundreds
# of requests.
MAX_CHAPTER_PAGES = 60


def get_soup(url: str) -> BeautifulSoup | None:
    resp = requests.get(url, headers=HEADERS, timeout=20)
    if resp.status_code != 200:
        print(f"    HTTP {resp.status_code} at {url}")
        return None
    return BeautifulSoup(resp.text, "html.parser")


def discover_chapter_urls(toc_soup: BeautifulSoup, toc_url: str) -> list[str]:
    """Pull the ordered, deduplicated list of same-book content page URLs
    linked from a toc.htm page. Internal Oracle Help Center TOC markup
    varies by book, so this matches generically on same-directory
    .htm/.html links rather than a specific CSS class, and skips
    fragment-only anchors and the TOC page itself."""
    book_dir = toc_url.rsplit("/", 1)[0] + "/"
    toc_filename = toc_url.rsplit("/", 1)[-1]

    seen = set()
    urls = []
    for a in toc_soup.find_all("a", href=True):
        href = a["href"].strip()
        if not href or href.startswith("#") or href.startswith("javascript:"):
            continue
        full_url = urljoin(toc_url, href)
        parsed = urlparse(full_url)
        if not parsed.path.endswith((".htm", ".html")):
            continue
        if not full_url.startswith(book_dir):
            continue  # don't follow links outside this book
        if full_url.rsplit("/", 1)[-1].split("#")[0] == toc_filename:
            continue  # skip self-links back to the TOC
        if full_url in seen:
            continue
        seen.add(full_url)
        urls.append(full_url)
    return urls[:MAX_CHAPTER_PAGES]


def extract_features(page_soup: BeautifulSoup) -> list[dict]:
    """Grab heading + following prose as a reasonable default. Oracle's
    doc template can shift slightly release to release."""
    features = []
    for heading in page_soup.find_all(["h1", "h2", "h3"]):
        title = heading.get_text(strip=True)
        if not title or title.lower().startswith(("previous", "next", "table of contents")):
            continue
        desc_parts = []
        for sib in heading.find_next_siblings():
            if sib.name in ("h1", "h2", "h3"):
                break
            text = sib.get_text(" ", strip=True)
            if text:
                desc_parts.append(text)
        features.append({
            "title": title,
            "description": " ".join(desc_parts)[:2000],  # cap length
        })
    return features


def fetch_module(release: str, module_code: str) -> dict | None:
    toc_url = f"{BASE}/{release}/{module_code}{release}/toc.htm"
    toc_soup = get_soup(toc_url)
    if toc_soup is None:
        return None

    chapter_urls = discover_chapter_urls(toc_soup, toc_url)
    if not chapter_urls:
        print(f"  [{module_code}] no chapter links found in TOC at {toc_url}")

    features = []
    for chapter_url in chapter_urls:
        chapter_soup = get_soup(chapter_url)
        if chapter_soup is None:
            continue
        features.extend(extract_features(chapter_soup))
        time.sleep(0.5)  # be polite between chapter requests

    return {
        "release": release,
        "module_code": module_code,
        "module_name": MODULE_CODES.get(module_code, module_code),
        "source_url": toc_url,
        "features": features,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--release", required=True, help="e.g. 26a")
    parser.add_argument("--out", default="./data")
    args = parser.parse_args()

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    results = []
    for module_code in MODULE_CODES:
        print(f"Fetching {module_code} ({args.release})...")
        data = fetch_module(args.release, module_code)
        if data:
            results.append(data)
        time.sleep(1.5)  # be polite - don't hammer Oracle's servers

    out_path = out_dir / f"scm_readiness_{args.release}.json"
    out_path.write_text(json.dumps(results, indent=2))
    print(f"\nSaved {len(results)} modules to {out_path}")


if __name__ == "__main__":
    main()
