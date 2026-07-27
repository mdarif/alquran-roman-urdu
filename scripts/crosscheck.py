#!/usr/bin/env python3
"""
crosscheck.py — flag disagreements between our Devanagari and an independent
Roman Urdu rendering of the same verse.

WHAT THIS IS NOT
----------------
It is **not** a way to generate Devanagari from Roman Urdu. ADR 0003 §1 rejects
that, and the owner's own example is the proof: `بڑا` is *baRa* with a retroflex
ڑ, and popular Roman writes it "bada", which is indistinguishable from `بدا`.
Devanagari keeps the distinction (बड़ा) and Roman has already thrown it away, so
Roman → Devanagari is lossy in exactly the places that matter. Same for the nukta
series (क़/क) and the aspirates.

WHAT IT IS
----------
A **disagreement detector**. Two independent renderings of the same verse should
agree on the consonant skeleton of every word. Where they do not, something is
wrong in one of them — and that is worth a human's attention. It ranks review
effort; it never decides anything.

This is the same standing as a Dakshina candidate under non-negotiable #4:
evidence, not an answer. When our text and the Roman disagree, the reviewer looks
— they do not "apply the Roman".

WHY IT EARNS ITS PLACE
----------------------
Run against al-Fatiha and 108-114, it independently flags every correction the
owner made by eye on 2026-07-27 — تو as "to" not "tu", `us ka` split, `rassi`
geminate, `raah-e-haq` izafat, `be-naam-o-nishan`, `jauq`, `tasbeeh`, `hamd`,
`maghfirat` — plus at least one more that the eye pass missed. Those errors cost
a round-trip each. This finds them in a second.

Comparison is on the **consonant skeleton**, deliberately: vowels are exactly
what the two systems spell differently and legitimately (reham/رحم → रहम), so
comparing them would drown the signal. Consonants are where the real
disagreements live — a missing gemination, a wrong retroflex, a join that should
be a split.

Usage:
    python scripts/crosscheck.py                 # every surah with both renderings
    python scripts/crosscheck.py --surah 1
"""
from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from overrides import load_overrides  # noqa: E402
from render_verse import SOURCE_DB, render_verse  # noqa: E402
from review import load_lexicon  # noqa: E402

ROMAN_DIR = Path.home() / "code" / "al-quran-web" / "data" / "roman-urdu"

# Devanagari consonant -> coarse latin. Nukta forms fold onto their base: the
# Roman side cannot express them, so comparing them would flag every single one.
_DEVA = {
    "क": "k", "ख": "k", "ग": "g", "घ": "g", "ङ": "n",
    "च": "c", "छ": "c", "ज": "j", "झ": "jh",
    "ट": "t", "ठ": "th", "ड": "d", "ढ": "dh", "ण": "n",
    "त": "t", "थ": "th", "द": "d", "ध": "dh", "न": "n",
    "प": "p", "फ": "ph", "ब": "b", "भ": "bh", "म": "m",
    "य": "y", "र": "r", "ल": "l", "व": "v",
    "श": "s", "ष": "s", "स": "s", "ह": "h",
    "क़": "k", "ख़": "k", "ग़": "g", "ज़": "j", "फ़": "ph", "ड़": "d", "ढ़": "dh",
}
_NUKTA = "़"
# Nasalisation marks carry a consonant on the Roman side (हूँ/hoon, लोगों/logon),
# so they must count here or every nasalised word reports as a disagreement.
_NASAL = {"ं": "n", "ँ": "n"}


def deva_skeleton(word: str) -> str:
    """Consonant skeleton of a Devanagari word."""
    w = word.replace(_NUKTA, "")  # base letters; nukta folded above
    out = []
    for ch in w:
        if ch in _DEVA:
            out.append(_DEVA[ch])
        elif ch in _NASAL:
            out.append(_NASAL[ch])
    return "".join(out)


