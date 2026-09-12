# Oracle Fusion SCM Quarterly Update Tracker

Fetches, structures, and diffs Oracle's quarterly SCM feature updates
(26A, 26B, 26C, 26D, ...) from Oracle's own public sources — no login
or scraping of paywalled content required.

## Data sources used

| Source | What it gives you | Script |
|---|---|---|
| Readiness Reports Center (`oracle.com` app) | Structured xlsx: Feature, Module, Product, Pillar, Update, Date Added, Action Required (Y/N), Short Description | `fetch_reports_center.py` |
| Oracle Help Center "What's New" pages (`docs.oracle.com/.../readiness/scm/...`) | Full prose: capability overview, setup steps, tips, required privileges | `fetch_readiness_docs.py` |

Use the Reports Center xlsx as your primary structured feed (it's already
categorized), and the Help Center scrape when a reviewer needs the full
description or setup steps for a specific feature.

## Setup

```bash
pip install requests beautifulsoup4 playwright pandas openpyxl --break-system-packages
playwright install chromium
```

## Running it

```bash
# Structured feed for one or more updates
python fetch_reports_center.py --updates 26A 26B 26C --out ./data

# Full prose per module for a given release
python fetch_readiness_docs.py --release 26a --out ./data

# What changed between two quarters
python diff_releases.py --old ./data/scm_readiness_26a.json \
                         --new ./data/scm_readiness_26b.json \
                         --out ./data/new_in_26b.json
```

## Known maintenance points (be aware, not alarmed)

- **`fetch_reports_center.py` selectors**: it's a live JS app Oracle
  doesn't version, so element selectors may need small updates over
  time. If a run fails, open the app in a browser, inspect the failing
  element, and adjust the selector.
- **`MODULE_CODES` in `fetch_readiness_docs.py`**: only 5 modules are
  pre-filled from confirmed URLs. Walk the Help Center once to find the
  rest (instructions in the script's docstring) — a one-time cost per
  module, not a recurring one.
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
