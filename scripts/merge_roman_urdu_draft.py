#!/usr/bin/env python3
"""
merge_roman_urdu_draft.py — combine scratch ayah-band JSON files into a surah.

This is for hand-written Roman Urdu drafts. It refuses to write partial surahs.

Usage:
    python3 scripts/merge_roman_urdu_draft.py --surah 3
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DRAFT_DIR = ROOT / "out" / "roman-urdu-drafts"
OUT_DIR = ROOT / "data" / "roman-urdu"
DEFAULT_DB = Path.home() / "code" / "alquran-app" / "assets" / "db" / "quran.db"

NOTE = (
    "DRAFT / BETA-UNVERIFIED. Not reviewed, not approved. Assistant-drafted in "
    "the popular register from the Urdu translation of Maulana Muhammad "
    "Junagarhi; ships only behind a visible Beta label until human review. "
    "House style: popular; see docs/decisions/0004-roman-urdu-working-style.md."
)


def expected_count(db: Path, surah: int) -> int:
    if not db.exists():
        sys.exit(f"source DB not found: {db}")
    con = sqlite3.connect(db)
    row = con.execute("SELECT total_ayahs FROM surahs WHERE id=?", (surah,)).fetchone()
    if row is None:
        sys.exit(f"unknown surah: {surah}")
    return int(row[0])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--surah", type=int, required=True)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()

    total = expected_count(args.db, args.surah)
    ayahs: dict[str, str] = {}
    paths = sorted(DRAFT_DIR.glob(f"surah-{args.surah:03d}.ayahs-*.json"))
    if not paths:
        sys.exit(f"no draft bands found for surah {args.surah}")

    for path in paths:
        data = json.loads(path.read_text(encoding="utf-8"))
        if data.get("surah") != args.surah:
            sys.exit(f"{path}: surah mismatch")
        for key, value in data.get("ayahs", {}).items():
            if key in ayahs:
                sys.exit(f"{path}: duplicate ayah {key}")
            ayahs[key] = value

    keys = sorted(int(k) for k in ayahs)
    gaps = [i for i in range(1, total + 1) if i not in keys]
    extra = [i for i in keys if i < 1 or i > total]
    blanks = [k for k, value in ayahs.items() if not value.strip()]
    if gaps or extra or blanks:
        sys.exit(f"refusing partial/invalid surah: gaps={gaps} extra={extra} blanks={blanks}")

    ordered = {str(i): ayahs[str(i)] for i in range(1, total + 1)}
    out = args.out or OUT_DIR / f"surah-{args.surah:03d}.json"
    out.write_text(json.dumps({
        "surah": args.surah,
        "status": "beta-unverified",
        "register": "popular",
        "source": "Transliterated from the Urdu translation of Maulana Muhammad Junagarhi.",
        "note": NOTE,
        "ayahs": ordered,
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {out} ({len(ordered)} ayahs from {len(paths)} draft bands)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
