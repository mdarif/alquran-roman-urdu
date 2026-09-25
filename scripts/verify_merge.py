#!/usr/bin/env python3
"""
verify_merge.py — ADR 0006 tooling: independent double AI verification plus
an owner-checked random sample
(docs/decisions/0006-ai-verified-owner-sampled.md), amending AGENTS.md §4
non-negotiables 1 and 2 for `data/roman-urdu/` only.

Subcommands:

  import-pass2 --from DIR --source-label LABEL
      Validate and copy second-pass verdict files (same 5-column format as
      data/roman-urdu/prereview/: ayah, verdict, sha256, concern, suggestion)
      into data/roman-urdu/verify2/, recording the reviewer label per surah
      in verify2/SOURCES.tsv. Each surah-NNN.tsv is validated independently
      -- header, one row per ayah (no gaps, no dupes), 5 fields, verdict
      ok|concern, sha256 matching the CURRENT Roman text -- and an invalid
      file is refused (skipped, reported), never partially copied.

  mark [--dry-run]
      Promote a `pending` ledger row to `verified` wherever pass-1
      (prereview) AND pass-2 (verify2) both verdict `ok` against the exact
      current text (hash-pinned) and lint has no error finding for that
      verse (ADR 0006 rule 2). Reviewer/date/note are set per rule 5. Never
      touches an `approved` row; never downgrades anything -- only `pending`
      rows are ever examined.

  queue --out FILE
      Write a Markdown disagreement queue (ADR 0006 rule 3): every pending
      verse where either verdict is `concern`, or a verdict is stale
      (sha256 mismatch) or missing entirely, grouped by surah, for the
      owner to rule on.

  queue-import FILE --out DIR
      Parse an owner-edited queue file back into apply_review.py patch
      TSVs, one per surah, named surah-NNN-patch.tsv so apply_review.py's
      own filename-inference (infer_surah_from_filename) finds the right
      surah without --surah. `ok` -> approve (apply_review.py's --reviewer
      sets who); a corrected verse -> needs-fix.

  sample --n 150 --seed S --out FILE
      Write a Markdown owner-read sample of `verified` verses (ADR 0006
      rule 4), stratified so surahs whose pass-2 review came from "claude
      sonnet" (per verify2/SOURCES.tsv) appear in proportion to their share
      of the verified population -- ADR 0006's own caveat that those
      surahs' two verdicts are less independent.

  sample-import FILE
      Summarise the owner's `- wrong:` findings from an edited sample file.

This script is not the ledger's writer for OWNER decisions -- apply_review.py
stays that (queue-import only produces patches for it to apply). `mark` is
the one command here that writes ledger rows directly, because a `verified`
row is not an owner decision -- it is what ADR 0006 rule 2 itself defines.
Nothing here ever writes to data/roman-urdu/*.json.

Usage:
    python3 scripts/verify_merge.py import-pass2 --from ~/Downloads/pass2 --source-label "codex gpt-5.5"
    python3 scripts/verify_merge.py mark --dry-run
    python3 scripts/verify_merge.py mark
    python3 scripts/verify_merge.py queue --out out/verify-merge/queue.md
    python3 scripts/verify_merge.py queue-import out/verify-merge/queue.md --out out/verify-merge/patches
    python3 scripts/verify_merge.py sample --n 150 --seed 20260925 --out out/verify-merge/sample.md
    python3 scripts/verify_merge.py sample-import out/verify-merge/sample.md
"""
from __future__ import annotations

import argparse
import csv
import datetime
import json
import random
import re
from pathlib import Path
from typing import NamedTuple

from lint_roman_urdu import (
    ALLOWLIST_PATH,
    CANONICAL_PATH,
    DEFAULT_SOURCE,
    REVIEW_DIR,
    ROMAN_DIR,
    load_allowlist,
    load_source,
)
from lint_roman_urdu import run as lint_run
from review_ledger import LedgerRow, ledger_path_for, load_ledger, save_ledger, sha256_hex
from review_sheet import PREREVIEW_DIR, load_prereview_rows
from status import write_status_for_surah

