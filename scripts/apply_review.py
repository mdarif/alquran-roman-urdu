#!/usr/bin/env python3
"""
apply_review.py --patch F --reviewer NAME [--dry-run] -- the only writer for
owner review decisions, matching docs/PHASE-5-REVIEW-DESIGN.md §4/§5.

Reads a TSV patch downloaded from a scripts/review_sheet.py page:
`ayah, decision(approve|needs-fix), corrected_text, note, seen_sha256`.

Rules (design §4/§5):

  approve:
    current sha256 == seen_sha256  -> ledger row: status=approved, sha256,
                                       reviewer, date, note.
    mismatch                       -> refused (stale); ledger untouched.

  needs-fix, corrected_text present:
    current sha256 == seen_sha256  -> exact-match, asserted-once single-verse
                                       replacement of the ayah text; ledger
                                       row reset: status=pending, sha256
                                       updated, reviewer/date cleared, note
                                       records what changed (P5).
    mismatch                       -> refused (stale); nothing applied.

  needs-fix, no corrected_text:
    text untouched; ledger row: status=pending, reviewer/date cleared, note
    recorded, for later.

  unknown ayah in the patch (not in this surah's ledger) -> hard error,
  nothing written at all -- the whole patch is validated before any write.

  a row the patch doesn't mention -> never touched.

  --dry-run counts everything above but writes nothing (ledger, verse text,
  or file-level status).

On a successful (non-dry-run) apply, calls scripts/status.py's
write_status_for_surah() for this surah, so the file-level `status` reflects
the new ledger state -- design §3.

Usage:
    python3 scripts/apply_review.py --patch out/review/surah-001-patch.tsv --reviewer "Abu Rayyan" --dry-run
    python3 scripts/apply_review.py --patch out/review/surah-001-patch.tsv --reviewer "Abu Rayyan"
"""
from __future__ import annotations

import argparse
import csv
import datetime
import json
import re
import sys
from pathlib import Path
from typing import NamedTuple

from review_ledger import LedgerRow, REVIEW_DIR, ROMAN_DIR, load_ledger, save_ledger, sha256_hex
from status import write_status_for_surah

_FILENAME_SURAH_RE = re.compile(r"surah-(\d+)")


class UnknownAyahError(ValueError):
    """Raised when a patch row names an ayah this surah's ledger doesn't
    have. The whole patch is invalid; nothing is written."""


class PatchError(ValueError):
    """Raised for a structurally bad patch (bad decision value, etc)."""


class ApplyReport(NamedTuple):
    surah: int
    approved: list[int]
    needs_fix_applied: list[int]
    needs_fix_flagged: list[int]
    refused_stale: list[tuple[int, str]]


# ---------------------------------------------------------------------------
# Patch parsing
# ---------------------------------------------------------------------------

def infer_surah_from_filename(path: Path) -> int | None:
    m = _FILENAME_SURAH_RE.search(path.stem)
    return int(m.group(1)) if m else None


