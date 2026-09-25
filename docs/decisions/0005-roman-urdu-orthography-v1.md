# ADR 0005 — Roman Urdu orthography v1

- **Status:** ACCEPTED 2026-09-25 by the owner (Abu Rayyan). No open
  points (R4's nested and dual cases were ruled the same day,
  `docs/OPEN-QUESTIONS.md` Q1/Q2).
- **Date:** 2026-09-24
- **Scope:** `data/roman-urdu/`
- **Supersedes:** ADR 0004 wherever the two conflict (ayn apostrophes,
  `nahin`, honorific spelling). Everything else in ADR 0004 stays in force.
- **Companion data:** `data/roman-urdu/canonical.tsv`

## Context

The corpus was drafted in batches, and each batch settled open spelling
questions its own way. Examples: `ta'ala` appears only in surahs 4–6;
`unhe` in s2–9 but `unhen` in s11–18; `farmaya` and `farmaaya` both appear
inside the same surah. About 800 word "skeletons" have more than one spelling.
The root cause was that nobody had decided whether to double long vowels.
See the plan's §1.2 B.

## Decision — the owner's rules

**R1 — Long vowels are written double** (`aa`, `ee`, `oo`), following the
corpus's dominant style: `kitaab`, `aap`, `raah`, `yaqeenan`, `zameen`.
Scope, as clarified by the owner: this applies to content words, above all
loanwords, and to any word the corpus currently spells both ways. Everyday
short forms keep their established spelling (`wala`, `ya`, `ja`, `bhai`,
`par`, `tak`). Homographs are never merged, because doubling changes the word:
`par/paar`, `pas/paas`, `kam/kaam`, `ghar/ghaar`, `mar/maar`, `den/deen`,
`hon/hoon`, `chand/chaand`, `amal/aamaal`, `hazrat/hazraat`,
`nikal/nikaal`, `utar/utaar`. Those are listed as `keep` in `canonical.tsv`.
Majhool vowels are not "long vowels" for this rule and stay single: `log`,
`mein`, `hai`, `koh`. A doubling applied blindly to every و/ی would be wrong.

**R2 — Negation and nasal endings.**
- The negative particle is always `nahi`.
- **Plural nouns take `-ein`, reaffirmed by the owner 2026-09-26:** `baatein`,
  `aayatein`, `cheezein`, `auratein` (114 words, 552 uses respelled from
  `-en`). Verbs keep `-en` (Q26). Homographs are decided per verse:
  `jaanein` "lives" vs `na jaanen` "may not know" (16:70); `kuwein` "wells"
  (22:45) vs `kuwen walon` "of the well" (25:38).
- Oblique plural pronouns: `unhein`, `tumhein`, `hamein`, `inhein`, and the
  relative `jinhein` (owner, Q16, 2026-09-25).
- Nasalised plurals take `-ein` / `-on` (`mushkein`, `koonchein`, `logon`).
- Recorded dissent: `nahi` drops the noon ghunna, and the rejected
  third-party edition was criticised for exactly that (`hai` for ہیں). The
  owner chose it deliberately: it is the dominant popular spelling, and it is
  simpler to search. `hain` for ہیں is **not** affected.
- **Ruling (2026-09-25):** nasal verb forms (`karen`, `den`, `len`, `rahen`)
  stay single-vowel and never change to `-ein`. This keeps them from
  colliding with important content words such as `deen`.

**R3 — `kuch`, never `kuchh`.** This keeps string search simple. It is a
deliberate exception to the aspiration principle in gotchas §2. It is limited
to this one word, and it does not permit dropping `h` from other aspirates.

**R4 — Honorifics are always bracketed, capitalised and hyphenated:**
- `(Alaihis-Salaam)`, plural `(Alaihimus-Salaam)`, after a Prophet's or
  Angel's name, whether or not the Urdu brackets it.
- The Prophet ﷺ: `(Sallallahu Alaihi Wasallam)`, with spaces and no hyphens
  (owner, 2026-09-24).
- Variants in the corpus today: `(alaihis salaam)` 259, `(alaihimas-salaam)` 8,
  `(alaihimus salaam)` 7, `(alaihim salaam)` 2, `(alaiha salaam)` 1, and five
  spellings of the Prophet's honorific. All of them converge.
- Correction (2026-09-25): an earlier draft said 18 honorifics had broken
  brackets. That was a counting error. Those honorifics sit inside a longer
  bracketed gloss by the translator, for example `(Yaqoob alaihis salaam ne)`
  at 12:83.
- **Ruling (2026-09-25, Q2):** inside a longer gloss, the honorific is
  capitalised and hyphenated but gets no brackets of its own:
  `(Yaqoob Alaihis-Salaam ne)`, `(Nabi Sallallahu Alaihi Wasallam)`.
- **Ruling (2026-09-25, Q1):** the dual (علیہما السلام) is
  `(Alaihimas-Salaam)`. It is distinct from the plural `(Alaihimus-Salaam)`,
  and the Urdu decides which applies.
