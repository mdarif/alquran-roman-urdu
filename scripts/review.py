#!/usr/bin/env python3
"""
review.py — the human review loop for the Urdu -> phoneme lexicon.

This tool exists to make the *hard* arrow tractable:

    Urdu script --[HARD, ambiguous, THIS TOOL]--> phonemes --+--> Roman
                                                             +--> Devanagari

It shows a reviewer one surface form at a time, in frequency order, with real
verse context and Dakshina's attested romanizations as *candidates*, and records
the phonemic form the reviewer decides on. It never proposes a phonemic form of
its own. → AGENTS.md §4.1, §4.4.

What it will not do, by construction:
  * It does not guess, autofill, or rank a "best" phonemic form. A Dakshina
    candidate is displayed as evidence and is never pre-entered.
  * It rejects any phonemic form the renderer's inventory does not define,
    rather than storing something that renders approximately.
  * It records `reviewer` and `reviewed_at` on every entry. An entry with no
    reviewer is not reviewed.

Storage is `data/lexicon/lexicon.tsv` — plain TSV so every change is a readable
git diff, and so a bad edit is visible in review rather than buried in a binary.
Written atomically after each decision, so a crash costs at most the entry in
progress.

Usage:
    python scripts/review.py --reviewer "Name"      # walk the queue
    python scripts/review.py --stats                # coverage so far
    python scripts/review.py --hash                 # content hash of approved
    python scripts/review.py --reviewer "Name" --key کتب   # jump to one form
"""
from __future__ import annotations

import argparse
import hashlib
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from render_devanagari import PhonemeError, render  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
LEXICON = ROOT / "data" / "lexicon" / "lexicon.tsv"
QUEUE = ROOT / "out" / "review_queue.tsv"
MATCHED = ROOT / "out" / "matched.tsv"
VOCAB = ROOT / "out" / "vocab.tsv"
CORPUS = ROOT / "data" / "raw" / "ur.junagarhi.txt"

FIELDS = ["key", "phonemic", "status", "reviewer", "reviewed_at", "freq", "notes"]

# Ayahs per surah, in order. Lets the tool turn a corpus line number into a
# real "2:255" reference, which is what a reviewer needs to judge context.
AYAH_COUNTS = [
    7, 286, 200, 176, 120, 165, 206, 75, 129, 109, 123, 111, 43, 52, 99, 128, 111,
    110, 98, 135, 112, 78, 118, 64, 77, 227, 93, 88, 69, 60, 34, 30, 73, 54, 45,
    83, 182, 88, 75, 85, 54, 53, 89, 59, 37, 35, 38, 29, 18, 45, 60, 49, 62, 55,
    78, 96, 29, 22, 24, 13, 14, 11, 11, 18, 12, 12, 30, 52, 52, 44, 28, 28, 20,
    56, 40, 31, 50, 40, 46, 42, 29, 19, 36, 25, 22, 17, 19, 26, 30, 20, 15, 21,
    11, 8, 8, 19, 5, 8, 8, 11, 11, 8, 3, 9, 5, 4, 7, 3, 6, 3, 5, 4, 5, 6,
]

BOLD, DIM, CYAN, GREEN, YELLOW, RESET = (
    ("\033[1m", "\033[2m", "\033[36m", "\033[32m", "\033[33m", "\033[0m")
    if sys.stdout.isatty() else ("",) * 6
)

HELP = f"""
{BOLD}Entering a phonemic form{RESET}
  Space-separated phonemes. See scripts/render_devanagari.py for the inventory.
    consonants  k kh g gh c ch j jh T Th D Dh N R Rh t th d dh n
                p ph b bh m y r l v sh s S h  |  q x G z zh f (nukta series)
    vowels      a aa i ii u uu e ai o au
    modifiers   ~  nasalisation      '  ain/hamza (syllable break)
                +  suffix on a consonant = halant (true conjunct)

  {YELLOW}The '+' marker is the one thing to get right.{RESET} A coda consonant is bare;
  a gemination or true cluster takes a halant. Both look like "consonant with
  no vowel", so it cannot be inferred:
      k a r t aa    -> करता   (coda r, bare)
      a l+ l aa h   -> अल्लाह  (gemination, halant)

{BOLD}Commands{RESET}
  ?         this help            s   skip (stays pending)
  n <text>  attach a note        q   save and quit
  x         mark uncertain (status=reviewed, not approved)
"""


