# Roman Urdu → golden: analysis and execution plan

Written 2026-09-24. Audience: a coding agent (a cheaper model is fine for
most phases, see §6) executing this plan in `~/code/alquran-roman-urdu`, with
the owner (Abu Rayyan) as the only reviewer.

Read first, in order: `AGENTS.md` §1 and §4 (non-negotiables),
`docs/TRANSLITERATION-GUIDE.md`, `docs/decisions/0004-roman-urdu-working-style.md`,
`docs/gotchas.md`. This plan does not override any of them.

**"Golden" means:** every verse is `approved` by the owner, the approval is
pinned to a content hash, and the automated checks below pass with zero
unexplained findings. Only then does `alquran-data` drop `experimental: true`
for `ur-roman-abu-rayyan`.

---

## 1. Current state (measured 2026-09-24, not copied from other docs)

| | |
|---|---|
| Coverage | 6,236 / 6,236 verses, 114 files, `validate_roman_urdu.py` all `ok` |
| Status | 114 / 114 files `beta-unverified`; 0 reviewed, 0 approved |
| Provenance | s2 hand; s1 model-vowelized; s3–107 assistant-drafted; s108–114 unstated |
| Published | `alquran-data` `sources/translations/ur-roman-abu-rayyan-simple.db` = repo JSON byte-for-byte (0 differing verses); `al-quran-web/data/roman-urdu/` identical too |
| Tests | none for the Roman text. `validate_roman_urdu.py` is a script, not a test, and reads verse counts from `~/code/alquran-app/assets/db/quran.db` |

### 1.1 What is good

- No structural defects: no gaps, blanks, stray digits, non-ASCII characters.
- The Junagarhi footnote markers `(1)` are stripped everywhere.
- Word-count ratio Roman/Urdu has a median of 1.00, and most surahs sit between
  0.96 and 1.00. There is no sign of systematic re-translation or abridgement.
- Parity of unambiguous function words is high: `ہیں`↔`hain` mismatches in 4
  verses, `نہیں`↔`nahin|nahi` in 5, `اللہ`↔`Allah` in 39, `اور`↔`aur` in 65.
  Almost all of these are source glue (`ہیںکہ`, `اورناحق`) or source typos,
  not Roman errors.

### 1.2 Defects found

**A. Content dropped (fidelity). This is the most serious class.** Examples:

- **70:8** `مثل تیل کی تلچھٹ کے` → `misl-e-talchhat ke`: "تیل کی" (of oil) is missing.
- **26:12, 26:14, 26:23, 26:49**: Junagarhi's parenthetical supplements are
  unbracketed in the Roman (26:12 `جھٹلا (نہ) دیں` → `jhutla na den`; 26:14
  `(دعویٰ)` → `dawa`; 26:23 `(چیز)` → `cheez`; 26:49 `(سردار)` → `sardaar`).
  The text is there, but the brackets that mark it as the translator's
  addition are gone. This breaks ADR 0004's "preserve parenthetical glosses".
  26:12 shows why comparing bracket *counts* isn't enough: the Roman adds
  `(alaihis salaam)` and loses `(نہ)`, so the totals still match.
- **Not the same defect:** 12:5, 26:28, 28:29 and 3:52 *add* brackets around
  an honorific that the Urdu leaves unbracketed. That is a typography policy
  question (decision 4), not lost content. Keep the two classes separate.
  (Corrected after the Codex review, 2026-09-24.)

Only a few checks were run, and they found these. Expect more of this class.
§4 Phase 4 searches for it systematically.

**B. Spelling drift, which follows the drafting batches.** 922 spelling
"skeletons" (lower-case, apostrophes and hyphens removed, doubled letters
collapsed) have more than one surface spelling, covering about 31.8k tokens.
Some of those are real homographs (`kam/kaam`, `pas/paas`, `deen/den`,
`hon/hoon`, `jin/jinn`, `amal/aamaal`). Many are not:

Counts are case-insensitive (`nahin` 956 = 942 `nahin` + 14 `Nahin`).
Case-sensitive counts differ slightly, as Codex found.

