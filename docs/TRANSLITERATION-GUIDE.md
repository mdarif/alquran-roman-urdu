# Roman Urdu — how to continue the transliteration

Written 2026-08-02 for an agent or reviewer picking this up cold. Read
`AGENTS.md` §1 and §4 first (non-negotiables), then this.

**The job:** extend `data/roman-urdu/` from **325 verses to 6,236**. 5,911 remain.

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
| Done | surahs **1**, **2** (all 286), **108–114** — 325 verses |
| Remaining | **5,911** verses, surahs 3–107 |
| Status of all existing files | `beta-unverified` — not reviewed, not approved |
| Consumers | Roman Urdu is **gated off** in app and web until this is ready |

### Provenance is NOT uniform — read this before treating the pilot as gold

The nine existing files carry three different `note` claims:

- **surah 2** — "Hand-transliterated in the popular register."
- **surah 1** — "A model produced these vowelizations."
- **surahs 108–114** — neither claim; house-style reference only.

So the pilot is a **good stylistic reference and a weak factual one**. Surah 2 is
the most trustworthy exemplar and the best model for new work. Do not silently
promote any of it to `approved` on the strength of it having existed for a while.

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

The edition appears as **`ur-roman-almarfa`**, labelled *Experimental*, off by
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

## 6. Suggested order of work

1. **Surah 3 onward in order**, or
2. **short high-traffic surahs first** — 36 (Yaseen), 55 (Ar-Rahman), 67 (Al-Mulk),
   18 (Al-Kahf) — which get read most and would let the flag flip on for a
   meaningful subset sooner.

Option 2 is worth considering because the consumers already handle partial
coverage: `al-quran-web` shipped a "coming soon" note for surahs with no Roman
Urdu yet (the `.rur-soon` rule still exists in `src/styles/global.css`).

**A vocabulary note:** the corpus is closed and repetitive — roughly 9–14k unique
surface forms across the whole translation. Per-verse effort drops sharply after
the first few surahs, so early progress is not a good predictor of total cost.

---

## 7. When it is ready to ship

Turning it back on is two one-line flips, both already wired:

- `alquran-app` — `FeatureFlags.romanUrdu = true`
  (`lib/core/feature_flags.dart`). The gate is applied in
  `translationResources()`, the single chokepoint for picker and reader.
- `al-quran-web` — remove/flip `'ur-roman-junagarhi-experimental'` in
  `EDITION_FLAGS` (`src/lib/editions.ts`).

But note **both flags currently point at the third-party text bundled in
`quran.db`**. Shipping *our* text additionally requires the pipeline step that
was never built: ingest `data/roman-urdu/` into `alquran-data` as a
`resources.type = 'transliteration'` row (its own slug, e.g.
`ur-roman-almarfa`), rebuild `quran.db`, run `make seed-version`, and propagate
to app **and** web. → `../alquran-data/TRANSLATIONS-ROADMAP.md`.

Until then, do not flip either flag.

### Required mobile artifact

The JSON files in this repo are the authoring source, not the final mobile
artifact. Before Roman Urdu can ship in Al Quran mobile, the release must produce
a SQLite DB that the app can bundle.

Minimum expected path:

1. Add an `alquran-data` importer for `data/roman-urdu/surah-*.json`.
2. Insert the text as a new resource, not the rejected third-party slug:
   `ur-roman-almarfa` or another Al Marfa-owned slug.
3. Mark it as `resources.type = 'transliteration'`.
4. Rebuild `quran.db`.
5. Run the app seed/version step so the mobile app sees the new DB as an update.
6. Update app/web flags to point at the Al Marfa resource only after the DB and
   web data both contain the same approved/release-ready text.

Do not overwrite or reuse `ur-roman-junagarhi-experimental`; it is useful as a
rejected comparison source, not as the shipping resource.
