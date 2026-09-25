# Phase 5 design — per-verse owner review and approval

Written 2026-09-25. Design only: no code, no data changes. Read first:
`AGENTS.md` §4 non-negotiables 2–3 and §9, `docs/ROMAN-URDU-GOLDEN-PLAN.md`
§3–§4 (Phase 5, Phase 6), `docs/decisions/0005-roman-urdu-orthography-v1.md`,
`docs/OPEN-QUESTIONS.md`, `docs/TRANSLITERATION-GUIDE.md` §5.

**Constraints this design must not violate:** nothing ships unreviewed
(non-negotiable 2); approved output is content-hashed, regeneration forces
re-approval (non-negotiable 3); only the owner sets `reviewed`/`approved`
(plan §3); a schema change is presented to the owner before it is built
(AGENTS.md §9, plan §4 Phase 5's own first line).

Owner questions raised here are P1–P6 at the end, in `OPEN-QUESTIONS.md`
format. Nothing here is built until those land.

---

## 1. Review ledger data format

**Recommended: `data/roman-urdu/review/surah-NNN.tsv`**, one file per surah,
mirroring `surah-NNN.json`. Columns:

```
ayah    status    sha256    reviewer    date    note
```

`status`: `pending|reviewed|approved`. `sha256`: hex digest of the current
Roman verse text (§2). `reviewer`/`date`: blank until decided. `note`: free
text. One row per ayah, `1..N`, no gaps — same discipline as `ayahs`.

| Option | Verdict | Why |
|---|---|---|
| Fields inside `surah-NNN.json` | Rejected | Mixes two independently-changing concerns in one file. `apply_canonical.py` is currently the *only* writer of the text JSON; a review write must never risk the text next to it. Also turns every approval into a diff on the scripture-text file, which §9's "no partial files" / "don't overwrite from a script" rules protect. |
| One corpus-wide `review.tsv` (6,236 rows) | Rejected | Every session, even one needs-fix, touches the whole file. Diffs stop being surah-scoped, concurrent sessions collide for no reason, and it breaks the per-surah shape everything else here uses (`--surah N`). |
| Per-surah TSV (recommended) | — | Diffs are small and localized; a merge conflict is confined to rows actually touched. Never touches the text file, so §2's hash check stays a clean one-way read. Matches `--surah N` everywhere else. |

Ledger files are bootstrapped lazily: the first tool that needs one for a
surah without a ledger yet (`review_sheet.py` or `apply_review.py`) creates
it with every row `pending`, `sha256` blank, from the current JSON. No
separate bootstrap script needed.

---

## 2. Hash rule

**What is hashed:** sha256 hex digest of the exact UTF-8 bytes of the Roman
verse string in `ayahs["N"]`. No normalisation, no trimming, no case-fold.

**Why no normalisation:** the hash exists to catch every byte-level change
so re-approval isn't optional. Normalising first (e.g. through
`scripts/normalise.py`) would hide exactly what must be caught — a
`canonical.tsv` rewrite is often one letter. Precedent: `scripts/review.py`'s
`content_hash()` already hashes exact strings, unnormalised, for the
Devanagari lexicon.

**When an approved/reviewed verse's text changes:**

1. **Enforced backstop — lint 2f (hash).** For every `reviewed`/`approved`
   row, recompute the sha256 of the current text and compare to the stored
   one. Mismatch → `error` finding (`2f-hash`), same severity as 2c/2e/2g —
   fails the build. This is what makes non-negotiable 3 real rather than
   aspirational: even if the step below is skipped, the build can't go
   green on a stale approval.
2. **Explicit, non-silent reset — the writer's job, not lint's.**
   `lint_roman_urdu.py` never writes files; that rule extends to the
   ledger. Any text writer (`apply_canonical.py`, the one-verse-edit helper
   in §5, a future Phase 4 accept-script) must, for every ayah it touches,
   reset that ledger row to `pending`, clear `sha256`/`reviewer`/`date`, and
   append the reason to `note` (e.g. `"reset: apply_canonical.py --rule
   nahin, 2026-09-26"`). A reader sees *why* a verse dropped out of
   `approved`, never just that it did.
