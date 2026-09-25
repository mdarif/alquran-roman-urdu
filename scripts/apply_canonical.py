#!/usr/bin/env python3
"""
apply_canonical.py -- mechanical, whole-word, case-preserving replacement of
canonical.tsv `decided` variants (ADR 0005 R2/R3/R5), plus a standalone-span
honorific normaliser (ADR 0005 R4), across data/roman-urdu/surah-*.json.

Phase 3 of docs/ROMAN-URDU-GOLDEN-PLAN.md. This is the ONLY thing that is
allowed to write to data/roman-urdu/*.json in Phase 3 -- never hand-edit.

Usage:
    python3 scripts/apply_canonical.py --rule nahin --dry-run
    python3 scripts/apply_canonical.py --rule nahin "ta'ala" kuchh
    python3 scripts/apply_canonical.py --honorifics --dry-run
    python3 scripts/apply_canonical.py --honorifics

Only `canonical.tsv` rows with status `decided` may be applied through
--rule. A `needs-review` or `keep` row raises and applies nothing.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROMAN_DIR = ROOT / "data" / "roman-urdu"
CANONICAL_PATH = ROMAN_DIR / "canonical.tsv"


class NotDecidedError(ValueError):
    """Raised when --rule names a canonical.tsv row that is not `decided`."""


# ---------------------------------------------------------------------------
# canonical.tsv
# ---------------------------------------------------------------------------

def load_canonical(path: Path = CANONICAL_PATH) -> dict[str, tuple[str, str]]:
    mapping: dict[str, tuple[str, str]] = {}
    with path.open(encoding="utf-8") as fh:
        reader = csv.DictReader(fh, delimiter="\t")
        for row in reader:
            mapping[row["variant"]] = (row["canonical"], row["status"])
    return mapping


# ---------------------------------------------------------------------------
# Tokenisation and case-preserving replacement
# ---------------------------------------------------------------------------

# A token is a maximal run of letters/apostrophes, optionally chained onto
# adjacent letter runs by a hyphen. This is deliberate: a variant with no
# hyphen in it (e.g. "ne'mat") can never match *inside* a hyphenated
# compound ("ne'mat-o-fazl") -- the compound is captured whole as one token
# and compared whole against the variant, so it simply doesn't match unless
# the variant itself is exactly that hyphenated compound.
_TOKEN_RE = re.compile(r"[A-Za-z']+(?:-[A-Za-z']+)*")

# ADR 0005 R2/R5: "taala" is always rendered with a capital T regardless of
# source casing -- a divine-title convention, not an ordinary word.
_ALWAYS_CAPITALISE = {"taala"}


def _recase_simple(source: str, canonical: str) -> str:
    if source.isupper():
        return canonical.upper()
    if source.islower():
        return canonical.lower()
    if source[:1].isupper() and source[1:].islower():
        return canonical[:1].upper() + canonical[1:].lower()
    return canonical


def match_case(source: str, canonical: str) -> str:
    """Re-case `canonical` (the canonical.tsv target spelling) to follow the
    casing pattern of `source` (the matched token from the actual text)."""
    if canonical.lower() in _ALWAYS_CAPITALISE:
        return "-".join(seg[:1].upper() + seg[1:].lower() for seg in canonical.split("-"))

    src_segs = source.split("-")
    can_segs = canonical.split("-")
    if len(src_segs) > 1 and len(src_segs) == len(can_segs):
        # Hyphenated compound: re-case each segment independently so e.g.
        # "Mash'ar-e-Haraam" (Title-E-Title) maps onto "mashar-e-haraam"
        # segment by segment.
        return "-".join(_recase_simple(s, c) for s, c in zip(src_segs, can_segs))

    return _recase_simple(source, canonical)


def apply_rule(text: str, variant: str, canonical: str) -> tuple[str, int]:
    """Whole-word, case-preserving replacement of one canonical.tsv rule.
    Returns (new_text, count_replaced)."""
    count = 0
    variant_lower = variant.lower()

    def repl(m: re.Match) -> str:
        nonlocal count
        token = m.group(0)
        if token.lower() != variant_lower:
            return token
        count += 1
        return match_case(token, canonical)

    new_text = _TOKEN_RE.sub(repl, text)
    return new_text, count


# ---------------------------------------------------------------------------
# Honorifics (ADR 0005 R4) -- standalone bracket spans only
# ---------------------------------------------------------------------------

_PAREN_SPAN_RE = re.compile(r"\(([^()]*)\)")


def _normalize_for_match(span: str) -> str:
    return re.sub(r"[-\s]+", " ", span.strip().lower()).strip()


_HONORIFIC_CANONICAL_BY_NORMALIZED: dict[str, str] = {
    "alaihis salaam": "Alaihis-Salaam",
    "alaihimus salaam": "Alaihimus-Salaam",
    "alaihimas salaam": "Alaihimas-Salaam",  # dual, owner Q1 2026-09-25
    "alaihim salaam": "Alaihimus-Salaam",
    "alaiha salaam": "Alaihas-Salaam",
    "sallallahu alaihi wasallam": "Sallallahu Alaihi Wasallam",
    "sallallahu alaihi wa sallam": "Sallallahu Alaihi Wasallam",
}


def normalize_honorific_span(span: str) -> str | None:
    """If `span` (the text inside one pair of parens, no parens included) is
    -- once whitespace/hyphens are collapsed -- EXACTLY one of the known
    honorific phrases and nothing else, return the ADR 0005 R4 canonical
    bracketed form. Otherwise (not an honorific at all, or an honorific
    embedded in a longer translator's gloss such as "Yaqoob alaihis salaam
    ne") return None -- scope (B) never touches those."""
    key = _normalize_for_match(span)
    canonical = _HONORIFIC_CANONICAL_BY_NORMALIZED.get(key)
    if canonical is None:
        return None
    return f"({canonical})"


# Honorific phrases as they may appear inside a longer translator's gloss,
# e.g. "(Yaqoob alaihis salaam ne)". Owner ruling Q2 (2026-09-25): there
# they are capitalised and hyphenated but get no brackets of their own.
_EMBEDDED_HONORIFIC_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"\bsallallahu[\s-]+alaihi[\s-]+wa[\s-]*sallam\b", re.I), "Sallallahu Alaihi Wasallam"),
    (re.compile(r"\balaihimas[\s-]+salaam\b", re.I), "Alaihimas-Salaam"),
    (re.compile(r"\balaihimu?s?[\s-]+salaam\b", re.I), "Alaihimus-Salaam"),
    (re.compile(r"\balaihis[\s-]+salaam\b", re.I), "Alaihis-Salaam"),
    (re.compile(r"\balaiha?s?[\s-]+salaam\b", re.I), "Alaihas-Salaam"),
]


