#!/usr/bin/env python3
"""
render_devanagari.py — phonemic form -> Devanagari.

The *second* arrow of the pipeline, and the easy one:

    Urdu script --[HARD, ambiguous, human review]--> phonemes --+--> Roman
                                                                +--> Devanagari

This module is deterministic and total. It never guesses, never consults a
model, and never sees Urdu script. Give it a phonemic form and it returns the
one Devanagari string that form denotes. Every ambiguity was already resolved by
a human upstream, which is the whole point of ADR 0001 §2 / ADR 0003 §1.

If you are tempted to add a heuristic here, you are solving the wrong arrow.

Phonemic notation
-----------------
A space-separated sequence of phoneme tokens. Consonants and vowels alternate
freely; the renderer decides matra vs independent vowel vs bare consonant.

  consonants  k kh g gh c ch j jh T Th D Dh N R Rh t th d dh n
              p ph b bh m y r l v sh s S h
  perso-arab  q x G z zh f            (-> nukta forms क़ ख़ ग़ ज़ झ़ फ़)
  vowels      a aa i ii u uu e ai o au
  modifiers   ~   nasalisation (renders ँ, or ं above a matra — see NASAL_ANUSVARA)
              '   ain / hamza: a syllable break, forcing the next vowel to be
                  independent. Renders nothing itself.
              +   suffix on a consonant: emit halant, i.e. a true conjunct.
              _   word break: emit a space. For Urdu tokens that Hindi writes as
                  two words — ہوگئے is one token but is हो गए, not होगए.

The `+` marker is load-bearing and the one thing reviewers must get right.
Devanagari writes a bare consonant for a *coda* (inherent schwa, deleted when
read) but a halant for a genuine cluster or gemination. Both are consonants with
no following vowel, so the notation cannot infer which:

    k a r t aa     -> करता    (r is a coda: bare)
    a l+ l aa h    -> अल्लाह   (l+l is gemination: halant)

Getting this wrong yields a real but different word, silently — the failure mode
this project exists to avoid. → docs/gotchas.md

Usage:
    python scripts/render_devanagari.py "sh u r uu"
    python scripts/render_devanagari.py --selftest
"""
from __future__ import annotations

import sys

# --------------------------------------------------------------------------- #
# Inventory
# --------------------------------------------------------------------------- #

# Consonants -> base Devanagari letter. Every distinction ADR 0003 §2 requires
# is present and MUST stay present: retroflex (T D N R) separate from dental
# (t d n r), aspirates separate from plain, and the Perso-Arabic series carrying
# its nukta. Popular Roman Urdu collapses all three groups; Devanagari does not,
# and a phonemic store pitched at Roman granularity cannot feed this table.
CONSONANTS = {
    # velar
    "k": "क", "kh": "ख", "g": "ग", "gh": "घ", "ng": "ङ",
    # palatal
    "c": "च", "ch": "छ", "j": "ज", "jh": "झ",
    # retroflex — NOT the same letters as the dental row below
    "T": "ट", "Th": "ठ", "D": "ड", "Dh": "ढ", "N": "ण",
    "R": "ड़", "Rh": "ढ़",
    # dental
    "t": "त", "th": "थ", "d": "द", "dh": "ध", "n": "न",
    # labial
    "p": "प", "ph": "फ", "b": "ब", "bh": "भ", "m": "म",
    # approximant / liquid
    "y": "य", "r": "र", "l": "ल", "v": "व",
    # sibilant / glottal
    "sh": "श", "S": "ष", "s": "स", "h": "ह",
    # Perso-Arabic, nukta-bearing. Dropping the nukta is a *house style* choice
    # (ADR 0003 open question 1) and belongs in a post-pass, never here: this
    # table stays maximally faithful so the choice remains reversible.
    "q": "क़", "x": "ख़", "G": "ग़", "z": "ज़", "zh": "झ़", "f": "फ़",
}

# Vowels -> (independent form, matra). "a" has no matra: it is the inherent
# vowel a bare consonant already carries.
VOWELS = {
    "a":  ("अ", ""),
    "aa": ("आ", "ा"),
    "i":  ("इ", "ि"),
    "ii": ("ई", "ी"),
    "u":  ("उ", "ु"),
    "uu": ("ऊ", "ू"),
    "e":  ("ए", "े"),
    "ai": ("ऐ", "ै"),
    "o":  ("ओ", "ो"),
    "au": ("औ", "ौ"),
}

