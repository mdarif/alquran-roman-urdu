#!/usr/bin/env python3
"""
export_pilot.py — publish renderable surahs to the al-quran-web pilot directory.

Run this after a review session; refresh the browser and you see exactly what you
just approved.

    python scripts/review.py --reviewer "Name" --suggested
    python scripts/export_pilot.py
    #   then, in al-quran-web:  PUBLIC_SHOW_HND=1 npm run dev

Only surahs that render with **no gaps** are written — a half-rendered surah with
⟨missing⟩ markers reads as broken rather than in progress, which is the same rule
al-quran-web's export applies to the Roman Urdu pilot.

Each file records the *worst* status among its tokens in `lexicon_status`, so the
page can tell "every word approved" from "still carries machine suggestions".
`--approved-only` writes just the surahs that are fully approved, which is what a
real publish should use.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from overrides import load_overrides  # noqa: E402
from render_verse import SOURCE_DB, render_verse  # noqa: E402
from review import load_lexicon  # noqa: E402

OUT_DIR = Path.home() / "code" / "al-quran-web" / "data" / "hindi-devanagari"

NOTE = (
    "PILOT / ILLUSTRATIVE. A model produced these vowelizations; per the project's "
    "non-negotiables they ship only behind a visible 'unverified' label until human "
    "review. This is Hindi SCRIPT carrying URDU vocabulary — a transliteration, not "
    "a Hindi translation. See alquran-roman-urdu ADR 0003."
)
SOURCE = "Transliterated from the Urdu translation of Maulana Muhammad Junagarhi (public domain)."

RANK = {"approved": 0, "reviewed": 1, "pending": 2}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--approved-only", action="store_true",
                    help="write only surahs where every token is approved")
    ap.add_argument("--out", type=Path, default=OUT_DIR)
    args = ap.parse_args()

    lex, ovr = load_lexicon(), load_overrides()
    con = sqlite3.connect(SOURCE_DB)
    args.out.mkdir(parents=True, exist_ok=True)

    written, skipped, stale = [], 0, 0
    for s in range(1, 115):
        ayahs, statuses, ok = {}, set(), True
        for a, t in con.execute(
            "select ayah,text from translation where sura=? order by ayah", (s,)
        ):
            deva, counts, gaps = render_verse(t, lex, f"{s}:{a}", ovr)
            if gaps:
                ok = False
                break
            ayahs[str(a)] = deva
            statuses |= {k for k in counts if k != "punct"}
        path = args.out / f"surah-{s:03d}.json"
        worst = max(statuses, key=lambda x: RANK.get(x, 9)) if statuses else "pending"
        if not ok or (args.approved_only and worst != "approved"):
            # Remove a file that no longer qualifies, so the site never keeps
            # serving output the lexicon has since invalidated.
            if path.exists():
                path.unlink()
                stale += 1
            skipped += 1
            continue
        path.write_text(json.dumps({
            "surah": s,
            "status": "approved" if worst == "approved" else "beta-unverified",
            "register": "perso-arabic",
            "source": SOURCE,
            "note": NOTE,
            "lexicon_status": sorted(statuses),
            "ayahs": ayahs,
        }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        written.append((s, worst, len(ayahs)))

    for s, worst, n in written:
        flag = "" if worst == "approved" else f"  ({worst})"
        print(f"  surah-{s:03d}.json  {n:>3} ayahs{flag}")
    print(f"\n{len(written)} surahs written, {skipped} skipped"
          + (f", {stale} stale file(s) removed" if stale else ""))
    if any(w != "approved" for _, w, _ in written):
        print("  NOT all approved — keep the site flag off for any deployed build.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
