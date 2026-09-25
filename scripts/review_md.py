#!/usr/bin/env python3
"""
review_md.py — Markdown review workflow, the owner's preferred alternative
to `review_sheet.py`'s HTML page (owner preference, 2026-09-25: reviewing in
a Markdown file in VS Code over the HTML page).

`export --surah N` / `export --all` reuse review_sheet.py's data assembly
(`build_review_data_for_surah`) — same Urdu (from the Junagarhi sqlite),
lint findings, fidelity rows, ledger state and AI pre-review verdicts the
HTML page shows, just laid out as a Markdown file instead.

`import FILE [--out PATCH]` parses an edited file back into the exact patch
TSV `scripts/apply_review.py` expects
(`ayah, decision, corrected_text, note, seen_sha256`). This script never
writes to the ledger or to `data/roman-urdu/*.json` itself — `apply_review.py`
stays the single writer, same discipline as `review_sheet.py`.

Usage:
    python3 scripts/review_md.py export --surah 2
    python3 scripts/review_md.py export --all
    python3 scripts/review_md.py import out/review-md/surah-002.md
    python3 scripts/apply_review.py --patch out/review-md/surah-002-patch.tsv --reviewer "Abu Rayyan" --dry-run
"""
from __future__ import annotations

import argparse
import re
import sqlite3
from pathlib import Path
from typing import NamedTuple

from lint_roman_urdu import ALLOWLIST_PATH, CANONICAL_PATH, DEFAULT_SOURCE, REVIEW_DIR, ROMAN_DIR
from review_ledger import LedgerRow, load_or_bootstrap_ledger, sha256_hex
from review_sheet import FIDELITY_PATH, PREREVIEW_DIR, build_review_data_for_surah

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "out" / "review-md"

# Read-only, best-effort surah-name lookup. This is a SIBLING repo's shipped
# asset, never written to. Missing/locked/schema-mismatched -> {} and the
# title falls back to the number alone; a name is a nicety, not a
# requirement.
APP_QURAN_DB = Path.home() / "code" / "alquran-app" / "assets" / "db" / "quran.db"


class AmbiguousDecisionError(ValueError):
    """`[x] approve` together with a non-empty `fix:` in the same block."""


class MissingHashError(ValueError):
    """A verse block has no `<!-- sha256:... -->` comment."""


class ImportedRow(NamedTuple):
    ayah: int
    decision: str  # "approve" | "needs-fix"
    corrected_text: str
    note: str
    seen_sha256: str


class ImportResult(NamedTuple):
    surah: int
    rows: list[ImportedRow]
    approved: int
    needs_fix: int
    untouched: int


# ---------------------------------------------------------------------------
# Surah names (best effort)
# ---------------------------------------------------------------------------

def load_surah_names(path: Path = APP_QURAN_DB) -> dict[int, str]:
    if not path.exists():
        return {}
    try:
        con = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
        try:
            rows = con.execute("SELECT id, name_english FROM surahs").fetchall()
        finally:
            con.close()
        return {int(i): n for i, n in rows}
    except sqlite3.Error:
        return {}


def surah_title(surah: int, names: dict[int, str]) -> str:
    name = names.get(surah)
    return f"# Surah {surah} — {name}" if name else f"# Surah {surah}"


# ---------------------------------------------------------------------------
# Per-verse rendering
# ---------------------------------------------------------------------------

_INSTRUCTIONS = (
    "How to review: read the Urdu and the Roman text for each verse below. "
    "If the Roman text is right, check `[x] approve`. If it needs a fix, "
    "leave the box unchecked and write the whole corrected verse after "
    "`fix:` (a `note:` explaining why helps but isn't required). Leave "
    "everything blank to skip a verse for now — it stays untouched. "
    "**AI verdicts are suggestions; approval is yours.**"
)


