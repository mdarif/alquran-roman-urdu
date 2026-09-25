#!/usr/bin/env python3
"""
canonical_review_md.py — Markdown front-end for the `canonical.tsv`
spelling-review batches in `out/canonical-review/batch-NN.tsv`
(732 needs-review rows, most-frequent-first, per
docs/PHASE-5-REVIEW-DESIGN.md §6 and §9's R1 canonical-settle step).

`export --batch NN` turns the existing `batch-NN.tsv` into a Markdown table
the owner can fill in directly (VS Code preference, same as review_md.py).
It never regenerates the batch's rows -- those already exist, most-frequent
first, from the earlier sweep; this only changes how they are presented.

`import FILE` reads a filled-in batch Markdown file and prints the owner's
decisions as a TSV (`variant, final, status`) -- it does NOT write
`data/roman-urdu/canonical.tsv` itself. The orchestrator applies the result,
same "review tool never becomes a writer" rule as review_md.py /
apply_review.py.

Usage:
    python3 scripts/canonical_review_md.py export --batch 2
    python3 scripts/canonical_review_md.py import out/canonical-review/batch-02.md
    python3 scripts/canonical_review_md.py import out/canonical-review/batch-02.md --out out/canonical-review/batch-02-decisions.tsv
"""
from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import NamedTuple

ROOT = Path(__file__).resolve().parents[1]
BATCH_DIR = ROOT / "out" / "canonical-review"
CANONICAL_PATH = ROOT / "data" / "roman-urdu" / "canonical.tsv"

_DECIDED_STATUSES = ("decided", "keep")


class BatchRow(NamedTuple):
    variant: str
    proposed: str
    count: str
    example_ref: str
    example: str


# ---------------------------------------------------------------------------
# Reading the existing batch TSV (never regenerated here)
# ---------------------------------------------------------------------------

def load_batch_tsv(path: Path) -> list[BatchRow]:
    with path.open(encoding="utf-8") as fh:
        reader = csv.DictReader(fh, delimiter="\t")
        return [
            BatchRow(
                variant=row["variant"],
                proposed=row["proposed_canonical"],
                count=row["count"],
                example_ref=row.get("example_ref", "") or "",
                example=row.get("example", "") or "",
            )
            for row in reader
        ]


# ---------------------------------------------------------------------------
# Cheap collision detection
# ---------------------------------------------------------------------------

def load_canonical_targets(path: Path) -> set[str]:
    """The set of spellings already established as a `decided`/`keep`
    canonical target elsewhere in canonical.tsv. If a batch row's proposed
    spelling is already in this set (via a DIFFERENT variant), adopting it
    would make two different original words render identically -- exactly
    the "saat clashes with seven" case already on record in canonical.tsv's
    own notes. Cheap: a single pass building a set, one membership test per
    row. Missing file -> empty set (nothing decided yet to collide with)."""
    if not path.exists():
        return set()
    targets: set[str] = set()
    with path.open(encoding="utf-8") as fh:
        reader = csv.DictReader(fh, delimiter="\t")
        for row in reader:
            if row.get("status") in _DECIDED_STATUSES:
                targets.add(row["canonical"])
    return targets


def collision_note(proposed: str, existing_targets: set[str]) -> str:
    if proposed in existing_targets:
        return f'collides with an existing decided spelling "{proposed}"'
    return ""


# ---------------------------------------------------------------------------
# Export -- render the Markdown table
# ---------------------------------------------------------------------------

def _escape_cell(text: str) -> str:
    return text.replace("|", "\\|").replace("\n", " ").strip()


_INSTRUCTIONS = (
    "Fill in the **decision** column for each row: leave it **blank** to "
    "accept the proposed spelling, write **`keep`** to keep the current "
    "spelling, or write any other spelling to use that instead."
)


def render_batch_md(batch_num: int, rows: list[BatchRow], existing_targets: set[str]) -> str:
    lines = [
        f"# Canonical spelling review — batch {batch_num:02d}",
        "",
        _INSTRUCTIONS,
        "",
        "| # | current | proposed | uses | example (ref) | decision |",
        "|---|---|---|---|---|---|",
    ]
    for i, row in enumerate(rows, start=1):
        note = collision_note(row.proposed, existing_targets)
        proposed_cell = _escape_cell(row.proposed)
        if note:
            proposed_cell = f"{proposed_cell} \u26a0 {note}"
        example_cell = _escape_cell(f"{row.example_ref}: {row.example}") if row.example_ref else _escape_cell(row.example)
        lines.append(
            f"| {i} | {_escape_cell(row.variant)} | {proposed_cell} | {_escape_cell(row.count)} | {example_cell} |  |"
        )
    return "\n".join(lines) + "\n"


def export_batch(
    batch_num: int, *, batch_dir: Path = BATCH_DIR, canonical_path: Path = CANONICAL_PATH, out: Path | None = None
) -> Path:
    src = batch_dir / f"batch-{batch_num:02d}.tsv"
    rows = load_batch_tsv(src)
    targets = load_canonical_targets(canonical_path)
    md = render_batch_md(batch_num, rows, targets)

    out_path = out or (batch_dir / f"batch-{batch_num:02d}.md")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(md, encoding="utf-8")
    return out_path


# ---------------------------------------------------------------------------
# Import -- parse the filled-in table; never touches canonical.tsv
# ---------------------------------------------------------------------------

def parse_batch_md(text: str) -> list[dict]:
    rows: list[dict] = []
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) != 6:
            continue
        if cells[0] == "#":
            continue
        if all(set(c) <= {"-"} for c in cells if c):
            continue
        try:
            int(cells[0])
        except ValueError:
            continue

        current = cells[1]
        proposed = cells[2].split(" \u26a0 ")[0].strip()
        decision = cells[5].strip()

        if decision == "":
            final, status = proposed, "decided"
        elif decision.lower() == "keep":
            final, status = current, "keep"
        else:
            final, status = decision, "decided"

        rows.append({"variant": current, "final": final, "status": status})
    return rows


def write_decisions_tsv(rows: list[dict], out: Path | None = None) -> str:
    lines = ["variant\tfinal\tstatus"]
    for row in rows:
        lines.append(f"{row['variant']}\t{row['final']}\t{row['status']}")
    text = "\n".join(lines) + "\n"
    if out is not None:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text, encoding="utf-8")
    return text


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    exp = sub.add_parser("export", help="write a Markdown table for one canonical-review batch")
    exp.add_argument("--batch", type=int, required=True)
    exp.add_argument("--batch-dir", type=Path, default=BATCH_DIR)
    exp.add_argument("--canonical", type=Path, default=CANONICAL_PATH)
    exp.add_argument("--out", type=Path, default=None)

    imp = sub.add_parser("import", help="parse a filled-in batch Markdown file into a decisions TSV")
    imp.add_argument("file", type=Path)
    imp.add_argument("--out", type=Path, default=None)

    args = parser.parse_args()

    if args.command == "export":
        out_path = export_batch(args.batch, batch_dir=args.batch_dir, canonical_path=args.canonical, out=args.out)
        print(f"wrote {out_path}")
        return 0

    if args.command == "import":
        text = args.file.read_text(encoding="utf-8")
        rows = parse_batch_md(text)
        out_text = write_decisions_tsv(rows, out=args.out)
        if args.out:
            print(f"wrote {args.out} ({len(rows)} rows)")
        else:
            print(out_text, end="")
        return 0

    parser.error("unknown command")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
