# AGENTS.md — alquran-roman-urdu

**Canonical.** This is the front door for any agent or human working in this
repo. If something here conflicts with a tool-specific file (`CLAUDE.md`,
`.cursor/rules`, a loaded skill), this file wins.

Al Marfa Technologies. Sibling to `alquran-data` → `alquran-app`. Follows the
memory pattern established in `hadith-data`.

---

## 1. What this is

An open, human-reviewed **Roman Urdu lexicon**, and the pipeline that applies it
to Quran translation text.

The framing that matters: **the lexicon is the deliverable.** As of July 2026 no
verified, machine-readable, openly licensed Roman Urdu Quran resource exists.
There are apps — 50k–100k+ installs — whose store reviews report zer/zabar/pesh
errors and ask for scholarly checking. There is one print edition (Eliasi),
copyrighted and undigitised. The gap is not that nobody has done it. The gap is
that **nobody has done it verifiably**, with attribution and a review record.

That gap is what we are closing. An app is downstream and optional.

### Why a separate repo

The lexicon is bootstrapped from Dakshina, which is CC BY-SA 4.0. Share-alike
propagates. Keeping this out of `alquran-data` means the question of whether
copyleft reaches the app's pipeline code never has to be argued. → ADR 0001

---

## 2. The core technical fact

**This is a diacritization problem wearing a transliteration costume.**

Urdu script marks consonants and long vowels; short vowels (zabar/zer/pesh) are
optional and normally absent. Roman Urdu requires them. So:

```
Urdu script  --[HARD, ambiguous, needs humans]-->  phonemes
phonemes     --[easy, deterministic]------------>  Roman
```

`کتب` is *kutub* or *kutab*. `بن` is *bin*, *ban*, *bun*, or *ban'na*. No
character mapping resolves these. A sequence model guesses plausibly and is
wrong often enough to matter.

**Consequences that follow directly:**

- Review effort concentrates entirely on the first arrow.
- We store one canonical **phonemic** form internally, and render Roman from it.
  Changing house style then becomes a config change, not a re-annotation.
- The corpus is closed (~9–14k unique surface forms for one translation), so
  exhaustive human review is tractable. This is the whole reason a lexicon-first
  approach beats a model-first one here and would not elsewhere.

---

## 3. Glossary

| Term | Meaning |
|---|---|
| **tashkeel / harakat** | Arabic-script diacritics. Unicode category `Mn`. Usually absent from Urdu text |
| **zabar / zer / pesh** | The three Urdu short vowels (a / i / u) |
| **diacritization / vowelization** | Restoring absent short vowels. The hard step |
| **do-chashmi he** | `ھ` U+06BE. Marks aspiration: bh, kh, th, ph. Phonemically distinct from `ہ` |
| **gol he** | `ہ` U+06C1. The ordinary /h/ |
| **noon ghunna** | `ں` U+06BA. Nasalisation, not a full /n/ |
| **izafat** | The `-e-` linker (*sahib-e-kitab*). Written as a diacritic or not at all |
| **retroflex** | `ٹ ڈ ڑ` — distinct from dental `ت د ر`. Roman Urdu conventionally collapses them; scholarly schemes don't |
| **surface form** | A token exactly as it appears in the text |
| **key** | A surface form after normalisation. What we look up on |
| **type / token** | Distinct forms / total occurrences. Type coverage is the honest metric |
| **attestation** | In Dakshina, how many annotators produced a given romanization |
| **house style** | Our fixed orthographic conventions. → ADR 0002, pending |
| **gold set** | Hand-annotated verses used as the regression contract. Not training data |

---

## 4. Non-negotiables

Each of these encodes a specific way of misleading someone about a religious
text. They are not preferences.

1. **Never let a model decide a vowel.** Neural, LLM, or heuristic output is a
   *suggestion* that enters the review queue. It is never shipped text. Not
   "provisionally", not "with a confidence score". Published SOTA sits at ~96
   Char-BLEU — roughly one wrong character in twenty-five. Acceptable for
   search indexing. Not for scripture.
2. **Nothing ships unreviewed.** Every entry carries
   `pending` / `reviewed` / `approved` and a reviewer. Anything not `approved`
   is hidden or explicitly marked as unverified.
3. **Approved output is content-hashed.** Regeneration diffs against the hash
   and forces re-approval. Otherwise a rule change silently rewrites scripture.
4. **A Dakshina match is a candidate, not an answer.** It is Wikipedia-domain
   crowd data. Where it disagrees with a reviewer, the reviewer wins.