HALANT = "्"   # ्
CHANDRABINDU = "ँ"  # ँ
ANUSVARA = "ं"      # ं

# Vowel signs that occupy the space above the letter, where a chandrabindu has
# nowhere to sit. Convention (and every Hindi typesetter) switches to anusvara
# there: हूँ keeps the chandrabindu, but मैं takes anusvara. Purely orthographic —
# the phoneme is the same nasalisation either way.
NASAL_ANUSVARA = {"ि", "ी", "े", "ै", "ो", "ौ"}


class PhonemeError(ValueError):
    """Raised on a token the inventory does not define. Never guess a repair."""


def render(phonemic: str) -> str:
    """Render one space-separated phonemic form to Devanagari.

    Deterministic and total over the inventory: any token outside it raises
    rather than being silently dropped or approximated.
    """
    out: list[str] = []
    # True when the previous token was a consonant still awaiting its vowel, so
    # a vowel now attaches as a matra rather than standing independently.
    pending_consonant = False

    for tok in phonemic.split():
        if tok == "'":
            # ain / hamza: pure syllable break. Emits nothing, but detaches the
            # next vowel so ta' aa l aa -> ताअला rather than ताला.
            pending_consonant = False
            continue

        if tok == "_":
            # Word break inside a single Urdu token. Urdu and Hindi do not agree
            # on where words end: Urdu glues verb particles (ہوگئے) that Hindi
            # separates (हो गए). Without this the output reads as one invented
            # word. The mirror case — Urdu splitting what Hindi joins, ہم نے ->
            # हमने — is handled by multi-token lexicon keys in render_verse.py.
            if not out:
                raise PhonemeError("word break '_' at the start of a form")
            out.append(" ")
            pending_consonant = False
            continue

        if tok == "~":
            if not out:
                raise PhonemeError("nasalisation '~' with nothing to nasalise")
            out.append(ANUSVARA if out[-1] in NASAL_ANUSVARA else CHANDRABINDU)
            continue

        if tok == "-":
            # Literal hyphen, for Persian compounds that Hindi/Urdu typography
            # writes hyphenated rather than spaced or joined: بے نام ونشان is
            # बे-नाम-ओ-निशाँ, not बे नाम ओ निशान. Distinct from `_`, which is a
            # plain word break.
            if not out:
                raise PhonemeError("hyphen '-' at the start of a form")
            out.append("-")
            pending_consonant = False
            continue

        if tok == "M":
            # Explicit anusvara. `~` picks chandrabindu unless a matra occupies
            # the space above, which is right for हूँ and अँधेरा but wrong for
            # words Hindi conventionally spells with anusvara regardless —
            # इंसान, not इँसान. The two are not interchangeable in print, and
            # nothing in the phonemes distinguishes them, so the reviewer must.
            if not out:
                raise PhonemeError("anusvara 'M' with nothing to nasalise")
            out.append(ANUSVARA)
            continue

        conjunct = tok.endswith("+")
        base = tok[:-1] if conjunct else tok

        if base in CONSONANTS:
            # A consonant directly after another consonant means the previous
            # one had no vowel. It keeps its inherent 'a' (bare) unless it was
            # explicitly marked '+', which already emitted the halant below.
            out.append(CONSONANTS[base])
            if conjunct:
                out.append(HALANT)
                pending_consonant = False
            else:
                pending_consonant = True
            continue

        if base in VOWELS:
            if conjunct:
                raise PhonemeError(f"'+' is only valid on a consonant, got {tok!r}")
            independent, matra = VOWELS[base]
            out.append(matra if pending_consonant else independent)
            pending_consonant = False
            continue

        raise PhonemeError(f"unknown phoneme {tok!r} in {phonemic!r}")

    return "".join(out)


def render_words(phonemic_words: list[str]) -> str:
    """Render a list of per-word phonemic forms into a space-joined string."""
    return " ".join(render(w) for w in phonemic_words)


