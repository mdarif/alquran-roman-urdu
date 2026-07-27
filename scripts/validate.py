#!/usr/bin/env python3
"""
validate.py — shrink the review queue to the words that actually need a human.

The point of this tool is to answer "which of my renderings might be wrong?"
without a person reading every verse. It does NOT approve anything. It sorts our
output into two piles:

  CORROBORATED  the exact word appears in an independently published Devanagari
                text of the same Quran translation, in the same register
  UNSEEN        it does not — so nobody but us has written it, and it wants a
                human

That second pile is the review queue. On al-Fatiha and 108-114 it is **18 words
out of 471** — 95% of the manual reading disappears, and the 5% that remains is
where the errors actually live.

WHY THIS IS EVIDENCE AND NOT PROOF
----------------------------------
Corroboration is a strong signal, not a guarantee, and it must not be treated as
one. Three specific ways it can pass something wrong:

  * **Right word, wrong place.** इस and उस are both perfectly attested; the
    homograph is still wrong if this occurrence needed the other one. Attestation
    is per *word*, never per *occurrence*.
  * **Izafat.** राह and हक़ are both attested. राह-ए-हक़ is still what the verse
    needs. → ADR 0002 ruling 5.
  * **Different word, same spelling.** Attestation cannot tell them apart.

So this narrows *where to look*. It never decides, and nothing here may set
`status=approved` on its own. → AGENTS.md §4.1, §4.2.

REFERENCE CORPUS
----------------
`hi-suhel-farooq-nadwi-simple.db` — the Suhel Farooq Khan & Saifur Rahman Nadwi
Hindi translation this project already ships. 9,331 distinct words of published
Devanagari in the Perso-Arabic register, produced by human translators with no
knowledge of us. It is a genuinely independent witness, which is exactly what
makes it useful. It is a *different translation*, so it will not contain every
word Junagarhi uses — an UNSEEN word is "unattested", not "wrong".

Usage:
    python scripts/validate.py                # all renderable surahs
    python scripts/validate.py --surah 1
    python scripts/validate.py --queue        # just the unseen words, one per line
"""
from __future__ import annotations

import argparse
import collections
import difflib
import re
import sqlite3
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from overrides import load_overrides  # noqa: E402
from render_verse import SOURCE_DB, render_verse  # noqa: E402
from review import load_lexicon  # noqa: E402

HINDI_DB = Path.home() / "code" / "alquran-data" / "sources" / "hi-suhel-farooq-nadwi-simple.db"

# Devanagari word characters, EXCLUDING the danda U+0964/U+0965 — which sit
# inside the Devanagari block, so a naive [ऀ-ॿ] silently glues sentence-final
# punctuation onto the word and makes every clause-final word look unattested.
WORD = re.compile(r"[ऀ-ॣ०-ॿ]+")

# U+0958..U+095F are precomposed nukta letters (क़ as one codepoint). Unicode
# lists them as composition exclusions, so NFC does NOT produce them and NFD
# does not consume them — two byte sequences that render identically will simply
# never compare equal. The published Hindi uses the precomposed form; we emit
# base + U+093C. Canonicalise both to the decomposed form before comparing.
_PRECOMPOSED = {chr(c): unicodedata.normalize("NFD", chr(c)) for c in range(0x958, 0x960)}


def canon(word: str) -> str:
    for pre, dec in _PRECOMPOSED.items():
        word = word.replace(pre, dec)
    return word


def reference_vocab() -> set[str]:
    if not HINDI_DB.exists():
        sys.exit(f"reference corpus not found: {HINDI_DB}")
    con = sqlite3.connect(HINDI_DB)
    return {
        canon(w)
        for (t,) in con.execute("select text from translation")
        for w in WORD.findall(t)
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--surah", type=int)
    ap.add_argument("--queue", action="store_true", help="print only the unseen words")
    args = ap.parse_args()

    vocab = reference_vocab()
    lex, ovr = load_lexicon(), load_overrides()
    con = sqlite3.connect(SOURCE_DB)
    surahs = [args.surah] if args.surah else range(1, 115)

    seen = 0
    unseen: collections.Counter[str] = collections.Counter()
    where: dict[str, list[str]] = collections.defaultdict(list)

    for s in surahs:
        for a, t in con.execute(
            "select ayah,text from translation where sura=? order by ayah", (s,)
        ):
            deva, _, gaps = render_verse(t, lex, f"{s}:{a}", ovr)
            if gaps:
                continue
            for w in WORD.findall(deva):
                if canon(w) in vocab:
                    seen += 1
                else:
                    unseen[w] += 1
                    if len(where[w]) < 3:
                        where[w].append(f"{s}:{a}")

    total = seen + sum(unseen.values())
    if not total:
        print("nothing renderable yet")
        return 0

    if args.queue:
        for w, _ in unseen.most_common():
            print(w)
        return 0

    print(f"corroborated by the published Hindi : {seen:>5} / {total}  ({seen/total*100:.1f}%)")
    print(f"unseen — needs a human              : {sum(unseen.values()):>5} / {total}"
          f"  ({len(unseen)} distinct)\n")
    # Nearest published spelling, when there is one. This is the actionable
    # part: "unseen" only says nobody else wrote it, whereas "published Hindi
    # writes इनसान" tells the reviewer what the alternative actually is. Still
    # evidence — the published text is a DIFFERENT translation and its house
    # style is not automatically ours.
    for w, n in unseen.most_common():
        near = difflib.get_close_matches(canon(w), vocab, n=2, cutoff=0.78)
        hint = f"   published: {', '.join(near)}" if near else ""
        print(f"   {w:<16} x{n:<3}  {', '.join(where[w]):<22}{hint}")
    print(
        "\nCorroborated is EVIDENCE, not proof: it is per-word, so it cannot catch a\n"
        "homograph in the wrong place (इस/उस) or a missing izafat (राह-ए-हक़).\n"
        "Nothing here approves anything."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
