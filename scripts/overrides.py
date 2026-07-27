#!/usr/bin/env python3
"""
overrides.py — per-occurrence phonemic overrides.

The lexicon is **type-level**: one phonemic form per surface form. That is right
for the overwhelming majority of Urdu, and it is what makes exhaustive review
tractable (6,837 types, not 187,325 tokens).

It cannot express a **homograph** — one spelling that is two different words:

    میں   3,751 tokens   مَیں  मैं  "I"      vs  مِیں  में  "in"
    ان    3,240 tokens   इन "these"          vs  उन "those"
    اس    3,180 tokens   इस "this"           vs  उस "that"
    کہ    3,144 tokens   कि "that" (conj.)   vs  कह "say"

Together ~7% of the corpus. Urdu drops the short vowels that would distinguish
them, so the spelling is genuinely identical and only the sentence decides. A
type-level entry must pick one and be wrong everywhere else — silently, in
scripture. Surah 109 (`نہ میں عبادت` → मैं) and 114 (`سینوں میں` → में) conflict
directly, so this is not hypothetical.

So: the lexicon supplies the DEFAULT, and this file overrides it at a specific
verse and token position. Same review rules — a reviewer decides, a model never
does. → AGENTS.md §4.1.

Format, `data/lexicon/overrides.tsv`:

    ref      surah:ayah, e.g. 114:5
    index    0-based index of the token WITHIN THE VERSE, after footnote splitting
    span     how many tokens this override consumes (default 1). An override may
             cover an n-gram, so `اس کا` -> उसका stays joined per ADR 0002 §4
    key      the normalised surface form(s), so a drifted index fails loudly
    phonemic the form to use here instead of the lexicon's
    status   pending | reviewed | approved
    reviewer who decided
    notes    why this occurrence differs

`key` is redundant with (ref, index) on purpose. If the tokenizer ever changes,
an index silently points at a different word; storing the expected form turns
that into a visible mismatch instead of a quiet corruption.
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

ROOT = Path(__file__).resolve().parent.parent
OVERRIDES = ROOT / "data" / "lexicon" / "overrides.tsv"
FIELDS = ["ref", "index", "span", "key", "phonemic", "status", "reviewer", "notes"]


def load_overrides() -> dict[tuple[str, int], dict]:
    if not OVERRIDES.exists():
        return {}
    out: dict[tuple[str, int], dict] = {}
    with OVERRIDES.open(encoding="utf-8") as fh:
        header = fh.readline().rstrip("\n").split("\t")
        for line in fh:
            if not line.strip():
                continue
            d = dict(zip(header, line.rstrip("\n").split("\t")))
            out[(d["ref"], int(d["index"]))] = d
    return out


def save_overrides(rows: dict[tuple[str, int], dict]) -> None:
    OVERRIDES.parent.mkdir(parents=True, exist_ok=True)

    def sort_key(r: dict) -> tuple[int, int, int]:
        s, a = r["ref"].split(":")
        return (int(s), int(a), int(r["index"]))

    ordered = sorted(rows.values(), key=sort_key)
    fd, tmp = tempfile.mkstemp(dir=OVERRIDES.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write("\t".join(FIELDS) + "\n")
            for r in ordered:
                fh.write("\t".join(str(r.get(f) or "").replace("\t", " ") for f in FIELDS) + "\n")
        os.replace(tmp, OVERRIDES)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


class OverrideMismatch(RuntimeError):
    """An override's recorded key no longer matches the token at that index."""