ROOT = Path(__file__).resolve().parents[1]
VERIFY2_DIR = ROMAN_DIR / "verify2"
SOURCES_HEADER = ["surah", "reviewer_label"]
PASS2_HEADER = ["ayah", "verdict", "sha256", "concern", "suggestion"]
_FILENAME_SURAH_RE = re.compile(r"surah-(\d+)")
_CLAUDE_LABEL_MARKER = "claude sonnet"
_REVIEWER_LABEL = "AI (double) + owner sample"
_NOTE = "ADR 0006"


class MissingHashError(ValueError):
    """A verse block in a queue/sample Markdown file has no
    `<!-- sha256:... -->` comment."""


class Pass2ImportReport(NamedTuple):
    imported: list[int]
    refused: list[tuple[int | None, str]]


class MarkReport(NamedTuple):
    verified: list[tuple[int, int]]
    already_approved: int
    disagreements: int
    stale: int
    lint_blocked: int


class QueueEntry(NamedTuple):
    surah: int
    ayah: int
    urdu: str
    roman: str
    sha256: str
    pass1: str
    pass2: str
    reason: str  # "concern" | "stale"


class QueueImportedRow(NamedTuple):
    surah: int
    ayah: int
    decision: str  # "approve" | "needs-fix"
    corrected_text: str
    seen_sha256: str


class QueueImportResult(NamedTuple):
    rows: list[QueueImportedRow]
    approved: int
    needs_fix: int
    untouched: int


class SampleFinding(NamedTuple):
    surah: int
    ayah: int
    description: str


class SampleImportResult(NamedTuple):
    total: int
    wrong: list[SampleFinding]
    fine: int


def _infer_surah(path: Path) -> int | None:
    m = _FILENAME_SURAH_RE.search(path.stem)
    return int(m.group(1)) if m else None


# ---------------------------------------------------------------------------
# verify2/SOURCES.tsv -- surah -> pass-2 reviewer label
# ---------------------------------------------------------------------------

def load_sources(path: Path) -> dict[int, str]:
    if not path.exists():
        return {}
    with path.open(encoding="utf-8") as fh:
        reader = csv.DictReader(fh, delimiter="\t")
        return {int(row["surah"]): row["reviewer_label"] for row in reader}