- **Ruling (2026-09-25):** the feminine honorific for Maryam is always
  `(Alaihas-Salaam)`, in brackets, capitalised and hyphenated like the others.

**R5 — No apostrophes or special marks inside words.** Drop the ayn and hamza
apostrophes and tanween marks: `wusat`, `qatan`, `nemat`, `inaam`,
`shafaat`, `Taala`. The reason is search. The app's SQLite FTS tokeniser
treats `'` as a word break, so `ne'mat` would be indexed as `ne` + `mat`.
Hyphens stay: izafat `-e-`, compounds `-o-`, and R4 all depend on them.
When dropping an apostrophe leaves three vowels in a row, reduce them to two
(`itaa'at` → `itaat`). A result that is short or ambiguous is left for the
owner to decide.
**Ruling (2026-09-25):** `saa'at` (hour) is written `saa-at`. Plain `saat`
would clash with "seven", and `saahat` would add an `h` sound that ساعت
doesn't have. The hyphen is allowed under this rule.

**R6 — Word-level rulings from the Phase 4 sweep (owner, 2026-09-25):**
- Future verbs are written joined: `jaaoge`, `kardega`, `bhejoonga`, never
  `jaao ge`. Enforced by lint 2j, and applied by `apply_canonical.py --join-futures` (Q17).
- `معبود برحق` is `mabood bar-haq`, with no izafat. This amends ADR 0004's
  compound list (Q14).
- `آڑ` (barrier) is `aar`, so it never collides with the people of ʿĀd (`Aad`) (Q13).
- `قرآن باحکمت` at 36:2 stays `Quran-e-Hakeem` by owner choice (Q12). This is
  a deliberate exception to transliterating Junagarhi's exact word.
- `مثل X کے` is `misl X ke`, never `misl-e-X ke`. Enforced by lint 2k and
  applied by `apply_canonical.py --misl` (Q19, following Q6 at 70:8).
- `Rabb`, never `Rab` (Q20; ADR 0004's canonical term).
- The past-tense verb دیں ("gave") is `dein` where `din` would read as
  "day" (45:17, Q21).
- ساٹھ (sixty) stays `saath`, even though it is spelled like "with"; context
  decides (58:4, Q22).
- **Round 4 (2026-09-25).** دیں is written by tense: past tense `dein`
  (including helper verbs: `kar dein`, `bana dein`), subjunctive or
  imperative `den` (Q25). Verbs never take `-ein`: `chaahen`, `len`,
  `karen`. Only plural nouns and the R2 pronouns take `-ein` (Q26). وہی is
  `wohi` and وحی is `wahi` (Q27). Past-tense کیں/لیں is `keen`/`leen`;
  کن "which" stays `kin` (Q28). A verse starts with a capital letter,
  enforced by lint 2l (Q29).

**R5 exception (owner, 2026-09-26):** تائید is `taa'eed`, kept with its
apostrophe. It is the one deliberate exception to R5, locked in canonical.tsv
(the variants taeed/taaeed/taayeed are rewritten to it, and `taa'eed` itself is
`keep`) and guarded by tests/test_canonical_locks.py.

**Precedence:** where R1 and R2/R3 conflict, R2/R3 win, because they are
explicit word-level rulings.

## `canonical.tsv`

Columns: `variant, canonical, count_2026_09_24, status, note`. Whole-word,
case-preserving replacement. Status values:

- `decided` — follows directly from R2, R3 or R5. Can be applied as soon as
  this ADR is accepted. 33 rows, 2,234 tokens.
- `keep` — a homograph or an everyday form. Never rewritten. 46 rows.
- `needs-review` — 792 rows, about 3,900 tokens. Most are R1 candidates
  generated from corpus clusters: the doubled form wins if it appears 3 or
  more times or makes up at least 15% of its cluster, so one-off typos don't
  win. Also here are the risky R5 results. **The machine produced these rows,
  so they are suggestions (AGENTS.md non-negotiable 1).** Each one needs a
  human reading. The main danger is transitive/intransitive verb pairs and
  singular/plural pairs that only look like spelling variants. The owner
  flips a row to `decided` or `keep`. An agent may triage the rows but must
  not flip them.

Generator (kept for provenance; a one-off, not a pipeline step):
`out/seed_canonical.py` and `out/load.py`.

## Consequences

- About 6,000 tokens change, mostly from `nahin`→`nahi`, `ta'ala`→`Taala`,
  `kuchh`→`kuch`, the pronoun forms, and the R1 clusters. Surah 2, the hand
  exemplar, changes too. That is intended.
- Search improves: no apostrophes, and one spelling per word.
- Every rule is enforced by lint (plan Phase 2, checks 2a/2g/2h), so drift
  can't come back one batch at a time.
- ADR 0004's ayn list (`in'aam`, `ne'mat`, `sha'oor`, `shafaa'at`) is
  superseded by R5.

## Sign-off

- [x] Owner (Abu Rayyan) — accepted on 2026-09-25.