def load_patch(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as fh:
        reader = csv.DictReader(fh, delimiter="\t")
        return list(reader)


# ---------------------------------------------------------------------------
# JSON I/O -- byte-identical formatting when nothing changes (apply_canonical
# precedent)
# ---------------------------------------------------------------------------

def _dump_json_like(data: dict) -> str:
    return json.dumps(data, indent=2) + "\n"


# ---------------------------------------------------------------------------
# Core
# ---------------------------------------------------------------------------

def apply_patch(
    patch_path: Path,
    *,
    surah: int,
    reviewer: str,
    roman_dir: Path = ROMAN_DIR,
    review_dir: Path = REVIEW_DIR,
    today: str | None = None,
    dry_run: bool = False,
) -> ApplyReport:
    today = today or datetime.date.today().isoformat()

    surah_path = roman_dir / f"surah-{surah:03d}.json"
    if not surah_path.exists():
        raise UnknownAyahError(f"no surah-{surah:03d}.json under {roman_dir}")
    surah_data = json.loads(surah_path.read_text(encoding="utf-8"))
    ayahs: dict[str, str] = surah_data["ayahs"]

    ledger_path = review_dir / f"surah-{surah:03d}.tsv"
    if not ledger_path.exists():
        raise UnknownAyahError(f"no ledger for surah {surah} at {ledger_path} -- run the bootstrap first")
    ledger = load_ledger(ledger_path)

    patch_rows = load_patch(patch_path)

    # Validate the WHOLE patch before writing anything.
    for row in patch_rows:
        ayah = int(row["ayah"])
        if ayah not in ledger or str(ayah) not in ayahs:
            raise UnknownAyahError(f"surah {surah} ayah {ayah}: not in this surah's ledger/text")
        if row["decision"] not in ("approve", "needs-fix"):
            raise PatchError(f"surah {surah} ayah {ayah}: unknown decision {row['decision']!r}")

    approved: list[int] = []
    needs_fix_applied: list[int] = []
    needs_fix_flagged: list[int] = []
    refused_stale: list[tuple[int, str]] = []

    new_ledger = dict(ledger)
    new_ayahs = dict(ayahs)
    text_changed = False

    for row in patch_rows:
        ayah = int(row["ayah"])
        key = str(ayah)
        current_text = ayahs[key]
        current_hash = sha256_hex(current_text)
        seen_sha256 = row["seen_sha256"]
        note = (row.get("note") or "").strip()

        if current_hash != seen_sha256:
            refused_stale.append((ayah, "text changed since the review page was generated (seen_sha256 mismatch)"))
            continue

        if row["decision"] == "approve":
            new_ledger[ayah] = LedgerRow(
                ayah=ayah, status="approved", sha256=current_hash, reviewer=reviewer, date=today, note=note,
            )
            approved.append(ayah)
            continue

        # needs-fix
        corrected_text = (row.get("corrected_text") or "").strip()
        if corrected_text:
            new_ayahs[key] = corrected_text
            text_changed = True
            new_hash = sha256_hex(corrected_text)
            new_ledger[ayah] = LedgerRow(
                ayah=ayah, status="pending", sha256=new_hash, reviewer="", date="",
                note=f"{note} [apply_review.py needs-fix, corrected text applied {today}]".strip(),
            )
            needs_fix_applied.append(ayah)
        else:
            new_ledger[ayah] = LedgerRow(
                ayah=ayah, status="pending", sha256="", reviewer="", date="",
                note=f"{note} [apply_review.py needs-fix, no text change {today}]".strip(),
            )
            needs_fix_flagged.append(ayah)

    report = ApplyReport(
        surah=surah, approved=approved, needs_fix_applied=needs_fix_applied,
        needs_fix_flagged=needs_fix_flagged, refused_stale=refused_stale,
    )

    if dry_run:
        return report

    if text_changed:
        surah_data["ayahs"] = new_ayahs
        surah_path.write_text(_dump_json_like(surah_data), encoding="utf-8")

    save_ledger(ledger_path, new_ledger)

    write_status_for_surah(surah, roman_dir=roman_dir, review_dir=review_dir)

    return report


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--patch", type=Path, required=True, help="TSV patch downloaded from review_sheet.py")
    parser.add_argument("--reviewer", required=True, help="reviewer name recorded on approved rows")
    parser.add_argument("--surah", type=int, default=None, help="override surah number (default: inferred from the patch filename, surah-NNN...)")
    parser.add_argument("--dry-run", action="store_true", help="report counts, write nothing")
    parser.add_argument("--roman-dir", type=Path, default=ROMAN_DIR)
    parser.add_argument("--review-dir", type=Path, default=REVIEW_DIR)
    args = parser.parse_args()

    surah = args.surah if args.surah is not None else infer_surah_from_filename(args.patch)
    if surah is None:
        parser.error(f"could not infer surah number from {args.patch.name!r}; pass --surah N")

    try:
        report = apply_patch(
            args.patch, surah=surah, reviewer=args.reviewer, roman_dir=args.roman_dir,
            review_dir=args.review_dir, dry_run=args.dry_run,
        )
    except (UnknownAyahError, PatchError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    mode = "(dry-run) " if args.dry_run else ""
    print(f"{mode}surah {surah}: approved={len(report.approved)} "
          f"needs-fix-applied={len(report.needs_fix_applied)} "
          f"needs-fix-flagged={len(report.needs_fix_flagged)} "
          f"refused-stale={len(report.refused_stale)}")
    for ayah, reason in report.refused_stale:
        print(f"  refused ayah {ayah}: {reason}")

    return 1 if report.refused_stale else 0


if __name__ == "__main__":
    raise SystemExit(main())