def save_sources(path: Path, sources: dict[int, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh, delimiter="\t")
        writer.writerow(SOURCES_HEADER)
        for surah in sorted(sources):
            writer.writerow([surah, sources[surah]])


# ---------------------------------------------------------------------------
# import-pass2
# ---------------------------------------------------------------------------

def validate_pass2_file(path: Path, ayahs: dict[str, str]) -> list[str]:
    """Validate one candidate pass-2 surah-NNN.tsv against that surah's
    CURRENT Roman text (`ayahs`, as in surah-NNN.json). Returns a list of
    problems; empty means valid. Checks: exact 5-column header; every row
    has exactly 5 fields; `ayah` is an integer with no duplicates; `verdict`
    is ok|concern; `sha256` matches the current text's hash; every ayah in
    `ayahs` has exactly one row (no gaps, no extras)."""
    problems: list[str] = []
    with path.open(encoding="utf-8", newline="") as fh:
        reader = csv.reader(fh, delimiter="\t")
        try:
            header = next(reader)
        except StopIteration:
            return ["empty file"]
        if header != PASS2_HEADER:
            return [f"header {header!r} != {PASS2_HEADER!r}"]

        seen: dict[int, list[str]] = {}
        for raw_row in reader:
            if not raw_row:
                continue
            if len(raw_row) != 5:
                problems.append(f"row {raw_row!r}: expected 5 fields, got {len(raw_row)}")
                continue
            ayah_s, verdict, sha, _concern, _suggestion = raw_row
            try:
                ayah = int(ayah_s)
            except ValueError:
                problems.append(f"row {raw_row!r}: non-integer ayah {ayah_s!r}")
                continue
            if ayah in seen:
                problems.append(f"ayah {ayah}: duplicate row")
                continue
            seen[ayah] = raw_row

            if verdict not in ("ok", "concern"):
                problems.append(f"ayah {ayah}: unknown verdict {verdict!r} (expected ok|concern)")

            key = str(ayah)
            if key not in ayahs:
                problems.append(f"ayah {ayah}: not part of this surah's current text")
                continue

            expected_hash = sha256_hex(ayahs[key])
            if sha != expected_hash:
                problems.append(
                    f"ayah {ayah}: sha256 {sha!r} does not match current text hash {expected_hash!r}"
                )

    missing = sorted(set(int(k) for k in ayahs) - set(seen))
    if missing:
        problems.append(f"missing row(s) for ayah(s): {missing}")

    return problems


def import_pass2(
    from_dir: Path,
    *,
    source_label: str,
    roman_dir: Path = ROMAN_DIR,
    verify2_dir: Path = VERIFY2_DIR,
) -> Pass2ImportReport:
    """Validate and copy every surah-NNN.tsv under `from_dir` into
    `verify2_dir`, one file at a time -- an invalid file is refused
    (reported, not copied) without affecting any other file in the batch.
    Records `source_label` for every successfully imported surah in
    `verify2_dir/SOURCES.tsv`, overwriting any existing label for a
    re-imported surah."""
    imported: list[int] = []
    refused: list[tuple[int | None, str]] = []
    sources_path = verify2_dir / "SOURCES.tsv"
    sources = load_sources(sources_path)

    for path in sorted(from_dir.glob("surah-*.tsv")):
        surah = _infer_surah(path)
        if surah is None:
            refused.append((None, f"{path.name}: cannot infer surah number from filename"))
            continue

        surah_path = roman_dir / f"surah-{surah:03d}.json"
        if not surah_path.exists():
            refused.append((surah, f"no surah-{surah:03d}.json under {roman_dir}"))
            continue
        ayahs = json.loads(surah_path.read_text(encoding="utf-8"))["ayahs"]

        problems = validate_pass2_file(path, ayahs)
        if problems:
            refused.append((surah, "; ".join(problems)))
            continue

        verify2_dir.mkdir(parents=True, exist_ok=True)
        dest = verify2_dir / f"surah-{surah:03d}.tsv"
        dest.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
        sources[surah] = source_label
        imported.append(surah)

    if imported:
        save_sources(sources_path, sources)

    return Pass2ImportReport(imported=sorted(imported), refused=refused)


# ---------------------------------------------------------------------------
# mark
# ---------------------------------------------------------------------------

def _findings_by_verse(findings) -> dict[tuple[int, int], list]:
    d: dict[tuple[int, int], list] = {}
    for f in findings:
        d.setdefault((f.surah, f.ayah), []).append(f)
    return d


def _verse_has_lint_error(findings_for_verse, allowlist, surah: int, ayah: int) -> bool:
    return any(
        f.level == "error" and (surah, ayah, f.check) not in allowlist
        for f in findings_for_verse
    )


def mark(
    *,
    roman_dir: Path = ROMAN_DIR,
    review_dir: Path = REVIEW_DIR,
    prereview_dir: Path = PREREVIEW_DIR,
    verify2_dir: Path = VERIFY2_DIR,
    canonical_path: Path = CANONICAL_PATH,
    allowlist_path: Path = ALLOWLIST_PATH,
    source: Path = DEFAULT_SOURCE,
    today: str | None = None,
    dry_run: bool = False,
) -> MarkReport:
    """ADR 0006 rule 2: promote every `pending` verse where prereview verdict
    == `ok`, verify2 verdict == `ok`, both sha256 == current text hash, and
    lint has no unallowed error for that verse, to `status=verified`. Only
    `pending` rows are ever examined -- `approved` rows are counted
    (informational) and never touched; anything else already carries a
    resolved status and is left alone too."""
    today = today or datetime.date.today().isoformat()

    all_findings, _ = lint_run(
        source=source, roman_dir=roman_dir, canonical_path=canonical_path,
        allowlist_path=allowlist_path, review_dir=review_dir,
    )
    allowlist = load_allowlist(allowlist_path)
    findings_by_verse = _findings_by_verse(all_findings)

    verified: list[tuple[int, int]] = []
    already_approved = 0
    disagreements = 0
    stale = 0
    lint_blocked = 0

    for surah_path in sorted(roman_dir.glob("surah-*.json")):
        data = json.loads(surah_path.read_text(encoding="utf-8"))
        surah = data["surah"]
        ayahs: dict[str, str] = data["ayahs"]

        ledger_path = ledger_path_for(surah, review_dir)
        if not ledger_path.exists():
            continue
        ledger = load_ledger(ledger_path)

        prereview = load_prereview_rows(prereview_dir / f"surah-{surah:03d}.tsv")
        verify2 = load_prereview_rows(verify2_dir / f"surah-{surah:03d}.tsv")

        new_ledger = dict(ledger)
        changed = False

        for ayah_key, text in ayahs.items():
            ayah = int(ayah_key)
            row = ledger.get(ayah)
            if row is None:
                continue
            if row.status == "approved":
                already_approved += 1
                continue
            if row.status != "pending":
                continue

            current_hash = sha256_hex(text)
            p = prereview.get(ayah)
            v2 = verify2.get(ayah)

            fresh_p = p is not None and p.sha256 == current_hash
            fresh_v2 = v2 is not None and v2.sha256 == current_hash
            if not fresh_p or not fresh_v2:
                stale += 1
                continue

            if p.verdict == "concern" or v2.verdict == "concern":
                disagreements += 1
                continue

            if _verse_has_lint_error(findings_by_verse.get((surah, ayah), []), allowlist, surah, ayah):
                lint_blocked += 1
                continue

            verified.append((surah, ayah))
            new_ledger[ayah] = LedgerRow(
                ayah=ayah, status="verified", sha256=current_hash,
                reviewer=_REVIEWER_LABEL, date=today, note=_NOTE,
            )
            changed = True

        if changed and not dry_run:
            save_ledger(ledger_path, new_ledger)
            write_status_for_surah(surah, roman_dir=roman_dir, review_dir=review_dir)

    return MarkReport(
        verified=verified, already_approved=already_approved,
        disagreements=disagreements, stale=stale, lint_blocked=lint_blocked,
    )


# ---------------------------------------------------------------------------
# queue
# ---------------------------------------------------------------------------

def _verdict_line(row, current_hash: str) -> str:
    if row is None:
        return "not available"
    if row.sha256 != current_hash:
        return "out of date"
    if row.verdict == "ok":
        return "looks right"
    return f"concern — {row.concern} → suggested: {row.suggestion}"


def build_queue(
    *,
    source: Path = DEFAULT_SOURCE,
    roman_dir: Path = ROMAN_DIR,
    review_dir: Path = REVIEW_DIR,
    prereview_dir: Path = PREREVIEW_DIR,
    verify2_dir: Path = VERIFY2_DIR,
) -> list[QueueEntry]:
    """ADR 0006 rule 3: every `pending` verse where either verdict is
    `concern`, or a verdict is stale (sha256 mismatch) or missing entirely.
    A verse both verdicts call `ok` and fresh is not a disagreement --
    that's exactly what `mark` promotes -- so it is never queued."""
    urdu_all = load_source(source)
    entries: list[QueueEntry] = []

    for surah_path in sorted(roman_dir.glob("surah-*.json")):
        data = json.loads(surah_path.read_text(encoding="utf-8"))
        surah = data["surah"]
        ayahs: dict[str, str] = data["ayahs"]

        ledger_path = ledger_path_for(surah, review_dir)
        if not ledger_path.exists():
            continue
        ledger = load_ledger(ledger_path)

        prereview = load_prereview_rows(prereview_dir / f"surah-{surah:03d}.tsv")
        verify2 = load_prereview_rows(verify2_dir / f"surah-{surah:03d}.tsv")

        for ayah_key, text in ayahs.items():
            ayah = int(ayah_key)
            row = ledger.get(ayah)
            if row is None or row.status != "pending":
                continue

            current_hash = sha256_hex(text)
            p = prereview.get(ayah)
            v2 = verify2.get(ayah)
            fresh_p = p is not None and p.sha256 == current_hash
            fresh_v2 = v2 is not None and v2.sha256 == current_hash

            if not fresh_p or not fresh_v2:
                reason = "stale"
            elif p.verdict == "concern" or v2.verdict == "concern":
                reason = "concern"
            else:
                continue

            entries.append(QueueEntry(
                surah=surah, ayah=ayah, urdu=urdu_all.get((surah, ayah), ""), roman=text,
                sha256=current_hash, pass1=_verdict_line(p, current_hash),
                pass2=_verdict_line(v2, current_hash), reason=reason,
            ))

    entries.sort(key=lambda e: (e.surah, e.ayah))
    return entries


def render_queue_md(entries: list[QueueEntry]) -> str:
    concern_n = sum(1 for e in entries if e.reason == "concern")
    stale_n = sum(1 for e in entries if e.reason == "stale")
    parts = [
        "# ADR 0006 disagreement queue",
        "",
        f"{len(entries)} verse(s) need a ruling — {concern_n} concern, {stale_n} stale/missing. "
        "Answer each with `- decision:` followed by `ok` (approve the current text as-is) "
        "or the full corrected verse. Leave it blank to skip for now.",
    ]

    current_surah: int | None = None
    for e in entries:
        if e.surah != current_surah:
            current_surah = e.surah
            parts += ["", f"## Surah {e.surah}"]
        parts += [
            "",
            f"### {e.surah}:{e.ayah}",
            f"**Urdu:** {e.urdu}",
            f"**Roman:** {e.roman}",
            f"**Pass 1:** {e.pass1}",
            f"**Pass 2:** {e.pass2}",
            "- decision:",
            f"<!-- sha256:{e.sha256} -->",
        ]

    return "\n".join(parts) + "\n"


# ---------------------------------------------------------------------------
# queue-import
# ---------------------------------------------------------------------------

_QUEUE_SURAH_HEADING_RE = re.compile(r"^##\s+Surah\s+(\d+)")
_QUEUE_VERSE_HEADER_RE = re.compile(r"^###\s+(\d+):(\d+)\s*$")
_QUEUE_SHA_RE = re.compile(r"<!--\s*sha256:([0-9a-f]{64})\s*-->")
_QUEUE_DECISION_RE = re.compile(r"^-\s*decision:\s*(.*)$")


def parse_queue_md(text: str) -> QueueImportResult:
    lines = text.splitlines()

    blocks: list[tuple[int, int, list[str]]] = []
    current_surah: int | None = None
    current_ayah: int | None = None
    current_lines: list[str] = []

    for line in lines:
        m_s = _QUEUE_SURAH_HEADING_RE.match(line)
        if m_s:
            if current_ayah is not None:
                blocks.append((current_surah, current_ayah, current_lines))
                current_ayah = None
                current_lines = []
            current_surah = int(m_s.group(1))
            continue

        m_v = _QUEUE_VERSE_HEADER_RE.match(line)
        if m_v:
            if current_ayah is not None:
                blocks.append((current_surah, current_ayah, current_lines))
            current_surah = int(m_v.group(1))
            current_ayah = int(m_v.group(2))
            current_lines = []
            continue

        if current_ayah is not None:
            current_lines.append(line)

    if current_ayah is not None:
        blocks.append((current_surah, current_ayah, current_lines))

    rows: list[QueueImportedRow] = []
    approved = needs_fix = untouched = 0

    for surah, ayah, block_lines in blocks:
        sha: str | None = None
        decision_parts: list[str] = []
        in_decision = False

        for line in block_lines:
            m_sha = _QUEUE_SHA_RE.search(line)
            if m_sha:
                sha = m_sha.group(1)
                in_decision = False
                continue

            m_dec = _QUEUE_DECISION_RE.match(line)
            if m_dec:
                in_decision = True
                first = m_dec.group(1).strip()
                if first:
                    decision_parts.append(first)
                continue

            stripped = line.strip()
            if not stripped:
                continue
            if stripped.startswith("#") or stripped.startswith("**"):
                in_decision = False
                continue
            if in_decision:
                decision_parts.append(stripped)

        if sha is None:
            raise MissingHashError(f"surah {surah} ayah {ayah}: missing sha256 comment")

        decision_text = " ".join(decision_parts).strip()

        if not decision_text:
            untouched += 1
        elif decision_text.lower() == "ok":
            rows.append(QueueImportedRow(surah=surah, ayah=ayah, decision="approve", corrected_text="", seen_sha256=sha))
            approved += 1
        else:
            rows.append(QueueImportedRow(surah=surah, ayah=ayah, decision="needs-fix", corrected_text=decision_text, seen_sha256=sha))
            needs_fix += 1

    return QueueImportResult(rows=rows, approved=approved, needs_fix=needs_fix, untouched=untouched)


def write_queue_patches(result: QueueImportResult, out_dir: Path) -> list[Path]:
    """One apply_review.py-format patch TSV per surah
    (`ayah, decision, corrected_text, note, seen_sha256`), named so
    apply_review.py's own infer_surah_from_filename finds the right surah
    without needing --surah."""
    out_dir.mkdir(parents=True, exist_ok=True)
    by_surah: dict[int, list[QueueImportedRow]] = {}
    for row in result.rows:
        by_surah.setdefault(row.surah, []).append(row)

    written: list[Path] = []
    for surah in sorted(by_surah):
        rows = sorted(by_surah[surah], key=lambda r: r.ayah)
        lines = ["ayah\tdecision\tcorrected_text\tnote\tseen_sha256"]
        for r in rows:
            lines.append("\t".join([str(r.ayah), r.decision, r.corrected_text, _NOTE + " queue", r.seen_sha256]))
        path = out_dir / f"surah-{surah:03d}-patch.tsv"
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        written.append(path)

    return written


# ---------------------------------------------------------------------------
# sample
# ---------------------------------------------------------------------------

def collect_verified_verses(
    *, roman_dir: Path = ROMAN_DIR, review_dir: Path = REVIEW_DIR,
) -> list[tuple[int, int, str]]:
    result: list[tuple[int, int, str]] = []
    for surah_path in sorted(roman_dir.glob("surah-*.json")):
        data = json.loads(surah_path.read_text(encoding="utf-8"))
        surah = data["surah"]
        ayahs: dict[str, str] = data["ayahs"]

        ledger_path = ledger_path_for(surah, review_dir)
        if not ledger_path.exists():
            continue
        ledger = load_ledger(ledger_path)

        for ayah_key, text in ayahs.items():
            ayah = int(ayah_key)
            row = ledger.get(ayah)
            if row is not None and row.status == "verified":
                result.append((surah, ayah, text))

    result.sort()
    return result


def stratified_sample(
    verses: list[tuple[int, int, str]], sources: dict[int, str], *, n: int, seed: int,
) -> list[tuple[int, int, str]]:
    """Random, seed-deterministic sample of `n` verses from `verses`,
    stratified so surahs whose pass-2 reviewer label mentions "claude
    sonnet" (ADR 0006's own caveat about those surahs' reduced independence)
    are drawn in proportion to their share of the population, not
    over/under-represented by chance."""
    total = len(verses)
    if total == 0 or n <= 0:
        return []
    n = min(n, total)

    claude_surahs = {s for s, label in sources.items() if _CLAUDE_LABEL_MARKER in label.lower()}
    claude = [v for v in verses if v[0] in claude_surahs]
    other = [v for v in verses if v[0] not in claude_surahs]

    n_claude = min(round(n * len(claude) / total), len(claude))
    n_other = min(n - n_claude, len(other))

    shortfall = n - (n_claude + n_other)
    if shortfall > 0:
        extra_claude = min(shortfall, len(claude) - n_claude)
        n_claude += extra_claude
        shortfall -= extra_claude
    if shortfall > 0:
        extra_other = min(shortfall, len(other) - n_other)
        n_other += extra_other

    rng = random.Random(seed)
    picked = rng.sample(claude, n_claude) + rng.sample(other, n_other)
    rng.shuffle(picked)
    return picked


def render_sample_md(verses: list[tuple[int, int, str]], urdu: dict[tuple[int, int], str]) -> str:
    parts = [
        "# ADR 0006 owner sample",
        "",
        f"{len(verses)} verified verse(s), randomly sampled for a read-aloud check "
        "(ADR 0006 rule 4). For each verse, leave `- wrong:` blank if it's fine, or "
        "describe the problem if it isn't.",
    ]
    for surah, ayah, text in verses:
        parts += [
            "",
            f"### {surah}:{ayah}",
            f"**Urdu:** {urdu.get((surah, ayah), '')}",
            f"**Roman:** {text}",
            "- wrong:",
            f"<!-- sha256:{sha256_hex(text)} -->",
        ]
    return "\n".join(parts) + "\n"


def sample(
    *,
    n: int = 150,
    seed: int,
    out: Path,
    roman_dir: Path = ROMAN_DIR,
    review_dir: Path = REVIEW_DIR,
    verify2_dir: Path = VERIFY2_DIR,
    source: Path = DEFAULT_SOURCE,
) -> list[tuple[int, int, str]]:
    verses = collect_verified_verses(roman_dir=roman_dir, review_dir=review_dir)
    sources = load_sources(verify2_dir / "SOURCES.tsv")
    picked = sorted(stratified_sample(verses, sources, n=n, seed=seed))

    urdu_all = load_source(source)
    md = render_sample_md(picked, urdu_all)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(md, encoding="utf-8")
    return picked


# ---------------------------------------------------------------------------
# sample-import
# ---------------------------------------------------------------------------

_SAMPLE_VERSE_HEADER_RE = re.compile(r"^###\s+(\d+):(\d+)\s*$")
_SAMPLE_SHA_RE = re.compile(r"<!--\s*sha256:([0-9a-f]{64})\s*-->")
_SAMPLE_WRONG_RE = re.compile(r"^-\s*wrong:\s*(.*)$")


def parse_sample_md(text: str) -> SampleImportResult:
    lines = text.splitlines()

    blocks: list[tuple[int, int, list[str]]] = []
    current_surah: int | None = None
    current_ayah: int | None = None
    current_lines: list[str] = []

    for line in lines:
        m = _SAMPLE_VERSE_HEADER_RE.match(line)
        if m:
            if current_ayah is not None:
                blocks.append((current_surah, current_ayah, current_lines))
            current_surah, current_ayah = int(m.group(1)), int(m.group(2))
            current_lines = []
            continue
        if current_ayah is not None:
            current_lines.append(line)

    if current_ayah is not None:
        blocks.append((current_surah, current_ayah, current_lines))

    wrong: list[SampleFinding] = []
    fine = 0

    for surah, ayah, block_lines in blocks:
        wrong_parts: list[str] = []
        in_wrong = False

        for line in block_lines:
            if _SAMPLE_SHA_RE.search(line):
                in_wrong = False
                continue
            m_w = _SAMPLE_WRONG_RE.match(line)
            if m_w:
                in_wrong = True
                first = m_w.group(1).strip()
                if first:
                    wrong_parts.append(first)
                continue
            stripped = line.strip()
            if not stripped:
                continue
            if stripped.startswith("#") or stripped.startswith("**"):
                in_wrong = False
                continue
            if in_wrong:
                wrong_parts.append(stripped)

        description = " ".join(wrong_parts).strip()
        if description:
            wrong.append(SampleFinding(surah=surah, ayah=ayah, description=description))
        else:
            fine += 1

    return SampleImportResult(total=len(blocks), wrong=wrong, fine=fine)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    p_imp = sub.add_parser("import-pass2", help="validate and copy second-pass verdict files into verify2/")
    p_imp.add_argument("--from", dest="from_dir", type=Path, required=True)
    p_imp.add_argument("--source-label", required=True)
    p_imp.add_argument("--roman-dir", type=Path, default=ROMAN_DIR)
    p_imp.add_argument("--verify2-dir", type=Path, default=VERIFY2_DIR)

    p_mark = sub.add_parser("mark", help="promote double-AI-ok pending verses to verified")
    p_mark.add_argument("--dry-run", action="store_true")
    p_mark.add_argument("--roman-dir", type=Path, default=ROMAN_DIR)
    p_mark.add_argument("--review-dir", type=Path, default=REVIEW_DIR)
    p_mark.add_argument("--prereview-dir", type=Path, default=PREREVIEW_DIR)
    p_mark.add_argument("--verify2-dir", type=Path, default=VERIFY2_DIR)
    p_mark.add_argument("--canonical", type=Path, default=CANONICAL_PATH)
    p_mark.add_argument("--allowlist", type=Path, default=ALLOWLIST_PATH)
    p_mark.add_argument("--source", type=Path, default=DEFAULT_SOURCE)

    p_queue = sub.add_parser("queue", help="write the ADR 0006 disagreement queue")
    p_queue.add_argument("--out", type=Path, required=True)
    p_queue.add_argument("--roman-dir", type=Path, default=ROMAN_DIR)
    p_queue.add_argument("--review-dir", type=Path, default=REVIEW_DIR)
    p_queue.add_argument("--prereview-dir", type=Path, default=PREREVIEW_DIR)
    p_queue.add_argument("--verify2-dir", type=Path, default=VERIFY2_DIR)
    p_queue.add_argument("--source", type=Path, default=DEFAULT_SOURCE)

    p_qimp = sub.add_parser("queue-import", help="convert an owner-edited queue file to apply_review.py patches")
    p_qimp.add_argument("file", type=Path)
    p_qimp.add_argument("--out", type=Path, required=True, help="directory to write surah-NNN-patch.tsv files into")

    p_sample = sub.add_parser("sample", help="write the ADR 0006 owner sample")
    p_sample.add_argument("--n", type=int, default=150)
    p_sample.add_argument("--seed", type=int, required=True)
    p_sample.add_argument("--out", type=Path, required=True)
    p_sample.add_argument("--roman-dir", type=Path, default=ROMAN_DIR)
    p_sample.add_argument("--review-dir", type=Path, default=REVIEW_DIR)
    p_sample.add_argument("--verify2-dir", type=Path, default=VERIFY2_DIR)
    p_sample.add_argument("--source", type=Path, default=DEFAULT_SOURCE)

    p_simp = sub.add_parser("sample-import", help="summarise owner findings from an edited sample file")
    p_simp.add_argument("file", type=Path)

    args = parser.parse_args()

    if args.command == "import-pass2":
        report = import_pass2(
            args.from_dir, source_label=args.source_label, roman_dir=args.roman_dir, verify2_dir=args.verify2_dir,
        )
        print(f"imported={len(report.imported)} refused={len(report.refused)}")
        for surah, reason in report.refused:
            print(f"  refused surah {surah}: {reason}")
        return 1 if report.refused else 0

    if args.command == "mark":
        report = mark(
            roman_dir=args.roman_dir, review_dir=args.review_dir, prereview_dir=args.prereview_dir,
            verify2_dir=args.verify2_dir, canonical_path=args.canonical, allowlist_path=args.allowlist,
            source=args.source, dry_run=args.dry_run,
        )
        mode = "(dry-run) " if args.dry_run else ""
        print(
            f"{mode}verified={len(report.verified)} already_approved={report.already_approved} "
            f"disagreements={report.disagreements} stale={report.stale} lint_blocked={report.lint_blocked}"
        )
        return 0

    if args.command == "queue":
        entries = build_queue(
            source=args.source, roman_dir=args.roman_dir, review_dir=args.review_dir,
            prereview_dir=args.prereview_dir, verify2_dir=args.verify2_dir,
        )
        md = render_queue_md(entries)
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(md, encoding="utf-8")
        print(f"wrote {len(entries)} verse(s) to {args.out}")
        return 0

    if args.command == "queue-import":
        text = args.file.read_text(encoding="utf-8")
        result = parse_queue_md(text)
        written = write_queue_patches(result, args.out)
        print(f"approve={result.approved} needs-fix={result.needs_fix} untouched={result.untouched}")
        for path in written:
            print(f"wrote {path}")
        return 0

    if args.command == "sample":
        picked = sample(
            n=args.n, seed=args.seed, out=args.out, roman_dir=args.roman_dir, review_dir=args.review_dir,
            verify2_dir=args.verify2_dir, source=args.source,
        )
        print(f"wrote {len(picked)} verse(s) to {args.out}")
        return 0

    if args.command == "sample-import":
        text = args.file.read_text(encoding="utf-8")
        result = parse_sample_md(text)
        print(f"total={result.total} fine={result.fine} wrong={len(result.wrong)}")
        for f in result.wrong:
            print(f"  {f.surah}:{f.ayah} — {f.description}")
        return 0

    parser.error("unknown command")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
