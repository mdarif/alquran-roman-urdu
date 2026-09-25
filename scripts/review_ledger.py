#!/usr/bin/env python3
"""
review_ledger.py — the per-surah review ledger:
`data/roman-urdu/review/surah-NNN.tsv`.

Phase 5 of docs/ROMAN-URDU-GOLDEN-PLAN.md, design in
docs/PHASE-5-REVIEW-DESIGN.md §1-§2. One row per ayah, `1..N`, no gaps --
same discipline as `ayahs` in the surah JSON. Columns:

    ayah  status(pending|reviewed|approved)  sha256  reviewer  date  note

`sha256` is the hex digest of the EXACT unnormalised UTF-8 bytes of the
current Roman verse text -- no normalisation, no trimming, no case-fold
(design §2). This module never writes to `data/roman-urdu/surah-*.json`;
it only reads ayah text to bootstrap or hash-check a ledger.

Usage:
    python3 scripts/review_ledger.py --bootstrap-all
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
from typing import NamedTuple

ROOT = Path(__file__).resolve().parents[1]
ROMAN_DIR = ROOT / "data" / "roman-urdu"
REVIEW_DIR = ROMAN_DIR / "review"

LEDGER_COLUMNS = ["ayah", "status", "sha256", "reviewer", "date", "note"]
# "verified" -- ADR 0006 (docs/decisions/0006-ai-verified-owner-sampled.md):
# a verse whose two independent AI verdicts agree `ok` on the exact current
# text and whose lint is clean. Distinct from `reviewed`, which is an older,
# unused rung -- see AGENTS.md §4 amendment. Never produced by hand; only
# scripts/verify_merge.py mark and apply_review.py write ledger rows.
STATUSES = ("pending", "reviewed", "approved", "verified")


class LedgerRow(NamedTuple):
    ayah: int
    status: str
    sha256: str
    reviewer: str
    date: str
    note: str


class LedgerError(ValueError):
    """Raised when a ledger file is structurally invalid: a gap or a
    duplicate ayah number."""


# ---------------------------------------------------------------------------
# Hashing
# ---------------------------------------------------------------------------

def sha256_hex(text: str) -> str:
    """sha256 hex digest of the exact UTF-8 bytes of `text`. No
    normalisation, no trimming, no case-fold -- design §2."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Load / save
# ---------------------------------------------------------------------------

def save_ledger(path: Path, rows: dict[int, LedgerRow]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh, delimiter="\t")
        writer.writerow(LEDGER_COLUMNS)
        for ayah in sorted(rows):
            row = rows[ayah]
            writer.writerow([row.ayah, row.status, row.sha256, row.reviewer, row.date, row.note])


def load_ledger(path: Path) -> dict[int, LedgerRow]:
    """Load a ledger TSV. Raises LedgerError if the ayah numbers present are
    not exactly 1..max with no gaps and no duplicates."""
    rows: dict[int, LedgerRow] = {}
    seen_order: list[int] = []
    with path.open(encoding="utf-8") as fh:
        reader = csv.DictReader(fh, delimiter="\t")
        for raw in reader:
            ayah = int(raw["ayah"])
            if ayah in rows:
                raise LedgerError(f"{path}: duplicate ayah {ayah}")
            rows[ayah] = LedgerRow(
                ayah=ayah,
                status=raw["status"],
                sha256=raw["sha256"],
                reviewer=raw["reviewer"],
                date=raw["date"],
                note=raw["note"],
            )
            seen_order.append(ayah)

    if rows:
        expected = set(range(1, max(rows) + 1))
        missing = sorted(expected - set(rows))
        if missing:
            raise LedgerError(f"{path}: gap(s) in ayah sequence: {missing}")

    return rows


# ---------------------------------------------------------------------------
# Bootstrap
# ---------------------------------------------------------------------------

def bootstrap_ledger(*, surah: int, ayahs: dict[str, str]) -> dict[int, LedgerRow]:
    """Build an all-`pending` ledger for one surah from its `ayahs` dict
    (keys are string ayah numbers, as in surah-NNN.json)."""
    rows: dict[int, LedgerRow] = {}
    for key in ayahs:
        ayah = int(key)
        rows[ayah] = LedgerRow(ayah=ayah, status="pending", sha256="", reviewer="", date="", note="")
    return rows


def bootstrap_all(*, roman_dir: Path = ROMAN_DIR, review_dir: Path = REVIEW_DIR) -> list[int]:
    """Create a ledger for every surah-*.json in `roman_dir` that does not
    already have one in `review_dir`. Never overwrites an existing ledger.
    Returns the sorted list of surah numbers a ledger was newly written for."""
    written: list[int] = []
    for path in sorted(roman_dir.glob("surah-*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        surah = data["surah"]
        ledger_path = review_dir / f"surah-{surah:03d}.tsv"
        if ledger_path.exists():
            continue
        rows = bootstrap_ledger(surah=surah, ayahs=data["ayahs"])
        save_ledger(ledger_path, rows)
        written.append(surah)
    return sorted(written)


def ledger_path_for(surah: int, review_dir: Path = REVIEW_DIR) -> Path:
    return review_dir / f"surah-{surah:03d}.tsv"


def load_or_bootstrap_ledger(
    surah: int, ayahs: dict[str, str], *, review_dir: Path = REVIEW_DIR
) -> dict[int, LedgerRow]:
    """Load the ledger for `surah` if it exists; otherwise bootstrap and save
    an all-pending one (design §1: ledgers are bootstrapped lazily)."""
    path = ledger_path_for(surah, review_dir)
    if path.exists():
        return load_ledger(path)
    rows = bootstrap_ledger(surah=surah, ayahs=ayahs)
    save_ledger(path, rows)
    return rows


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--bootstrap-all", action="store_true", help="create a ledger for every surah that doesn't have one yet")
    parser.add_argument("--roman-dir", type=Path, default=ROMAN_DIR)
    parser.add_argument("--review-dir", type=Path, default=REVIEW_DIR)
    args = parser.parse_args()

    if not args.bootstrap_all:
        parser.error("nothing to do: pass --bootstrap-all")

    written = bootstrap_all(roman_dir=args.roman_dir, review_dir=args.review_dir)
    print(f"bootstrapped {len(written)} ledger(s): {written}" if written else "bootstrapped 0 ledgers (all already existed)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