| Variants (count) | Where the minority lives |
|---|---|
| `Taala` 1209 / `ta'ala` 345 | surahs 4, 5, 6 only (ADR 0004 says `Taala`) |
| `nahin` 956 / `nahi` 448 | s2–10, 17, 19 (including the s2 "exemplar") |
| `unhein` 381 / `unhe` 216 / `unhen` 93 | `unhe` s2–9; `unhen` s11–18 |
| `tumhein` 307 / `tumhe` 158 / `tumhen` 3 | same pattern |
| `kuchh` 344 / `kuch` 230 | s2–10, 29, 57, 58 |
| `farmaaya` 88 / `farmaya` 73 | 7 surahs mixed within the file |
| `aasman` 97 / `aasmaan` 14; `aasmanon` 114 / `aasmaanon` 28 | mixed |
| `parwardigar` 142 / `parwardigaar` 89 | split by surah |
| `insaan` 65 / `insan` 44, `imaan` 544 / `iman` 37 | split by surah |
| `beshak` 227 / `be-shak` 91 | 5 surahs mixed |
| `shaitaan` 36 / `shaitan` 23, `Nooh` 38 / `Nuh` 5, `Ibraheem` 73 / `Ibrahim` 2 | scattered |
| `alaihis salaam`: bracketed in 229 verses, bare in 12 | Urdu brackets it inconsistently too |

The root cause is **policy, not diligence**. The house style never settled
**long-vowel doubling** (`aa/ee/oo`). The draft says to double. ADR 0004's own
confirmed list mostly doesn't (`kitab-e-kamil`, `khazane`, `maidan-e-jang`).
Surah 2 doubles heavily. Every drafting batch picked its own rule. A readable
text cannot say `farmaaya` and `farmaya` in the same surah.

**C. Source-text defects, silently corrected.** Example: 83:18 has `لرگزنہیں` in
the source; the Roman correctly reads `Hargiz nahin`. That is the right call,
but nothing records it. A reviewer comparing against the Urdu will stumble on
it again.

**D. Checks that no tool can do.** `میں` main/mein, izafat, and `کہ`
ke/kah still need human reading (ADR 0004). A spot check found no `mein ne`
(always wrong), which is a good sign. It is not proof.

**E. Tooling gaps.** No test suite. The validator depends on another repo's
build output. Per-verse review state can't be recorded, because the file-level
`status` is too coarse to review 6,236 verses incrementally. There is no
content hash. The status figures are hand-typed into about 7 docs
(gotchas §10).

---

## 2. Owner decisions — Phase 0, blocks everything after Phase 1

> **Decided 2026-09-24 → `docs/decisions/0005-roman-urdu-orthography-v1.md`**
> (PROPOSED until the owner signs). The owner chose: double long vowels in
> content words and mixed clusters, protecting homographs and everyday forms;
> `nahi`; `unhein`/`tumhein`/`hamein`; `kuch`; `(Alaihis-Salaam)` and
> `(Sallallahu Alaihi Wasallam)` always bracketed; no apostrophes. ADR 0005 is
> the authority. The options below are kept as a record of what was weighed.

The agent **must not** choose these. Put them to the owner, then record the
answers as **ADR 0005 — Roman Urdu orthography v1**, which supersedes ADR 0004
wherever the two conflict. Recommendations are in *italics*.

1. **Long-vowel doubling.** Pick one:
   (a) always double long ا/و/ی (`farmaaya`, `aasmaan`, `insaan`);
   (b) never double, except a closed list of doubled spellings that are
   established or disambiguating (`aap`, `paas`, `kaam`, `aamaal`, `baad`, `naam`);
   (c) canonical word list only, with no general rule.
   *Claude recommends (b): it is the popular register readers actually type,
   it matches ADR 0004's own confirmed spellings, and the exception list is
   small and testable. Under (b), surah 2 changes a lot.* **Codex disagrees and
   recommends (c):** `imaan`, `insaan`, `aasmaan` and `farmaaya` are more
   legible for Quran reading and closer to surah 2, and (c) avoids a broad
   "never double" rewrite. Under (c), the canonical list is bigger to build
   but each entry is decided on its own. Read a page of each before choosing.
