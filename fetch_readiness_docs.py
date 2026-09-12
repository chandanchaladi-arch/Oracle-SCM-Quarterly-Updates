"""
fetch_readiness_docs.py

Scrapes the public, no-login Oracle Help Center "What's New" readiness
pages for Oracle Fusion Cloud SCM modules, for a given quarterly update
(e.g. "26a", "26b"). These pages carry the full prose Oracle's xlsx
Feature Listing doesn't include: capability overview, setup considerations,
tips, and role/privilege requirements.

URL PATTERN (confirmed working, no auth required):
    https://docs.oracle.com/en/cloud/saas/readiness/scm/{release}/{module_code}{release}/toc.htm

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


def fetch_module(release: str, module_code: str) -> dict | None:
    url = f"{BASE}/{release}/{module_code}{release}/toc.htm"
    resp = requests.get(url, headers=HEADERS, timeout=20)
    if resp.status_code != 200:
        print(f"  [{module_code}] HTTP {resp.status_code} at {url}")
        return None

    soup = BeautifulSoup(resp.text, "html.parser")

    features = []
    # Feature titles are typically h1/h2 headings within the content body;
    # Oracle's doc template can shift slightly release to release, so this
    # grabs headings + the following paragraph text as a reasonable default.
    for heading in soup.find_all(["h1", "h2", "h3"]):
        title = heading.get_text(strip=True)
        if not title or title.lower().startswith("previous") or title.lower().startswith("next"):
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

    return {
        "release": release,
        "module_code": module_code,
        "module_name": MODULE_CODES.get(module_code, module_code),
        "source_url": url,
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
