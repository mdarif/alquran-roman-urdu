# ADR 0001 — Roman Urdu: source selection and licence posture

- **Status:** Proposed
- **Date:** 2026-07-18
- **Scope:** `alquran-data` Roman Urdu pipeline
- **Supersedes:** nothing
- **Renumber on merge** if the target repo already has ADRs in this range.

## Context

We want a Roman Urdu rendering of an Urdu Quran translation. The naive framing
— "transliterate Urdu script to Latin" — is wrong. Urdu script omits short
vowels; Roman Urdu requires them. The pipeline is therefore
**diacritization → romanization**, and diacritization is the ambiguous step.
`کتب` is *kutub* or *kutab*; only context decides.

Two further facts constrain the design.

**No gold source exists.** Surveyed July 2026:

| Source | What it is | Verdict |
|---|---|---|
| Dakshina (Google Research) | 25,000 Urdu word types + 2,500 dev / 2,500 test, each with human-attested romanizations and attestation counts; round-trip validated at 3.5–8.5% CER | Best available. Wikipedia domain. CC BY-SA 4.0. Repo **archived Apr 2026** — mirror it |
| Roman-Urdu-Parl | 6.37M sentence pairs, 0.186B words | Large but substantially machine-generated (ijunoon API). Training signal only, never reference |
| Rekhta ghazals | Hand-romanized poetry | Wrong register — archaic, poetic |
| CLE Lahore lexicon / PronouncUR | Urdu lexicons carrying POS, lemma, phonemic transcription | Right shape for the **vowelization** step |
| Eliasi Roman-script Quran | Print edition (Qari Faheemuddin Ahmed / M. A. H. Eliasi) | Nearest thing to scholarly gold. Paper only, copyrighted |
| Existing Roman Urdu apps | 50k–100k+ installs | No export. Store reviews report zer/zabar/pesh errors and ask for scholarly review |
| `fawazahmed0/quran-api` `-la` / `-lad` editions | Auto-generated Latin variants | Machine output. Baseline to beat, never truth |

**Published neural transliteration is not accurate enough.** The current
state of the art reports Char-BLEU ≈ 96 for Urdu→Roman-Urdu. That is roughly
one wrong character in twenty-five. Acceptable for search; not acceptable for
scripture.

## Decision

**1. Lexicon-first, not model-first.**
A Quran translation is a closed corpus (~9–14k unique surface forms for one
translation). That is human-reviewable. Any neural or LLM component is a
**suggester** whose output enters the review queue — never the shipped artifact.
This is the same rule as "never populate a scholarly ruling by inference": a
suggestion with a confidence score attached is still a fabrication if it ships.

**2. Route through phonemes, not directly to Latin.**
Urdu-script → phoneme is the hard, ambiguous step and is where review effort
goes. Phoneme → Latin is deterministic and cheap. One canonical internal
phonemic form renders to either popular Roman Urdu or diacritic-marked
scholarly Roman without re-review.

**3. Source Urdu text: Tanzil `ur.junagarhi`** (6,236 verses, added Apr 2011).
Junagarhi (d. 1941) is the cleanest copyright path and the edition Darussalam
circulates. Note Tanzil's permission notice covers verbatim copying of the
*Quran text* and forbids modification; translation rights are a **separate
unresolved question**. → `ATTRIBUTION.md`, blocking.

**4. Dakshina is a bootstrap and a validation reference, and we accept
CC BY-SA on the resulting lexicon.**
Share-alike propagates into anything derived from it. Rather than contort the
pipeline to avoid this, we publish the Roman Urdu lexicon openly under CC BY-SA
4.0. It is the artifact nobody else has built; publishing it is the point.
The *app* is not a derivative of the lexicon in the copyleft sense — the
lexicon ships as data with its own licence file.

**5. Eliasi is an adjudication reference, not a corpus.**
Acquire a print copy. Consult it when reviewers disagree on a vowelization.
Do not ingest, do not transcribe wholesale.

**6. Nothing ships unreviewed.**
Per-verse status `generated` / `reviewed` / `approved`. Content-hash each
approved verse; regeneration diffs against the hash and forces re-approval.
Anything not `approved` is hidden or explicitly marked — the same posture as
NULLing an unknown `hukm` rather than guessing it.

## Consequences

**Good**
- Review effort is bounded and frequency-prioritised: the top ~2,000 forms
  cover the large majority of tokens.
- The phoneme layer makes the popular/scholarly render a config choice rather
  than a second annotation pass.
- Publishing the lexicon creates a citable asset and an external correction
  channel.

**Bad / accepted**
- CC BY-SA on the lexicon. Accepted deliberately, see (4).
- Dakshina's Wikipedia domain means expected coverage of Quranic vocabulary is
  only ~40–60%. Religious register is exactly where it is thinnest.
- A print reference in the loop means adjudication is not automatable.
- Translation copyright is unresolved and blocks release.

**Open**
- Which Roman orthography is the shipping default — popular (readable to a
  Karachi teenager) or diacritic-marked. These are different products.
  Decide before the gold set is annotated, not after.
- Whether Junagarhi's parenthetical glosses are transliterated, dropped, or
  rendered distinctly.

## Known landmines

1. **The Tanzil Junagarhi text contains lam-alef presentation forms.** `واﻻ`
   ends in U+FEFB, not `ل` + `ا`. NFC does not decompose it; NFKC does.
   Vocabulary keyed on unnormalised text will silently split into two entries.
2. **Do-chashmi he `ھ` (U+06BE) is load-bearing** — it marks aspiration
   (`bh`, `kh`, `th`). Do not fold it into `ہ` during normalisation. Folding
   the *other* he forms is correct; folding this one destroys the word.
3. **Tashkeel are Unicode category `Mn`.** Same trap as FTS5 — anything
   treating `Mn` as a separator shatters vocalised words into single letters.
4. **Python↔Dart normaliser divergence fails silently.** If any of this runs
   client-side, the normalisation vectors file is the contract, exactly as on
   the hadith side.
5. **Never run the Arabic Quran text through the Urdu engine.** Separate path,
   established Arabic transliteration standards, no shared code.

## References

- Roark et al. (2020), *Processing South Asian Languages Written in the Latin
  Script: the Dakshina Dataset*, LREC. Data: CC BY-SA 4.0.
- Alam & Hussain (2022), *Roman-Urdu-Parl*, TALLIP 21(1).
- Butt, Varanasi & Neumann (2025), *Low-Resource Transliteration for Roman-Urdu
  and Urdu Using Transformer-Based Models*, LoResMT.
- *PronouncUR: An Urdu Pronunciation Lexicon Generator*, LREC 2018.
