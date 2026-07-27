# ADR 0002 — House style for Roman Urdu and Devanagari output

- **Status:** Proposed — rulings 1–4 need the owner's sign-off before bulk review
- **Date:** 2026-07-27
- **Scope:** `alquran-roman-urdu` — the phonemic store and both renderers
- **Referenced by:** ADR 0001 §2 (one phonemic form, many renderings), ADR 0003
  (Devanagari as a first-class target)

## Why this exists, and why now

ADR 0001 committed to storing **one canonical phonemic form** and rendering each
orthography from it. That makes house style a *rendering* concern rather than an
annotation one — but only for choices the phonemic form can express. Anything
the phonemic form has to *encode* must be settled before review starts, or the
corpus gets annotated twice.

The al-Fatiha pilot (2026-07-27) surfaced four such choices. All four recur
thousands of times, and none is resolvable by instinct per-entry. Without a
ruling, 6,787 forms become 6,787 aesthetic judgements and the output is
inconsistent by construction.

**Sequencing:** ruling 4 blocks bulk review outright (→ ADR 0003, "Word
boundaries"). Rulings 1–3 are recoverable later if the phonemic store stays
maximally faithful, which ruling 1 is designed to guarantee.

---

## Ruling 1 — Nukta: PRESERVE in the store, decide at render

**The store always keeps the Perso-Arabic consonant distinct.** `q x G z zh f`
are separate phonemes from `k kh g j jh ph`, always, with no exceptions.

Rendering is then a switch:

| Policy | Output | For |
|---|---|---|
| `faithful` (default) | क़ ख़ ग़ ज़ फ़ | this project |
| `popular` | क ख ग ज फ | if reader testing ever demands it |

**Why store-then-decide.** Dropping a nukta is lossy and irreversible; keeping
one is not. If the store ever collapses `q` into `k`, recovering it means
re-annotating the corpus. → ADR 0003 §2.

**Scale.** Nukta-bearing letters appear in a large minority of the corpus:

| Letter | Phoneme | Types | Tokens | % |
|---|---|---|---|---|
| ف | f | 374 | 4,136 | 2.21% |
| ق | q | 387 | 4,014 | 2.14% |
| ز | z | 333 | 3,473 | 1.85% |
| خ | x | 305 | 2,880 | 1.54% |
| غ | G | 135 | 842 | 0.45% |

**Note:** `ژ` (zh) has **zero** occurrences in this corpus. `झ़` is in the
inventory for completeness and should never appear in output.

**Caveat for Roman.** Popular Roman Urdu has no nukta convention at all, so the
Roman renderer collapses these regardless. That is a *Roman* limitation and must
never be allowed to justify collapsing the store. → ADR 0003 §2.

---

## Ruling 2 — Ain (ع): render the vowel it carries, not a letter

`ع` is a consonant in Arabic that Urdu speakers do not pronounce as one. Hindi
has no letter for it, so every rendering is a choice about the *vowel*.

**Rule, in order:**

| Position | Treatment | Example |
|---|---|---|
| Word-initial | render as the independent vowel | عبادت → **इबादत**, عمل → **अमल** |
| Between vowels, lengthening | absorb into the long vowel | تعریف → **तारीफ़**, یعنی → **यानी** |
| Between vowels, syllable break | independent vowel via `'` | تعالیٰ → **ताअला** |
| Post-consonantal | silent | بعد → **बाद** |

**The pilot got this inconsistent, which is what prompted the ruling.** تعریف
and یعنی absorbed the ain (तारीफ़, यानी) while انعام kept it (इनआम). Under this
rule **انعام is इनाम**, matching conventional Hindi.

**Test:** write what a Hindi-reading Urdu speaker would write unprompted. تعریف
is तारीफ़ in every Hindi newspaper; it is not तअरीफ़.

**Scale:** 394 types / 6,168 tokens (3.29%), dominated by تعالیٰ (1,532).

**Consequence:** the `'` phoneme means *syllable break*, not "an ain is here."
Reviewers use it only when the vowel genuinely restarts.

---

## Ruling 3 — وه → वो

Junagarhi writes وه 2,287 times (plus 16 as وہ, which the normaliser folds).

**Ruling: वो, not वह.** Both are correct Hindi; वो is the spoken register and
matches the Perso-Arabic, conversational feel of Junagarhi's prose, which ADR
0003 identifies as the product. वह reads formal and Sanskritic-adjacent — the
register being rejected.

Same logic: یہ → **ये**.

**This is a preference, not a correctness issue** — the cheapest of the four to
reverse, since it is a pure render-time substitution.

---

## Ruling 4 — Pronoun + postposition: join, with an explicit exception list

**This one blocks bulk review.** → ADR 0003, "Word boundaries do not map 1:1".

Urdu writes pronoun and postposition apart; Hindi usually joins them. 9,099
tokens — **4.9% of the corpus**.

**Ruling: join, via an n-gram lexicon key**, for the closed set below.

| Urdu | Devanagari | Tokens |
|---|---|---|
| ان کے | उनके | 1,076 |
| ہم نے | हमने | 821 |
| اس کے | इसके / उसके | 645 |
| ان کی | उनकी | 393 |
| اس کی | इसकी | 357 |
| انہوں نے | उन्होंने | 314 |
| اس سے | इससे | 310 |
| ان سے | उनसे | 308 |
| ان میں | उनमें | 237 |
| اس میں | इसमें | 213 |
| اس کا | इसका | 210 |
| ان کو | उनको | 203 |
| اس نے | इसने | 202 |
| جنہوں نے | जिन्होंने | 85 |
| تو نے | तूने | — |

**Exceptions — do NOT join:**

- **`میں سے` → में से.** Here میں is the postposition "in", not the pronoun
  "main". 594 tokens, and the single most common false positive.
- **`جن` / `کس` + postposition** stay apart: जिन पर, किस पर. Relative and
  interrogative forms do not contract the way demonstratives do.
- **Pronoun + noun** never joins: `ان لوگوں` → उन लोगों, not उनलोगों.

**Why n-gram keys and not a rule.** `ان` before a postposition joins; the same
`ان` before a noun does not. Only context decides, and context is exactly what a
mechanical rule cannot see. Keying `"ان کی"` separately from `"ان"` records the
decision instead of re-deriving it. That is the same reasoning as
non-negotiable #1 applied to boundaries rather than vowels.

**Also settled here:** the split direction. Urdu glues verb particles Hindi
separates — `ہوگئے` → **हो गए**, `کردیا` → **कर दिया** (400 tokens / 76 types).
Use the `_` word-break phoneme. Beware `رضامندی` and `پابندی`, which merely end
in `دی` and are single words.

---

## Consequences

- Rulings 1 and 4 constrain the **phonemic store** and must be settled first.
  Rulings 2 and 3 are render-time and cheaper to revisit.
- `review.py` walks single surface forms and cannot propose an n-gram. The
  frequent pairs in ruling 4 must be **seeded as keys before bulk review**, or
  every join is missed and the corpus is reviewed twice.
- The Roman renderer needs its own answer to ruling 4 (*hum ne* or *humne*?).
  Shared machinery, potentially different style. → ADR 0003 open question 5.
- Nothing here relaxes review. A house style makes decisions *consistent*, not
  *automatic*; every entry still passes a human. → `AGENTS.md` §4.

## Open

- Ruling 2 leaves `ہ` word-final unsettled (مہربان → मेहरबान) — ADR 0003 open
  question 3.
- `اس` is इस or उस by context (this/that). Not a style question; per-entry, and
  a genuine ambiguity for reviewers.