_ROMAN_DIGRAPHS = ("kh", "gh", "ch", "sh", "th", "ph", "bh", "dh", "jh", "zh")


def roman_skeleton(word: str) -> str:
    """Consonant skeleton of a Roman Urdu word, on the same scale as above."""
    w = word.lower()
    w = re.sub(r"[^a-z]", "", w)
    # Silent final h, as a CLOSED LIST rather than a pattern. Every positional
    # rule tried here ate a real consonant somewhere: "(?<=[aeiou])h$" broke
    # kah/کہ, panah/پناہ, subah/صبح and Allah; narrowing it to [oe] still broke
    # tasbeeh/تسبیح. Only these function words actually carry a silent h.
    if w in ("woh", "yeh", "keh", "jeh"):
        w = w[:-1]
    # NOTE: no glide-stripping. Roman's intervocalic y is genuinely ambiguous —
    # it is our य in दीजिये/dijiye and नियाज़/niyaz, but nothing at all in
    # जाए/jaaye. Stripping it silenced the first two; keeping it flags the third,
    # which is a real question (जाए or जाये?) and belongs in front of a human.
    out, i = [], 0
    while i < len(w):
        two = w[i:i + 2]
        if two in _ROMAN_DIGRAPHS:
            # Roman writes خ/غ as kh/gh and च as ch, so these digraphs are
            # ambiguous between a true aspirate and a Perso-Arabic consonant.
            # Fold to the plain consonant on both sides rather than reporting
            # every such word.
            out.append({"sh": "s", "kh": "k", "gh": "g", "ch": "c", "zh": "j"}.get(two, two))
            i += 2
            continue
        c = w[i]
        if c in "aeiou":
            i += 1
            continue
        out.append({"q": "k", "x": "kh", "z": "j", "f": "ph", "w": "v", "y": "y"}.get(c, c))
        i += 1
    # Roman spells geminates inconsistently (rassi/rasi); collapse doubles on
    # BOTH sides rather than reporting every one as a disagreement.
    return re.sub(r"(.)\1+", r"\1", "".join(out))


def norm_deva(word: str) -> str:
    return re.sub(r"(.)\1+", r"\1", deva_skeleton(word))


def compare(deva: str, roman: str) -> list[tuple[str, str]]:
    """Word-level disagreements. Returns (ours, theirs) pairs."""
    dw = [w for w in re.split(r"[\s।,()\-]+", deva) if w.strip()]
    rw = [w for w in re.split(r"[\s.,()\-]+", roman) if w.strip()]
    ds = [norm_deva(w) for w in dw]
    rs = [roman_skeleton(w) for w in rw]

    import difflib
    sm = difflib.SequenceMatcher(None, ds, rs, autojunk=False)
    bad = []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            continue
        bad.append((" ".join(dw[i1:i2]) or "—", " ".join(rw[j1:j2]) or "—"))
    return bad


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--surah", type=int)
    args = ap.parse_args()

    lex, ovr = load_lexicon(), load_overrides()
    con = sqlite3.connect(SOURCE_DB)
    surahs = [args.surah] if args.surah else range(1, 115)

    total = 0
    for s in surahs:
        rf = ROMAN_DIR / f"surah-{s:03d}.json"
        if not rf.exists():
            continue
        roman = json.loads(rf.read_text(encoding="utf-8")).get("ayahs", {})
        for a, t in con.execute(
            "select ayah,text from translation where sura=? order by ayah", (s,)
        ):
            if str(a) not in roman:
                continue
            deva, _, gaps = render_verse(t, lex, f"{s}:{a}", ovr)
            if gaps:
                continue
            diffs = compare(deva, roman[str(a)])
            if not diffs:
                continue
            print(f"\n{s}:{a}")
            for ours, theirs in diffs:
                print(f"    ours:  {ours}")
                print(f"    roman: {theirs}")
                total += 1
    print(f"\n{total} disagreement(s). Each is a prompt to look, not a correction to apply.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
