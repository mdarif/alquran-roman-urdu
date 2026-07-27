# ADR 0003 — Devanagari as a first-class render target

- **Status:** Proposed
- **Date:** 2026-07-27
- **Scope:** `alquran-roman-urdu` lexicon + renderer; consumed by `alquran-data`
- **Supersedes:** nothing. Extends ADR 0001 §2 (route through phonemes)

## Context

`alquran-data` needs a Hindi-script Quran for readers who cannot read Nastaliq.
The obvious route is a real Hindi translation, but the search for one came up
short: QUL, quran.com, QuranEnc and Tanzil between them carry exactly three
Hindi translators (Azizul Haque al-Umari, Muhammad Farooq Khan/Ahmed, Suhel
Farooq Khan/Nadwi). The owner asked for a specific Salafi/Ahle Hadith Hindi
translation by Mohammad Rais Qureshi; no such edition is findable in any digital
source, in Latin, Devanagari or Arabic search.

The alternative: render the **Junagarhi Urdu** into Devanagari. Junagarhi is
already the Ahle Hadith Urdu translation and already ships in `alquran-data`, so
a Devanagari rendering delivers a Salafi-creed Quran in a script Hindi readers
can read, from a text already cleared and bundled.

The owner supplied the target register (1:1):

| | |
|---|---|
| Urdu | شروع کرتا ہوں اللہ تعالیٰ کے نام سے جو بڑا مہربان نہایت رحم والا ہے۔ |
| Roman | Shuroo karta hoon Allah ta'ala ke naam se jo bada meharban nihayat reham wala hai. |
| Devanagari | शुरू करता हूँ अल्लाह ताअला के नाम से जो बड़ा मेहरबान निहायत रहम वाला है। |

Two things are decided by that example rather than by argument.

**It is a transliteration, not a translation.** Every content word survives
unchanged: अल्लाह ताअला, मेहरबान, निहायत, रहम, वाला. Only the script moves. The
output is Urdu-in-Devanagari — a reader who knows only Sanskritised Hindi will
pronounce every word and not know several of them. For the intended audience
(Hindustani speakers who cannot read Nastaliq) that is correct and arguably
better than a formal Hindi translation. It is not a substitute for one.

**The Devanagari was not derived from the Roman.** "Shuroo" → शुरू, not शुरूऊ;
"reham" → रहम. Both were rendered from the sound, discarding Roman's spelling
artifacts. Going Roman → Devanagari would inherit exactly the losses Roman
already took.

## Decision

**1. Devanagari is a sibling renderer off the phonemic store, not a stage after
Roman.**

```
Urdu script --[HARD, ambiguous, human review]--> phonemes --+--> Roman
                                                            +--> Devanagari
```

ADR 0001 §2 already committed to one canonical internal phonemic form for
house-style reasons. Devanagari is the second consumer of that decision and is
close to free once the lexicon is reviewed. The expensive step — vowelization —
is shared, not duplicated.

**2. The phonemic inventory must preserve every distinction Devanagari can
render, even where popular Roman collapses it.**

This is the load-bearing clause and the reason the ADR is filed *before* review
starts rather than after. Devanagari is an Indic script and fits Urdu phonology
far better than Latin does:

| Urdu | Devanagari | What popular Roman does |
|---|---|---|
| `ٹ ڈ ڑ` retroflex | `ट ड ड़` | collapses into dental t/d/r |
| `بھ کھ` aspirates | `भ ख` | ambiguous digraphs |
| `ں` noon ghunna | `ँ` | usually dropped |
| `ق خ غ ز ژ ف` | `क़ ख़ ग़ ज़ झ़ फ़` (nukta) | no convention |

The owner's own example demonstrates this live. `بڑا` is `ب` + **`ڑ` U+0691
RREH** + `ا`. The supplied Roman "bada" has lost the retroflex and is now
indistinguishable from `بدا`; the supplied Devanagari बड़ा keeps it. Likewise
`ہوں` → हूँ uses chandrabindu for the noon ghunna, which "hoon" cannot express.

So: **a reviewer may never record a phoneme at popular-Roman granularity.** If
the phonemic store collapses retroflex into dental because the Roman house style
was going to collapse it anyway, Devanagari cannot be recovered without
re-annotating the corpus. Cheap to require now, expensive to retrofit.

**3. Devanagari does not lower the review bar.** All of §4 in `AGENTS.md`
applies unchanged — no model decides a vowel, nothing ships unreviewed, output
is content-hashed. `کرتا` is `ک ر ت ا` with no vowels: **karta** (does) and
**kurta** (the garment) are the same bytes, and Devanagari must commit to करता
or कुर्ता exactly as Roman must commit. The ambiguity is in the script, not in
the target.

**4. Ship it typed as a transliteration.** In `alquran-data` this is
`resources.type = "transliteration"` with `language_code: hi`, never a third
Hindi `translation` row. Per `AGENTS.md` §4.7 the translator is credited and the
text is never presented as "the Quran says". A script conversion is a derivative
work of Junagarhi, in the same category as the Khuda→Allah adaptation already
recorded in `alquran-data/ATTRIBUTION.md` — and the Junagarhi licence is still
**UNVERIFIED** in this repo's `ATTRIBUTION.md`. That gate is unchanged and
unmet.

## Consequences

- The lexicon schema needs its phonemic field specified at the finer
  granularity before the first reviewed entry lands. Any entry approved at
  Roman granularity is a future re-annotation.
- Devanagari output needs its own gold set and its own approval status. Sharing
  a phonemic form does not mean sharing an approval — the rendering rules can be
  wrong independently.
- House style (ADR 0002, pending) now has two orthographies to fix, not one.
  Devanagari has real choices to make: nukta consistency (क़ vs क — Hindi
  typography frequently drops nuktas), chandrabindu vs anusvara, and whether
  `ع` surfaces as अ (as in the owner's ताअला) or is dropped.
- This does **not** close the Hindi-translation gap in `alquran-data`. al-Umari
  remains the actual Salafi Hindi *translation*, is already downloaded, and is
  permissively licensed via QuranEnc. The two are complements.

## Open questions

1. Nukta policy. Preserving `क़ ख़ ग़ ज़ फ़` is more faithful; dropping them is
   more conventional Hindi. The owner's example has no nukta-bearing word, so it
   does not settle this.
2. Whether the Devanagari gold set can reuse the Roman gold verses or needs an
   independent selection.
3. Whether `ہ` word-final (e.g. `مہربان` → मेहरबान) needs a schwa rule distinct
   from Roman's.