5. **Never run the Arabic Quran text through this engine.** Separate path,
   established Arabic transliteration standards, no shared code, no shared
   normaliser.
6. **`license:` is required on every source.** `"UNVERIFIED — clear before
   release"` is an honest state to be in. Shipping while still in it is not.
7. **Attribute the translator, always.** Roman Urdu output is a derivative of a
   specific Urdu translation and is rendered as such — never as "the Quran says".

---

## 5. Sources

| Source | Role | Licence |
|---|---|---|
| Tanzil `ur.junagarhi` (6,236 verses) | The source text | **PUBLIC DOMAIN** — Junagarhi d. 1941 → ATTRIBUTION.md |
| Dakshina v1.0, `ur/lexicons` | Bootstrap candidates + validation reference | CC BY-SA 4.0 |
| CLE Lahore lexicon / PronouncUR | Phonemic transcription for the vowelization step | Per-source, check |
| Eliasi Roman-script Quran (print) | **Adjudication reference only** — consult on reviewer disagreement. Do not ingest, do not transcribe wholesale | Copyrighted |
| Roman-Urdu-Parl | Training signal for suggesters only. Substantially machine-generated | Check before use |
| `fawazahmed0/quran-api` `-la`/`-lad` | Auto-generated baseline to beat | Machine output |

Dakshina's GitHub repo was **archived by Google in April 2026**. It is vendored
under `data/vendor/`. Do not rely on the upstream URL persisting.

---

## 6. Layout

```
AGENTS.md                 this file — canonical
ATTRIBUTION.md            the licensing gate
README.md
CLAUDE.md                 tool-specific; defers to this file
docs/
  gotchas.md              landmines, append as found
  decisions/              ADRs
data/
  raw/                    ur.junagarhi.txt (gitignored, fetched by hand)
  vendor/                 dakshina (gitignored, large)
  lexicon/                THE DELIVERABLE — reviewed entries, committed
scripts/
  vocab_coverage.py       vocabulary extraction + Dakshina coverage
tests/
  normalization_vectors.json   the normaliser contract
out/                      generated, gitignored
```

`data/lexicon/` is the only data directory that is committed. It is the product.

---

## 7. Normalisation is a contract

`scripts/vocab_coverage.py` holds the reference normaliser and an inline vector
set. Rules:

- **Never change a vector to make a test pass.** If normalisation changes, that
  is an ADR, and every existing key must be migrated.
- **Extend vectors whenever a new fold is added.**
- If a second implementation ever exists (Dart, for the app), divergence fails
  **silently** — no error, every lookup just misses. `tests/normalization_vectors.json`
  is the contract between them. This exact failure has already bitten the
  hadith side.

Deliberately folded: Arabic yeh/alef-maksura → farsi yeh; Arabic kaf → keheh;
heh variants and teh marbuta → gol he; hamza-carrying alef → bare alef;
presentation-form ligatures via targeted NFKC; tashkeel stripped; joiners and
tatweel removed.

Deliberately **not** folded: **do-chashmi he `ھ`** and **alef madda `آ`**. Both
are phonemically distinct. Folding either produces a plausible-looking wrong
word rather than an error.

---

## 8. Workflow

**Current phase: measurement.** Nothing is annotated yet.

1. Run `scripts/vocab_coverage.py`. Read `out/report.txt`.
2. Decide house style — popular Roman Urdu (readable to a Karachi teenager) vs
   diacritic-marked scholarly. These are different products. The ambiguity
   figure in the report is the input to this call. **Must land before anyone
   annotates**; it cannot be retrofitted. → ADR 0002, to write.
3. Pilot: annotate the top 200 forms by frequency. Purpose is not progress — it
   is to time one entry and to surface where house style is underspecified.
4. Write ADR 0002 fixing house style, informed by the pilot.
5. Scale annotation, frequency-ordered.
6. Gold set: 300–500 verses hand-annotated, adjudicated against Eliasi where
   reviewers disagree. This is the regression contract, not training data.

---

## 9. Working preferences

- Consolidate terminal commands into single copy-paste blocks.
- Maximum heavy lifting by the agent; minimal manual steps for the maintainer.
- Present copy and schema changes for review before applying them unilaterally.
- Repos live under `~/code/` with short, clean names.

---

## 10. Memory

When you learn something that would have saved you time: append to
`docs/gotchas.md`, or add an ADR under `docs/decisions/`, **in the same change
as the work**. Not in a follow-up. Not in a tool-specific file. This repo is the
memory; anything outside it does not travel.
