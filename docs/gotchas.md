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

---

## §11 — Roman compounds of اللہ spell "-ullah", not "-allah"

Plan §4 Phase 2 check 2b describes matching Roman tokens "containing 'allah'"
to cover compounds like `Baitullah`, `kalaamullah`, `Rasoolullah`. Taken
literally that fails: `Baitullah` is spelled with a **u** before the doubled
lam (`bait` + `u` + `llah`), so the literal substring `"allah"` (a-l-l-a-h) is
not present — only `"ullah"` is. Grepping the real corpus confirms it: 3072
`allah`, but the compounds are `rasoolullah` (12), `wallah` (6), `baitullah`
(3), `kalaamullah` (1), `ghairullah` (1), `zikrullah` (1) — every one of them
an `-ullah` spelling, zero literal `-allah` compounds.

`scripts/lint_roman_urdu.py`'s 2b parity check therefore matches on the
substring `"llah"` (case-insensitive), not `"allah"` — that's the one
substring every form (`Allah`, `Baitullah`, `Rasoolullah`, `kalaamullah`)
actually shares. Matching literally on `"allah"` would have silently missed
every compound and made the check far noisier than the warn-level design
intends.

---

## §12 — A verse-level "balanced parentheses" check can hide a broken bracket

`lint_roman_urdu.py` check 2g-parens counts total `(` vs `)` per verse and
flags a mismatch. That only catches a broken bracket if the verse's *total*
count is off. Two independent bracket defects in the same verse — one gloss
missing its `(`, another honorific missing its `)` — cancel out numerically
and the verse reads as "balanced" even though both spans are individually
broken. Over the real corpus this check fires exactly once (57:12); a
per-honorific / per-gloss adjacency check (each opening `(` must be matched by
the *next* `)`, not just an equal count) would be needed to catch the
cancelling case, and does not exist yet.

Related, but not currently a problem: `check_honorific_typography` (2g) only
inspects honorific mentions that already sit inside some `(...)` span — an
honorific written with **no** brackets at all (`Alaihis-Salaam` bare in
running text) would not be flagged by 2g-honorific, and would not disturb the
2g-parens count either (zero added on both sides). Checked against the real
corpus: this does not currently happen — every `alaih*`/`sallallahu*` mention
in `data/roman-urdu/` sits inside *some* pair of parentheses, canonical or
not — but a future edit that drops an honorific's brackets entirely would
slip past both checks silently. Worth a dedicated "honorific has zero
brackets" check if ADR 0005 R4 is enforced as `error`.

---

## §13 — `lint_roman_urdu.py`'s 2a tokenizer silently mis-scores hyphenated
`canonical.tsv` rows (Phase 3)

`check_canonical`'s word regex is `[A-Za-z']+` — it treats a hyphen as a
token boundary. Three `decided` rows are themselves hyphenated compounds
(`mash'ar-e-haraam`, `ne'mat-o-fazl`, `ita'at-guzari`). Against those:

- The lint **never** matches the compound as a whole (`"mash'ar-e-haraam"`
  never appears as one token under this regex), so it can never fire for
  that row at all.
- Worse, it can **false-positive**: `"ne'mat-o-fazl"` tokenizes into
  `ne'mat`, `o`, `fazl`, and `ne'mat` happens to be a *different*,
  legitimate `decided` row on its own — so the lint counts that fragment as
  a real `ne'mat` occurrence even though it's actually part of the
  hyphenated compound. Same for `ita'at` inside `ita'at-guzari`.

Verified against the real corpus (2026-09-25, before Phase 3's apostrophe
group ran): `scripts/apply_canonical.py`'s hyphen-aware tokenizer (a token is
a maximal run of letters/apostrophes, chained across hyphens only when
adjacent to more letters) correctly counted **110** occurrences across the 25
non-`ta'ala` apostrophe rows; `lint_roman_urdu.py`'s 2a check counted **109**
for the same set — a net undercount from a missed compound and a
false-positive fragment cancelling differently per row. Both
`mash'ar-e-haraam` and `ne'mat-o-fazl` and `ita'at-guzari` fire zero 2a
findings before **and** after being fixed, because the lint's tokenizer can
never see them as a whole token either way.

