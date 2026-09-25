# Roman Urdu — how to continue the transliteration

Written 2026-08-02 for an agent or reviewer picking this up cold. Updated
2026-08-03: coverage is complete. Read `AGENTS.md` §1 and §4 first
(non-negotiables), then this.

**The job — coverage phase: done.** `data/roman-urdu/` holds all 6,236 verses
across all 114 surahs. **The job now: review.** Nothing is `reviewed` or
`approved` yet — that is the only thing standing between this text and
shipping. See §7.

---

## 0. The one decision you must not re-open

**Al Quran ships our own Roman Urdu, or none at all.** A complete third-party
edition was fetched, bundled, compared and rejected on quality (AGENTS.md §1).
Do not adopt, patch, or blend it. If you want to *consult* it as a disagreement
signal that is fine and useful — that is exactly what `scripts/crosscheck.py`
does — but it is evidence, never an answer.

The rejected text is still in `quran.db` as `ur-roman-junagarhi-experimental`.
Its known defect classes are a useful checklist of what **not** to produce:

| Defect | Their output | Correct |
|---|---|---|
| خ → `q` | `qarch`, `aaqirath` | `kharch`, `aakhirat` |
| final ت → `th` | `hidaayath`, `najaath` | `hidayat`, `najaat` |
| nasalisation dropped | `hai` (ہیں), `dilo` (دلوں) | `hain`, `dilon` |
| footnote marker fused | `parhezgaaro1` | `parhezgaron` |
| retroflex/typo | `darsana` (2:6) | `darana` |

---

## 1. Where things stand

| | |
|---|---|
| Coverage | **6,236 of 6,236 verses, all 114 surahs — complete** |
| Review | **0 verses reviewed, 0 approved** — this is now the only gap |
| Status of all files | `beta-unverified` — not reviewed, not approved |
| Consumers | Roman Urdu is **gated off** in app and web until this is reviewed |

Don't hand-type these numbers into a doc (gotchas §10) — run
`python3 scripts/status.py` for current coverage and per-status counts.

### Provenance is NOT uniform — read this before treating any surah as gold

Files carry four different `note` claims — check the `note` field of the
specific surah you're reviewing before trusting it as a style reference:

- **surah 2** — "Hand-transliterated in the popular register." The strongest
  exemplar; use it as the model for judging everything else.
- **surah 1** — "A model produced these vowelizations."
- **surahs 3–107** — "Assistant-drafted in the popular register... following
  ADR 0004." Drafted directly against the Surah 2 pattern and the ADR 0004
  working rules, never reviewed.
- **surahs 108–114** — neither claim; house-style reference only.

So the corpus is a **good stylistic reference and a weak factual one** almost
everywhere except surah 2. Do not silently promote any surah to `approved` on
the strength of it having existed for a while, or of having passed
`validate_roman_urdu.py` — that script only checks structure (no gaps, no
blank verses, no stray digits), never meaning.

---

## 2. Getting the source text

The base is the **Junagarhi** Urdu translation — transliterated, *never*
re-translated. Two equivalent sources; `data/raw/` is gitignored, so on a fresh
clone use the DB:

```bash
# Preferred: by surah, straight from the shipped DB (resource_id 1 = Junagarhi)
sqlite3 ~/code/alquran-app/assets/db/quran.db \
  "SELECT a.ayah_number, t.text_content
     FROM ayahs a JOIN translations t ON t.ayah_id = a.id
    WHERE a.surah_id = 3 AND t.resource_id = 1
    ORDER BY a.ayah_number;"
```

```bash
# Alternative: the flat file, one verse per line, line N = global ayah id N
head -1 data/raw/ur.junagarhi.txt        # 6,236 lines, gitignored
```

`scripts/render_verse.py` uses a third path
(`~/code/alquran-data/sources/ur-junagarri-simple.db` — note the upstream
filename typo). All three carry the same text.

---

## 3. The file format

One file per surah: `data/roman-urdu/surah-NNN.json`, zero-padded to three
digits. Keys are verse numbers **as strings**, `1..N` with no gaps.

```json
{
  "surah": 3,
  "status": "beta-unverified",
  "register": "popular",
  "source": "Transliterated from the Urdu translation of Maulana Muhammad Junagarhi.",
  "note": "PILOT / ILLUSTRATIVE. Not reviewed, not approved. Hand-transliterated in the popular register; ships only behind the visible Beta label until human review. House style: popular (see alquran-roman-urdu/out/house-style-popular-DRAFT.md).",
  "ayahs": {
    "1": "Alif Laam Meem.",
    "2": "…"
  }
}
```

