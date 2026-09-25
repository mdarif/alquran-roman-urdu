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

---

# Round 2 — from the Phase 4 fidelity sweep (2026-09-25)

**All seven answered 2026-09-25 and applied** (160 verses; recorded in ADR 0005 R6).

Swept: surahs 1, 2, 18, 36, 55, 67 (594 verses). Findings are in
`out/fidelity/surah-NNN.tsv`. The orchestrator verified each finding and
read a sample of verses independently. Result: no dropped content in these
surahs. The source typos at 2:282, 18:16 and 55:52 are logged in
`source-errata.tsv`; they need no Roman change.

## Q11 — Typo at 36:37

```yaml
id: Q11-36-37-typo
status: answered
context: 'Urdu کھینچ دیتے ہیں. The Roman has a stray space: "kheen ch dete hain".'
proposed: "kheench dete hain"
recommendation: apply
on_answer: "One-verse edit, then lint."
answer: apply
answered_on: 2026-09-25
```

## Q12 — 36:2 has a different word than the Urdu

```yaml
id: Q12-36-2-hakeem
status: answered
context: >
  Urdu "قسم ہے قرآن باحکمت کی". The Roman "Qasam hai Quran-e-Hakeem ki" uses
  the Arabic-derived Hakeem, where Junagarhi wrote باحکمت (ba-hikmat).
options:
  a: "Qasam hai Quran ba-hikmat ki   — transliterate Junagarhi's word"
  b: "keep Quran-e-Hakeem"
recommendation: a   # the edition is Junagarhi's Urdu; a well-known Arabic phrase should not replace it
answer: b
answered_on: 2026-09-25
```

## Q13 — "Aad" (barrier) capitalised, so it reads as the people of ʿĀd

```yaml
id: Q13-aad-barrier
status: answered
context: >
  آڑ (barrier) is rendered "aad" in 55:20, 59:14, 7:46 and 8:24, which is
  consistent with ڑ -> d in the popular register. At 36:9 it is capitalised,
  "ek Aad", which is exactly how the tribe of ʿĀd is written in 7:65 and
  elsewhere.
options:
  a: "lowercase 'aad' at 36:9"
  b: "a distinct spelling for the barrier everywhere (e.g. 'aar'), so it can never collide with ʿĀd"
recommendation: b   # the collision exists in every one of the 5 verses once a reader searches; 'aar' is a common popular spelling of آڑ
answer: b
answered_on: 2026-09-25
```

## Q14 — 2:163 and 2:255 treat معبود برحق differently

```yaml
id: Q14-mabood-bar-haq
status: answered
context: >
  The same Urdu phrase is "mabood bar-haq" at 2:163 but "mabood-e-bar-haq"
  at 2:255. ADR 0004 lists mabood-e-bar-haq as an established compound. The
  sweep argues برحق is an adjective, so the izafat is invented.
options:
  a: "mabood-e-bar-haq everywhere (ADR 0004 as written)"
  b: "mabood bar-haq everywhere (amend ADR 0004)"
recommendation: b   # Urdu writes no izafat and برحق qualifies معبود adjectivally; ADR 0005 already supersedes 0004 where they conflict
on_answer: "Add a canonical.tsv row plus an ADR note; apply with apply_canonical.py."
answer: b
answered_on: 2026-09-25
```

## Q15 — 2:96 "inhi ko" for انہیں کو

```yaml
id: Q15-2-96-inhi
status: answered
context: 'Urdu "آپ انہیں کو پائیں گے" (emphatic: "it is them you will find"). Roman "Aap inhi ko paayenge".'
options:
  a: "keep inhi ko (emphatic sense preserved)"
  b: "unhein ko"
recommendation: a   # sweep confidence low; انہیں کو here is the emphatic form, which "inhi ko" captures
answer: a
answered_on: 2026-09-25
```

## Q16 — jinhe / jinhen / jinhein (a spelling drift R2 didn't cover)

```yaml
id: Q16-jinhein
status: answered
context: "Counts: jinhein 69, jinhe 30, jinhen 30. R2 settled unhein/tumhein/inhein/hamein but not this one."
options:
  a: "jinhein (parallel to R2)"
  b: "other spelling"
recommendation: a
on_answer: "Add canonical.tsv rows as decided, record under ADR 0005 R2, apply."
answer: a
answered_on: 2026-09-25
```

## Q17 — Split future verbs ("jaao ge") vs joined ("jaaoge")

```yaml
id: Q17-future-verbs
status: answered
context: >
  114 split future forms in 18 surahs (18:49 "jaayen ge", 18:16 "karde ga";
  39 of them in surah 18) against 2,037 joined forms (dega, jaayenge,
  karoonga).
options:
  a: "join them all (jaao ge -> jaaoge, karde ga -> kardega)"
  b: "leave as is"
recommendation: a   # the corpus is overwhelmingly joined; a split form breaks search for the verb
on_answer: "Add a lint rule (red first) and a joining rule in apply_canonical.py (red first), then apply."
answer: a
answered_on: 2026-09-25
```

---

# Round 3 — full-corpus fidelity sweep (2026-09-25)

**All six answered 2026-09-25 and applied** (45 verses; recorded in ADR 0005 R6).

All 114 surahs were swept (6,236 verses). All findings, with the Urdu, are in
`data/roman-urdu/fidelity-findings.tsv` (45 rows). The 11 source typos where
the Roman is already right are logged in `source-errata.tsv` and need no
decision. The orchestrator checked every fix below against the Urdu.

**How complete the sweep is:** a mechanical plural check run afterwards found
6 errors the sweep agents had missed (Q18 group B), plus 6 more `misl-e-`
cases (Q19). Treat the sweep as a strong pass, not proof that the text is
clean. The per-verse read-aloud review (Phase 5) is still needed.

