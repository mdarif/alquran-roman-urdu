# Gotchas

Landmines found the hard way. Append as you find more — in the same change as
the work, not afterwards.

Ordered roughly by how much time each costs if met cold.

---

## §1 — The Junagarhi text contains presentation-form ligatures

**Verified in the actual Tanzil text**, not hypothetical. In Al-Fatiha, `واﻻ`
ends in **U+FEFB** (ARABIC LIGATURE LAM WITH ALEF ISOLATED FORM), not `ل` + `ا`.

- NFC leaves it untouched.
- NFKC decomposes it correctly.

Vocabulary keyed on unnormalised or NFC-only text splits that word into two
distinct entries, and **every Dakshina lookup for it misses**. No error is
raised. The coverage number just comes out quietly wrong.

**Fix:** targeted NFKC over the presentation-form blocks only
(U+FB50–U+FDFF, U+FE70–U+FEFF), rather than blanket NFKC over the whole string —
blanket NFKC has other effects we don't want. See `fold_presentation_forms()`.

Pinned by a normalisation vector. Assume there are more of these in the text
than the one we found.

---

## §2 — Do-chashmi he is load-bearing; do not fold it

`ھ` U+06BE marks **aspiration**: bh, kh, th, ph, dh, jh, gh. It is a different
phoneme from `ہ` U+06C1 (gol he), the ordinary /h/.

Folding the various heh forms together is a standard and correct Urdu
normalisation step — *except* for this one. Fold `ه` U+0647, `ة` U+0629,
`ۃ` U+06C3 into `ہ`. Never fold `ھ`.

Get it wrong and `کھانا` (*khaana*, food) becomes `کہانا`. That is a real
Urdu-looking word. The pipeline runs clean, the output is confidently wrong,
and a reviewer skimming Latin output will not catch it because the damage
happened before romanization.

Same argument applies to alef madda `آ` U+0622 — phonemically distinct from
bare alef, do not fold.

Both pinned by vectors.

---

## §3 — Tashkeel are Unicode category `Mn`

Any tooling that treats `Mn` as a token separator will shatter a vocalised word
into single letters. This is exactly the SQLite FTS5 trap from the hadith side,
and it recurs anywhere a default "word character" class is applied.

If we ever index Roman *and* Urdu text in the same FTS table, re-read
`hadith-data/docs/gotchas.md §1` before writing the schema. The
`remove_diacritics` option is Latin-only regardless of what its name suggests.

---

## §4 — Type coverage and token coverage tell different stories

Token coverage will look encouraging. Function words (`کے`, `اور`, `ہے`, `کی`)
dominate the head of the frequency distribution and are all in Dakshina.

Type coverage is the honest metric. The tail carries the religious and classical
register — precisely where a Wikipedia-derived lexicon has the least. Expect
roughly 40–60% type coverage and do not be reassured by a much higher token
figure.

When reporting progress, lead with types.

---

## §5 — The dagger alef is genuinely ambiguous

U+0670 is a mark standing in for a letter. `اللّٰہ` carries one. Stripping it
with the rest of the tashkeel is right for *keying*, but it is not a
semantically empty mark, and for display or phonemic work it matters.

Same underlying issue as `hadith-data/docs/gotchas.md §2`. Do not "simplify"
the handling. If the phonemic layer ever needs it back, keying and rendering
must diverge rather than one being bent to serve both.

---

## §6 — Python↔Dart normaliser divergence fails silently

If any of this ever runs client-side in `alquran-app`, a mismatch between the
two normalisers produces **no error** — every lookup simply misses and the
feature appears empty. This has already happened once on the hadith side.

`tests/normalization_vectors.json` is the contract between implementations.
Both must run it in CI.

---

## §7 — Verse count mismatches are a bismillah convention, not corruption

Tanzil's Urdu files should be 6,236 lines. If the count is off, the usual cause
is how the bismillah is handled at surah boundaries, or a header/footer line —
not a damaged download. Check before re-fetching.

---

## §8 — The vector set claimed pins it did not have; "documented" ≠ "tested"

