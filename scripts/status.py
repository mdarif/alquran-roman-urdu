#!/usr/bin/env python3
"""
status.py — coverage and review counts for the Roman Urdu corpus, derived
from `data/roman-urdu/*.json` itself.

Nothing here is hand-typed. Run this instead of copy-pasting a verse count
into a doc — gotchas §10 records what happened the last time that number was
typed into seven files by hand and went stale.

Usage:
    python3 scripts/status.py
    python3 scripts/status.py --dir path/to/fixtures
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROMAN_DIR = ROOT / "data" / "roman-urdu"


def compute_status(roman_dir: Path) -> dict:
    files = 0
    verses = 0
    by_status: dict[str, dict[str, int]] = {}

    for path in sorted(roman_dir.glob("surah-*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        status = data.get("status", "unknown")
        n = len(data.get("ayahs", {}))

        files += 1
        verses += n
        bucket = by_status.setdefault(status, {"files": 0, "verses": 0})
        bucket["files"] += 1
        bucket["verses"] += n

    return {"files": files, "verses": verses, "by_status": by_status}


def format_report(report: dict) -> str:
    lines = [f"files:  {report['files']}", f"verses: {report['verses']}", "", "by status:"]
    for status, counts in sorted(report["by_status"].items()):
        lines.append(f"  {status:<20} files={counts['files']:<4} verses={counts['verses']}")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dir", type=Path, default=ROMAN_DIR, help=f"directory of surah-*.json files (default: {ROMAN_DIR})")
    args = parser.parse_args()

    report = compute_status(args.dir)
    print(format_report(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
