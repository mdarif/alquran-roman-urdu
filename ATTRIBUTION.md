# ATTRIBUTION.md

**Status: source text CLEARED. Release gated on review, not on licensing.**

The **source text is public domain** (Junagarhi, d. 1941 — see below), settled by
the owner on 2026-07-27. That removes what was the primary blocker: derivative
works need no permission, so Roman Urdu and Devanagari output are both permitted,
and no verbatim-only clause applies.

That clearance is about permission to *make* the derivative, not about who
owns the *rendering* we produce. The Quran Roman Urdu text this repo produces
(`data/roman-urdu/`) is itself asserted **proprietary, all rights reserved**
— see "Outputs" below and `LICENSE` — because it is still `beta-unverified`
and unreviewed end to end.

What still gates a release, in order:

1. **Review completeness — the real gate.** `AGENTS.md` §4.2 is unchanged:
   nothing ships unreviewed. `data/lexicon/` is currently empty and every
   `out/review_queue.tsv` row is `pending`, so there is nothing shippable yet
   regardless of licensing.
2. **Dakshina's CC BY-SA 4.0 share-alike**, which propagates into the lexicon.
   Resolved and accepted per ADR 0001, but it dictates how `data/lexicon/` is
   published — it is not a blocker, it is a constraint.
3. **Two `UNVERIFIED` rows below — CLE Lahore/PronouncUR and Roman-Urdu-Parl.**
   Both are **prospective and currently unused**: no suggester exists and neither
   has been ingested. They block only at the moment something actually consumes
   them. Clear them before that, not before release.

`"UNVERIFIED"` is an honest state for a source we have not used. Shipping output
derived from one while it still reads that way is not.

---

## Sources

### Tanzil `ur.junagarhi` — Urdu translation, Maulana Muhammad Junagarhi

- **Role:** the source text. Everything else is derived from it.
- **Licence:** **PUBLIC DOMAIN — RESOLVED** (owner determination, 2026-07-27).
- **Basis:** Junagarhi died in **1941**. India and Pakistan both apply
  life-plus-sixty, putting the translation in the public domain around **2001**;
  life-plus-seventy jurisdictions clear it by **2011**. The text is also
  distributed openly and at scale as an Islamic educational work — Quran.com,
  Tanzil, Islam360 and others carry it with no licensing step.
- **On Tanzil's terms:** Tanzil is a *redistributor* of this translation, not a
  rights holder. Their non-commercial-with-attribution request attaches to their
  distribution and cannot bind a public-domain work. We credit them for the
  digital copy as a courtesy, not an obligation. (Their permission notice about
  verbatim copying governs the **Arabic** text, which is a separate path and
  never touches this engine — → `AGENTS.md` §4.5.)
- **Consequence — this repo is unblocked.** A derivative of a public-domain text
  needs nobody's permission, so **transliteration is permitted**: neither Roman
  Urdu nor Devanagari is constrained by a verbatim-only clause, and neither
  requires clearance before shipping. Full determination and reasoning:
  `../alquran-data/ATTRIBUTION.md` §2.
- **Residual, recorded not resolved:** the text carries parenthetical glosses in
  **1,479 verses** (e.g. 1:4 `بدلے کے دن (یعنی قیامت) کا مالک ہے۔`). These are a
  hallmark of Junagarhi's own translation and are public domain with it. A
  publisher (Darussalam) could in principle claim rights over a specific
  *edition's* apparatus — typesetting, orthographic normalisation — separate
  from the translation. Assessed as thin against a text mirrored this widely,
  and **not a blocker**. Revisit only if a publisher raises it.
- **Owner:** determined by repo owner, 2026-07-27.

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

### `data/roman-urdu/` — the Quran Roman Urdu transliteration text

- **Licence: PROPRIETARY — all rights reserved.** © Al Marfa Technologies
  (transliterator: Abu Rayyan / Mohammad Arif). See `LICENSE` at repo root.
  **Not CC BY-SA** — do not reuse the CC BY-SA line below for this text; that
  licence covers only `data/lexicon/`, a separate, unrelated artifact in this
  repo (a word-level romanization reference bootstrapped from Dakshina), not
  the Quran transliteration itself.
- **Underlying words:** the Junagarhi Urdu translation, public domain (see
  above) — nobody, including us, can restrict those. The transliteration
  itself (vowelization choices, house style per ADR 0004, izafat/homograph
  judgment calls) is original creative and editorial labor, not a mechanical
  1:1 transcription, and is claimed as Al Marfa Technologies' own protectable
  expression — same position `../alquran-data/ATTRIBUTION.md` §"Roman Urdu"
  and `../alquran-data/LICENSE` already take once this text is ingested there
  (`resources.slug = ur-roman-abu-rayyan`).
- **Why proprietary while `beta-unverified`:** every verse here is unreviewed
  (§ "Status" in README.md). Keeping it closed while it's in this state avoids
  an unreviewed, potentially-erroneous rendering circulating as if it were a
  finished, citable text. Revisit the licence once review clears it — see
  `LICENSE` for the standing offer to reconsider.

### Pipeline code (`scripts/`)

- **Licence:** _to decide._ Not a derivative of the lexicon data. Keeping it
  separately licensed is the reason this repo exists apart from `alquran-data`.

---

## Required in any published output

Roman Urdu text is a derivative of a specific Urdu translation and must be
rendered as such — never presented as "the Quran says". Minimum attribution
(matches `config/sources.yaml`'s `author`/`license` fields in `alquran-data`
and `al-quran-web/scripts/export-quran.mjs`'s overlay verbatim):

> Muhammad Junagarhi; transliterated by Abu Rayyan. Junagarhi translation is
> public domain. Transliteration © Abu Rayyan. Not a translation of the
> Quran — unreviewed beta text.

Do not attach the CC BY-SA 4.0 notice above to this text — that notice is for
`data/lexicon/` only. Unreviewed entries must be visibly marked or hidden
entirely.

Unreviewed entries must be visibly marked or hidden entirely.