def normalize_embedded_honorifics(inner: str) -> str:
    for pattern, canonical in _EMBEDDED_HONORIFIC_PATTERNS:
        inner = pattern.sub(canonical, inner)
    return inner


def apply_honorifics(text: str) -> tuple[str, int]:
    count = 0

    def repl(m: re.Match) -> str:
        nonlocal count
        replacement = normalize_honorific_span(m.group(1))
        if replacement is None:
            inner = normalize_embedded_honorifics(m.group(1))
            if inner == m.group(1):
                return m.group(0)
            count += 1
            return f"({inner})"
        if replacement == m.group(0):
            return m.group(0)
        count += 1
        return replacement

    new_text = _PAREN_SPAN_RE.sub(repl, text)
    return new_text, count


# Owner ruling Q17 (2026-09-25): future verbs are written joined. A split
# suffix is " ga"/" ge"/" gi" standing alone right after a word.
SPLIT_FUTURE_RE = re.compile(r"(?<=[A-Za-z]) (g[aei])(?![A-Za-z'\-])")


def join_split_futures(text: str) -> tuple[str, int]:
    return SPLIT_FUTURE_RE.subn(r"\1", text)


# ---------------------------------------------------------------------------
# JSON I/O -- byte-identical formatting when nothing changes
# ---------------------------------------------------------------------------

def dump_json_like(data: dict) -> str:
    return json.dumps(data, indent=2) + "\n"