## Q18 — Clear fixes (the Roman says a different word, or drops or garbles one)

```yaml
id: Q18-clear-fixes
status: answered
recommendation: apply all; say which to skip, if any
group_A_sweep_found:
  "9:31":   "apne aalim aur darweshon   -> apne aalimon aur darweshon   (عالموں, plural)"
  "10:17":  "aise mujrim ko             -> aise mujrimon ko             (مجرموں)"
  "49:15":  "apne maal se               -> apne maalon se               (مالوں; parallel to jaanon)"
  "22:51":  "dozakhhi                   -> dozakhi                      (typo)"
  "40:6":   "dozakhii                   -> dozakhi                      (typo)"
  "39:24":  "chakhho                    -> chakho                       (typo)"
  "69:24":  "guzashtha                  -> guzashta                     (گزشتہ, no aspirate)"
  "80:30":  "ghanjaan                   -> ganjaan                      (گنجان has گ, not غ)"
  "47:4":   "muthbher                   -> mudbher                      (مڈبھیڑ, retroflex ڈ)"
  "96:13":  "munh phirta                -> munh pherta                  (پھیرنا turn away, not پھرنا wander)"
  "72:26":  "muttale                    -> muttali                      (مطلع)"
  "77:27":  "serab                      -> seeraab                      (سیراب quenched; 'serab' reads like saraab, mirage)"
  "32:8":   "be-waqar paani             -> be-waqat paani               (وقعت worth, not وقار dignity)"
  "86:2":   "numaayaan hone wali        -> numoodar hone wali           (نمودار, not نمایاں)"
  "92:20":  "Parwardigaar-e-Buzurg-o-Buland -> Parwardigaar Buzurg-o-Buland (Urdu has no izafat)"
group_B_orchestrator_found:  # plurals missing their nasal -n; these are not vocatives
  "9:5":    "mahino ke    -> mahinon ke"
  "11:30":  "in momino ko -> in mominon ko"
  "11:94":  "momino ko    -> mominon ko"
  "11:120": "momino ke liye -> mominon ke liye"
  "5:54":   "musalmano par -> musalmanon par"
  "5:56":   "musalmano se  -> musalmanon se"
on_answer: "One-verse scripted edits (exact match, asserted once), lint, one commit."
answer: apply all
answered_on: 2026-09-25
```

## Q19 — `misl-e-X` → `misl X` (follows your 70:8 ruling)

```yaml
id: Q19-misl
status: answered
context: >
  Your Q6 ruling wrote 70:8 as "misl tel ki talchhat ke". 9 verses still
  use misl-e-: 41:13, 44:45, 44:46, 47:12, 55:58, 56:6, 68:35, 70:9, 77:32.
  Many other verses already use "misl X" (2:194, 4:176, 5:36, ...).
options:
  a: "misl X everywhere (drop the -e-)"
  b: "leave them"
recommendation: a
on_answer: "Add a canonical rule with its test first (red), apply, and add a lint check."
answer: a
answered_on: 2026-09-25
```

## Q20 — `Rab` → `Rabb`

```yaml
id: Q20-rabb
status: answered
context: >
  "Rabb" is the canonical term (ADR 0004). "Rab" appears 19 times, all in
  surahs 7, 8 and 10 (one drafting batch).
recommendation: apply
answer: apply
answered_on: 2026-09-25
```

## Q21 — 45:17: the verb دیں ("gave") is written `din` (reads as "day")

```yaml
id: Q21-45-17-deen
status: answered
context: 'Urdu "صاف صاف دلیلیں دیں" (gave clear proofs). Roman "daleelein din".'
options:
  a: "daleelein deen — the correct sound; collides in spelling with deen (religion), and the same verse also has 'deen ki'"
  b: "daleelein dein — avoids the collision, though it reads like the present 'dein'"
  c: "keep din"
recommendation: b   # 'deen' twice in one verse with two meanings is worse; 'dein' is the common popular spelling for دیں
answer: b
answered_on: 2026-09-25
```

## Q22 — 58:4: ساٹھ (sixty) is written `saath`, the same as "with"

```yaml
id: Q22-58-4-saath
status: answered
context: 'Urdu "ساٹھ مسکینوں کو کھانا کھلانا". Roman "saath miskeenon ko..." can be read as "feed along with the needy".'
options:
  a: "keep saath (context disambiguates)"
  b: "saath (60) — the digit is forbidden by lint 2e; not recommended"
  c: "a distinct spelling, e.g. 'saath' -> 'saatth'"
recommendation: a   # every popular spelling of ساٹھ is 'saath'; an invented form would confuse more than it helps
answer: a
answered_on: 2026-09-25
```

## Q23 — Low-confidence items (recommend no change)

```yaml
id: Q23-low-confidence
status: answered
items:
  "48:6":  "unhi par for انہیں پر — same emphatic reading you kept at 2:96 (Q15). Keep."
  "46:9":  "alal-aalaan for علی الاعلان — 'alal-ailaan' matches 9:1's 'ailaan'. Minor; apply?"
  "28:15, 23:47, 65:2": "do shakhs for دو شخصوں — colloquial number agreement. Keep."
recommendation: "keep all; apply 46:9 only if you want it consistent with 9:1"
answer: keep all (46:9 not applied)
answered_on: 2026-09-25
```

Also noted for the Q7 long-vowel review, not decided here: `kochein`/`koonchein`
(91:14 vs 26:157, 54:29), `qaem`/`qaaim`, `bipharnaa`/`dhaarnaa` (25:12).