def _prereview_line(prereview: dict) -> str:
    verdict = prereview.get("verdict", "none")
    if verdict == "ok":
        return "looks right"
    if verdict == "concern":
        return f"concern — {prereview.get('concern', '')} → suggested: {prereview.get('suggestion', '')}"
    if verdict == "stale":
        return "out of date"
    return "not yet reviewed"


def _flags_line(verse: dict) -> str:
    parts = [f"{f['check']}: {f['level']}" for f in verse.get("flags", [])]
    parts += [f"{r['class']} ({r['confidence']})" for r in verse.get("fidelity", [])]
    return "; ".join(parts)


def render_verse_block(surah: int, verse: dict) -> str:
    lines = [
        f"### {surah}:{verse['ayah']}",
        f"**Urdu:** {verse['urdu']}",
        f"**Roman:** {verse['roman']}",
        f"**AI:** {_prereview_line(verse.get('prereview', {}))}",
    ]
    flags = _flags_line(verse)
    if flags:
        lines.append(f"**Flags:** {flags}")
    lines += [
        "- [ ] approve",
        "- fix:",
        "- note:",
        f"<!-- sha256:{verse['sha256']} -->",
    ]
    return "\n".join(lines)


def render_approved_line(surah: int, verse: dict) -> str:
    return f"- **{surah}:{verse['ayah']}** {verse['roman']}"


# ---------------------------------------------------------------------------
# Bucketing -- pure function, unit-tested directly (design's own convention:
# data assembly is tested without going through file I/O or HTML/Markdown
# rendering)
# ---------------------------------------------------------------------------

def bucket_verses(ayahs: list[dict], ledger: dict[int, LedgerRow]) -> dict:
    """Split one surah's verses (as returned by
    `review_sheet.assemble_review_data`) into needs_eyes / looks_right /
    already_approved, and count AI verdicts. A verse only lands in
    already_approved when the ledger says `approved` AND the stored hash
    still matches the text shown -- an approval whose text has since
    changed must re-enter the ordinary AI-triage buckets, never stay in the
    no-controls list."""
    needs_eyes: list[dict] = []
    looks_right: list[dict] = []
    already_approved: list[dict] = []
    counts = {"ok": 0, "concern": 0, "stale": 0, "none": 0}

    for verse in ayahs:
        verdict = verse.get("prereview", {}).get("verdict", "none")
        counts[verdict] = counts.get(verdict, 0) + 1

        row = ledger.get(verse["ayah"])
        if row is not None and row.status == "approved" and row.sha256 == verse["sha256"]:
            already_approved.append(verse)
            continue

        if verdict in ("concern", "stale"):
            needs_eyes.append(verse)
        else:
            looks_right.append(verse)

    return {
        "needs_eyes": needs_eyes,
        "looks_right": looks_right,
        "already_approved": already_approved,
        "counts": counts,
    }


def _summary_line(total: int, counts: dict, approved_count: int) -> str:
    return (
        f"{total} verses — AI: {counts.get('ok', 0)} looks right, "
        f"{counts.get('concern', 0)} concern, {counts.get('stale', 0)} out of date, "
        f"{counts.get('none', 0)} not yet reviewed — {approved_count} already approved."
    )


# ---------------------------------------------------------------------------
# Full-document rendering
# ---------------------------------------------------------------------------

def render_surah_md(surah: int, ayahs: list[dict], ledger: dict[int, LedgerRow], names: dict[int, str]) -> str:
    buckets = bucket_verses(ayahs, ledger)

    parts = [
        surah_title(surah, names),
        "",
        _INSTRUCTIONS,
        "",
        _summary_line(len(ayahs), buckets["counts"], len(buckets["already_approved"])),
    ]

    if buckets["needs_eyes"]:
        parts += ["", "## Needs your eyes", ""]
        for v in buckets["needs_eyes"]:
            parts += [render_verse_block(surah, v), ""]

    if buckets["looks_right"]:
        parts += ["", "## Looks right to the AI", ""]
        for v in buckets["looks_right"]:
            parts += [render_verse_block(surah, v), ""]

    if buckets["already_approved"]:
        parts += ["", "## Already approved", ""]
        parts += [render_approved_line(surah, v) for v in buckets["already_approved"]]

    return "\n".join(parts) + "\n"


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------