Rules the consumers rely on:

- **No partial surahs.** A half-rendered surah reads as broken, not as work in
  progress. Write the file only when every verse is present — this is the same
  rule `export_pilot.py` applies to the Devanagari pilot.
- **`status` lifecycle:** `beta-unverified` → `reviewed` → `approved`. Only a
  human moves it, and only `approved` may ship unlabelled.
- Keep the `note` honest about how the text was produced. If a model drafted it,
  say so, exactly as `surah-001.json` does.

---

## 4. House style

**`docs/decisions/0004-roman-urdu-working-style.md` is the operative reference
for new Roman Urdu coverage**, with `out/house-style-popular-DRAFT.md` as its
background style proposal. The ADR records the working rulings for pronoun
splitting, `میں`, ayn apostrophes, izafat, parenthetical glosses, and canonical
spellings.

`out/house-style-popular-DRAFT.md` is still useful, but it is a DRAFT and was
never ratified as the Roman Urdu authority. It was written as a proposal for
ADR 0002, but ADR 0002 was accepted primarily for the **Devanagari** house style
and explicitly left Roman pronoun + postposition boundaries open. Two
consequences:

1. Follow ADR 0004 for new text, using the draft and Surah 2 as supporting
   references.
2. `docs/STYLE_GUIDE.md` is authoritative for **Devanagari**, not for this. Do
   not apply its rulings here without checking they transfer; the two scripts
   legitimately differ (ADR 0002 splits pronoun+postposition on Devanagari
   evidence, and Roman may not follow).

### Gaps in the draft you will hit immediately

- **Rule 3 (`میں`) is ambiguous** and the draft does not resolve it. The word is
  two words: pronoun "I" → `main`, postposition "in" → `mein`. The pilot gets
  this right by context (2:2 `mein`, 1:5-style `main`). Only context decides —
  same homograph class as §7 of the Devanagari style guide (`اس` is/us, `ان`
  in/un, `تو` to/tu, `کہ` ke/kah), ~7% of the corpus.
- **Rule 10 (ayn) is applied inconsistently** in the pilot itself: `Taala` and
  `ibaadat` keep the draft's convention, but 1:7 reads `inaam` where the
  apostrophe form `in'aam` was also in play. Pick one and note it.
- **Izafat** (rule 14, `raah-e-haq`): Urdu does not write the linker, so nothing
  in the text signals it. **Do not invent a heuristic** — it would insert linkers
  into phrases that lack them. This must be recognised word by word.
- **Parenthetical glosses.** Junagarhi's `()` asides are preserved and
  transliterated in the pilot. That is still formally an open question in
  ADR 0001; follow the pilot and flag rather than silently drop.

---

## 5. Verify before you write

`validate.py` and `crosscheck.py` target the Devanagari path. Run the Roman Urdu
structural check on anything you add:

```bash
python3 scripts/validate_roman_urdu.py
python3 scripts/validate_roman_urdu.py --surah 3
```

Stray digits are deliberately flagged: fused footnote markers are precisely the
defect that disqualified the third-party edition (309 verses). Never ship a digit
inside a transliterated word.

Then **read it aloud**. Two error classes reach no automated check — homographs
and izafat — and both were originally caught by the owner reading the page, not
by tooling.

### Proofread it on a real reader page

`al-quran-web` reads this directory directly at export time, so work in progress
can be checked on a real verse page rather than in a JSON file:

```bash
cd ~/code/al-quran-web
npm run sync:roman-urdu     # copy this repo's text into the web repo
npm run dev
# http://localhost:4321/surah/2-al-baqarah/ → toggle "Roman Urdu" in the toolbar
```

The edition appears as **`ur-roman-abu-rayyan`**, labelled *Experimental*, off by
default, with a per-verse "suggest a correction" link. Surahs you have not
covered show a "still expanding" note instead of an empty block. No `quran.db`
rebuild is involved.

**⚠ The web repo holds a COMMITTED COPY, not a live link.** The Cloudflare Pages
build clones `al-quran-web` only, so a path into this repo resolves on your
machine and nowhere else — the text has to be committed there to reach
production. Consequences:

- **This repo stays the source of truth.** Never hand-edit
  `al-quran-web/data/roman-urdu/`; edit here, then re-run `sync:roman-urdu`.
- **Your changes are not live until you sync AND commit the web repo.** Forget
  the sync and the site keeps serving the previous text with no error.
- `sync:roman-urdu` validates before writing — invalid JSON, an empty verse, or
  **any digit inside a verse** (the fused-footnote defect) aborts the copy.