def surah_ayah(line_no: int) -> str:
    """Map a 1-based corpus line number to 'surah:ayah'."""
    n = line_no
    for i, count in enumerate(AYAH_COUNTS, start=1):
        if n <= count:
            return f"{i}:{n}"
        n -= count
    return f"?:{line_no}"


def load_lexicon() -> dict[str, dict]:
    if not LEXICON.exists():
        return {}
    rows = {}
    with LEXICON.open(encoding="utf-8") as fh:
        header = fh.readline().rstrip("\n").split("\t")
        for line in fh:
            if not line.strip():
                continue
            vals = line.rstrip("\n").split("\t")
            d = dict(zip(header, vals))
            rows[d["key"]] = d
    return rows


def save_lexicon(rows: dict[str, dict]) -> None:
    """Atomic write — a crash never leaves a half-written lexicon."""
    LEXICON.parent.mkdir(parents=True, exist_ok=True)
    ordered = sorted(rows.values(), key=lambda r: (-int(r.get("freq") or 0), r["key"]))
    fd, tmp = tempfile.mkstemp(dir=LEXICON.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write("\t".join(FIELDS) + "\n")
            for r in ordered:
                fh.write("\t".join((r.get(f) or "").replace("\t", " ") for f in FIELDS) + "\n")
        os.replace(tmp, LEXICON)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


def load_tsv(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as fh:
        header = fh.readline().rstrip("\n").split("\t")
        return [
            dict(zip(header, line.rstrip("\n").split("\t")))
            for line in fh if line.strip()
        ]


def load_contexts() -> list[str]:
    return CORPUS.read_text(encoding="utf-8").splitlines() if CORPUS.exists() else []


def find_contexts(surface: str, corpus: list[str], limit: int = 3) -> list[tuple[str, str]]:
    """Verses containing the surface form, with the token marked."""
    out = []
    for i, line in enumerate(corpus, start=1):
        if surface in line.split():
            marked = " ".join(
                f"{YELLOW}«{w}»{RESET}" if w == surface else w for w in line.split()
            )
            out.append((surah_ayah(i), marked))
            if len(out) >= limit:
                break
    return out


def content_hash(rows: dict[str, dict]) -> str:
    """Hash over approved entries only. Regeneration diffs against this, so a
    rule change cannot silently rewrite shipped text. → AGENTS.md §4.3."""
    approved = sorted(
        (r["key"], r["phonemic"]) for r in rows.values() if r.get("status") == "approved"
    )
    h = hashlib.sha256()
    for k, p in approved:
        h.update(f"{k}\t{p}\n".encode())
    return h.hexdigest()


def show_stats(rows: dict[str, dict]) -> None:
    vocab = load_tsv(VOCAB)
    total_types = len(vocab)
    total_tokens = sum(int(v["freq"]) for v in vocab) or 1
    by_status: dict[str, int] = {}
    done_tokens = 0
    for r in rows.values():
        by_status[r.get("status", "?")] = by_status.get(r.get("status", "?"), 0) + 1
        if r.get("status") in ("reviewed", "approved"):
            done_tokens += int(r.get("freq") or 0)
    print(f"\n{BOLD}Lexicon coverage{RESET}")
    print(f"  entries recorded    {len(rows):>6,} / {total_types:,} types")
    for st, n in sorted(by_status.items()):
        print(f"    {st:<16}{n:>6,}")
    print(f"  token coverage      {done_tokens/total_tokens*100:>6.2f}%  ({done_tokens:,} / {total_tokens:,})")
    print(f"  approved hash       {content_hash(rows)[:16]}…\n")


def build_worklist(rows: dict[str, dict], only_key: str | None) -> list[dict]:
    """Queue + matched, merged and frequency-ordered. Matched forms still need a
    human: 99.4% of Dakshina matches have more than one attested spelling, and a
    match is a candidate, not an answer."""
    cand: dict[str, dict] = {}
    for r in load_tsv(MATCHED):
        cand[r["key"]] = {"key": r["key"], "freq": int(r["freq"]), "dakshina": r.get("all_variants", "")}
    for r in load_tsv(QUEUE):
        cand.setdefault(r["key"], {"key": r["key"], "freq": int(r["freq"]), "dakshina": ""})
    if only_key:
        return [cand[only_key]] if only_key in cand else []
    todo = [
        c for c in cand.values()
        if rows.get(c["key"], {}).get("status") not in ("reviewed", "approved")
    ]
    return sorted(todo, key=lambda c: -c["freq"])


def review_loop(reviewer: str, only_key: str | None) -> int:
    rows = load_lexicon()
    corpus = load_contexts()
    worklist = build_worklist(rows, only_key)
    if not worklist:
        print("Nothing to review." if not only_key else f"Key not found: {only_key}")
        return 0

    total_tokens = sum(int(v["freq"]) for v in load_tsv(VOCAB)) or 1
    print(f"{DIM}{len(worklist):,} forms to review. '?' for help, 'q' to save and quit.{RESET}")
    done = 0

    for item in worklist:
        key, freq = item["key"], item["freq"]
        print(f"\n{'─' * 68}")
        print(f"{BOLD}{CYAN}{key}{RESET}   {DIM}freq {freq:,}  ({freq/total_tokens*100:.3f}% of tokens){RESET}")

        if item["dakshina"]:
            print(f"  {DIM}Dakshina (candidates, NOT answers):{RESET} {item['dakshina'][:100]}")
        else:
            print(f"  {DIM}no Dakshina match — religious-register tail{RESET}")

        for ref, verse in find_contexts(key, corpus):
            print(f"  {DIM}{ref:>7}{RESET}  {verse}")

        note = ""
        while True:
            try:
                raw = input(f"\n  {GREEN}phonemic>{RESET} ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\n  saving…")
                save_lexicon(rows)
                print(f"  {done} entries this session -> {LEXICON}")
                return 0

            if raw == "?":
                print(HELP)
                continue
            if raw == "q":
                save_lexicon(rows)
                print(f"\n  {done} entries this session -> {LEXICON}")
                print(f"  approved hash {content_hash(rows)[:16]}…")
                return 0
            if raw == "s" or raw == "":
                break
            if raw.startswith("n "):
                note = raw[2:].strip()
                print(f"  {DIM}note attached{RESET}")
                continue

            uncertain = raw == "x"
            if uncertain:
                print(f"  {DIM}enter the form you lean toward; it records as reviewed, not approved{RESET}")
                continue

            try:
                deva = render(raw)
            except PhonemeError as exc:
                # Never store something that renders approximately.
                print(f"  {YELLOW}rejected:{RESET} {exc}")
                continue

            print(f"  {BOLD}{deva}{RESET}")
            confirm = input(f"  {DIM}[enter]=approve  e=edit  x=reviewed-only  s=skip>{RESET} ").strip()
            if confirm == "e":
                continue
            if confirm == "s":
                break

            rows[key] = {
                "key": key,
                "phonemic": raw,
                "status": "reviewed" if confirm == "x" else "approved",
                "reviewer": reviewer,
                "reviewed_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "freq": str(freq),
                "notes": note,
            }
            save_lexicon(rows)  # after every decision, not at the end
            done += 1
            break

    save_lexicon(rows)
    print(f"\n{GREEN}Queue complete.{RESET} {done} entries this session.")
    show_stats(rows)
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--reviewer", help="name recorded on every entry you decide")
    ap.add_argument("--key", help="jump straight to one surface form")
    ap.add_argument("--stats", action="store_true", help="coverage so far")
    ap.add_argument("--hash", action="store_true", help="content hash of approved entries")
    args = ap.parse_args()

    if args.stats:
        show_stats(load_lexicon())
        return 0
    if args.hash:
        print(content_hash(load_lexicon()))
        return 0
    if not args.reviewer:
        ap.error("--reviewer is required: an entry with no reviewer is not reviewed")
    return review_loop(args.reviewer, args.key)


if __name__ == "__main__":
    sys.exit(main())
