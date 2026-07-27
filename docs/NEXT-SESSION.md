# Next session — start here

Written 2026-07-27 at the end of a long session, for a **fresh Claude session**
with no memory of it. Read `AGENTS.md` first, then this.

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

**Rendered surahs:** 1, 108–114 (8 of 114). None shippable — `render_verse.py
--surah N --strict` exits non-zero while anything is `pending`.

---

## The one thing that matters tomorrow

**Review the ~188 pending entries.** Everything else is secondary.

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

- **`review.py --stats` reports 0.00% token coverage** even with 13 approved.
  The seeded entries carry `freq="0"`, so the weighting is wrong. Cosmetic but
  misleading — it looks like no progress.
- **`validate.py` and `review.py` are separate passes.** Folding corroboration
  into the review walk (stop only on unseen words) was offered and not yet done.

---

## Repo state

| Repo | Branch | Note |
|---|---|---|
| `alquran-data` | `develop` | clean, pushed. **`main` is 6 behind** |
| `alquran-roman-urdu` | `main` | clean, pushed. No `develop` branch |
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