- `PUBLIC_SHOW_RUR=0` builds without the edition; missing data warns rather than
  failing, so the site is never broken by its absence.

**This is live on alquranreader.com** (owner, 2026-08-02) as an opt-in
Experimental edition. Text you sync and commit is public — treat `beta-unverified`
as "publicly readable and labelled", not "private".

---

## 6. Suggested order of work — now a review order, not a drafting order

Drafting is finished (§1). What's left is the human read-aloud review pass
that AGENTS.md §4 requires before any surah can move past `beta-unverified`.
Suggested order:

1. **Surah 2 first**, as a calibration pass — it's the hand-transliterated
   exemplar, so reviewing it establishes what "approved" should look like
   before judging assistant-drafted surahs against it.
2. Then **short high-traffic surahs** — 36 (Yaseen), 55 (Ar-Rahman), 67
   (Al-Mulk), 18 (Al-Kahf), 1 (Al-Fatiha) — which get read most and would let
   the flag flip on for a meaningful subset sooner even before the full corpus
   is reviewed.
3. Then the rest, in any order — the consumers already handle partial
   `approved` coverage: `al-quran-web` shipped a "coming soon" note for surahs
   without Roman Urdu (the `.rur-soon` rule in `src/styles/global.css`), and
   the same per-surah gating applies to review state.

Two error classes reach no automated check — homographs and izafat (§4) —
so `validate_roman_urdu.py` passing is not evidence a surah is ready; only
reading it is.

---

## 7. When it is ready to ship

Coverage being complete does **not** mean this is ready to ship — review (§6)
comes first. When a surah (eventually the whole corpus) is `approved`, turning
it back on is two one-line flips, both already wired:

- `alquran-app` — `FeatureFlags.romanUrdu = true`
  (`lib/core/feature_flags.dart`). The gate is applied in
  `translationResources()`, the single chokepoint for picker and reader.
- `al-quran-web` — remove/flip `'ur-roman-junagarhi-experimental'` in
  `EDITION_FLAGS` (`src/lib/editions.ts`).

But note **both flags currently point at the third-party text bundled in
`quran.db`**. Shipping *our* text additionally requires the pipeline step that
was never built: ingest `data/roman-urdu/` into `alquran-data` as a
`resources.type = 'transliteration'` row (its own slug, e.g.
`ur-roman-abu-rayyan`), rebuild `quran.db`, run `make seed-version`, and propagate
to app **and** web. → `../alquran-data/TRANSLATIONS-ROADMAP.md`.

Until then, do not flip either flag.

### Required mobile artifact

The JSON files in this repo are the authoring source, not the final mobile
artifact. Before Roman Urdu can ship in Al Quran mobile, the release must produce
a SQLite DB that the app can bundle.

Minimum expected path:

1. Add an `alquran-data` importer for `data/roman-urdu/surah-*.json`.
2. Insert the text as a new resource, not the rejected third-party slug:
   `ur-roman-abu-rayyan` or another Al Marfa-owned slug.
3. Mark it as `resources.type = 'transliteration'`.
4. Rebuild `quran.db`.
5. Run the app seed/version step so the mobile app sees the new DB as an update.
6. Update app/web flags to point at the Al Marfa resource only after the DB and
   web data both contain the same approved/release-ready text.

Do not overwrite or reuse `ur-roman-junagarhi-experimental`; it is useful as a
rejected comparison source, not as the shipping resource.

---

## 8. How to review

Phase 5 (`docs/PHASE-5-REVIEW-DESIGN.md`) is the per-verse approval tool. One
review ledger per surah lives at `data/roman-urdu/review/surah-NNN.tsv`
(`ayah, status, sha256, reviewer, date, note`), already bootstrapped for all
114 surahs with every row `pending`. Review happens on the Mac, in a desktop
browser (owner ruling P6, 2026-09-25) — no iPad/LAN step.

```bash
# 1. Generate the review page for a surah
python3 scripts/review_sheet.py --surah 1
# writes out/review/surah-001.html — Urdu (large, RTL) and Roman (large) per
# verse, lint + fidelity-findings chips, Approve / Needs fix controls.

# 2. Open it in a desktop browser and review, verse by verse
open out/review/surah-001.html

# 3. On the page: Approve, or Needs fix (a corrected Roman text is optional,
#    a note is required). Decisions are kept on the page and mirrored to
#    localStorage as a reload safety net only — never the record of truth.
#    Click "Download patch" when done; it saves surah-001-patch.tsv.

# 4. Apply the downloaded patch — dry run first, then for real
python3 scripts/apply_review.py --patch ~/Downloads/surah-001-patch.tsv --reviewer "Abu Rayyan" --dry-run
python3 scripts/apply_review.py --patch ~/Downloads/surah-001-patch.tsv --reviewer "Abu Rayyan"
```

