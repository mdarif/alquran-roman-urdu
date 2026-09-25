#!/usr/bin/env python3
"""
review_sheet.py --surah N — writes one self-contained static HTML review
page, `out/review/surah-NNN.html`.

Phase 5 of docs/ROMAN-URDU-GOLDEN-PLAN.md, design in
docs/PHASE-5-REVIEW-DESIGN.md §4. Owner ruling P6 (2026-09-25): reviewed on
the Mac, in a desktop browser -- no server, no LAN/iPad delivery.

All data (Urdu, Roman, lint findings, fidelity-findings.tsv rows, ledger
status/note) is inlined into the page as a JS object. Nothing is fetched at
view time. The Urdu text is read from the same `ur-junagarri-simple.db`
lint_roman_urdu.py defaults to -- NEVER the Arabic Quran text.

The page has no filesystem write access. Approve/Needs-fix decisions are
kept in page state, mirrored to localStorage only as a reload safety net
(never the record of truth), and exported via "Download patch" as a TSV:
`ayah, decision(approve|needs-fix), corrected_text, note, seen_sha256`.
`seen_sha256` is this script's sha256 of the Roman text at generation time,
so scripts/apply_review.py can refuse a patch against text that has since
changed.

Usage:
    python3 scripts/review_sheet.py --surah 1
    python3 scripts/review_sheet.py --surah 1 --out out/review/surah-001.html
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import NamedTuple

from lint_roman_urdu import (
    ALLOWLIST_PATH,
    CANONICAL_PATH,
    DEFAULT_SOURCE,
    REVIEW_DIR,
    ROMAN_DIR,
    load_roman,
    load_source,
)
from lint_roman_urdu import run as lint_run
from review_ledger import LedgerRow, load_or_bootstrap_ledger, sha256_hex

ROOT = Path(__file__).resolve().parents[1]
FIDELITY_PATH = ROMAN_DIR / "fidelity-findings.tsv"
PREREVIEW_DIR = ROMAN_DIR / "prereview"
OUT_DIR = ROOT / "out" / "review"

_FIDELITY_FIELDS = ("class", "urdu_span", "roman_span", "suggestion", "confidence", "note")
PREREVIEW_VERDICTS = ("ok", "concern")


class PrereviewError(ValueError):
    """Raised when an AI pre-review TSV row has an unrecognised verdict."""


class PrereviewRow(NamedTuple):
    ayah: int
    verdict: str
    sha256: str
    concern: str
    suggestion: str


def load_prereview_rows(path: Path) -> dict[int, PrereviewRow]:
    """Load one surah's AI pre-review TSV --
    `data/roman-urdu/prereview/surah-NNN.tsv`, header exactly
    `ayah  verdict  sha256  concern  suggestion` -- written by a separate
    agent, never by this one. A missing file means pre-review hasn't reached
    this surah yet, not an error: returns {}. `verdict` must be `ok` or
    `concern`; anything else is a malformed row and raises PrereviewError
    rather than silently passing bad data through to the page."""
    if not path.exists():
        return {}
    rows: dict[int, PrereviewRow] = {}
    with path.open(encoding="utf-8") as fh:
        reader = csv.DictReader(fh, delimiter="\t")
        for raw in reader:
            ayah = int(raw["ayah"])
            verdict = raw["verdict"]
            if verdict not in PREREVIEW_VERDICTS:
                raise PrereviewError(
                    f"{path}: ayah {ayah}: unknown verdict {verdict!r} (expected one of {PREREVIEW_VERDICTS})"
                )
            rows[ayah] = PrereviewRow(
                ayah=ayah,
                verdict=verdict,
                sha256=raw["sha256"] or "",
                # csv.DictReader fills a short row's missing trailing
                # columns with None (its `restval`), not "" -- a real row
                # shape seen in practice for `ok` verses, whose writer omits
                # the empty trailing concern/suggestion tabs entirely.
                concern=raw["concern"] or "",
                suggestion=raw["suggestion"] or "",
            )
    return rows


# ---------------------------------------------------------------------------
# Data assembly -- unit-tested directly (tests/test_review_sheet.py)
# ---------------------------------------------------------------------------

def assemble_review_data(
    surah: int,
    *,
    urdu: dict[int, str],
    roman: dict[int, str],
    findings: list,
    fidelity_rows: list[dict],
    ledger: dict[int, LedgerRow],
    prereview: dict[int, PrereviewRow] | None = None,
) -> dict:
    """Merge one surah's Urdu/Roman text with its lint findings, fidelity
    rows, and review ledger into the page's data structure. A verse with no
    fidelity row gets an empty list, never a missing key."""
    findings_by_ayah: dict[int, list[dict]] = {}
    for f in findings:
        if f.surah != surah:
            continue
        findings_by_ayah.setdefault(f.ayah, []).append(
            {"check": f.check, "level": f.level, "detail": f.detail}
        )

    fidelity_by_ayah: dict[int, list[dict]] = {}
    for row in fidelity_rows:
        if int(row["surah"]) != surah:
            continue
        ayah = int(row["ayah"])
        fidelity_by_ayah.setdefault(ayah, []).append({k: row[k] for k in _FIDELITY_FIELDS})

    prereview = prereview or {}
    ayahs = []
    for ayah in sorted(roman):
        text = roman[ayah]
        ledger_row = ledger.get(ayah)
        prereview_row = prereview.get(ayah)
        if prereview_row is None:
            # No row for this ayah -- either the file doesn't exist yet, or
            # this ayah just isn't in it. Either way: no AI pre-check ran.
            prereview_entry = {"verdict": "none", "concern": "", "suggestion": ""}
        elif prereview_row.sha256 != sha256_hex(text):
            # The stored hash was taken of the text the AI actually read.
            # A mismatch means the verse text changed since -- the verdict
            # no longer applies to what's on the page now.
            prereview_entry = {
                "verdict": "stale",
                "concern": prereview_row.concern,
                "suggestion": prereview_row.suggestion,
            }
        else:
            prereview_entry = {
                "verdict": prereview_row.verdict,
                "concern": prereview_row.concern,
                "suggestion": prereview_row.suggestion,
            }
        ayahs.append({
            "ayah": ayah,
            "urdu": urdu.get(ayah, ""),
            "roman": text,
            "sha256": sha256_hex(text),
            "flags": findings_by_ayah.get(ayah, []),
            "fidelity": fidelity_by_ayah.get(ayah, []),
            "status": ledger_row.status if ledger_row else "pending",
            "note": ledger_row.note if ledger_row else "",
            "prereview": prereview_entry,
        })

    return {"surah": surah, "ayahs": ayahs}


def load_fidelity_rows(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as fh:
        return list(csv.DictReader(fh, delimiter="\t"))


def build_review_data_for_surah(
    surah: int,
    *,
    source: Path = DEFAULT_SOURCE,
    roman_dir: Path = ROMAN_DIR,
    review_dir: Path = REVIEW_DIR,
    canonical_path: Path = CANONICAL_PATH,
    allowlist_path: Path = ALLOWLIST_PATH,
    fidelity_path: Path = FIDELITY_PATH,
    prereview_dir: Path = PREREVIEW_DIR,
) -> dict:
    urdu_all = load_source(source)
    urdu = {a: t for (s, a), t in urdu_all.items() if s == surah}

    roman_all = load_roman(roman_dir)
    roman = {a: t for (s, a), t in roman_all.items() if s == surah}
    if not roman:
        raise SystemExit(f"no Roman Urdu text found for surah {surah} under {roman_dir}")

    findings, _ = lint_run(
        source=source, roman_dir=roman_dir, canonical_path=canonical_path,
        allowlist_path=allowlist_path, review_dir=review_dir, surah=surah,
    )
    fidelity_rows = load_fidelity_rows(fidelity_path)
    ledger = load_or_bootstrap_ledger(
        surah, {str(a): t for a, t in roman.items()}, review_dir=review_dir
    )
    prereview = load_prereview_rows(prereview_dir / f"surah-{surah:03d}.tsv")

    return assemble_review_data(
        surah, urdu=urdu, roman=roman, findings=findings, fidelity_rows=fidelity_rows, ledger=ledger,
        prereview=prereview,
    )


# ---------------------------------------------------------------------------
# HTML rendering -- NOT unit-tested directly, per the design's own test plan
# (§8: "unit-test the data-assembly function directly, not the HTML").
# ---------------------------------------------------------------------------

_PAGE_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Roman Urdu review — Surah {surah:03d}</title>
<style>
:root {{
  --bg: #f7f5f2;
  --panel: #ffffff;
  --text: #1c1a17;
  --muted: #6b645c;
  --border: #e4ddd3;
  --accent: #7a3b12;
  --approve: #1f7a3d;
  --approve-bg: #e5f4ea;
  --fix: #a33b1e;
  --fix-bg: #fbe9e3;
  --chip-error: #b3261e;
  --chip-error-bg: #fbe3e1;
  --chip-warn: #8a5a00;
  --chip-warn-bg: #fbeecb;
  --chip-info: #2454a6;
  --chip-info-bg: #e3ecfb;
  --chip-fidelity: #5a4b8a;
  --chip-fidelity-bg: #ece7f7;
  --precheck-ok: #1f6f5c;
  --precheck-ok-bg: #e2f3ef;
  --precheck-concern: #a3540b;
  --precheck-concern-bg: #fdead2;
  --precheck-stale: #6b645c;
  --precheck-stale-bg: #eee9e2;
}}
@media (prefers-color-scheme: dark) {{
  :root {{
    --bg: #17140f;
    --panel: #211d17;
    --text: #efe9e0;
    --muted: #a89e91;
    --border: #3a342a;
    --accent: #e2a26b;
    --approve: #63c98a;
    --approve-bg: #16301f;
    --fix: #e88a6c;
    --fix-bg: #3a1f16;
    --chip-error: #ff9a90;
    --chip-error-bg: #3a1a17;
    --chip-warn: #f0c66b;
    --chip-warn-bg: #3a2c0e;
    --chip-info: #8fb4f0;
    --chip-info-bg: #16233a;
    --chip-fidelity: #c3b3f0;
    --chip-fidelity-bg: #241c3a;
    --precheck-ok: #7fd9c4;
    --precheck-ok-bg: #123029;
    --precheck-concern: #f2b366;
    --precheck-concern-bg: #3a2712;
    --precheck-stale: #a89e91;
    --precheck-stale-bg: #2a251d;
  }}
}}
* {{ box-sizing: border-box; }}
body {{
  margin: 0;
  background: var(--bg);
  color: var(--text);
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  display: flex;
  flex-direction: column;
  min-height: 100vh;
}}
header {{
  padding: 14px 20px;
  border-bottom: 1px solid var(--border);
  display: flex;
  flex-direction: column;
  gap: 8px;
}}
header .header-top {{
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
}}
header h1 {{ font-size: 1.05rem; margin: 0; font-weight: 600; }}
header .progress {{ color: var(--muted); font-size: 0.9rem; }}
.precheck-header-note {{
  margin: 0;
  font-size: 0.8rem;
  color: var(--muted);
}}
.sort-toggle {{ display: flex; gap: 8px; align-items: center; font-size: 0.85rem; }}
.sort-toggle span {{ color: var(--muted); }}
.sort-btn {{
  font: inherit;
  font-size: 0.8rem;
  padding: 5px 12px;
  border-radius: 999px;
  border: 1px solid var(--border);
  background: var(--panel);
  color: var(--text);
  cursor: pointer;
}}
.sort-btn.active {{ border-color: var(--accent); color: var(--accent); font-weight: 600; }}
main {{
  flex: 1;
  display: flex;
  justify-content: center;
  padding: 24px 16px 120px;
}}
.card {{
  background: var(--panel);
  border: 1px solid var(--border);
  border-radius: 14px;
  padding: 28px;
  max-width: 720px;
  width: 100%;
}}
.urdu {{
  direction: rtl;
  text-align: right;
  font-family: "Noto Nastaliq Urdu", "Jameel Noori Nastaleeq", "Al Qalam Quran Majeed Web",
               "Scheherazade New", "Traditional Arabic", serif;
  font-size: 2rem;
  line-height: 2.4;
  margin: 0 0 20px;
}}
.roman {{
  font-size: 1.3rem;
  line-height: 1.7;
  margin: 0 0 18px;
}}
.chips {{ display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 14px; }}
.chip {{
  font-size: 0.75rem;
  padding: 3px 9px;
  border-radius: 999px;
  border: 1px solid transparent;
  white-space: nowrap;
}}
.chip-error {{ color: var(--chip-error); background: var(--chip-error-bg); }}
.chip-warn {{ color: var(--chip-warn); background: var(--chip-warn-bg); }}
.chip-info {{ color: var(--chip-info); background: var(--chip-info-bg); }}
.chip-fidelity {{ color: var(--chip-fidelity); background: var(--chip-fidelity-bg); }}
.precheck {{
  font-size: 0.85rem;
  line-height: 1.4;
  padding: 8px 12px;
  border-radius: 8px;
  border: 1px solid transparent;
  margin-bottom: 14px;
}}
.precheck-ok {{ color: var(--precheck-ok); background: var(--precheck-ok-bg); border-color: var(--precheck-ok); }}
.precheck-concern {{ color: var(--precheck-concern); background: var(--precheck-concern-bg); border-color: var(--precheck-concern); }}
.precheck-stale {{ color: var(--precheck-stale); background: var(--precheck-stale-bg); border-color: var(--precheck-stale); }}
.precheck-none {{ color: var(--muted); background: transparent; border: 1px dashed var(--border); }}
.status-line {{ color: var(--muted); font-size: 0.85rem; margin-bottom: 18px; }}
.status-line.is-decided {{ color: var(--approve); font-weight: 600; }}
label {{ display: block; font-size: 0.8rem; color: var(--muted); margin: 14px 0 4px; }}
textarea {{
  width: 100%;
  font-family: inherit;
  font-size: 0.95rem;
  padding: 8px 10px;
  border-radius: 8px;
  border: 1px solid var(--border);
  background: var(--bg);
  color: var(--text);
  resize: vertical;
  min-height: 44px;
}}
.actions {{ display: flex; gap: 10px; margin-top: 18px; flex-wrap: wrap; }}
button {{
  font: inherit;
  font-weight: 600;
  padding: 10px 18px;
  border-radius: 9px;
  border: 1px solid var(--border);
  background: var(--panel);
  color: var(--text);
  cursor: pointer;
}}
button.approve {{ color: var(--approve); border-color: var(--approve); background: var(--approve-bg); }}
button.fix {{ color: var(--fix); border-color: var(--fix); background: var(--fix-bg); }}
button:disabled {{ opacity: 0.45; cursor: default; }}
.nav {{
  position: sticky;
  bottom: 0;
  background: var(--panel);
  border-top: 1px solid var(--border);
  padding: 12px 20px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
}}
.nav .side {{ display: flex; gap: 8px; }}
.nav button {{ padding: 8px 16px; }}
.download {{ margin-left: auto; }}
</style>
</head>
<body>
<header>
  <div class="header-top">
    <h1>Surah {surah:03d} — Roman Urdu review</h1>
    <div class="progress" id="progress"></div>
  </div>
  <p class="precheck-header-note">An AI pre-checks every verse before you see it. It is a suggestion only — it never auto-approves, and it never pre-selects Approve. Approval is yours alone.</p>
  <div class="sort-toggle" role="group" aria-label="Verse order">
    <span>Order:</span>
    <button type="button" id="sortAllBtn" class="sort-btn">Show all</button>
    <button type="button" id="sortConcernBtn" class="sort-btn">Concerns &amp; stale first</button>
  </div>
</header>
<main>
  <div class="card" id="card"></div>
</main>
<div class="nav">
  <div class="side">
    <button id="prevBtn" type="button">&larr; prev</button>
    <button id="nextBtn" type="button">next &rarr;</button>
  </div>
  <button id="downloadBtn" class="download" type="button">Download patch (0 decided)</button>
</div>
<script>
const DATA = {data_json};
const STORAGE_KEY = "roman-urdu-review:surah-{surah:03d}";

function loadDecisions() {{
  try {{
    const raw = window.localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : {{}};
  }} catch (e) {{
    return {{}};
  }}
}}

function saveDecisions(decisions) {{
  try {{
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(decisions));
  }} catch (e) {{
    /* localStorage unavailable (private mode, quota) -- page state still holds it */
  }}
}}

let decisions = loadDecisions();
let index = 0;

// Verse order for navigation. "all" is ayah order (the default); "concerns"
// puts every verse whose AI pre-check is "concern" or "stale" first, in a
// stable sort (a plain ayah-order sweep still reaches every verse either
// way -- this only changes what you hit first). Purely a display/triage
// aid: it reorders navigation, never the underlying data, the ledger, or
// which button is selected.
let sortMode = "all";
let order = DATA.ayahs.map((_, i) => i);

function computeOrder(mode) {{
  const idx = DATA.ayahs.map((_, i) => i);
  if (mode === "concerns") {{
    const priority = (v) => (v.prereview.verdict === "concern" || v.prereview.verdict === "stale") ? 0 : 1;
    idx.sort((a, b) => priority(DATA.ayahs[a]) - priority(DATA.ayahs[b]));
  }}
  return idx;
}}

function setSortMode(mode) {{
  sortMode = mode;
  order = computeOrder(mode);
  index = 0;
  render();
}}

function escapeHtml(s) {{
  return String(s).replace(/[&<>"']/g, (c) => ({{
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  }}[c]));
}}

function chipClass(level) {{
  if (level === "error") return "chip chip-error";
  if (level === "warn") return "chip chip-warn";
  return "chip chip-info";
}}

// The AI pre-check is rendered in its own labelled block, never mixed into
// the lint/fidelity `.chips` row -- it is a suggestion from a model, not a
// finding from a rule, and must read as visibly different. It never
// pre-fills or pre-selects Approve/Needs fix below; the owner still clicks.
function precheckClass(verdict) {{
  if (verdict === "ok") return "precheck precheck-ok";
  if (verdict === "concern") return "precheck precheck-concern";
  if (verdict === "stale") return "precheck precheck-stale";
  return "precheck precheck-none";
}}

function precheckText(p) {{
  if (p.verdict === "ok") return "AI pre-check: looks right";
  if (p.verdict === "concern") {{
    return `AI pre-check: concern — ${{escapeHtml(p.concern)}} → suggested: ${{escapeHtml(p.suggestion)}}`;
  }}
  if (p.verdict === "stale") return "AI pre-check: out of date (verse text changed since the AI read it)";
  return "AI pre-check: not yet run for this verse";
}}

function render() {{
  const verse = DATA.ayahs[order[index]];
  const decided = decisions[verse.ayah];

  document.getElementById("progress").textContent =
    `${{index + 1}} / ${{order.length}} — ayah ${{verse.ayah}} — ledger: ${{verse.status}}`;

  document.getElementById("sortAllBtn").classList.toggle("active", sortMode === "all");
  document.getElementById("sortConcernBtn").classList.toggle("active", sortMode === "concerns");

  const flagChips = verse.flags.map(
    (f) => `<span class="${{chipClass(f.level)}}" title="${{escapeHtml(f.detail)}}">${{escapeHtml(f.check)}}</span>`
  ).join("");
  const fidelityChips = verse.fidelity.map(
    (r) => `<span class="chip chip-fidelity" title="${{escapeHtml(r.note)}}">${{escapeHtml(r.class)}} (${{escapeHtml(r.confidence)}})</span>`
  ).join("");
  const chipsHtml = (flagChips || fidelityChips)
    ? `<div class="chips">${{flagChips}}${{fidelityChips}}</div>`
    : `<div class="chips"><span class="chip chip-info">no flags</span></div>`;

  const precheckHtml = `<div class="${{precheckClass(verse.prereview.verdict)}}">${{precheckText(verse.prereview)}}</div>`;

  const statusHtml = decided
    ? `<div class="status-line is-decided">decided this session: ${{escapeHtml(decided.decision)}}</div>`
    : `<div class="status-line">not yet decided this session (ledger: ${{escapeHtml(verse.status)}})</div>`;

  document.getElementById("card").innerHTML = `
    <p class="urdu">${{escapeHtml(verse.urdu)}}</p>
    <p class="roman">${{escapeHtml(verse.roman)}}</p>
    ${{precheckHtml}}
    ${{chipsHtml}}
    ${{statusHtml}}
    <label for="correctedText">Corrected Roman text (needs-fix only, optional)</label>
    <textarea id="correctedText" rows="2">${{decided ? escapeHtml(decided.corrected_text || "") : ""}}</textarea>
    <label for="noteField">Note (required for needs-fix)</label>
    <textarea id="noteField" rows="2">${{decided ? escapeHtml(decided.note || "") : ""}}</textarea>
    <div class="actions">
      <button class="approve" id="approveBtn" type="button">Approve</button>
      <button class="fix" id="fixBtn" type="button">Needs fix</button>
    </div>
  `;

  document.getElementById("approveBtn").addEventListener("click", () => decide("approve"));
  document.getElementById("fixBtn").addEventListener("click", () => decide("needs-fix"));
  document.getElementById("prevBtn").disabled = index === 0;
  document.getElementById("nextBtn").disabled = index === order.length - 1;
  updateDownloadLabel();
}}

function decide(kind) {{
  const verse = DATA.ayahs[order[index]];
  const note = document.getElementById("noteField").value.trim();
  const correctedText = document.getElementById("correctedText").value.trim();

  if (kind === "needs-fix" && !note) {{
    alert("A note is required for Needs fix.");
    return;
  }}

  decisions[verse.ayah] = {{
    decision: kind,
    corrected_text: kind === "needs-fix" ? correctedText : "",
    note: note,
    seen_sha256: verse.sha256,
  }};
  saveDecisions(decisions);
  render();
}}

function updateDownloadLabel() {{
  const n = Object.keys(decisions).length;
  document.getElementById("downloadBtn").textContent = `Download patch (${{n}} decided)`;
}}

function downloadPatch() {{
  const header = "ayah\\tdecision\\tcorrected_text\\tnote\\tseen_sha256";
  const rows = Object.keys(decisions).map(Number).sort((a, b) => a - b).map((ayah) => {{
    const d = decisions[ayah];
    const clean = (s) => String(s || "").replace(/[\\t\\n\\r]/g, " ");
    return [ayah, d.decision, clean(d.corrected_text), clean(d.note), d.seen_sha256].join("\\t");
  }});
  const tsv = [header].concat(rows).join("\\n") + "\\n";
  const blob = new Blob([tsv], {{ type: "text/tab-separated-values" }});
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "surah-{surah:03d}-patch.tsv";
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}}

document.getElementById("prevBtn").addEventListener("click", () => {{ if (index > 0) {{ index -= 1; render(); }} }});
document.getElementById("nextBtn").addEventListener("click", () => {{ if (index < order.length - 1) {{ index += 1; render(); }} }});
document.getElementById("downloadBtn").addEventListener("click", downloadPatch);
document.getElementById("sortAllBtn").addEventListener("click", () => setSortMode("all"));
document.getElementById("sortConcernBtn").addEventListener("click", () => setSortMode("concerns"));

render();
</script>
</body>
</html>
"""


