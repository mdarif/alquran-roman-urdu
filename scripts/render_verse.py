#!/usr/bin/env python3
"""
render_verse.py — render whole Urdu verses to Devanagari via the lexicon.

Joins the two halves: look each surface form up in `data/lexicon/lexicon.tsv`,
then hand its phonemic form to the renderer. This module supplies no phonemes of
its own — a form that is not in the lexicon is reported as a gap, never guessed.

Status is carried through to the output, because it is the whole point:

    approved   ready to ship
    reviewed   a human decided it but stopped short of approving
    pending    a SUGGESTION — machine-proposed, not yet decided by anyone
    (missing)  no entry at all

Any verse containing a `pending` or missing form is NOT shippable. → AGENTS.md
§4.2. `--strict` exits non-zero in that case so a build can gate on it.

Usage:
    python scripts/render_verse.py --surah 1
    python scripts/render_verse.py --surah 1 --strict
    python scripts/render_verse.py --text "شروع کرتا ہوں"
"""
from __future__ import annotations

import argparse
import re
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from render_devanagari import PhonemeError, render  # noqa: E402
from review import LEXICON, load_lexicon  # noqa: E402

# The Urdu source this project is derived from. Read-only, and deliberately
# reached across to alquran-data rather than duplicated: one copy of scripture.
SOURCE_DB = Path.home() / "code" / "alquran-data" / "sources" / "ur-junagarri-simple.db"

# Punctuation carried straight through, mapped to its Devanagari equivalent
# where one exists. Parentheses matter: Junagarhi's parenthetical glosses appear
# in 1,479 verses and are part of the translation, not our apparatus.
PUNCT_MAP = {"۔": "।", "،": ",", "؟": "?", "(": "(", ")": ")", "﴿": "﴿", "﴾": "﴾"}
_EDGE = re.compile(r"^(?P<pre>[(«﴾]*)(?P<core>.*?)(?P<post>[)»﴿،۔؟,]*)$", re.DOTALL)

BOLD, DIM, YELLOW, RED, GREEN, RESET = (
    ("\033[1m", "\033[2m", "\033[33m", "\033[31m", "\033[32m", "\033[0m")
    if sys.stdout.isatty() else ("",) * 6
)


def render_token(tok: str, lex: dict[str, dict]) -> tuple[str, str]:
    """Render one whitespace-delimited token. Returns (text, status)."""
    m = _EDGE.match(tok)
    pre, core, post = m["pre"], m["core"], m["post"]
    pre_d = "".join(PUNCT_MAP.get(c, c) for c in pre)
    post_d = "".join(PUNCT_MAP.get(c, c) for c in post)

    if not core:
        return pre_d + post_d, "punct"

    entry = lex.get(core)
    if entry is None or not entry.get("phonemic"):
        return f"{pre_d}⟨{core}⟩{post_d}", "missing"

    try:
        deva = render(entry["phonemic"])
    except PhonemeError as exc:
        return f"{pre_d}⟨!{core}⟩{post_d}", f"error: {exc}"

    return pre_d + deva + post_d, entry.get("status", "pending")


# Longest multi-token lexicon key to attempt. Urdu splits some sequences that
# Hindi writes as one word — ہم نے -> हमने, انہوں نے -> उन्होंने — 1,611 tokens
# in this corpus. A key may therefore span several whitespace-delimited tokens,
# and the longest match wins so "انہوں نے" beats a bare "انہوں".
MAX_NGRAM = 3


