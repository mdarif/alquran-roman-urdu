#!/usr/bin/env python3
"""
normalise.py — the reference Urdu-key normaliser for alquran-roman-urdu.

This is the CONTRACT. It produces the lookup key a surface form is matched on.
It is lossy by design: a key, not display text. If a second implementation ever
exists (Dart, for alquran-app), divergence fails *silently* — no error, every
lookup just misses. `tests/normalization_vectors.json` is the shared contract;
both implementations must pass every vector. → AGENTS.md §7, docs/gotchas.md §6.

Rules (do not change without an ADR + migration of every existing key):
  Folded:     Arabic yeh / alef-maksura / yeh-with-tail -> Farsi yeh;
              Arabic kaf / swash kaf -> keheh;
              Arabic heh / teh-marbuta / teh-marbuta-goal -> gol he;
              heh+yeh ligature -> gol he with hamza;
              alef+hamza above/below -> bare alef;
              presentation-form ligatures via targeted NFKC (U+FEFB &c.);
              tashkeel (Mn) stripped; joiners / tatweel removed;
              Urdu-Indic digits -> ASCII.
  NOT folded: do-chashmi he `ھ` U+06BE (aspiration — bh/kh/th/ph) and
              alef madda `آ` U+0622. Both are phonemically distinct; folding
              either produces a plausible-looking WRONG word, not an error.
              → gotchas §1, §2.

This module was extracted verbatim from scripts/vocab_coverage.py and is pinned
equivalent to it: identical regex character sets, identical fold map, zero
mismatches over a 16k-input fuzz of the Arabic + presentation-form ranges.
Several character classes below span invisible or combining marks, so each
carries its exact U+ range in a comment — audit those by codepoint, not glyph.
"""

from __future__ import annotations

import json
import re
import sys
import unicodedata
from pathlib import Path

# ---------------------------------------------------------------------------
# Normalisation
# ---------------------------------------------------------------------------

# Arabic presentation forms. The Tanzil Junagarhi text really does contain
# these: `واﻻ` ends in U+FEFB (lam-alef ligature), not lam + alef. NFC leaves
# it alone; NFKC decomposes it. Fold only this block, not the whole string,
# so we don't invite NFKC's other surprises. → gotchas §1
# Range: U+FB50–U+FDFF and U+FE70–U+FEFF (Arabic Presentation Forms A & B).
_PRESENTATION_FORMS = re.compile(r"[ﭐ-﷿ﹰ-﻿]")

# Letter folding. Arabic-script variants that Urdu writes differently, plus
# forms that arrive from mixed sources.
_LETTER_FOLD = {
    "ي": "ی",  # ARABIC YEH        -> FARSI YEH
    "ى": "ی",  # ALEF MAKSURA      -> FARSI YEH
    "ۍ": "ی",  # YEH WITH TAIL     -> FARSI YEH
    "ك": "ک",  # ARABIC KAF        -> KEHEH
    "ڪ": "ک",  # SWASH KAF         -> KEHEH
    "ه": "ہ",  # ARABIC HEH        -> HEH GOAL
    "ۃ": "ہ",  # TEH MARBUTA GOAL  -> HEH GOAL
    "ة": "ہ",  # TEH MARBUTA       -> HEH GOAL
    "ۀ": "ۂ",  # HEH+YEH LIGATURE  -> HEH GOAL WITH HAMZA
    "أ": "ا",  # ALEF WITH HAMZA ABOVE -> ALEF
    "إ": "ا",  # ALEF WITH HAMZA BELOW -> ALEF
    "آ": "آ",  # ALEF MADDA — keep, it is phonemically distinct
}
# NOT folded, deliberately:
#   U+06BE HEH DOACHASHMEE (ھ) — marks aspiration. bh/kh/th/ph all depend on
#   it. Folding it into ہ destroys the word. This is the single most damaging
#   normalisation mistake available here.

# Combining marks: tashkeel and friends. Category Mn.
# Range: U+064B–U+065F, U+0670 (dagger alef), U+06D6–U+06ED.
_TASHKEEL = re.compile(r"[ً-ٰٟۖ-ۭ]")

# Joiners and invisible formatting.
# Range: U+200B–U+200F, U+202A–U+202E, U+2066–U+2069, U+FEFF (BOM), U+0640 (tatweel).
_INVISIBLE = re.compile(r"[​-‏‪-‮⁦-⁩﻿ـ]")

# Urdu-Indic digits U+06F0–U+06F9 -> ASCII 0–9.
_URDU_DIGITS = str.maketrans("۰۱۲۳۴"
                             "۵۶۷۸۹", "0123456789")


def fold_presentation_forms(text: str) -> str:
    """NFKC only the presentation-form blocks, leave everything else alone."""
    return _PRESENTATION_FORMS.sub(
        lambda m: unicodedata.normalize("NFKC", m.group(0)), text
    )


def normalise(text: str, *, strip_tashkeel: bool = True) -> str:
    """Canonical key form. Lossy by design — a lookup key, not display text."""
    text = unicodedata.normalize("NFC", text)
    text = fold_presentation_forms(text)
    text = _INVISIBLE.sub("", text)
    if strip_tashkeel:
        text = _TASHKEEL.sub("", text)
    text = "".join(_LETTER_FOLD.get(ch, ch) for ch in text)
    text = text.translate(_URDU_DIGITS)
    return unicodedata.normalize("NFC", text)


# ---------------------------------------------------------------------------
# The contract. Vectors live in tests/normalization_vectors.json so a Dart
# port reads the same file. Never quietly change a vector to make a test pass
# (AGENTS.md §7); extend the set whenever a fold is added.
# ---------------------------------------------------------------------------

VECTORS_PATH = Path(__file__).resolve().parent.parent / "tests" / "normalization_vectors.json"


def load_vectors(path: Path = VECTORS_PATH) -> list[dict]:
    """Return the vector records from the shared contract file."""
    data = json.loads(path.read_text(encoding="utf-8"))
    return data["vectors"]


def self_test(path: Path = VECTORS_PATH) -> None:
    """Run every contract vector; exit non-zero on any failure."""
    vectors = load_vectors(path)
    failures = [(v["id"], v["input"], v["expected"], got)
                for v in vectors
                if (got := normalise(v["input"])) != v["expected"]]
    if failures:
        for vid, src, want, got in failures:
            print(f"VECTOR FAIL [{vid}]: {src!r} -> {got!r}, expected {want!r}",
                  file=sys.stderr)
        sys.exit("normalisation vectors failed — fix before trusting any coverage number")


if __name__ == "__main__":
    self_test()
    print(f"OK — {len(load_vectors())} normalisation vectors pass")
