#!/usr/bin/env python3
"""
lint_roman_urdu.py — content-quality checks over `data/roman-urdu/`, cross-read
against the Urdu source (read at runtime, never vendored — Phase 1 step 3 of
docs/ROMAN-URDU-GOLDEN-PLAN.md is on hold pending owner approval of committing
the source text).

This is Phase 2 of the plan: it REPORTS findings. It does not fix anything and
must never write to data/roman-urdu/*.json.

Checks (see docs/ROMAN-URDU-GOLDEN-PLAN.md §4 Phase 2 and
docs/decisions/0005-roman-urdu-orthography-v1.md for the rules each encodes):

  2a canonical         — a token matches a canonical.tsv `variant` where the
                          row's status is `decided` (error) or `needs-review`
                          (info); `keep` rows are never flagged.
  2b parity             — per-verse token-count parity for a handful of
                          unambiguous function words. Noisy by nature (source
                          glue like ہیںکہ) -> warn only.
  2c gloss parity        — count of non-footnote, non-honorific bracketed
                          spans must match between Urdu and Roman.
  2d length outlier      — Roman/Urdu word-count ratio < 0.75 on a verse with
                          >= 6 Urdu words -> warn (a review prompt, not proof
                          of a defect).
  2e forbidden forms     — `mein ne`, standalone `kay`/`key`/`wo`, digits,
                          non-ASCII characters.
  2g honorific typography — ADR 0005 R4 canonical honorific spellings, plus
                          unbalanced parentheses (always an error).

  2h names — SKIPPED. Needs an owner-supplied canonical name list before it
             can be written. TODO, not code: see plan §4 Phase 2 "2h names".

Usage:
    python3 scripts/lint_roman_urdu.py
    python3 scripts/lint_roman_urdu.py --surah 26
    python3 scripts/lint_roman_urdu.py --source /path/to/ur-junagarri-simple.db
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sqlite3
import sys
from pathlib import Path
from typing import NamedTuple

ROOT = Path(__file__).resolve().parents[1]
ROMAN_DIR = ROOT / "data" / "roman-urdu"
CANONICAL_PATH = ROMAN_DIR / "canonical.tsv"
ALLOWLIST_PATH = ROMAN_DIR / "lint-allowlist.tsv"
OUT_PATH = ROOT / "out" / "lint.tsv"
DEFAULT_SOURCE = Path.home() / "code" / "alquran-data" / "sources" / "translations" / "ur-junagarri-simple.db"

# ADR 0005 was ACCEPTED by the owner 2026-09-25. Non-canonical honorific
# typography on a STANDALONE bracket span (the whole "(...)" is just the
# honorific) is now `error`. One sub-question is still explicitly open per
# the ADR: an honorific embedded inside a longer translator's gloss, e.g.
# "(Yaqoob alaihis salaam ne)" -- those stay `info` regardless of this flag,
# because nesting policy for that case has not been decided yet.
ADR_0005_ACCEPTED = True


class Finding(NamedTuple):
    surah: int
    ayah: int
    check: str
    level: str
    detail: str


# ---------------------------------------------------------------------------
# Tokenisation
# ---------------------------------------------------------------------------

# Punctuation that would otherwise glue two words into one false "token" or
# leave a bracket character stuck to a word. Deliberately not full
# normalisation (scripts/normalise.py) — this is word-splitting for counting,
# not a lookup key.
_URDU_PUNCT = "۔،؟!.,()﴿﴾:؛"
_URDU_PUNCT_RE = re.compile("[" + re.escape(_URDU_PUNCT) + "]")


def tokenize_urdu(text: str) -> list[str]:
    return _URDU_PUNCT_RE.sub(" ", text).split()


# ---------------------------------------------------------------------------
# 2a — canonical spelling
# ---------------------------------------------------------------------------

_ROMAN_WORD_RE = re.compile(r"[A-Za-z']+")


def load_canonical(path: Path) -> dict[str, tuple[str, str]]:
    mapping: dict[str, tuple[str, str]] = {}
    with path.open(encoding="utf-8") as fh:
        reader = csv.DictReader(fh, delimiter="\t")
        for row in reader:
            mapping[row["variant"].lower()] = (row["canonical"], row["status"])
    return mapping


def check_canonical(surah: int, ayah: int, roman_text: str, canonical_map: dict[str, tuple[str, str]]) -> list[Finding]:
    findings: list[Finding] = []
    for m in _ROMAN_WORD_RE.finditer(roman_text):
        word = m.group(0)
        entry = canonical_map.get(word.lower())
        if entry is None:
            continue
        canonical, status = entry
        if canonical.lower() == word.lower():
            continue
        if status == "decided":
            level = "error"
        elif status == "needs-review":
            level = "info"
        else:  # "keep" or anything else -> never flagged
            continue
        findings.append(Finding(
            surah, ayah, "2a-canonical", level,
            f"{word!r} matches canonical.tsv variant -> canonical {canonical!r} (status={status})",
        ))
    return findings


# ---------------------------------------------------------------------------
# 2b — parity
# ---------------------------------------------------------------------------

# (urdu exact token, roman regex) pairs that are unambiguous enough to count.
_PARITY_EXACT_PAIRS = [
    ("اور", re.compile(r"\baur\b", re.IGNORECASE)),
    ("نہیں", re.compile(r"\b(nahin|nahi)\b", re.IGNORECASE)),
    ("ہیں", re.compile(r"\bhain\b", re.IGNORECASE)),
]
_WOH_TOKENS = ("وہ", "وه")
_ROMAN_WOH_RE = re.compile(r"\bwoh\b", re.IGNORECASE)
_ROMAN_WAHI_RE = re.compile(r"\bwahi\b", re.IGNORECASE)
# "llah" rather than "allah": Roman compounds attach the root as "-ullah"
# (Baitullah, kalaamullah, Rasoolullah), which does not literally contain the
# substring "allah" — only standalone "Allah" does. "llah" is the substring
# every one of them shares, verified against the real corpus.
_ROMAN_ALLAH_FAMILY_RE = re.compile(r"llah", re.IGNORECASE)


def check_parity(surah: int, ayah: int, urdu_text: str, roman_text: str) -> list[Finding]:
    findings: list[Finding] = []
    urdu_tokens = tokenize_urdu(urdu_text)

    for urdu_word, roman_re in _PARITY_EXACT_PAIRS:
        u_count = sum(1 for t in urdu_tokens if t == urdu_word)
        r_count = len(roman_re.findall(roman_text))
        if u_count != r_count:
            findings.append(Finding(
                surah, ayah, "2b-parity", "warn",
                f"{urdu_word} count={u_count} vs roman count={r_count}",
            ))

    woh_count = sum(1 for t in urdu_tokens if t in _WOH_TOKENS)
    bigram_count = sum(
        1 for i in range(len(urdu_tokens) - 1)
        if urdu_tokens[i] in _WOH_TOKENS and urdu_tokens[i + 1] == "ہی"
    )
    roman_woh = len(_ROMAN_WOH_RE.findall(roman_text))
    roman_wahi = len(_ROMAN_WAHI_RE.findall(roman_text))
    roman_woh_equiv = roman_woh + min(roman_wahi, bigram_count)
    if woh_count != roman_woh_equiv:
        findings.append(Finding(
            surah, ayah, "2b-parity", "warn",
            f"وہ/وه count={woh_count} vs roman woh/wahi-equivalent count={roman_woh_equiv}",
        ))

    u_allah = sum(1 for t in urdu_tokens if "اللہ" in t)
    r_allah = len(_ROMAN_ALLAH_FAMILY_RE.findall(roman_text))
    if u_allah != r_allah:
        findings.append(Finding(
            surah, ayah, "2b-parity", "warn",
            f"اللہ count={u_allah} vs roman allah-family count={r_allah}",
        ))

    return findings


# ---------------------------------------------------------------------------
# 2c — gloss parity
# ---------------------------------------------------------------------------

_BRACKET_RE = re.compile(r"\(([^()]*)\)|﴿([^﴿﴾]*)﴾")

_HONORIFIC_URDU_SUBSTRINGS = (
    "علیہ السلام", "علیہم السلام", "علیہما السلام", "علیہا السلام",
    "صلی اللہ علیہ وسلم",
)
_HONORIFIC_ROMAN_RE = re.compile(r"alaih|sallallahu", re.IGNORECASE)


def extract_bracket_spans(text: str) -> list[str]:
    spans = []
    for m in _BRACKET_RE.finditer(text):
        inner = m.group(1) if m.group(1) is not None else m.group(2)
        spans.append(inner)
    return spans


def _is_honorific_urdu(span: str) -> bool:
    s = span.strip()
    if any(h in s for h in _HONORIFIC_URDU_SUBSTRINGS):
        return True
    # Loose fallback for spelling variants the corpus contains (gotchas: many
    # honorific spellings, ADR 0005 R4).
    return ("علیہ" in s and "السلام" in s) or ("صلی" in s and "وسلم" in s)


def _is_honorific_roman(span: str) -> bool:
    return bool(_HONORIFIC_ROMAN_RE.search(span))


def check_gloss_parity(surah: int, ayah: int, urdu_text: str, roman_text: str) -> list[Finding]:
    urdu_spans = [s for s in extract_bracket_spans(urdu_text) if s.strip() and not s.strip().isdigit()]
    urdu_non_honorific = [s for s in urdu_spans if not _is_honorific_urdu(s)]

    roman_spans = [s for s in extract_bracket_spans(roman_text) if s.strip() and not s.strip().isdigit()]
    roman_non_honorific = [s for s in roman_spans if not _is_honorific_roman(s)]

    if len(urdu_non_honorific) != len(roman_non_honorific):
        return [Finding(
            surah, ayah, "2c-gloss", "error",
            f"non-honorific gloss spans: urdu={len(urdu_non_honorific)} {urdu_non_honorific!r} "
            f"vs roman={len(roman_non_honorific)} {roman_non_honorific!r}",
        )]
    return []


# ---------------------------------------------------------------------------
# 2d — length outlier
# ---------------------------------------------------------------------------

def check_length_outlier(surah: int, ayah: int, urdu_text: str, roman_text: str) -> list[Finding]:
    urdu_tokens = tokenize_urdu(urdu_text)
    if len(urdu_tokens) < 6:
        return []
    roman_tokens = roman_text.split()
    ratio = len(roman_tokens) / len(urdu_tokens)
    if ratio < 0.75:
        return [Finding(
            surah, ayah, "2d-length", "warn",
            f"roman/urdu word ratio={ratio:.2f} ({len(roman_tokens)}/{len(urdu_tokens)})",
        )]
    return []


# ---------------------------------------------------------------------------
# 2e — forbidden forms
# ---------------------------------------------------------------------------

_FORBIDDEN_PHRASE_RE = re.compile(r"\bmein ne\b", re.IGNORECASE)
_FORBIDDEN_WORD_RE = re.compile(r"\b(kay|key|wo)\b", re.IGNORECASE)
_DIGIT_RE = re.compile(r"[0-9]")
_NON_ASCII_RE = re.compile(r"[^\x00-\x7F]")


def check_forbidden(surah: int, ayah: int, roman_text: str) -> list[Finding]:
    findings: list[Finding] = []
    for m in _FORBIDDEN_PHRASE_RE.finditer(roman_text):
        findings.append(Finding(surah, ayah, "2e-forbidden", "error", f"forbidden phrase: {m.group(0)!r}"))
    for m in _FORBIDDEN_WORD_RE.finditer(roman_text):
        findings.append(Finding(surah, ayah, "2e-forbidden", "error", f"forbidden standalone word: {m.group(0)!r}"))
    for m in _DIGIT_RE.finditer(roman_text):
        findings.append(Finding(surah, ayah, "2e-forbidden", "error", f"digit: {m.group(0)!r}"))
    for m in _NON_ASCII_RE.finditer(roman_text):
        findings.append(Finding(surah, ayah, "2e-forbidden", "error", f"non-ascii character: {m.group(0)!r}"))
    return findings


# ---------------------------------------------------------------------------
# 2g — honorific typography (+ unbalanced parentheses)
# ---------------------------------------------------------------------------

_PAREN_SPAN_RE = re.compile(r"\([^()]*\)")

_ALLOWED_HONORIFICS = {
    "(Alaihis-Salaam)",
    "(Alaihimus-Salaam)",
    "(Alaihimas-Salaam)",  # dual, owner Q1 2026-09-25
    "(Alaihas-Salaam)",
    "(Sallallahu Alaihi Wasallam)",
}

# A "standalone" honorific span is one where the WHOLE "(...)" is nothing but
# the honorific phrase -- these are the ones ADR 0005 R4 actually settles.
# Anything else that merely contains an honorific keyword (a name, "ne",
# "ki", "bhi", ...) is an honorific embedded in a longer translator's gloss,
# which the ADR explicitly leaves open (nested-brackets question). Compare
# with scripts/apply_canonical.py's normalize_honorific_span, which applies
# the same standalone/embedded distinction mechanically.
_HONORIFIC_ONLY_NORMALIZED = {
    "alaihis salaam",
    "alaihimus salaam",
    "alaihimas salaam",
    "alaihim salaam",
    "alaiha salaam",
    "sallallahu alaihi wasallam",
    "sallallahu alaihi wa sallam",
}


_EMBEDDED_HONORIFIC_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"\bsallallahu[\s-]+alaihi[\s-]+wa[\s-]*sallam\b", re.I), "Sallallahu Alaihi Wasallam"),
    (re.compile(r"\balaihimas[\s-]+salaam\b", re.I), "Alaihimas-Salaam"),
    (re.compile(r"\balaihimu?s?[\s-]+salaam\b", re.I), "Alaihimus-Salaam"),
    (re.compile(r"\balaihis[\s-]+salaam\b", re.I), "Alaihis-Salaam"),
    (re.compile(r"\balaiha?s?[\s-]+salaam\b", re.I), "Alaihas-Salaam"),
]


def _normalize_for_honorific_match(span: str) -> str:
    return re.sub(r"[-\s]+", " ", span.strip().lower()).strip()


def _is_standalone_honorific_span(span: str) -> bool:
    return _normalize_for_honorific_match(span) in _HONORIFIC_ONLY_NORMALIZED


def check_honorific_typography(
    surah: int, ayah: int, roman_text: str, *, adr_0005_accepted: bool = ADR_0005_ACCEPTED
) -> list[Finding]:
    findings: list[Finding] = []

    open_count = roman_text.count("(")
    close_count = roman_text.count(")")
    if open_count != close_count:
        findings.append(Finding(
            surah, ayah, "2g-parens", "error",
            f"unbalanced parentheses: {open_count} '(' vs {close_count} ')'",
        ))

    for m in _PAREN_SPAN_RE.finditer(roman_text):
        span = m.group(0)
        if not _is_honorific_roman(span):
            continue
        if span in _ALLOWED_HONORIFICS:
            continue
        inner = span[1:-1] if span.startswith("(") and span.endswith(")") else span
        if not _is_standalone_honorific_span(inner):
            # Embedded in a longer gloss. Owner ruling Q2 (2026-09-25): the
            # honorific is written canonically there, without its own
            # brackets -- fine when it already is.
            if all(m2.group(0) == canonical
                   for pattern, canonical in _EMBEDDED_HONORIFIC_PATTERNS
                   for m2 in pattern.finditer(inner)):
                continue
        level = "error" if adr_0005_accepted else "info"
        findings.append(Finding(
            surah, ayah, "2g-honorific", level,
            f"non-canonical honorific typography (ADR 0005 R4): {span!r}",
        ))

    return findings


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

# 2j -- split future verbs (owner ruling Q17, 2026-09-25): "jaao ge" must be
# written "jaaoge". Same pattern as apply_canonical.SPLIT_FUTURE_RE.
_SPLIT_FUTURE_RE = re.compile(r"([A-Za-z]+) (g[aei])(?![A-Za-z'\-])")


def check_split_future(surah: int, ayah: int, roman_text: str) -> list[Finding]:
    return [
        Finding(surah, ayah, "2j-split-future", "error",
                f"split future verb {m.group(0)!r}; write {m.group(1) + m.group(2)!r}")
        for m in _SPLIT_FUTURE_RE.finditer(roman_text)
    ]


# 2k -- "misl-e-X" (owner ruling Q19, 2026-09-25): write "misl X".
_MISL_IZAFAT_RE = re.compile(r"\b[Mm]isl-e-\S+")


def check_misl(surah: int, ayah: int, roman_text: str) -> list[Finding]:
    return [
        Finding(surah, ayah, "2k-misl", "error", f"invented izafat {m.group(0)!r}; write 'misl X'")
        for m in _MISL_IZAFAT_RE.finditer(roman_text)
    ]


def lint_verse(
    surah: int, ayah: int, urdu_text: str, roman_text: str,
    canonical_map: dict[str, tuple[str, str]], *, adr_0005_accepted: bool = ADR_0005_ACCEPTED,
) -> list[Finding]:
    findings: list[Finding] = []
    findings += check_canonical(surah, ayah, roman_text, canonical_map)
    findings += check_parity(surah, ayah, urdu_text, roman_text)
    findings += check_gloss_parity(surah, ayah, urdu_text, roman_text)
    findings += check_length_outlier(surah, ayah, urdu_text, roman_text)
    findings += check_forbidden(surah, ayah, roman_text)
    findings += check_split_future(surah, ayah, roman_text)
    findings += check_misl(surah, ayah, roman_text)
    findings += check_honorific_typography(surah, ayah, roman_text, adr_0005_accepted=adr_0005_accepted)
    return findings


def load_allowlist(path: Path) -> set[tuple[int, int, str]]:
    allowed: set[tuple[int, int, str]] = set()
    if not path.exists():
        return allowed
    with path.open(encoding="utf-8") as fh:
        reader = csv.DictReader(fh, delimiter="\t")
        for row in reader:
            allowed.add((int(row["surah"]), int(row["ayah"]), row["check"]))
    return allowed


def load_source(path: Path) -> dict[tuple[int, int], str]:
    if not path.exists():
        sys.exit(
            f"Urdu source DB not found: {path}\n"
            "Phase 1 step 3 (vendoring the source) is on hold pending owner "
            "approval; lint reads it at runtime via --source."
        )
    con = sqlite3.connect(path)
    rows = con.execute("SELECT sura, ayah, text FROM translation")
    return {(int(s), int(a)): t for s, a, t in rows}


def load_roman(roman_dir: Path) -> dict[tuple[int, int], str]:
    result: dict[tuple[int, int], str] = {}
    for path in sorted(roman_dir.glob("surah-*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        surah = data["surah"]
        for ayah_str, text in data["ayahs"].items():
            result[(surah, int(ayah_str))] = text
    return result


def run(
    *, source: Path = DEFAULT_SOURCE, roman_dir: Path = ROMAN_DIR,
    canonical_path: Path = CANONICAL_PATH, allowlist_path: Path = ALLOWLIST_PATH,
    surah: int | None = None, adr_0005_accepted: bool = ADR_0005_ACCEPTED,
) -> tuple[list[Finding], bool]:
    urdu = load_source(source)
    roman = load_roman(roman_dir)
    canonical_map = load_canonical(canonical_path)
    allowlist = load_allowlist(allowlist_path)

    all_findings: list[Finding] = []
    for (s, a), roman_text in sorted(roman.items()):
        if surah is not None and s != surah:
            continue
        urdu_text = urdu.get((s, a), "")
        all_findings.extend(
            lint_verse(s, a, urdu_text, roman_text, canonical_map, adr_0005_accepted=adr_0005_accepted)
        )

    has_unallowed_error = any(
        f.level == "error" and (f.surah, f.ayah, f.check) not in allowlist
        for f in all_findings
    )
    return all_findings, has_unallowed_error


def write_findings(findings: list[Finding], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh, delimiter="\t")
        writer.writerow(["surah", "ayah", "check", "level", "detail"])
        for f in findings:
            writer.writerow([f.surah, f.ayah, f.check, f.level, f.detail])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--surah", type=int, help="lint a single surah")
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE, help=f"Urdu source sqlite DB (default: {DEFAULT_SOURCE})")
    parser.add_argument("--roman-dir", type=Path, default=ROMAN_DIR)
    parser.add_argument("--canonical", type=Path, default=CANONICAL_PATH)
    parser.add_argument("--allowlist", type=Path, default=ALLOWLIST_PATH)
    parser.add_argument("--out", type=Path, default=OUT_PATH)
    args = parser.parse_args()

    findings, has_unallowed_error = run(
        source=args.source, roman_dir=args.roman_dir, canonical_path=args.canonical,
        allowlist_path=args.allowlist, surah=args.surah,
    )
    write_findings(findings, args.out)
    print(f"wrote {len(findings)} findings to {args.out}")
    return 1 if has_unallowed_error else 0


if __name__ == "__main__":
    sys.exit(main())
