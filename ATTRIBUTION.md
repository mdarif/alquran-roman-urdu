# ATTRIBUTION.md

**Status: NOT CLEAR FOR RELEASE.**

Nothing in this repo may be published, shipped, or bundled into `alquran-app`
until every row below reads a resolved licence. `"UNVERIFIED — clear before
release"` is an honest state to be in. Shipping while still in it is not.

---

## Sources

### Tanzil `ur.junagarhi` — Urdu translation, Maulana Muhammad Junagarhi

- **Role:** the source text. Everything else is derived from it.
- **Licence:** `UNVERIFIED — clear before release`
- **What we know:** Junagarhi died in 1941. Pakistan and India both apply
  life-plus-sixty, so the **translation text itself** is very likely public
  domain. Tanzil's own permission notice covers verbatim copying of the *Quran
  text* and forbids modification — that governs the Arabic, not the translation.
- **What is open:** the Tanzil file derives from a published edition
  (Darussalam). A publisher may assert rights over typesetting, orthographic
  normalisation, or editorial apparatus — including the parenthetical glosses
  in the text — separate from the translation itself.
- **Action:** written enquiry to Tanzil regarding the provenance of their file,
  and to Darussalam regarding any claim over the edition. Start now; this has
  latency and will otherwise surface at ship time.
- **Owner:** _unassigned_

### Dakshina v1.0 — Google Research

- **Role:** bootstrap candidates and validation reference for the lexicon.
- **Licence:** **CC BY-SA 4.0** — resolved, but consequential.
- **Consequence:** share-alike propagates into any lexicon derived from it. Per
  ADR 0001 we accept this deliberately and publish `data/lexicon/` under
  CC BY-SA 4.0. This is why the lexicon lives in its own repo.
- **Attribution required:** Roark, Wolf-Sonkin, Kirov, Mielke, Johny,
  Demirşahin & Hall (2020), *Processing South Asian Languages Written in the
  Latin Script: the Dakshina Dataset*, LREC.
- **Note:** upstream repo archived by Google, April 2026. Vendored locally.

### Eliasi Roman-script Quran (print)

- **Role:** **adjudication reference only.** Consulted when reviewers disagree
  on a vowelization.
- **Licence:** copyrighted, in print.
- **Hard rule:** do not ingest, do not transcribe wholesale, do not treat as a
  corpus. Consulting a reference to settle a disagreement is not copying it.

### CLE Lahore lexicon / PronouncUR

- **Role:** phonemic transcription supporting the vowelization step.
- **Licence:** `UNVERIFIED` — terms differ per resource, check each individually
  before any use beyond reading the papers.

### Roman-Urdu-Parl

- **Role:** potential training signal for suggester models only.
- **Licence:** `UNVERIFIED`
- **Note:** substantially machine-generated. Never a reference regardless of
  licence outcome.

---

## Outputs

### `data/lexicon/`

- **Licence:** CC BY-SA 4.0 (inherited from Dakshina, accepted per ADR 0001).
- This is the deliverable. It ships with its own LICENSE file.

### Pipeline code (`scripts/`)

- **Licence:** _to decide._ Not a derivative of the lexicon data. Keeping it
  separately licensed is the reason this repo exists apart from `alquran-data`.

---

## Required in any published output

Roman Urdu text is a derivative of a specific Urdu translation and must be
rendered as such — never presented as "the Quran says". Minimum attribution:

> Roman Urdu transliteration of the Urdu translation by
> Maulana Muhammad Junagarhi. Transliteration by Al Marfa Technologies,
> CC BY-SA 4.0. Not a translation of the Quran.

Unreviewed entries must be visibly marked or hidden entirely.
