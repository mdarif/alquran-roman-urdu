# Next session — start here

Written 2026-07-27 at the end of a long session, for a **fresh Claude session**
with no memory of it. Read `AGENTS.md` first, then this.

---

## Update 2026-08-03 — Roman Urdu coverage is complete; review is next

`data/roman-urdu/` now holds **all 6,236 verses, all 114 surahs** — surahs 3–70
and 71–107 were drafted since the 2026-08-02 update below, closing what was then
a 5,911-verse gap. Every mention of "325 verses" or "surahs 3–107 remaining"
elsewhere in this repo's docs describes the state *before* this update; treat
those as historical unless a doc has been updated to say otherwise.

**Everything is still `beta-unverified`.** Coverage finishing does not mean
review finished — AGENTS.md §2 still applies in full: nothing ships unreviewed.
The Roman Urdu track's "one thing that matters tomorrow" is now the read-aloud
review pass in `docs/TRANSLITERATION-GUIDE.md` §6, parallel to (and independent
of) the Devanagari lexicon review below.

→ To review or extend Roman Urdu further, read **`docs/TRANSLITERATION-GUIDE.md`**,
which is kept current; this file's Roman Urdu numbers below are not.

---

## Update 2026-08-02 — the Roman Urdu track is live again, and it is separate

Two things changed, and the second one splits this repo into **two tracks that do
not gate each other**.

1. **Owner ruling: our Roman Urdu, or none.** A complete third-party edition
   (Al-QuranJino / Muhammad Kazim) was fetched, bundled into `quran.db` and
   compared against our own pilot on Al-Baqarah 1–7. It lost on every axis —
   `qarch`/`aaqirath` for خ, `hidaayath` for final ت, dropped nasalisation,
   footnote markers fused into words in **309 verses**, `darsana` typo at 2:6.
   Roman Urdu is now **gated off** in app and web (`FeatureFlags.romanUrdu`,
   `EDITION_FLAGS`) rather than shipped rough. → `AGENTS.md` §1.

2. **The Roman Urdu pilot was recovered into this repo** at
   `data/roman-urdu/` — 325 verses (surahs 1, 2 in full, 108–114). It had been
   living in `al-quran-web` and was deleted there; recovered from that repo's
   history, byte-exact.

**Why this matters for what you do next:** the pilot is **hand-written, not
generated**. No script produces it, and the lexicon's 13/201 review state does
**not** gate it. So "review the ~188 pending entries" below is the bottleneck for
the **Devanagari** track only. Extending Roman Urdu coverage is now a parallel,
unblocked task with a shipped feature waiting on it.

→ To work on Roman Urdu, read **`docs/TRANSLITERATION-GUIDE.md`**.
→ To work on Devanagari, continue with this file.

---

## Where things stand

The Devanagari transliteration pipeline is **built and working**. What is missing
is human review, and nothing ships without it.

| | |
|---|---|
| Renderer | done — `scripts/render_devanagari.py`, reproduces the owner's target verse exactly |
| Verse renderer | done — `scripts/render_verse.py`, n-grams + per-occurrence overrides |
| Review tool | done — `scripts/review.py --suggested` (confirm-or-correct) |
| Validator | done — `scripts/validate.py`, 95.8% corroborated |
| Cross-check | done — `scripts/crosscheck.py` vs the Roman Urdu pilot |
| Style guide | done — `docs/STYLE_GUIDE.md`, **authoritative** |
| Licensing | resolved — Junagarhi is public domain |
| **Lexicon review** | **13 approved / 201 entries. This is the bottleneck.** |

**Rendered surahs (Devanagari):** 1, 108–114 (8 of 114). None shippable —
`render_verse.py --surah N --strict` exits non-zero while anything is `pending`.

**Roman Urdu (separate track, hand- and assistant-written, not gated by the
above):** **6,236 of 6,236 verses, all 114 surahs — coverage complete** as of
2026-08-03 (see the update at the top of this file). All still
`beta-unverified`. → `docs/TRANSLITERATION-GUIDE.md`.

---

## The one thing that matters tomorrow

**Review the ~188 pending entries.** Everything else on the *Devanagari* track is
secondary. (Roman Urdu is the other track and does not wait on this — its
coverage is now complete and its own review pass is the next task there; see
the 2026-08-03 update above.)

```bash
cd ~/code/alquran-roman-urdu
python3 scripts/validate.py                              # 14 words no published text has written
python3 scripts/review.py --reviewer "Mohammad Arif" --suggested
python3 scripts/export_pilot.py                          # push results to the web pilot
```