`apply_review.py` hash-checks every row against the text it was shown
(`seen_sha256`); a stale row (the text changed since the page was generated)
is refused, never force-applied, and the run exits non-zero. A `needs-fix`
row with corrected text is applied as one exact, hash-checked single-verse
edit and the ledger row resets to `pending` (P5: reviewer/date cleared, the
note carries the history) — it needs a fresh read-aloud approval next
session, like any other pending verse. On success it also rewrites the
surah's file-level `status` (never `ayahs`) per the derivation in
`docs/PHASE-5-REVIEW-DESIGN.md` §3.

`python3 scripts/status.py` reports review counts (`pending`/`reviewed`/
`approved`) alongside the existing file-status block; `--write-status`
recomputes and rewrites file-level `status` for every surah without being
asked through `apply_review.py`.

Lint check 2f (`scripts/lint_roman_urdu.py`) is the backstop: any
`reviewed`/`approved` row whose stored hash no longer matches the current
text is an `error` finding, so a stale approval can't silently ship even if
a text writer forgets to reset the ledger row itself.

Each verse also shows an AI pre-check (owner decision 2026-09-25, from
`data/roman-urdu/prereview/surah-NNN.tsv`) in its own labelled block —
"looks right" / "concern — ... → suggested: ..." / "out of date" —
visually distinct from the lint/fidelity chips and never auto-approving.

### Reviewing in Markdown

The owner prefers reviewing in a Markdown file in VS Code over the HTML
page. `scripts/review_md.py` is a second front-end onto the exact same
data `review_sheet.py` assembles (`build_review_data_for_surah` — Urdu from
the Junagarhi sqlite, lint findings, fidelity rows, ledger state, AI
pre-review verdicts); it changes only how that data is presented and how a
decision comes back, never who's allowed to write it.

```bash
# 1. Generate the Markdown review file for a surah (or --all for every surah)
python3 scripts/review_md.py export --surah 1
# writes out/review-md/surah-001.md — CONCERN/out-of-date verses first
# under "## Needs your eyes", then the rest under "## Looks right to the
# AI", then already-approved verses listed compactly (no controls) under
# "## Already approved".

# 2. Open it in VS Code and review, verse by verse. Per verse:
#      [x] approve                      -- check the box, leave fix: empty
#      leave the box unchecked and
#      write the whole corrected verse
#      after `fix:`                     -- needs a fix; note: is encouraged
#      leave both blank                 -- skip for now, untouched
#    AI verdicts are suggestions; approval is yours.

# 3. Parse the edited file into the same patch format apply_review.py
#    expects -- ayah, decision, corrected_text, note, seen_sha256
python3 scripts/review_md.py import out/review-md/surah-001.md
# writes out/review-md/surah-001-patch.tsv and prints a summary:
# approve N, needs-fix N, untouched N.

# 4. Apply exactly as in the HTML flow -- review_md.py never writes the
#    ledger or the text itself; apply_review.py stays the single writer.
python3 scripts/apply_review.py --patch out/review-md/surah-001-patch.tsv --reviewer "Abu Rayyan" --dry-run
python3 scripts/apply_review.py --patch out/review-md/surah-001-patch.tsv --reviewer "Abu Rayyan"
```

Each verse block carries an HTML comment, `<!-- sha256:... -->`, hashing
the exact Roman text shown — the same `seen_sha256` staleness check as the
HTML page's downloaded patch. Editing that comment or deleting it makes the
verse block unparseable (`import` raises rather than silently dropping the
row); checking `[x] approve` while also writing a `fix:` is rejected the
same way, since the two are contradictory decisions for one verse.

`scripts/canonical_review_md.py` is the equivalent for the `canonical.tsv`
spelling-review batches (`out/canonical-review/batch-NN.tsv`, §6 of
`docs/PHASE-5-REVIEW-DESIGN.md`): `export --batch NN` writes
`out/canonical-review/batch-NN.md`, one row per candidate spelling change,
with a blank `decision` column — leave it blank to accept the proposed
spelling, write `keep` to keep the current one, or write any other spelling
to use that instead. `import FILE` prints the decisions as a TSV
(`variant, final, status`); it never writes `canonical.tsv` itself, same
single-writer discipline as everywhere else in this workflow.
