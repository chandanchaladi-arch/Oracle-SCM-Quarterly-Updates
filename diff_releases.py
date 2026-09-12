"""
diff_releases.py

Compares two quarters' scraped readiness JSON (from fetch_readiness_docs.py)
and reports which feature titles are new in the later release. Useful for
routing only *new* items to functional leads each quarter instead of
re-reviewing everything.

USAGE:
    python diff_releases.py --old ./data/scm_readiness_26a.json \
                             --new ./data/scm_readiness_26b.json \
                             --out ./data/new_in_26b.json
"""

import argparse
import json
from pathlib import Path


def titles_by_module(data):
    result = {}
    for module in data:
        result[module["module_code"]] = {
            f["title"] for f in module["features"]
        }
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--old", required=True)
    parser.add_argument("--new", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    old_data = json.loads(Path(args.old).read_text())
    new_data = json.loads(Path(args.new).read_text())

    old_titles = titles_by_module(old_data)
    new_by_module = {m["module_code"]: m for m in new_data}

    report = []
    for module_code, module in new_by_module.items():
        previously_seen = old_titles.get(module_code, set())
        new_features = [
            f for f in module["features"] if f["title"] not in previously_seen
        ]
        if new_features:
            report.append({
                "module_code": module_code,
                "module_name": module["module_name"],
                "new_feature_count": len(new_features),
                "new_features": new_features,
            })

    Path(args.out).write_text(json.dumps(report, indent=2))
    total = sum(m["new_feature_count"] for m in report)
    print(f"{total} new features across {len(report)} modules -> {args.out}")


if __name__ == "__main__":
    main()
