# ADR 0006 — AI-verified, owner-sampled review

- **Status:** ACCEPTED 2026-09-25 by the owner (Abu Rayyan)
- **Scope:** `data/roman-urdu/` (the Roman Urdu text only; the Devanagari
  lexicon track is unaffected)
- **Amends:** AGENTS.md §4 non-negotiables 1 and 2, for the Roman Urdu text

## Context

Phase 5 built per-verse approval for the owner to use. A careful
read-aloud pass over 6,236 verses is 35–70 hours. The owner's ruling: "it's
next to impossible to review the entire Quran in Roman Urdu, I would need
something automated."

By this point the text has been through:
- the ADR 0005 orthography rules, enforced by lint;
- a full fidelity sweep against the Urdu;
- a full AI pre-review, one verdict per verse;
- four rounds of owner rulings (docs/OPEN-QUESTIONS.md Q1–Q30).

## Decision

A verse reaches the final state through **independent double AI
verification plus an owner-checked random sample**. Owner approval of every
verse is no longer required.

1. **Two independent AI verdicts.** Verdict A is the existing pre-review
   (`data/roman-urdu/prereview/`). Verdict B comes from a second reviewer:
   a different vendor (Codex), a different prompt, and no access to
   verdict A. It is stored in `data/roman-urdu/verify2/`.
   **As run (2026-09-25):** Codex (gpt-5.5) covered 92 surahs (4,292
   verses) before hitting the owner's usage limit. The owner chose Claude
   Sonnet for the remaining 22 surahs (13–25 and 34–42, 1,944 verses), with
   a blind prompt and only the verse text in its folder. For those surahs
   both verdicts come from Claude models, so the two are less independent;
   the owner's random sample should include them in proportion.
2. **Verified** means: both verdicts are `ok` for the exact current text
   (hash-pinned) and lint is clean.
3. **Disagreements** (either verdict raises a concern) go to the owner in
   chat, exceptions only. The owner's ruling is applied and recorded as
   before.
4. **Sample.** About 150 verified verses are drawn at random and read by the
   owner. With 0 errors, the verified set's error rate is below about 2%
   (95% confidence, rule of three). If errors are found, the pattern is
   fixed across the whole corpus and a fresh sample is drawn.
5. **Record.** The review ledger is truthful about method. Owner-read verses
   are `approved` with reviewer `Abu Rayyan`. Machine-verified verses are
   `verified` with reviewer `AI (double) + owner sample`. Every row stays
   hash-pinned: any later text change drops the verse to pending (lint 2f).
6. **Public credit is unchanged.** The owner's ruling: the credit stays
   "Abu Rayyan" only. That credit names the author of the transliteration,
   and does not claim that every verse was read by hand. No AI credit
   appears in consumers.
7. "Experimental" is dropped only on the owner's explicit word (ADR 0005,
   P4).

## Consequences

- Non-negotiable 1 ("never let a model decide a vowel") no longer holds for
  this text. Two models must agree, and the owner's sample measures how
  often they are wrong. Non-negotiable 2's "nothing ships unreviewed" is
  replaced, for this text, by rules 2–5 above.
- The error-rate bound comes from the sample and is only as good as it. A
  systematic error shared by both reviewers could slip past both. The
  corpus-wide pattern checks (lint, plus the round 1–4 audits) are what
  guard against that.
- Owner time drops from 35–70 hours to about 3–4 hours.