2. **Nasal endings.** `nahin` vs `nahi`; `unhein/tumhein` vs `unhen/tumhen` vs
   `unhe/tumhe`. *Recommend `nahin`, plus the majority `-ein` series
   (`unhein`, `tumhein`, `inhein`, `hamein`), because it is already the
   corpus majority. Codex: `nahin` agreed, but settle the pronouns by reading,
   not by counting; `unhen`/`tumhen` may be the cleaner Urdu. Whatever is
   chosen, list exactly one spelling per word.*
3. **`kuchh` vs `kuch`.** *Recommend `kuchh` (preserves the aspirate, per
   gotchas §2).*
4. **Honorifics.** Always `(alaihis salaam)` / `(sallallahu alaihi wasallam)` in
   brackets, even where the Urdu has none? *Recommend yes. It is a consumer-facing
   typographic convention, and it is consistent.*
5. **Translator's bracketed supplements.** Confirm ADR 0004: always keep them,
   in brackets, even single words like `(نہ)`. *Recommend yes. Otherwise the
   Roman reads more certain than Junagarhi wrote.*
6. **Source typos.** Correct them in Roman and record each one in an errata file
   (see Phase 1). *Recommend yes.*
7. **What "golden" gates.** Does the whole edition have to be approved before
   `experimental: true` is dropped, or does it drop per surah? *Recommend the
   whole edition. The catalogue flag is per edition, and a per-surah
   Experimental pill would need app and web work.*

Output: `docs/decisions/0005-roman-urdu-orthography-v1.md` and
`data/roman-urdu/canonical.tsv` (`variant<TAB>canonical<TAB>note`, whole-word,
case-preserving). The owner signs the ADR. The agent drafts it and does not
accept it.

---

## 3. Working rules for the executing agent

- **Red before green, always** (`~/.claude/CLAUDE.md`). Every check below is
  written as a failing test first, run, and the failure output shown. Then
  implement, and show the same test green. Report both runs.
- **Never set `reviewed` or `approved`.** Only the owner does, per verse (§4 Phase 5).
- **Never apply a model suggestion to `data/roman-urdu/` without the owner's
  per-finding OK**, except for the mechanical canonical-spelling rewrites in
  Phase 3, which the owner approves as a rule, in ADR 0005.
- **No partial files.** Keep every `surah-NNN.json` complete and valid after
  every change.
- **Commit only when the owner asks. No AI attribution trailers.**
- Record anything surprising in `docs/gotchas.md` in the same change.
- Don't hand-type status numbers into docs. Phase 1 adds a script that prints them.

---

## 4. Phases

### Phase 1 — Test harness and self-contained validation (no owner input needed)

1. Add `pytest` and a `tests/` suite. Add `make test`, or a single documented
   command, to `README.md`.
2. Vendor the verse counts: `data/meta/surah_ayah_counts.json` (114 entries,
   sum 6,236). Make `validate_roman_urdu.py` default to it. Keep `--db` as an
   option. Test: a fixture file with a gap or a digit fails, and the real corpus passes.
3. **Owner approval required before committing** (it adds a copy of the source
   text to the repo; ADR 0001 kept `data/raw/` gitignored). Vendor the Urdu
   source text as `data/source/ur.junagarhi.json`, keyed
   `"S:A"`, taken from
   `~/code/alquran-data/sources/translations/ur-junagarri-simple.db`
   (table `translation(sura, ayah, text)`). Every later check aligns against
   it. Record its sha256 in `ATTRIBUTION.md`. It is public domain.
4. Add `data/roman-urdu/source-errata.tsv`
   (`surah<TAB>ayah<TAB>source_span<TAB>read_as<TAB>note`), seeded with 83:18.