Then preview:

```bash
cd ~/code/al-quran-web && PUBLIC_SHOW_HND=1 npm run dev
# http://localhost:4321/surah/1-al-fatihah/
```

When a surah is fully approved, `--strict` passes and the flag can go on for it.

### Two things the tooling cannot catch — only reading can

Both were found by the owner reading the page, and no word-level check reaches
them:

1. **Homographs** (§7 of the style guide). One Urdu spelling, two Hindi words.
   `میں` = मैं/में, `اس` = इस/उस, `تو` = तू/तो, `ان` = इन/उन, `کہ` = कि/कह.
   ~7% of the corpus. Fix with a per-occurrence entry in
   `data/lexicon/overrides.tsv`, never by changing the default.
2. **Izafat** (§6). `راه حق` → **राह-ए-हक़**. Urdu does not write the linker, so
   nothing in the text signals it. **No heuristic may be invented** — it would
   insert linkers into phrases that lack them.

---

## Open decisions (owner)

1. **Word-final `ہ`** — مہربان → मेहरबान. Does it need a schwa rule? (§9)
2. **Roman Urdu's postposition convention.** ADR 0002 splits pronoun+postposition
   on Devanagari evidence; Roman may legitimately differ. (§9)
3. **AI4Bharat as a seeder.** Not used today — the pipeline is pure stdlib, zero
   dependencies, and the only model in the loop is the assistant. The measured
   suggestion error rate is **~15%**, so a purpose-built transliteration model may
   well beat it and would at least be reproducible. Blocked on: a licence check
   (another `ATTRIBUTION.md` row, and Dakshina's CC BY-SA already propagates) and
   accepting the loss of the zero-dependency property. **Evaluate by measuring
   against the owner's corrections — do not adopt on reputation.**

---

## Known issues worth fixing

- ~~**`review.py --stats` reports 0.00% token coverage**~~ — **fixed 2026-07-28.**
  Stats now read the real counts from `out/vocab.tsv` (`vocab_freq()`/`freq_of()`)
  instead of the row's stored `freq` stamp. Reports **0.93%** (1,750 / 187,325).
  The review queue's ordering was *not* affected — only the 7 n-gram keys ever
  sorted on the stored value, and those have no corpus count either way.
  → `docs/gotchas.md §9`
- **`validate.py` and `review.py` are separate passes.** Folding corroboration
  into the review walk (stop only on unseen words) was offered and not yet done.

---

## Repo state

| Repo | Branch | Note |
|---|---|---|
| `alquran-data` | `develop` | clean, pushed. **`main` is 6 behind** |
| `alquran-roman-urdu` | `main` | as of 2026-07-27: clean, pushed, no `develop` branch. Stale — see the 2026-08-03 update above; check `git status` rather than trusting this row |
| `al-quran-web` | `main` | clean, pushed. Auto-deploys on push |
| `alquran-app` | `develop` | pushed; owner's `home_overflow_menu.dart` WIP + 2 untracked `docs/` items are **pre-existing, leave them** |

**`al-quran-web` auto-deploys to production on push to `main`** (see
`wrangler.toml`). The Devanagari pilot is gated behind `PUBLIC_SHOW_HND`, which
the deploy never sets — an env var rather than a literal precisely so an
unreviewed text cannot go live by accident. **Do not replace it with a hardcoded
`true`.**

---

## Hard-won lessons from this session

Four bugs shared one shape: **a silent miss, never an error.** Expect more.

- Arabic presentation forms in the shipped Urdu (304 codepoints) — search failed
  across `غ` and `ﻎ`.
- Lexicon keyed on raw surface forms while the review queue used normalised ones
  — reviewed entries would never have been found.
- Precomposed vs decomposed Devanagari nukta — Unicode composition exclusions, so
  NFC/NFD do not reconcile them and search failed across identical-looking text.
- n-gram matcher rejected any window whose first token had a leading bracket, so
  parenthesised phrases silently never joined.

Also: **the assistant's suggestions were wrong ~15% of the time** — पीछहे, कुछह,
तुमहारे, इनसान, वनिशान, and two override indices simply guessed wrong. Al-Fatiha
looked clean only because its 15 forms had been hand-annotated into the renderer's
gold set, which made the check circular. Treat every machine suggestion as
unreviewed, because it is.

**The Roman Urdu pilot already contained most of the corrections** the owner made
by eye — `to` not `tu`, `us ka` split, `rassi`, `raah-e-haq`. `crosscheck.py`
exists so that never happens again. Consult it before asking the owner.