def _match_ngram(toks: list[str], i: int, lex: dict[str, dict]) -> tuple[str, str, int] | None:
    """Longest multi-token lexicon match starting at `i`, or None.

    Only bare tokens may join: a comma, paren or full stop mid-window is a real
    break, so a sequence containing one is never collapsed into a single word.
    """
    for span in range(min(MAX_NGRAM, len(toks) - i), 1, -1):
        window = toks[i:i + span]
        if any(_EDGE.match(w)["pre"] or _EDGE.match(w)["post"] for w in window[:-1]):
            continue
        if _EDGE.match(window[0])["pre"]:
            continue
        key = " ".join(_EDGE.match(w)["core"] for w in window)
        entry = lex.get(key)
        if not (entry and entry.get("phonemic")):
            continue
        try:
            deva = render(entry["phonemic"])
        except PhonemeError:
            continue  # a broken entry falls back to per-token rendering
        post = "".join(PUNCT_MAP.get(c, c) for c in _EDGE.match(window[-1])["post"])
        return deva + post, entry.get("status", "pending"), span
    return None


def render_verse(text: str, lex: dict[str, dict]) -> tuple[str, dict[str, int], list[str]]:
    out, counts, gaps = [], {}, []
    toks = text.split()
    i = 0
    while i < len(toks):
        hit = _match_ngram(toks, i, lex)
        if hit:
            rendered, status, span = hit
            out.append(rendered)
            counts[status] = counts.get(status, 0) + span
            i += span
            continue
        rendered, status = render_token(toks[i], lex)
        out.append(rendered)
        if status != "punct":
            counts[status] = counts.get(status, 0) + 1
        if status == "missing":
            gaps.append(_EDGE.match(toks[i])["core"])
        i += 1
    return " ".join(out), counts, gaps


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--surah", type=int, help="render a whole surah from the source DB")
    ap.add_argument("--text", help="render one line of Urdu directly")
    ap.add_argument("--strict", action="store_true", help="exit 1 if anything is not approved")
    args = ap.parse_args()

    lex = load_lexicon()
    if not lex:
        print(f"lexicon is empty: {LEXICON}", file=sys.stderr)
        return 1

    verses: list[tuple[str, str]] = []
    if args.text:
        verses = [("—", args.text)]
    elif args.surah:
        if not SOURCE_DB.exists():
            print(f"source not found: {SOURCE_DB}", file=sys.stderr)
            return 1
        con = sqlite3.connect(SOURCE_DB)
        verses = [
            (f"{args.surah}:{a}", t)
            for a, t in con.execute(
                "select ayah,text from translation where sura=? order by ayah", (args.surah,)
            )
        ]
    else:
        ap.error("need --surah or --text")

    totals: dict[str, int] = {}
    all_gaps: list[str] = []
    for ref, urdu in verses:
        deva, counts, gaps = render_verse(urdu, lex)
        for k, v in counts.items():
            totals[k] = totals.get(k, 0) + v
        all_gaps += gaps
        flag = ""
        if gaps:
            flag = f"  {RED}[{len(gaps)} missing]{RESET}"
        elif counts.get("pending"):
            flag = f"  {YELLOW}[{counts['pending']} unreviewed]{RESET}"
        print(f"\n{DIM}{ref}{RESET}{flag}")
        print(f"  {DIM}{urdu}{RESET}")
        print(f"  {BOLD}{deva}{RESET}")

    print(f"\n{'─' * 60}")
    for st in ("approved", "reviewed", "pending", "missing"):
        if totals.get(st):
            colour = GREEN if st == "approved" else (RED if st == "missing" else YELLOW)
            print(f"  {colour}{st:<10}{RESET} {totals[st]:>5} tokens")
    if all_gaps:
        print(f"\n  {RED}missing forms:{RESET} {', '.join(sorted(set(all_gaps)))}")

    unshippable = totals.get("pending", 0) + totals.get("missing", 0)
    if unshippable:
        print(
            f"\n  {YELLOW}NOT SHIPPABLE{RESET} — {unshippable} tokens are unreviewed or absent.\n"
            f"  {DIM}Machine suggestions are not review. → AGENTS.md §4.2{RESET}"
        )
        if args.strict:
            return 1
    else:
        print(f"\n  {GREEN}All tokens approved.{RESET}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