5. Add `scripts/status.py`, which prints coverage and review counts from the
   data. Replace the hand-typed figures in docs with "run `scripts/status.py`"
   where practical (gotchas §10).

Done when: `pytest` is green, with each test's red run recorded in the handoff.

### Phase 2 — `scripts/lint_roman_urdu.py` (needs `canonical.tsv` for check 2a only)

Output `out/lint.tsv` (`surah, ayah, check, detail`) and exit non-zero on any
finding that is not allowlisted. Allowlist: `data/roman-urdu/lint-allowlist.tsv`
(`surah, ayah, check, reason`). Each allowlist entry needs a human-readable
reason. The agent may add an entry only when the cause is provably a source
artefact (glue, typo in errata).

Each check gets a test with a tiny fixture that proves it fires (red first):

- **2a canonical** — any token that appears as a `variant` in `canonical.tsv`.
- **2b parity** — per-verse counts must match for pairs that can't be
  ambiguous: `اور`→`aur`, `نہیں`→`nahin`, `ہیں`→`hain`, `وہ|وه`→`woh`
  (also allow `wahi` for `وه ہی`), `اللہ`→`Allah` (including `Baitullah`, `kalaamullah`,
  `Rasoolullah`). Tokenise Urdu by stripping `۔،؟!.,()﴿﴾:؛` first, because
  the naive regex gives false mismatches in thousands of verses.
- **2c gloss parity** — per gloss, not per count. Extract each non-footnote
  `(…)`/`﴿…﴾` span from the Urdu, skip honorific spans (`علیہ السلام`,
  `صلی اللہ علیہ وسلم`, and so on), and require the same number of non-honorific
  bracketed spans in the Roman, in order. Honorific brackets are handled by
  **2g** under decision 4. It must fire on 26:12, 26:14, 26:23 and 26:49, and
  must not fire on 12:5 or 26:28.
- **2g honorific typography** — enforce decision 4 (for example, every
  `alaihis salaam` is bracketed). Keep this separate from 2c.
- **2h names** — one spelling per proper name and divine title (`Rabbul-Aalameen`,
  `Rabb Taala`, `Haq Taala`, prophet names), enforced from `canonical.tsv`,
  including capitalisation.
- **2d length outlier** — Roman/Urdu word ratio below 0.75 in a verse with at
  least 6 Urdu words. This is a review prompt, not an error: output it at
  `warn` level and don't fail on it.
- **2e forbidden forms** — `mein ne`, `kay`, `key`, `hai` for `ہیں`, `wo`
  standing alone, digits, non-ASCII. Carry over the checks from the rejected
  third-party edition (TRANSLITERATION-GUIDE §0).

Done when: the lint runs over the corpus, and the finding counts per check are
reported to the owner. Don't fix anything in this phase.

### Phase 3 — Mechanical normalisation (after ADR 0005 is signed)

For each row, or group of rows, in `canonical.tsv`:

1. Red: lint 2a reports N > 0 for that variant (show the count).
2. Apply a whole-word, case-preserving replacement through a script
   (`scripts/apply_canonical.py --rule <variant>`). Never hand-edit in bulk.
   Skip any variant marked `homograph` in the note column. Those go to Phase 4.
3. Green: that variant now counts 0, `validate_roman_urdu.py` is `ok`, and the
   diff touches only that word (`git diff --word-diff | grep -c` matches N).
4. One change per rule group, so the owner can review each diff on its own.

Do the ADR-already-settled rules first (`ta'ala`→`Taala`, 345 occurrences in
s4–6), then the decisions from §2.

### Phase 4 — Fidelity sweep (model-assisted, suggestions only)

For each surah, compare each Urdu verse with its Roman verse and write
`out/fidelity/surah-NNN.tsv`:
`ayah, class, urdu_span, roman_span, suggestion, confidence, note`.