# --------------------------------------------------------------------------- #
# Self-test — the gold contract
# --------------------------------------------------------------------------- #

# Junagarhi 1:1. The Devanagari column is the owner's own target output
# (2026-07-27), quoted verbatim in ADR 0003. It is the specification, not a
# sample: if the renderer stops reproducing it exactly, the renderer is wrong.
#
#   Urdu   شروع کرتا ہوں اللہ تعالیٰ کے نام سے جو بڑا مہربان نہایت رحم والا ہے۔
#   Target शुरू करता हूँ अल्लाह ताअला के नाम से जो बड़ा मेहरबान निहायत रहम वाला है।
#
# The phonemic column here is HAND-ANNOTATED for this one verse to exercise the
# renderer. It is not lexicon data and nothing downstream may read it.
GOLD_1_1 = [
    ("sh u r uu",           "शुरू"),
    ("k a r t aa",          "करता"),      # coda r stays bare -> करता, not कर्ता
    ("h uu ~",              "हूँ"),        # chandrabindu: ू leaves the top free
    ("a l+ l aa h",         "अल्लाह"),     # gemination needs the explicit '+'
    ("t aa ' a l aa",       "ताअला"),     # ain detaches the vowel -> अ
    ("k e",                 "के"),
    ("n aa m",              "नाम"),
    ("s e",                 "से"),
    ("j o",                 "जो"),
    ("b a R aa",            "बड़ा"),       # retroflex R; Roman "bada" loses this
    ("m e h a r b aa n",    "मेहरबान"),
    ("n i h aa y a t",      "निहायत"),
    ("r a h a m",           "रहम"),
    ("v aa l aa",           "वाला"),
    ("h ai",                "है"),
]

# Distinctions Devanagari keeps that popular Roman Urdu collapses. These are the
# evidence for ADR 0003 §2 and exist to fail loudly if the inventory is ever
# "simplified" to Roman granularity.
GOLD_CONTRASTS = [
    ("T aa l",   "टाल"),   ("t aa l",  "ताल"),    # retroflex vs dental
    ("D aa l",   "डाल"),   ("d aa l",  "दाल"),
    ("b a R aa", "बड़ा"),   ("b a d aa", "बदा"),   # the بڑا case from ADR 0003
    ("k aa m",   "काम"),   ("q aa m",  "क़ाम"),    # nukta series
    ("z aa t",   "ज़ात"),   ("j aa t",  "जात"),
    ("b h aa ii", "बहाई"), ("bh aa ii", "भाई"),   # h-cluster vs true aspirate
    ("m ai ~",   "मैं"),                          # anusvara: ै occupies the top
]


def selftest() -> int:
    failures = 0

    for phon, expect in GOLD_1_1:
        got = render(phon)
        ok = got == expect
        failures += not ok
        print(f"  {'ok ' if ok else 'FAIL'}  {phon:<20} -> {got}" + ("" if ok else f"   expected {expect}"))

    whole = render_words([p for p, _ in GOLD_1_1]) + "।"
    target = " ".join(e for _, e in GOLD_1_1) + "।"
    ok = whole == target
    failures += not ok
    print("\n  verse 1:1")
    print(f"    got    {whole}")
    print(f"    target {target}")
    print(f"    {'MATCH' if ok else 'MISMATCH'}")

    print("\n  contrasts Roman collapses:")
    for phon, expect in GOLD_CONTRASTS:
        got = render(phon)
        ok = got == expect
        failures += not ok
        print(f"    {'ok ' if ok else 'FAIL'}  {phon:<12} -> {got}" + ("" if ok else f"   expected {expect}"))

    # Tokens outside the inventory must raise, never be repaired or dropped:
    # an unknown phoneme is a lexicon bug, and silently rendering around it
    # would put an invented word into scripture.
    for bad in ["k a Q", "aa+", "~", "th3"]:
        try:
            render(bad)
        except PhonemeError:
            pass
        else:
            failures += 1
            print(f"    FAIL  {bad!r} should have raised PhonemeError")

    print(f"\n{'PASS' if not failures else str(failures) + ' FAILURE(S)'}")
    return 1 if failures else 0


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--selftest":
        sys.exit(selftest())
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    print(render(" ".join(sys.argv[1:])))