AGENTS.md §7 and §2 both stated alef madda `آ` and do-chashmi he `ھ` were "pinned
by vectors." Only do-chashmi actually was. The original inline set had **6**
vectors and pinned exactly one deliberate fold plus the lam-alef ligature, the
dagger-alef strip, the yeh fold and the kaf fold. **Not pinned:** alef madda
staying unfolded, `أ`/`إ` → bare alef, teh marbuta → gol he, tatweel removal,
Urdu-digit mapping.

Why it bites: a regression that started folding alef madda into bare alef — the
exact "plausible wrong word" failure §2 warns about — would have **passed** the
old self-test silently. The contract asserted less than the prose promised, and
the prose is what a reviewer trusts.

Fix applied in this change: the normaliser was extracted to
`scripts/normalise.py`, the vectors moved to `tests/normalization_vectors.json`
(now the single source of truth for Python and any future Dart port), and the
set extended to **12** so every deliberate fold — and every deliberate
non-fold — is pinned. Each added vector's `expected` was computed from the
current normaliser and confirmed to equal the documented intent before being
frozen; none was reverse-fitted to make a test pass.

Lesson for the next fold: adding a rule to the normaliser without adding a vector
leaves a claim in the docs with nothing enforcing it. Extend the JSON in the
same change. → AGENTS.md §7.

---

## §9 — A lexicon row's `freq` is a stamp, not a count

`data/lexicon/lexicon.tsv` carries a `freq` column, but it only records whatever
was true when the row was *written*. The 188 seeded machine suggestions were all
written with `freq=0`, and the 13 approved entries kept that zero.

`review.py --stats` summed that column and so reported **0.00% token coverage
with 13 entries approved** — not an error, just a number that said no progress
had been made when nearly 1% of the corpus was in fact done. The real coverage
is 0.93%.

The only place a real count lives is `out/vocab.tsv`, keyed and summed over the
surface forms that fold to each key. `vocab_freq()` / `freq_of()` in `review.py`
read it there rather than backfilling the TSV — a backfill goes stale the next
time the corpus is re-tokenised, which reintroduces the same silent wrong number.

**Multi-token keys are absent from `vocab.tsv` by construction** — it is built
from single whitespace tokens, so `ہم نے`, `راہ حق` and the five other n-gram
keys have no count and legitimately stay at 0. `freq_of()` falls back to the
stored value rather than inventing one; they sort last, which is why
`build_worklist` folds lexicon keys in explicitly instead of relying on the
queue files.

Same family as §4: a frequency number that looks plausible and is wrong is worse
than a missing one, because nobody re-checks it.

---

## §10 — Roman Urdu coverage numbers are copy-pasted into seven files, not sourced from one

When surahs 71–107 (785 verses) were drafted 2026-08-03 to complete Roman Urdu
coverage, the "325 of 6,236 verses" / "5,911 remain" / "surahs 3–107 missing"
figures turned out to be hand-written, independently, in: `README.md`,
`data/roman-urdu/README.md`, `docs/TRANSLITERATION-GUIDE.md` (three separate
spots in that file alone), `docs/NEXT-SESSION.md`, `AGENTS.md` (two spots),
`docs/decisions/0004-roman-urdu-working-style.md`, and `docs/roman-urdu-pilot.md`.
None of them derive from a script or from `data/roman-urdu/` itself — they are
prose someone typed once and no `validate_roman_urdu.py`-style check verifies
against the actual file count.

Nothing was broken by this — it's a documentation staleness risk, not a data
bug — but a session that trusts any one of those numbers without grepping the
rest will confidently repeat a wrong "verses remaining" figure. `docs/roman-urdu-pilot.md`
is deliberately exempt: it's a historical snapshot of the pre-recovery
`al-quran-web` coordination doc (marked as such), not live status.

**Fix applied in this change:** all of the above were updated to reflect
6,236/6,236 coverage, and `docs/TRANSLITERATION-GUIDE.md` is now the doc
pointed to as "kept current" for Roman Urdu status.

**Lesson for next time coverage changes** (a review pass moving surahs to
`approved`, for instance): `grep -rn "325\|5,911\|beta-unverified" --include=*.md .`
before trusting any single file's numbers, and update every hit in the same
change — not just the file you happened to be reading.