This did not cause any wrong edits — `apply_canonical.py` has its own
correct tokenizer and is the only thing that writes to
`data/roman-urdu/*.json` — but anyone reading `out/lint.tsv` 2a counts as a
precise per-row occurrence count for a hyphenated row should not trust it.
Fixing `lint_roman_urdu.py`'s `_ROMAN_WORD_RE` to chain across hyphens the
same way `apply_canonical.py`'s `_TOKEN_RE` does would remove both failure
modes; not done in Phase 3 because Phase 3's rule is "never hand-edit
`lint_roman_urdu.py` checks beyond what the plan's step 3 asks for" and this
wasn't in scope.

---

## §14 — Phase 5 review tooling: two independent hash checks, and the patch has no surah column

Built 2026-09-25/26 per `docs/PHASE-5-REVIEW-DESIGN.md`. Two things a future
agent extending this should know before touching it:

**The hash-staleness check exists in two places, not one.** Lint 2f
(`lint_roman_urdu.check_hash`) and `status.derive_file_status`'s
"hash-clean" test both recompute `sha256(current text)` and compare it
against a ledger row's stored `sha256`, independently. They currently agree
(same `review_ledger.sha256_hex`, same "exact unnormalised UTF-8 bytes, no
trim/case-fold" rule), but nothing enforces that they keep agreeing if either
is changed later. Same shape as gotchas §6 (Python↔Dart normaliser
divergence) — if you touch one, touch the other and re-run
`tests/test_lint_hash.py` **and** `tests/test_status.py` together, not just
the one whose file you edited.

**The review-sheet patch format has no surah column.** Design §4 specifies
exactly five columns — `ayah, decision, corrected_text, note, seen_sha256`
— with no way to tell which surah a downloaded patch belongs to.
`review_sheet.py`'s "Download patch" button names the file
`surah-{NNN}-patch.tsv`; `apply_review.py` infers the surah from that
filename (`surah-(\d+)` in the stem) and only falls back to a required
`--surah N` if the name doesn't match. **Renaming a downloaded patch file
before applying it will silently apply it to the wrong surah** unless
`--surah` is passed explicitly — there is no cross-check against the
patch's own content, because the patch's own content doesn't carry the
surah. If this bites in practice, the fix is to add a `surah` column to the
patch format (a schema change, so present it to the owner first, per
AGENTS.md §9), not to make the inference cleverer.

**`status.py --write-status` only writes a file when the derived status
actually differs from the current one.** This is deliberate, not an
oversight: it's what keeps `git diff --stat data/roman-urdu/surah-*.json`
empty when run against the real corpus while everything is still `pending`
(verified 2026-09-25/26), even though `apply_canonical.py`'s own
byte-identical-JSON-formatting guarantee would probably have made an
unconditional rewrite safe too. Don't "simplify" this to an unconditional
write without re-running that real-corpus diff check.

---

## §15 — A "short" TSV row reads as `None`, not `""`, via `csv.DictReader`

Found 2026-09-25 building the AI pre-check loader
(`review_sheet.load_prereview_rows`) against the other agent's real output
at `data/roman-urdu/prereview/surah-001.tsv`. Its `ok` rows write only three
fields (`ayah`, `verdict`, `sha256`) and omit the trailing empty
`concern`/`suggestion` tabs entirely, rather than writing them as `""`. Fed
through `csv.DictReader`, a row shorter than the header fills every missing
trailing column with `None` (its `restval`, default `None`) — not `""`.

A test built only from hand-written fixtures (every column always present,
even when empty) never exercises this and stays green while the loader
quietly returns `concern=None`/`suggestion=None` for most real rows —
`None` then serialises to JSON `null` and would print as the literal text
`"None"` if ever interpolated into the page without a guard. Caught by a
red test built from the real file's actual shape, not a synthetic one;
`load_prereview_rows` now coerces every field with `raw[key] or ""`. Assume
any other TSV loader here that trusts `csv.DictReader`'s dict directly has
the same gap for optional trailing columns.
