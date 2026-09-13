# Oracle Fusion SCM Quarterly Update Tracker

Fetches, structures, and diffs Oracle's quarterly SCM feature updates
(26A, 26B, 26C, 26D, ...) from Oracle's own public sources — no login
or scraping of paywalled content required.

## Data sources used

| Source | What it gives you | Script |
|---|---|---|
| Oracle's public Readiness Reports Center backend API (`apexapps.oracle.com`) | Structured JSON: full feature records (title, description, business benefit, setup steps) per product/module/release, straight from the same backend the Reports Center UI itself calls | `fetch_readiness_api.py` |
| Oracle Help Center "What's New" pages (`docs.oracle.com/.../readiness/scm/...`) | Full prose per chapter: capability overview, setup steps, tips, required privileges | `fetch_readiness_docs.py` |

Use the API script as your primary structured feed (it's already
categorized and needs no HTML parsing), and the Help Center scrape when
you want the docs-site framing of a feature in addition to the API's data.

`fetch_reports_center.py` is retired (kept only as a stub pointing here) —
it was an earlier attempt to drive the Reports Center's JS app directly
with Playwright, but `fetch_readiness_api.py` gets the same data straight
from that app's own backend API, with no browser and no UI-selector
maintenance.

## Setup

```bash
pip install requests beautifulsoup4 --break-system-packages
```

## Running it

```bash
# Structured feed for one or more updates
python fetch_readiness_api.py --updates 26A 26B 26C --out ./data

# Full prose per module for a given release
python fetch_readiness_docs.py --release 26a --out ./data

# What changed between two quarters (comparing fetch_readiness_docs.py output)
python diff_releases.py --old ./data/scm_readiness_26a.json \
                         --new ./data/scm_readiness_26b.json \
                         --out ./data/new_in_26b.json
```

## Known maintenance points (be aware, not alarmed)

- **`fetch_readiness_docs.py` TOC parsing**: it discovers chapter pages
  by following same-book `.htm`/`.html` links out of each module's
  `toc.htm`, rather than matching a specific CSS class — more robust to
  markup tweaks, but if Oracle restructures how a book's TOC links to its
  chapters, `discover_chapter_urls()` may need adjusting.
- **`MODULE_CODES` in `fetch_readiness_docs.py`**: only 5 modules are
  pre-filled from confirmed URLs. Walk the Help Center once to find the
  rest (instructions in the script's docstring) — a one-time cost per
  module, not a recurring one.
- **`fetch_readiness_api.py`'s backend endpoints**: these are Oracle's
  internal (undocumented) API, discovered from the Reports Center app's
  own network traffic. They could change without notice; if a fetch
  starts returning empty results, re-inspect that app's network tab.
- **Be a polite scraper**: both scripts already throttle requests
  (`time.sleep`). Don't tighten these loops — Oracle's readiness content
  is refreshed weekly, not by the minute, so there's no reason to hit it
  hard.

## Suggested schedule

Oracle's readiness content for a given update typically goes live
4-6 weeks before that update reaches your test environment. A safe
polling cadence:

- **Weekly**, starting ~6 weeks before each quarter's expected release
  (roughly mid-Jan, mid-Apr, mid-Jul, mid-Oct)
- Run `diff_releases.py` after each fetch to surface only what's new
  since your last run, rather than re-reviewing the full set

## Next steps to extend this

1. **Storage**: load the xlsx + JSON into Postgres or even a single
   Excel workbook per quarter, with columns matching the Reports Center
   output plus a `reviewed_by` / `disposition` column your functional
   leads fill in.
2. **Notification**: after each fetch + diff, email or Slack/Teams a
   per-module summary to the relevant SCM process owner.
3. **Review workflow**: track Reviewed / Adopt / Ignore / Needs Testing
   per feature, so there's an audit trail before your cohort's test
   environment go-live date.
