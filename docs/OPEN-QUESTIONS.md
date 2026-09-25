# Open questions — Roman Urdu golden track

Last updated: 2026-09-25. **All ten answered by the owner on 2026-09-25.**
Outcomes: Q1–Q7 applied; Q8 committed; Q9 not published (by choice);
Q10 Phase 4 started on surahs 1, 2, 18, 36, 55, 67. Q7 review batches are
in `out/canonical-review/batch-01..08.tsv` (732 rows, most frequent first). Only the owner (Abu Rayyan) answers these.

**For agents:** each question below has a fixed `id`. Treat `status: open` as
blocking the listed `blocks` work. Do not act on a recommendation until the
owner writes an `answer`. When one is answered, update its block
(`status: answered`, `answer`, `answered_on`), record the ruling where
`record_in` points, and do the `on_answer` work. Follow the working rules in
`docs/ROMAN-URDU-GOLDEN-PLAN.md` §3: red before green, no commits unless
asked, no AI attribution.

Context: `docs/ROMAN-URDU-GOLDEN-PLAN.md`,
`docs/decisions/0005-roman-urdu-orthography-v1.md` (ACCEPTED 2026-09-25).
State: Phases 1–3 are applied in the working tree, uncommitted.

---

## Q1 — Dual honorific form

```yaml
id: Q1-dual-honorific
status: answered
blocks: [fix of 9 verses, lint 2g canonical set]
context: >
  Urdu علیہما السلام is dual (two prophets). Phase 3 wrongly folded it into
  the plural (Alaihimus-Salaam). A test in tests/test_apply_canonical.py
  (param "(alaihimas-salaam)-(Alaihimus-Salaam)") locks that mistake in.
verses: ["2:136", "3:84", "10:75", "14:39", "19:49", "20:70", "21:78", "29:27", "37:120"]
options:
  a: "(Alaihimas-Salaam)  — dual, same pattern as R4"
  b: "(Alaihimus-Salaam)  — keep the plural for dual too (the current state)"
recommendation: a
record_in: ADR 0005 R4
on_answer: >
  If a: change the test to expect (Alaihimas-Salaam) and run it red. Fix
  apply_canonical.py's honorific map. Re-apply to the 9 verses, choosing by
  the Urdu (علیہما = dual). Run green. Add (Alaihimas-Salaam) to lint 2g's
  canonical set. If b: record it in ADR 0005 only.
answer: a
answered_on: 2026-09-25
```

## Q2 — Honorific inside a translator's gloss

```yaml
id: Q2-nested-honorific
status: answered
blocks: [33 lint 2g info findings]
context: >
  33 honorifics sit inside a longer bracketed gloss, e.g. 12:83
  "(Yaqoob alaihis salaam ne) kaha". R4 covers only standalone spans.
examples: ["12:83", "7:79", "7:116", "15:62", "19:17", "21:87", "37:98"]
options:
  a: "(Yaqoob Alaihis-Salaam ne)          — capitalise and hyphenate, no inner brackets"
  b: "(Yaqoob (Alaihis-Salaam) ne)        — nested brackets"
  c: "leave as is"
recommendation: a   # nested brackets are awkward to read and break simple bracket parsing
record_in: ADR 0005 R4
on_answer: >
  a or b: add a test first (red), extend apply_canonical.py --honorifics,
  apply, green, and make lint 2g an error for this case. c: allowlist the
  33 findings with the reason "owner ruling Q2".
answer: a
answered_on: 2026-09-25
```

## Q3 — Unclosed bracket in the source at 57:12

```yaml
id: Q3-57-12-bracket
status: answered
blocks: [lint 2g-parens error]
context: >
  The Urdu opens "(" before قیامت کے دن and never closes it. The Roman copies
  the open bracket. Most likely intended gloss: "(قیامت کے دن)".
urdu: "(قیامت کے دن تو دیکھے گا کہ مومن مردوں اور عورتوں کا نور ..."
roman_now: "(Qayamat ke din tu dekhega ke momin mardon ..."
options:
  a: "(Qayamat ke din) tu dekhega ke ...   — close it after 'din'"
  b: "Qayamat ke din tu dekhega ke ...     — drop the stray bracket"
recommendation: a
record_in: data/roman-urdu/source-errata.tsv
on_answer: >
  Add the errata row, edit the verse by script or with an explicit
  one-verse edit, and confirm the lint error is gone.
answer: a
answered_on: 2026-09-25
```

## Q4 — Source bracket defects at 41:30 and 41:31 (Roman already sensible)

```yaml
id: Q4-41-30-31-brackets
status: answered
blocks: [2 lint 2c errors]
context: >
  41:30: the Urdu opens "(یہ کہتے ہوئے آتے ہیں کہ ..." and never closes it;
  the Roman closes it as "(yeh kehte hue)". 41:31: the Urdu opens with "("
  and closes with "﴾"; the Roman uses "(jannat mein maujood)".
options:
  a: "Accept the Roman as is. Add errata rows and lint allowlist entries."
  b: "Owner re-reads and corrects the Roman."
recommendation: a
record_in: [data/roman-urdu/source-errata.tsv, data/roman-urdu/lint-allowlist.tsv]
on_answer: "a: add the 2 errata rows and 2 allowlist rows, citing Q4."
answer: a
answered_on: 2026-09-25
```

## Q5 — Restore the translator's lost brackets in surah 26

