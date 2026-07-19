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
