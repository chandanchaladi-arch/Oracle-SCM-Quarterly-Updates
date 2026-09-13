"""
fetch_reports_center.py -- RETIRED

This was an in-progress Playwright scraper for Oracle's "Cloud
Applications Readiness Reports Center" JS app. It never got past the
selector-discovery stage (see git history prior to commit e7de9fb for
the abandoned attempt, plus data/debug/ for the screenshots/video/frame
dump left over from that work) -- fighting a live, unversioned JET app's
internal selectors turned out to be more fragile than needed.

fetch_readiness_api.py replaces it: it hits the same Reports Center data
through Oracle's own public backend REST API directly (no browser, no
selector maintenance, no bot-detection risk). Use that instead:

    python fetch_readiness_api.py --updates 26A 26B 26C --out ./data

This file is kept only as a pointer for anyone who finds it via history
or an old bookmark. It intentionally has no functionality of its own.
"""

raise SystemExit(
    "fetch_reports_center.py is retired -- use fetch_readiness_api.py instead."
)