```yaml
id: Q5-restore-glosses
status: answered
blocks: [4 lint 2c errors]
context: >
  ADR 0004 requires preserving Junagarhi's bracketed supplements. The words
  are present but unbracketed.
fixes:
  "26:12": "jhutla na den      -> jhutla (na) den"
  "26:14": "ka dawa bhi        -> ka (dawa) bhi"
  "26:23": "kya cheez hai      -> kya (cheez) hai"
  "26:49": "bada sardaar hai   -> bada (sardaar) hai"
options:
  a: "Apply all 4"
  b: "Apply some (list which)"
  c: "Don't apply"
recommendation: a
record_in: none (this applies an existing rule)
on_answer: "Edit the 4 verses and confirm lint 2c drops by 4."
answer: a
answered_on: 2026-09-25
```

## Q6 — Content omission at 70:8

```yaml
id: Q6-70-8-omission
status: answered
blocks: []
context: 'Urdu "مثل تیل کی تلچھٹ کے" (like the dregs of oil). The Roman drops "تیل کی".'
roman_now: "Jis din aasman misl-e-talchhat ke ho jaayega."
proposed: "Jis din aasmaan misl tel ki talchhat ke ho jaayega."   # literal Urdu word order
alternatives: ["Jis din aasmaan misl-e-tel ki talchhat ke ho jaayega."]
recommendation: proposed   # transliterate, don't re-order; aasman->aasmaan only if Q7 approves that row
record_in: none
on_answer: "Apply the owner's wording to 70:8 only."
answer: proposed
answered_on: 2026-09-25
```

## Q7 — The 792 `needs-review` rows in canonical.tsv

```yaml
id: Q7-needs-review-rows
status: answered
blocks: [Phase 3 part 2 (R1 long vowels), about 4,015 lint 2a info findings]
context: >
  These are machine-suggested and unsafe as a batch: the clustering merges
  different words. Rows the orchestrator judged WRONG are listed below,
  proposed to become status=keep.
proposed_keep:
  verb_pairs: [marne, marte, marna, mara, mare, marta, maro, nikalne, nikalte,
    nikalta, nikala, nikalna, utarte, utara, utarta, chalen, chalata,
    guzarta, guzare, guzari, deni]
  different_words: [bech, bhed, bari, bhari, khata, pata, alam, asar, abad,
    kelon, amaan, maloon, ghate, mal, hal, jam, tal, kat, lad, pa, bala,
    mani, mail, hari]
  bad_targets: [rahoon, kaaron, chaloon, malikon, haalon, dozakhi, qayaam,
    makaanat, khawind, boda, koda, poj, ongh, taa-waqteke]
  note: "farmabardari: fix the vowel AND the missing n -> farmaanbardaari (decide)"
options:
  a: "Mark proposed_keep as keep. Owner reviews the rest in batches of about 100, most frequent first."
  b: "Owner reviews all 792 from scratch."
recommendation: a
record_in: data/roman-urdu/canonical.tsv (status column; only the owner flips rows to decided)
on_answer: >
  An agent may set the proposed_keep rows to keep only after answer a. It
  then prepares review batches. It never sets a row to decided.
answer: a
answered_on: 2026-09-25
```

## Q8 — Commit the work so far

```yaml
id: Q8-commit
status: answered
blocks: [clean baseline for Phase 4]
context: >
  Uncommitted in alquran-roman-urdu: Phase 1–2 tooling and tests; ADR 0005;
  canonical.tsv; Phase 3 text changes (1,804 verses) with per-group patches
  in out/phase3/ (gitignored).
options:
  a: "One commit per phase: tooling (P1–2), ADR+canonical, text (P3), each group separately if wanted"
  b: "A single commit"
  c: "Not yet"
recommendation: a   # after Q1 is fixed, so the text commit doesn't carry the dual error
record_in: git (the owner's authorship only; no AI trailers)
on_answer: "Commit as instructed. Do not push unless asked."
answer: a
answered_on: 2026-09-25
```

## Q9 — Publish the improved text as an interim update

```yaml
id: Q9-interim-publish
status: answered
blocks: []
context: >
  The live edition (ur-roman-abu-rayyan, Experimental) still serves the
  pre-Phase-3 text. Re-export = alquran-data
  pipeline/roman_urdu/export_simple_db.py -> build -> build_editions.py ->
  publish_editions.sh; web = al-quran-web npm run sync:roman-urdu + commit.
  It stays labelled Experimental either way.
options:
  a: "Publish after Q1 and Q8"
  b: "Wait until more of the review is done"
recommendation: a
record_in: none
on_answer: "Follow the alquran-data runbook. Each publish step needs the owner's go."
answer: b
answered_on: 2026-09-25
```

## Q10 — Start Phase 4 (fidelity sweep)

```yaml
id: Q10-phase-4
status: answered
blocks: []
context: >
  A verse-by-verse Urdu vs Roman comparison that produces
  out/fidelity/surah-NNN.tsv as suggestions only. Needs a Sonnet-class model
  or better (not Haiku). Order: 2, 1, 36, 55, 67, 18, 78–114, then the rest.
  Starting points: 80 parity warnings, 10 length warnings.
options:
  a: "Start now, on surahs 1, 2, 36, 55, 67, 18 first"
  b: "Start after Q7"
recommendation: a   # fidelity findings are independent of the long-vowel spellings
record_in: none
on_answer: "Run the sweep. The owner accepts or rejects each finding row."
answer: a
answered_on: 2026-09-25
```

---

## Technical follow-ups (no owner decision needed)

- **T1:** lint 2a's tokenizer doesn't read hyphenated compounds
  (`ne'mat-o-fazl`) as whole words, so it undercounts them (gotchas §13).
  Fix: align `_ROMAN_WORD_RE` with `apply_canonical.py`'s `_TOKEN_RE`, with
  the test written red first.
- **T2:** lint 2g only inspects honorifics that are already inside brackets
  (gotchas §12). Add a check for bare honorifics, red first.
