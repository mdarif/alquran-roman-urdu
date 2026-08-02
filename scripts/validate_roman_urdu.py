#!/usr/bin/env python3
"""
validate_roman_urdu.py — structural checks for hand-written Roman Urdu surahs.

This does not review or approve transliteration quality. It catches the things a
machine can honestly catch: missing ayahs, blank ayahs, duplicate/misnamed surah
files, and stray digits that may be fused footnote markers.

Usage:
    python3 scripts/validate_roman_urdu.py
    python3 scripts/validate_roman_urdu.py --surah 3
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ROMAN_DIR = ROOT / "data" / "roman-urdu"
DEFAULT_DB = Path.home() / "code" / "alquran-app" / "assets" / "db" / "quran.db"


def expected_counts(db: Path) -> dict[int, int]:
    if not db.exists():
        sys.exit(f"source DB not found: {db}")
    con = sqlite3.connect(db)
    return dict(con.execute("SELECT id, total_ayahs FROM surahs"))


def validate_file(path: Path, expect: dict[int, int]) -> tuple[bool, str]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return False, f"{path.name}: invalid JSON: {exc}"

    surah = data.get("surah")
    ayahs = data.get("ayahs")
    ok = True
    problems: list[str] = []

    if not isinstance(surah, int):
        return False, f"{path.name}: missing/integer `surah`"
    if not isinstance(ayahs, dict):
        return False, f"{path.name}: missing/object `ayahs`"
    if surah not in expect:
        ok = False
        problems.append(f"unknown-surah={surah}")

    expected_name = f"surah-{surah:03d}.json"
    if path.name != expected_name:
        ok = False
        problems.append(f"filename-should-be={expected_name}")

    total = expect.get(surah, 0)
    keys: list[int] = []
    bad_keys: list[str] = []
    for key in ayahs:
        try:
            keys.append(int(key))
        except ValueError:
            bad_keys.append(key)

    gaps = [i for i in range(1, total + 1) if i not in keys]
    extra = sorted(k for k in keys if k < 1 or k > total)
    blanks = sorted((k for k, value in ayahs.items() if not str(value).strip()), key=str)
    digits = sorted(
        (k for k, value in ayahs.items() if any(ch.isdigit() for ch in str(value))),
        key=int_key,
    )

    if bad_keys:
        ok = False
        problems.append(f"bad-keys={bad_keys}")
    if gaps:
        ok = False
        problems.append(f"gaps={gaps}")
    if extra:
        ok = False
        problems.append(f"extra={extra}")
    if blanks:
        ok = False
        problems.append(f"blank={blanks}")
    if digits:
        ok = False
        problems.append(f"stray-digits={digits}")

    if not problems:
        problems.append("ok")
    return ok, f"surah {surah:>3}: {len(ayahs):>3}/{total:<3} " + " ".join(problems)


def int_key(value: str) -> int:
    try:
        return int(value)
    except ValueError:
        return 10**9


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--surah", type=int, help="validate a single surah file")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB, help=f"source quran.db path (default: {DEFAULT_DB})")
    args = parser.parse_args()

    expect = expected_counts(args.db)
    paths = [ROMAN_DIR / f"surah-{args.surah:03d}.json"] if args.surah else sorted(ROMAN_DIR.glob("surah-*.json"))
    if not paths:
        sys.exit(f"no Roman Urdu files found in {ROMAN_DIR}")

    all_ok = True
    for path in paths:
        if not path.exists():
            print(f"{path.name}: missing")
            all_ok = False
            continue
        ok, line = validate_file(path, expect)
        print(line)
        all_ok = all_ok and ok
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