def render_html(data: dict) -> str:
    data_json = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    return _PAGE_TEMPLATE.format(surah=data["surah"], data_json=data_json)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--surah", type=int, required=True)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE, help=f"Urdu source sqlite DB (default: {DEFAULT_SOURCE})")
    parser.add_argument("--roman-dir", type=Path, default=ROMAN_DIR)
    parser.add_argument("--review-dir", type=Path, default=REVIEW_DIR)
    parser.add_argument("--canonical", type=Path, default=CANONICAL_PATH)
    parser.add_argument("--allowlist", type=Path, default=ALLOWLIST_PATH)
    parser.add_argument("--fidelity", type=Path, default=FIDELITY_PATH)
    parser.add_argument("--prereview-dir", type=Path, default=PREREVIEW_DIR, help="AI pre-review TSVs, one per surah (owner decision 2026-09-25)")
    parser.add_argument("--out", type=Path, default=None, help=f"output HTML path (default: {OUT_DIR}/surah-NNN.html)")
    args = parser.parse_args()

    data = build_review_data_for_surah(
        args.surah, source=args.source, roman_dir=args.roman_dir, review_dir=args.review_dir,
        canonical_path=args.canonical, allowlist_path=args.allowlist, fidelity_path=args.fidelity,
        prereview_dir=args.prereview_dir,
    )
    html = render_html(data)

    out_path = args.out or (OUT_DIR / f"surah-{args.surah:03d}.html")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding="utf-8")
    print(f"wrote {out_path} ({len(data['ayahs'])} verses)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