3. If step 2 is missed (hand-edit, bug), step 1 still catches it on the
   next lint run — the reset is a courtesy; the hash check is the guarantee.

`status.py` (§3) reports demotions so a drop in `approved` count is visible.

---

## 3. File-level `status`, and `scripts/status.py`

The JSON's `status` field stops being hand-set once Phase 5 starts. It
becomes **derived** per surah:

| Ledger state | File `status` |
|---|---|
| every row `approved`, hash-clean | `approved` |
| every row `reviewed`/`approved`, none `pending` | `reviewed` |
| anything else | `beta-unverified` |

**Who writes it:** a `--write-status` mode on `scripts/status.py` recomputes
this and rewrites *only* the `status` key — never `ayahs`. Invoked
explicitly, typically as the last step of `apply_review.py` for that surah,
so the change is a visible, reviewable diff, not a side effect of linting.

**Reporting:** extend `status.py`'s output with a review block sourced from
`data/roman-urdu/review/*.tsv`, parallel to the existing file-status block:

```
by file status:
  beta-unverified      files=114  verses=6236
by review status:
  pending              verses=6236
  reviewed             verses=0
  approved             verses=0
```

Nothing hand-typed (gotchas §10) — both blocks read the files on disk.

---

## 4. Review tool: `scripts/review_sheet.py --surah N`

Produces one **self-contained static HTML file**, `out/review/surah-NNN.html`
— verse text, lint findings and `fidelity-findings.tsv` rows all inlined as
a JS object (no `fetch()` of a sibling file). This is not cosmetic: Safari
on iPad blocks `fetch()` of local files under `file://`, and read-aloud
review happens on mobile/iPad. A file that opens by itself, AirDropped or
emailed, is more reliable than anything needing a running server.