Classes: `omission`, `addition`, `gloss-lost`, `mein-main`, `ke-kah`,
`izafat-missing`, `izafat-invented`, `wrong-word`, `vowel`, `source-typo`,
`punctuation` (a clause boundary moved or lost; token parity can't see this).

**Not cheap-agent work.** This phase needs someone who actually reads Urdu.
Use a Sonnet-class model or better from the start, and expect the parity
checks in Phase 2 to be noisy (`اللہ` inside compounds, `وه ہی`→`wahi`, words
glued together in the source). Triage their output here, not in Phase 2.

- Start from the lint findings (2b–2d) and from the seeds in §1.2 A. Then read
  every verse. Lint is only a starting point, not the full scope.
- Don't edit `data/roman-urdu/`. The owner accepts or rejects each row in
  Phase 5, and an accepted row is applied by script with its row id in the
  commit message.
- `confidence` is for ordering the queue only. It never gates anything
  (non-negotiable 1).
- Batch by surah. Order: 2, 1, 36, 55, 67, 18, then 78–114, then the rest by
  length ascending.

### Phase 5 — Owner review and per-verse approval (owner's time; the agent builds the tool)

**Schema change: present it to the owner before building (AGENTS.md §9).**
Proposal:

- `data/roman-urdu/review/surah-NNN.tsv`:
  `ayah, status(pending|reviewed|approved), sha256(roman text), reviewer, date, note`.
- The file-level `status` becomes derived: `approved` only when every verse is.
- Lint check **2f hash**: an `approved` verse whose current text hash differs
  fails the build, so the verse needs re-approval (non-negotiable 3).
- A review sheet, `scripts/review_sheet.py --surah N`, writes a local HTML page:
  Urdu | Roman | lint and fidelity flags | approve / needs-fix controls that
  export a TSV patch. The owner reads it aloud, per TRANSLITERATION-GUIDE §5.
  Alternatively, proofread on `al-quran-web` (`npm run sync:roman-urdu`).

Rough cost: about 6,236 verses at 20–40 s each comes to 35–70 owner-hours.
The high-traffic order in Phase 4 gets the most-read text golden first.

### Phase 6 — Release as golden

When `scripts/status.py` reports 6,236 approved and the lint (2a–2f) is clean:

1. Set each file's `status` to `approved`, and update the `note` to state the
   review honestly (who reviewed it, the date, and that the provenance was
   assistant-drafted and owner-reviewed).
2. `alquran-data`: `python3 pipeline/roman_urdu/export_simple_db.py`, set
   `experimental: false` in `config/sources.yaml` (and decide `default_on`),
   update `ATTRIBUTION.md` from "UNVERIFIED" to reviewed, add a test that the
   exporter refuses any non-`approved` verse once the edition is non-experimental
   (red first), then run the normal build → `build_editions.py` → publish.
3. `al-quran-web`: `npm run sync:roman-urdu`, drop the Experimental label, commit.
4. `alquran-app`: no code change. The catalogue carries the flag.

Between phases, it's fine to re-export after Phase 3 or 4 fixes, so readers of
the Experimental edition get better text while the review continues.

---

## 5. Explicitly out of scope

- The Devanagari track and `data/lexicon/`. That is a separate track and does
  not gate this one.
- Building the phoneme → Roman renderer from ADR 0001. It would be nice, but
  the text is hand-authored and golden-by-review doesn't need it.
- Any third-party Roman Urdu as a source. It may be used only as a disagreement
  signal (`crosscheck.py`).
- The Arabic text. Never.

## 6. Model allocation

| Phase | Who | Why |
|---|---|---|
| 0 | Owner (agent drafts ADR) | Policy |
| 1, 2, 3 | Cheaper model (Sonnet/Haiku class) | Mechanical and test-driven. The tests are the guard rail |
| 4 | Sonnet class or better; **not Haiku** | Needs real Urdu reading. Output is suggestions only |
| 5 | Owner; agent builds the tool | Non-negotiable 2 |
| 6 | Cheaper model, owner-gated | Follows existing runbooks |

Phases 1 and 2 can start today. Phase 3 waits on the ADR 0005 signature.
Phase 4 can run in parallel with Phase 3, but should run **after** it on any
given surah, so its findings aren't buried in spelling noise.