def load_json_file(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json_file(path: Path, data: dict) -> None:
    path.write_text(dump_json_like(data), encoding="utf-8")


# ---------------------------------------------------------------------------
# Apply over the corpus
# ---------------------------------------------------------------------------

def require_decided(variant: str, canonical_map: dict[str, tuple[str, str]]) -> str:
    entry = canonical_map.get(variant)
    if entry is None:
        raise NotDecidedError(f"{variant!r} is not a row in canonical.tsv")
    canonical, status = entry
    if status != "decided":
        raise NotDecidedError(
            f"{variant!r} has status {status!r}, not 'decided' -- refusing to apply. "
            "needs-review and keep rows are never applied by this script."
        )
    return canonical


def apply_rules_to_ayahs(
    ayahs: dict[str, str], rules: list[tuple[str, str]]
) -> tuple[dict[str, str], int]:
    total = 0
    out: dict[str, str] = {}
    for ayah, text in ayahs.items():
        new_text = text
        for variant, canonical in rules:
            new_text, n = apply_rule(new_text, variant, canonical)
            total += n
        out[ayah] = new_text
    return out, total


def apply_honorifics_to_ayahs(ayahs: dict[str, str]) -> tuple[dict[str, str], int]:
    total = 0
    out: dict[str, str] = {}
    for ayah, text in ayahs.items():
        new_text, n = apply_honorifics(text)
        total += n
        out[ayah] = new_text
    return out, total


def process_corpus(
    *, rules: list[tuple[str, str]] | None = None, honorifics: bool = False,
    join_futures: bool = False, roman_dir: Path = ROMAN_DIR, dry_run: bool = False,
) -> int:
    """Apply `rules` and/or the honorifics normaliser across every
    surah-*.json in `roman_dir`. Returns the total number of replacements.
    In --dry-run mode, counts but never writes."""
    total = 0
    for path in sorted(roman_dir.glob("surah-*.json")):
        data = load_json_file(path)
        ayahs = data["ayahs"]
        changed = False

        if rules:
            ayahs, n = apply_rules_to_ayahs(ayahs, rules)
            if n:
                total += n
                changed = True

        if honorifics:
            ayahs, n = apply_honorifics_to_ayahs(ayahs)
            if n:
                total += n
                changed = True

        if join_futures:
            joined = {}
            for key, text in ayahs.items():
                joined[key], n = join_split_futures(text)
                if n:
                    total += n
                    changed = True
            ayahs = joined

        if changed and not dry_run:
            data["ayahs"] = ayahs
            write_json_file(path, data)

    return total


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--rule", nargs="+", metavar="VARIANT", help="one or more canonical.tsv variants to apply (must be status=decided)")
    parser.add_argument("--honorifics", action="store_true", help="normalise standalone-span honorifics (ADR 0005 R4)")
    parser.add_argument("--join-futures", action="store_true", help="join split future verbs, 'jaao ge' -> 'jaaoge' (owner ruling Q17)")
    parser.add_argument("--dry-run", action="store_true", help="count only, do not write")
    parser.add_argument("--canonical", type=Path, default=CANONICAL_PATH)
    parser.add_argument("--roman-dir", type=Path, default=ROMAN_DIR)
    args = parser.parse_args(argv)

    if not args.rule and not args.honorifics and not args.join_futures:
        parser.error("nothing to do: pass --rule <variant> [...], --honorifics and/or --join-futures")

    rules: list[tuple[str, str]] = []
    if args.rule:
        canonical_map = load_canonical(args.canonical)
        for variant in args.rule:
            canonical = require_decided(variant, canonical_map)
            rules.append((variant, canonical))

    total = process_corpus(
        rules=rules or None, honorifics=args.honorifics, join_futures=args.join_futures,
        roman_dir=args.roman_dir, dry_run=args.dry_run,
    )

    mode = "would replace" if args.dry_run else "replaced"
    parts = [v for v, _ in rules] + (["honorifics"] if args.honorifics else []) + (["join-futures"] if args.join_futures else [])
    label = ", ".join(parts)
    print(f"{mode} {total} occurrence(s) [{label}]")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