Per verse: Urdu (large, RTL), Roman (large, underneath), lint/fidelity flags
as chips, and **Approve**/**Needs fix** controls — needs-fix opens a text
box (corrected Roman, optional) and a note field (required).

```
+-------------------------------------------+
| Surah 1 — Al-Fatiha                 2/7    |
+-------------------------------------------+
|  سب تعریف اللہ تعالیٰ کے لئے ہے جو تمام جہانوں  |  Junagarhi Urdu, large, RTL (never the Arabic)
|                                           |
|  Sab tareef Allah Taala ke liye hai jo   |  Roman, large
|  tamaam jahanon ka paalne wala hai.      |
+-------------------------------------------+
| flags: [2b-parity: warn]                 |
| fidelity: (none for this verse)          |
+-------------------------------------------+
| note: [___________________________]      |
|   [ Approve ]        [ Needs fix ]       |
+-------------------------------------------+
        prev            next
  [ Download patch — 3 decided so far ]
+-------------------------------------------+
```

**Getting decisions back into the ledger.** The page has no filesystem
write access. Decisions accumulate in the page (mirrored to `localStorage`
only as a crash/reload safety net, never the record of truth). **Download
patch** serialises them to
`ayah, decision(approve|needs-fix), corrected_text, note, seen_sha256` — one
row per decided verse. `seen_sha256` is stamped by `review_sheet.py` at
generation time from the hash the page actually rendered — this is what
makes the merge hash-checked.

`scripts/apply_review.py --patch <file> --reviewer "Abu Rayyan"`:

1. Per `approve` row: recompute the ayah's current sha256 and compare to
   `seen_sha256`. Mismatch → refuse the row (text changed after the page
   was generated; the owner read stale text) and report it, never approve.
   Match → write `status=approved`, `sha256`, `reviewer`, `date`, `note`.
2. Per `needs-fix` row: see §5.
3. Touches at most one ayah per row; never a row the patch doesn't mention.
4. `--dry-run` (same convention as `apply_canonical.py`) reports counts
   without writing; a real run prints a summary (approved / needs-fix
   applied / needs-fix flagged-only / refused-stale) and exits non-zero on
   any refusal.
5. On success, calls the §3 `--write-status` step for that surah.

**Rejected alternative:** a local server writing the ledger on each click.
(A *read-only* static server that only serves the generated page is
different, and is the recommended delivery in P6.)
Reintroduces "review tool writes data files unsupervised," and needs a
terminal reachable from the iPad. The al-quran-web `sync:roman-urdu`
proofreading path (TRANSLITERATION-GUIDE §5) stays available as a secondary
way to read the text in page context; it produces no patch and isn't a
substitute.

---

## 5. The needs-fix flow

The owner never edits `data/roman-urdu/*.json` by hand (existing rule for
Phase 3; Phase 5 gets its own single writer: `apply_review.py`).

1. Owner clicks **Needs fix**, types a correction (optional) and a note
   (required).
2. Owner downloads the patch; it reaches the agent.
3. Agent runs `apply_review.py --dry-run` first, shows the diff
   (`git diff --word-diff`, the Phase 3 convention), then runs for real.
4. If `corrected_text` is present: applied as an **exact-match,
   asserted-once** single-verse replacement — same discipline as the
   one-off owner corrections already in `OPEN-QUESTIONS.md` (Q11, Q21,
   etc). If the current text no longer matches what the page showed
   (caught by `seen_sha256`), refused, never force-applied.
5. Ledger row → `status=pending` (never silently re-approved), `sha256`
   updated, `reviewer`/`date` cleared (only `note` carries history — P5),
   `note` records what changed and why.
6. The verse re-enters the pending queue and needs a fresh read-aloud
   approval next session, like any other verse. A needs-fix with no
   `corrected_text` leaves the text untouched, ledger stays `pending`, note
   recorded, for later.
7. Committed only when the owner asks, message naming which verses changed
   and why — never silent (plan §3).

---

## 6. Interaction with the ongoing `canonical.tsv` review (732 rows)

Risk: a verse approved today gets its spelling rewritten later when one of
the 732 `needs-review` R1 rows is decided and `apply_canonical.py` runs —
the hash rule (§2) correctly demotes it, but every hour spent approving
text R1 will still touch is an hour partly at risk of rework, and it breaks
the owner's reading rhythm.

**Recommend: settle the 732 rows before starting general Phase 5 approval**,
except surah 2, which can start now — it's already the hand exemplar and
most `decided` rules are already applied to it (OPEN-QUESTIONS.md Q8), so
its remaining R1 exposure is small.

**Cost estimate.** 8 review batches are already prepared
(`out/canonical-review/batch-01..08.tsv`, ~100 rows each, most-frequent
first — Q7). These are word-level judgements, faster than a verse read (no
Urdu line to re-check): at ~20–30 s/row, 732 rows ≈ **4–6 owner-hours**,
against Phase 5's 35–70 hours — under a fifth of a single day's review
budget, for removing the largest remaining source of post-approval churn.

If the owner declines to block on this (P2), the fallback: demotions are
visible (§3), cheap to re-review (usually one word), and Phase 5 can start
on the groups Phase 4 already gave a head start (§9).

---

## 7. Phase 6 gate: exporter behaviour once reviewing starts

`export_simple_db.py` today reads every surah unconditionally and hard-fails
unless it gets exactly 6,236 rows; it doesn't gate on `status`, only counts
and prints how many aren't `approved`.

**Recommend: unchanged for the whole of Phase 5.** The edition stays
`experimental: true` (one edition-level flag in `config/sources.yaml` — no
per-verse/per-surah signal exists downstream today), and every re-export
keeps publishing the full, currently-best text, exactly as the plan already
intends ("readers of the Experimental edition get better text while the
review continues"). Exporting approved-only now would conflict with the
exporter's own invariant (all-6,236-or-fail) and would make the live
Experimental edition regress to near-empty at the start of Phase 5 — worse
for existing readers, no safety benefit, since it's already labelled
unverified.

**What changes, and when:** exactly plan §4 Phase 6 — add the
refuse-if-not-`approved` test (red first), on only when the owner flips
`experimental: false` for the whole edition. Recommend a `--require-approved`
flag on `export_simple_db.py`, off by default, turned on only in the Phase 6
runbook. No per-surah machinery needed — a per-surah Experimental pill needs
app/web UI work out of scope here, and plan §2 item 7 already leans
whole-edition. That item, though, has no recorded `answer:` (unlike
Q1–Q23) — carried forward as P4, not assumed settled.

---

## 8. Test plan (red-first for every new script and lint check)

| File | Behaviour under test | Red-first case |
|---|---|---|
| `tests/test_review_ledger.py` (new) | Ledger load/save round-trip; bootstrap creates all-`pending` rows matching ayah count; loader rejects a gap/duplicate ayah; sha256 helper matches a fixed vector (pattern of `tests/normalization_vectors.json`) | Call the not-yet-written functions against fixtures — missing-function error is the red, then a gap-fixture must raise, a known string must hash to a known digest, before green |
| `tests/test_lint_hash.py` (new) | 2f: `approved`/`reviewed` + stale `sha256` → `error`; matching hash → no finding; `pending` never checked | Fixture with a wrong stored hash on an `approved` row must produce zero findings before 2f exists, then fire after |
| `tests/test_status.py` (extend) | Review-count block matches ledger fixtures; `--write-status` rewrites only `status`, never `ayahs`; derivation table (§3) | Fixture with one `pending` row must still report `beta-unverified` before derivation logic exists |
| `tests/test_review_sheet.py` (new) | Data-assembly function (verse + lint + fidelity + ledger → page structure) unit-tested directly, not through HTML; no fidelity row → empty list, not a missing key | Call the function before it exists; assert it merges lint + fidelity rows for the right (surah, ayah) |
| `tests/test_apply_review.py` (new, largest) | approve+match → ledger written; approve+stale `seen_sha256` → refused, ledger untouched; needs-fix+matching `corrected_text` → edit applied, ledger reset to `pending`; needs-fix+non-matching text → refused, nothing applied; needs-fix with no text → stays `pending`, note recorded; unknown ayah in patch → hard error; `--dry-run` writes nothing | One fixture triple (JSON + ledger + patch) per case; assert against the not-yet-built script, show the failure, then implement |
| alquran-data `tests/test_export_simple_db.py` (extend, per plan §4 Phase 6) | `--require-approved` refuses export with any non-`approved` verse; default behaves as today | Fixture with one non-approved surah must make `--require-approved` fail before the flag exists |

Every red run is shown before its implementation, per the owner's
red-before-green rule — this table is the work list, not a description of
code already written.

---

## 9. Suggested review order and time estimate

Carries forward the order already established by Phase 4's sweep and
TRANSLITERATION-GUIDE §6 — no new ordering logic:

1. **R1 canonical settle** (§6) — 732 rows, ~4–6 owner-hours. Blocks
   everything below except surah 2.
2. **Surah 2**, calibration — 286 verses.
3. **High-traffic, already fidelity-swept**: 1, 36, 55, 67, 18 — 308 more
   verses (group total 594, matching Phase 4 Round 2's coverage).
4. **Juz Amma / short high-recitation surahs 78–114** — 564 verses.
5. **Everything else**, shortest first, for visible momentum — 5,078 verses.

| Group | Verses | At 20–40 s/verse |
|---|---:|---|
| 2, then 1/36/55/67/18 | 594 | 3.3–6.6 hours |
| 78–114 | 564 | 3.1–6.3 hours |
| Remainder | 5,078 | 28.2–56.4 hours |
| **Total** | **6,236** | **34.6–69.3 hours** (matches the plan's own 35–70h) |

R1 settle (§6) adds 4–6 hours on top, once, before step 2.

---

## 10. Owner decisions needed

```yaml
id: P1-ledger-schema
status: answered
context: >
  AGENTS.md §9 and plan §4 Phase 5 require the ledger schema to be
  presented before it is built. §1 proposes
  data/roman-urdu/review/surah-NNN.tsv:
  ayah, status(pending|reviewed|approved), sha256, reviewer, date, note.
options:
  a: "Accept the schema as proposed in §1"
  b: "Change it (say what)"
recommendation: a
blocks: [building review_sheet.py, apply_review.py, lint 2f]
answer: a   # owner accepted the recommendation ("let's do it")
answered_on: 2026-09-25
```

```yaml
id: P2-r1-sequencing
status: answered
context: >
  732 canonical.tsv rows (R1 long-vowel doubling) are still needs-review.
  A later decision on one demotes any now-approved verse it touches
  (§2, §6). Settling R1 first costs an estimated 4-6 owner-hours against
  Phase 5's 35-70.
options:
  a: "Settle all 732 rows before general Phase 5 approval (surah 2 may start now regardless)"
  b: "Start Phase 5 now; accept re-approval churn as R1 rows get decided over time"
recommendation: a
blocks: [Phase 5 review order, §9]
answer: a   # owner accepted the recommendation ("let's do it")
answered_on: 2026-09-25
```

```yaml
id: P3-interim-exporter
status: answered
context: >
  During Phase 5, should export_simple_db.py keep exporting every verse
  unconditionally (today's behaviour, edition stays experimental: true),
  or hold back non-approved verses?
options:
  a: "Keep unconditional export; add --require-approved, off by default, on only at Phase 6 (§7)"
  b: "Switch now to approved-only export (shrinks the live Experimental edition to near-empty at first)"
recommendation: a
blocks: [any Phase 5-era re-export]
answer: a   # owner accepted the recommendation ("let's do it")
answered_on: 2026-09-25
```

```yaml
id: P4-final-gate-scope
status: answered
context: >
  Plan §2 item 7 asked whether "golden" (experimental: false) requires the
  whole edition approved, or can drop per surah. Never formally answered
  (no answer: field, unlike Q1-Q23) though ADR 0005 settled the other
  Phase 0 items. §7 assumes whole-edition gating.
options:
  a: "Whole edition (§7's assumption; no per-surah UI work in app/web)"
  b: "Per surah (needs an app + web Experimental-pill change, out of scope here)"
recommendation: a
record_in: ADR 0005 or a short addendum
blocks: [Phase 6 runbook, export_simple_db.py --require-approved semantics]
answer: "Experimental stays until the owner explicitly says to drop it. No automatic flip, even when every verse is approved."
answered_on: 2026-09-25
```

```yaml
id: P5-needs-fix-reviewer-field
status: answered
context: >
  After a needs-fix correction (§5 step 5), should the ledger row's
  reviewer/date be cleared (not yet re-read) or kept with a separate
  correction marker?
options:
  a: "Clear reviewer/date; note carries history (simplest; status.py never reports a stale-looking approval)"
  b: "Keep last reviewer/date and add a correction_count column"
recommendation: a
blocks: [apply_review.py's needs-fix write path]
answer: a   # owner accepted the recommendation ("let's do it")
answered_on: 2026-09-25
```

```yaml
id: P6-review-page-delivery
status: answered
context: >
  review_sheet.py's HTML has all data inlined (no fetch()). How should it
  reach the reading device? Orchestrator note (2026-09-25): on iPad, an
  AirDropped or emailed .html usually opens in Files/Quick Look, where
  scripts, localStorage and the "Download patch" button are unreliable, so
  option a is doubtful for the approve/needs-fix controls. Untested on a
  real iPad either way; step one of building this is a 5-minute device test.
options:
  a: "AirDrop / iCloud / email the generated file directly (no server, works offline)"
  b: "Read-only local server on the Mac (python3 -m http.server --directory out/review), opened in iPad Safari over the LAN; the patch downloads in Safari. The server serves files only and writes nothing, so the 'unsupervised writes' objection in §4 does not apply"
  c: "Review on the Mac only (open the file in a desktop browser)"
recommendation: b   # works in real Safari, where downloads and localStorage behave; fall back to c if the LAN is awkward
blocks: [whether review_sheet.py needs any server-facing option at all]
answer: c   # owner has no iPad to hand; review on the Mac in a desktop browser
answered_on: 2026-09-25
```