def export_surah(
    surah: int,
    *,
    source: Path = DEFAULT_SOURCE,
    roman_dir: Path = ROMAN_DIR,
    review_dir: Path = REVIEW_DIR,
    canonical_path: Path = CANONICAL_PATH,
    allowlist_path: Path = ALLOWLIST_PATH,
    fidelity_path: Path = FIDELITY_PATH,
    prereview_dir: Path = PREREVIEW_DIR,
    names_db: Path = APP_QURAN_DB,
    out: Path | None = None,
) -> Path:
    data = build_review_data_for_surah(
        surah, source=source, roman_dir=roman_dir, review_dir=review_dir,
        canonical_path=canonical_path, allowlist_path=allowlist_path,
        fidelity_path=fidelity_path, prereview_dir=prereview_dir,
    )
    ledger = load_or_bootstrap_ledger(
        surah, {str(v["ayah"]): v["roman"] for v in data["ayahs"]}, review_dir=review_dir
    )
    names = load_surah_names(names_db)
    md = render_surah_md(surah, data["ayahs"], ledger, names)

    out_path = out or (OUT_DIR / f"surah-{surah:03d}.md")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(md, encoding="utf-8")
    return out_path


# ---------------------------------------------------------------------------
# Import -- parse an edited Markdown file back into a patch
# ---------------------------------------------------------------------------

_TITLE_RE = re.compile(r"^#\s+Surah\s+(\d+)")
_VERSE_HEADER_RE = re.compile(r"^###\s+(\d+):(\d+)\s*$")
_SHA_RE = re.compile(r"<!--\s*sha256:([0-9a-f]{64})\s*-->")
_CHECKBOX_RE = re.compile(r"^-\s*\[([ xX])\]\s*approve\s*$")
_FIX_RE = re.compile(r"^-\s*fix:\s*(.*)$")
_NOTE_RE = re.compile(r"^-\s*note:\s*(.*)$")


def parse_md(text: str) -> ImportResult:
    lines = text.splitlines()

    surah = None
    for line in lines:
        m = _TITLE_RE.match(line)
        if m:
            surah = int(m.group(1))
            break
    if surah is None:
        raise ValueError("no '# Surah N' title found in file")

    blocks: list[tuple[int, list[str]]] = []
    current_ayah: int | None = None
    current_lines: list[str] = []
    for line in lines:
        m = _VERSE_HEADER_RE.match(line)
        if m:
            if current_ayah is not None:
                blocks.append((current_ayah, current_lines))
            current_ayah = int(m.group(2))
            current_lines = []
            continue
        if current_ayah is not None:
            current_lines.append(line)
    if current_ayah is not None:
        blocks.append((current_ayah, current_lines))

    rows: list[ImportedRow] = []
    approved = needs_fix = untouched = 0

    for ayah, block_lines in blocks:
        checked = False
        sha: str | None = None
        fix_parts: list[str] = []
        note_parts: list[str] = []
        state: str | None = None

        for line in block_lines:
            m_sha = _SHA_RE.search(line)
            if m_sha:
                sha = m_sha.group(1)
                state = None  # the hash comment ends the verse's fields
                continue

            m_check = _CHECKBOX_RE.match(line.strip())
            if m_check:
                checked = m_check.group(1).lower() == "x"
                state = None
                continue

            m_fix = _FIX_RE.match(line)
            if m_fix:
                state = "fix"
                first = m_fix.group(1).strip()
                if first:
                    fix_parts.append(first)
                continue

            m_note = _NOTE_RE.match(line)
            if m_note:
                state = "note"
                first = m_note.group(1).strip()
                if first:
                    note_parts.append(first)
                continue

            stripped = line.strip()
            if not stripped:
                continue
            if stripped.startswith("#"):
                # A section heading (e.g. "## Looks right to the AI") is never
                # part of a fix or note.
                state = None
                continue
            if state == "fix":
                fix_parts.append(stripped)
            elif state == "note":
                note_parts.append(stripped)

        if sha is None:
            raise MissingHashError(f"surah {surah} ayah {ayah}: missing sha256 comment")

        fix_text = " ".join(fix_parts).strip()
        note_text = " ".join(note_parts).strip()

        if checked and fix_text:
            raise AmbiguousDecisionError(
                f"surah {surah} ayah {ayah}: 'approve' is checked together with a non-empty fix"
            )

        if checked:
            rows.append(ImportedRow(ayah=ayah, decision="approve", corrected_text="", note=note_text, seen_sha256=sha))
            approved += 1
        elif fix_text:
            rows.append(ImportedRow(ayah=ayah, decision="needs-fix", corrected_text=fix_text, note=note_text, seen_sha256=sha))
            needs_fix += 1
        else:
            untouched += 1

    return ImportResult(surah=surah, rows=rows, approved=approved, needs_fix=needs_fix, untouched=untouched)


