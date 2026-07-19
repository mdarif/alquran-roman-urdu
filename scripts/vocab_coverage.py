#!/usr/bin/env python3
"""
vocab_coverage.py — how much of the Junagarhi Urdu Quran translation can
Dakshina actually cover?

Extracts the vocabulary of an Urdu Quran translation, normalises it, intersects
it with the Dakshina Urdu romanization lexicon, and reports coverage by type and
by token. Emits the unmatched forms, frequency-sorted, as the review queue.

Nothing here decides a romanization. It tells you how big the human job is.

INPUTS
------
  1. Tanzil ur.junagarhi as plain text, one verse per line (6236 lines).
     Get it from https://tanzil.net/trans/ (pick Urdu > Muhammad Junagarhi,
     text format). The download is behind a form, so fetch it by hand.

  2. Dakshina v1.0. Mirror it now — the repo was archived April 2026.
       curl -LO https://storage.googleapis.com/gresearch/dakshina/dakshina_dataset_v1.0.tar
       tar xf dakshina_dataset_v1.0.tar
     We use dakshina_dataset_v1.0/ur/lexicons/ur.translit.sampled.{train,dev,test}.tsv
     Format is: native_word <TAB> romanization <TAB> attestation_count
     A word appears on multiple lines, once per attested romanization.
     Licence: CC BY-SA 4.0 — see ADR 0001 before shipping anything derived.

USAGE
-----
  python3 vocab_coverage.py \
      --translation ur.junagarhi.txt \
      --dakshina    dakshina_dataset_v1.0/ur/lexicons \
      --outdir      out/

OUTPUTS
-------
  out/vocab.tsv          every surface form, frequency, normalised key, status
  out/review_queue.tsv   unmatched forms only, frequency-desc — the human job
  out/matched.tsv        matched forms with Dakshina's attested romanizations
  out/report.txt         the numbers
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

# The normaliser is the contract; it lives in its own module so a future Dart
# port can be pinned against the same vectors. → normalise.py, AGENTS.md §7.
# Add this script's own directory to the path so the import works whether the
# file is run directly or imported from another CWD (e.g. CI).
sys.path.insert(0, str(Path(__file__).resolve().parent))
from normalise import normalise, self_test  # noqa: E402,F401  (re-exported for main)

# Urdu / Arabic punctuation and ASCII punctuation.
_PUNCT = re.compile(r"[\u060C\u061B\u061F\u06D4\u066A-\u066D\u00AB\u00BB"
                    r"!-/:-@\[-`{-~\u2000-\u206F]")


# A token we care about: at least one Arabic-block letter.
_HAS_LETTER = re.compile(r"[\u0620-\u064A\u066E-\u06D3\u06FA-\u06FF]")


# ---------------------------------------------------------------------------
# Tokenisation
# ---------------------------------------------------------------------------

def tokenise(line: str) -> list[str]:
    """Whitespace + punctuation split. Keeps only tokens containing a letter.

    Junagarhi's text carries parenthetical glosses — (یعنی قیامت) and similar.
    Those words are counted here. Whether they get transliterated, dropped, or
    rendered distinctly is an open question in ADR 0001; count them so the
    decision has a number attached.
    """
    line = _PUNCT.sub(" ", line)
    return [t for t in line.split() if _HAS_LETTER.search(t)]


# ---------------------------------------------------------------------------
# Dakshina
# ---------------------------------------------------------------------------

def load_dakshina(lexdir: Path) -> dict[str, list[tuple[str, int]]]:
    """native_key -> [(romanization, attestations), ...] sorted by attestations desc.

    Reads train + dev + test. They are disjoint by native word, so the union is
    the full 30,000-type lexicon.
    """
    lex: dict[str, list[tuple[str, int]]] = defaultdict(list)
    files = sorted(lexdir.glob("ur.translit.sampled.*.tsv"))
    if not files:
        sys.exit(f"no ur.translit.sampled.*.tsv under {lexdir}")

    for path in files:
        with path.open(encoding="utf-8") as fh:
            for lineno, row in enumerate(csv.reader(fh, delimiter="\t"), 1):
                if len(row) < 2:
                    continue
                native, roman = row[0].strip(), row[1].strip()
                try:
                    count = int(row[2]) if len(row) > 2 and row[2].strip() else 1
                except ValueError:
                    count = 1
                if not native or not roman:
                    continue
                lex[normalise(native)].append((roman, count))

    for key in lex:
        merged: Counter[str] = Counter()
        for roman, count in lex[key]:
            merged[roman] += count
        lex[key] = merged.most_common()

    print(f"  dakshina: {len(lex):,} normalised types from {len(files)} files",
          file=sys.stderr)
    return dict(lex)


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def coverage_curve(freqs: list[int]) -> list[tuple[int, float]]:
    """How many top-N types to reach 50/75/90/95/99% of tokens."""
    total = sum(freqs)
    targets = [0.50, 0.75, 0.90, 0.95, 0.99]
    out, running, ti = [], 0, 0
    for rank, f in enumerate(sorted(freqs, reverse=True), 1):
        running += f
        while ti < len(targets) and running / total >= targets[ti]:
            out.append((rank, targets[ti]))
            ti += 1
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--translation", type=Path, required=True,
                    help="ur.junagarhi.txt, one verse per line")
    ap.add_argument("--dakshina", type=Path, required=True,
                    help="dakshina_dataset_v1.0/ur/lexicons")
    ap.add_argument("--outdir", type=Path, default=Path("out"))
    ap.add_argument("--keep-tashkeel", action="store_true",
                    help="do not strip vocalisation marks when keying")
    args = ap.parse_args()

    self_test()
    args.outdir.mkdir(parents=True, exist_ok=True)

    # --- read translation ---------------------------------------------------
    lines = args.translation.read_text(encoding="utf-8").splitlines()
    lines = [ln for ln in lines if ln.strip()]
    print(f"  translation: {len(lines):,} non-empty lines", file=sys.stderr)
    if len(lines) != 6236:
        print(f"  WARNING: expected 6236 verses, got {len(lines)}. "
              f"Check for a header/footer or a bismillah convention mismatch.",
              file=sys.stderr)

    surface = Counter()          # raw surface form -> freq
    key_of = {}                  # surface -> normalised key
    for ln in lines:
        for tok in tokenise(ln):
            surface[tok] += 1
            if tok not in key_of:
                key_of[tok] = normalise(tok, strip_tashkeel=not args.keep_tashkeel)

    keys = Counter()             # normalised key -> freq
    for tok, freq in surface.items():
        keys[key_of[tok]] += freq

    total_tokens = sum(surface.values())

    # --- intersect ----------------------------------------------------------
    dak = load_dakshina(args.dakshina)

    matched_keys = {k for k in keys if k in dak}
    unmatched_keys = [k for k in keys if k not in dak]

    matched_types = len(matched_keys)
    matched_tokens = sum(keys[k] for k in matched_keys)

    # --- write --------------------------------------------------------------
    with (args.outdir / "vocab.tsv").open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh, delimiter="\t")
        w.writerow(["surface", "freq", "key", "status"])
        for tok, freq in surface.most_common():
            k = key_of[tok]
            w.writerow([tok, freq, k, "matched" if k in dak else "unmatched"])

    with (args.outdir / "matched.tsv").open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh, delimiter="\t")
        w.writerow(["key", "freq", "n_variants", "top_romanization",
                    "top_attestations", "all_variants"])
        for k in sorted(matched_keys, key=lambda k: -keys[k]):
            variants = dak[k]
            w.writerow([k, keys[k], len(variants), variants[0][0], variants[0][1],
                        "|".join(f"{r}:{c}" for r, c in variants)])

    with (args.outdir / "review_queue.tsv").open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh, delimiter="\t")
        w.writerow(["key", "freq", "cumulative_token_pct", "roman", "phonemic",
                    "status", "reviewer", "source", "notes"])
        running = 0
        for k in sorted(unmatched_keys, key=lambda k: -keys[k]):
            running += keys[k]
            w.writerow([k, keys[k], f"{100 * running / total_tokens:.2f}",
                        "", "", "pending", "", "", ""])

    # --- report -------------------------------------------------------------
    ambiguous = sum(1 for k in matched_keys if len(dak[k]) > 1)
    curve = coverage_curve(list(keys.values()))

    report = [
        "Junagarhi Urdu Quran — vocabulary and Dakshina coverage",
        "=" * 58,
        "",
        f"verses                       {len(lines):>10,}",
        f"tokens                       {total_tokens:>10,}",
        f"unique surface forms         {len(surface):>10,}",
        f"unique normalised keys       {len(keys):>10,}",
        f"  collapsed by normalisation {len(surface) - len(keys):>10,}",
        "",
        "Dakshina coverage",
        "-" * 58,
        f"matched types                {matched_types:>10,}  "
        f"({100 * matched_types / len(keys):.1f}% of types)",
        f"matched tokens               {matched_tokens:>10,}  "
        f"({100 * matched_tokens / total_tokens:.1f}% of tokens)",
        f"unmatched types              {len(unmatched_keys):>10,}   <- the review queue",
        f"matched but ambiguous        {ambiguous:>10,}  "
        f"({100 * ambiguous / matched_types:.1f}% of matches have >1 attested spelling)",
        "",
        "Review effort — types needed to reach N% of tokens",
        "-" * 58,
    ]
    for rank, target in curve:
        report.append(f"  {target:>5.0%} of tokens   <-  top {rank:>6,} types")
    report += [
        "",
        "Note: token coverage always beats type coverage because the head of the",
        "distribution is function words. The tail is where the religious register",
        "lives, which is exactly where Dakshina's Wikipedia domain is thinnest.",
        "A matched key is a CANDIDATE, not an answer. Ambiguous matches and the",
        "whole review queue need a human. Nothing here is approved output.",
    ]
    text = "\n".join(report)
    (args.outdir / "report.txt").write_text(text + "\n", encoding="utf-8")
    print("\n" + text + "\n")
    print(f"wrote {args.outdir}/vocab.tsv, matched.tsv, review_queue.tsv, report.txt")


if __name__ == "__main__":
    main()
