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

from review_ledger import LedgerRow, load_ledger, sha256_hex

ROOT = Path(__file__).resolve().parents[1]
ROMAN_DIR = ROOT / "data" / "roman-urdu"
REVIEW_DIR = ROMAN_DIR / "review"


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


def derive_file_status(rows: dict[int, LedgerRow], ayahs: dict[str, str]) -> str:
    """File-level `status`, derived from the review ledger -- design §3,
    amended by ADR 0006 (docs/decisions/0006-ai-verified-owner-sampled.md):

        every row `approved`, hash-clean                    -> approved
        every row `verified`/`approved`, >= 1 `verified`     -> verified
        every row `reviewed`/`approved`, none pending        -> reviewed
        anything else (incl. no ledger rows at all)          -> beta-unverified

    `approved` stays reserved for when EVERY verse was owner-read one by
    one; a file with even one `verified` (double-AI, not owner-read) row
    is `verified`, never `approved` -- ADR 0006 rule 5 is explicit that the
    two are recorded, and therefore reported, differently.
    """
    if not rows:
        return "beta-unverified"

    if all(row.status == "approved" for row in rows.values()):
        hash_clean = all(row.sha256 == sha256_hex(ayahs[str(row.ayah)]) for row in rows.values())
        if hash_clean:
            return "approved"
        return "reviewed"

    if (
        all(row.status in ("verified", "approved") for row in rows.values())
        and any(row.status == "verified" for row in rows.values())
    ):
        return "verified"

    if all(row.status in ("reviewed", "approved") for row in rows.values()):
        return "reviewed"

    return "beta-unverified"


def compute_review_status(review_dir: Path) -> dict[str, int]:
    """Verse counts by ledger status, across every ledger under `review_dir`.
    A missing directory (no ledgers bootstrapped yet) is all zero."""
    counts = {"pending": 0, "reviewed": 0, "approved": 0, "verified": 0}
    if not review_dir.exists():
        return counts
    for path in sorted(review_dir.glob("surah-*.tsv")):
        for row in load_ledger(path).values():
            counts[row.status] = counts.get(row.status, 0) + 1
    return counts


def _dump_json_like(data: dict) -> str:
    return json.dumps(data, indent=2) + "\n"


def write_status_for_surah(
    surah: int, *, roman_dir: Path = ROMAN_DIR, review_dir: Path = REVIEW_DIR
) -> tuple[str, str] | None:
    """Recompute and rewrite ONLY the `status` key of surah-NNN.json from its
    review ledger -- never `ayahs`, never any other key. Returns
    (old_status, new_status), or None if the surah file doesn't exist.
    Writes nothing when the derived status matches the current one, so a
    no-op run leaves the file byte-identical (git diff empty)."""
    path = roman_dir / f"surah-{surah:03d}.json"
    if not path.exists():
        return None

    data = json.loads(path.read_text(encoding="utf-8"))
    old_status = data.get("status")

    ledger_path = review_dir / f"surah-{surah:03d}.tsv"
    rows = load_ledger(ledger_path) if ledger_path.exists() else {}
    new_status = derive_file_status(rows, data.get("ayahs", {}))

    if new_status == old_status:
        return (old_status, new_status)

    data["status"] = new_status
    path.write_text(_dump_json_like(data), encoding="utf-8")
    return (old_status, new_status)


def write_status_all(
    *, roman_dir: Path = ROMAN_DIR, review_dir: Path = REVIEW_DIR
) -> list[tuple[int, str, str]]:
    """Run write_status_for_surah over every surah-*.json in `roman_dir`.
    Returns only the surahs whose status actually changed, as
    (surah, old_status, new_status)."""
    changes: list[tuple[int, str, str]] = []
    for path in sorted(roman_dir.glob("surah-*.json")):
        surah = json.loads(path.read_text(encoding="utf-8"))["surah"]
        result = write_status_for_surah(surah, roman_dir=roman_dir, review_dir=review_dir)
        if result is None:
            continue
        old_status, new_status = result
        if old_status != new_status:
            changes.append((surah, old_status, new_status))
    return changes


def format_report(report: dict, review_report: dict[str, int] | None = None) -> str:
    lines = [f"files:  {report['files']}", f"verses: {report['verses']}", "", "by file status:"]
    for status, counts in sorted(report["by_status"].items()):
        lines.append(f"  {status:<20} files={counts['files']:<4} verses={counts['verses']}")
    if review_report is not None:
        lines += ["", "by review status:"]
        for status in ("pending", "reviewed", "verified", "approved"):
            lines.append(f"  {status:<20} verses={review_report.get(status, 0)}")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dir", type=Path, default=ROMAN_DIR, help=f"directory of surah-*.json files (default: {ROMAN_DIR})")
    parser.add_argument("--review-dir", type=Path, default=REVIEW_DIR, help=f"directory of review/surah-*.tsv ledgers (default: {REVIEW_DIR})")
    parser.add_argument(
        "--write-status", action="store_true",
        help="recompute and rewrite each surah's file-level `status` from its review ledger (design §3); writes nothing else",
    )
    args = parser.parse_args()

    if args.write_status:
        changes = write_status_all(roman_dir=args.dir, review_dir=args.review_dir)
        if changes:
            for surah, old, new in changes:
                print(f"surah {surah:>3}: {old} -> {new}")
        else:
            print("no status changes")

    report = compute_status(args.dir)
    review_report = compute_review_status(args.review_dir)
    print(format_report(report, review_report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