def write_patch(result: ImportResult, out_path: Path) -> Path:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["ayah\tdecision\tcorrected_text\tnote\tseen_sha256"]
    for row in sorted(result.rows, key=lambda r: r.ayah):
        lines.append("\t".join([str(row.ayah), row.decision, row.corrected_text, row.note, row.seen_sha256]))
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out_path


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    exp = sub.add_parser("export", help="write a Markdown review file for one or all surahs")
    exp.add_argument("--surah", type=int, default=None)
    exp.add_argument("--all", action="store_true")
    exp.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    exp.add_argument("--roman-dir", type=Path, default=ROMAN_DIR)
    exp.add_argument("--review-dir", type=Path, default=REVIEW_DIR)
    exp.add_argument("--canonical", type=Path, default=CANONICAL_PATH)
    exp.add_argument("--allowlist", type=Path, default=ALLOWLIST_PATH)
    exp.add_argument("--fidelity", type=Path, default=FIDELITY_PATH)
    exp.add_argument("--prereview-dir", type=Path, default=PREREVIEW_DIR)
    exp.add_argument("--names-db", type=Path, default=APP_QURAN_DB)
    exp.add_argument("--out", type=Path, default=None, help="only valid with --surah")

    imp = sub.add_parser("import", help="parse an edited Markdown file into a patch TSV")
    imp.add_argument("file", type=Path)
    imp.add_argument("--out", type=Path, default=None)

    args = parser.parse_args()

    if args.command == "export":
        if not args.surah and not args.all:
            parser.error("pass --surah N or --all")
        if args.all and args.out:
            parser.error("--out is only valid with --surah")

        if args.all:
            surahs = sorted(
                int(p.stem.split("-")[1]) for p in args.roman_dir.glob("surah-*.json")
            )
        else:
            surahs = [args.surah]

        for s in surahs:
            out_path = export_surah(
                s, source=args.source, roman_dir=args.roman_dir, review_dir=args.review_dir,
                canonical_path=args.canonical, allowlist_path=args.allowlist,
                fidelity_path=args.fidelity, prereview_dir=args.prereview_dir,
                names_db=args.names_db, out=args.out,
            )
            print(f"wrote {out_path}")
        return 0

    if args.command == "import":
        text = args.file.read_text(encoding="utf-8")
        result = parse_md(text)
        out_path = args.out or args.file.with_name(f"surah-{result.surah:03d}-patch.tsv")
        write_patch(result, out_path)
        print(f"surah {result.surah}: approve={result.approved} needs-fix={result.needs_fix} untouched={result.untouched}")
        print(f"wrote {out_path}")
        return 0

    parser.error("unknown command")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
