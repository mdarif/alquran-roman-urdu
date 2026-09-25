from __future__ import annotations

import json
from pathlib import Path

import pytest

import apply_review as AR
import review_md as RM
from review_ledger import LedgerRow, save_ledger, sha256_hex


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _verse(ayah: int, roman: str = "Roman text.", *, verdict: str = "none",
           concern: str = "", suggestion: str = "", flags: list | None = None,
           fidelity: list | None = None, status: str = "pending", note: str = "") -> dict:
    return {
        "ayah": ayah,
        "urdu": "اردو",
        "roman": roman,
        "sha256": sha256_hex(roman),
        "flags": flags or [],
        "fidelity": fidelity or [],
        "status": status,
        "note": note,
        "prereview": {"verdict": verdict, "concern": concern, "suggestion": suggestion},
    }


def _pending_row(ayah: int) -> LedgerRow:
    return LedgerRow(ayah=ayah, status="pending", sha256="", reviewer="", date="", note="")


# ---------------------------------------------------------------------------
# surah_title
# ---------------------------------------------------------------------------

def test_surah_title_with_name() -> None:
    assert RM.surah_title(2, {2: "Al-Baqarah"}) == "# Surah 2 — Al-Baqarah"


def test_surah_title_without_name_falls_back_to_number_only() -> None:
    assert RM.surah_title(2, {}) == "# Surah 2"


# ---------------------------------------------------------------------------
# render_verse_block
# ---------------------------------------------------------------------------

def test_render_verse_block_has_required_fields() -> None:
    verse = _verse(19, "Roman verse.", verdict="ok")
    block = RM.render_verse_block(2, verse)
    assert "### 2:19" in block
    assert "**Urdu:** اردو" in block
    assert "**Roman:** Roman verse." in block
    assert "**AI:** looks right" in block
    assert "- [ ] approve" in block
    assert "- fix:" in block
    assert "- note:" in block
    assert f"<!-- sha256:{sha256_hex('Roman verse.')} -->" in block


def test_render_verse_block_concern_shows_suggestion() -> None:
    verse = _verse(1, "X.", verdict="concern", concern="wrong word", suggestion="Y.")
    block = RM.render_verse_block(1, verse)
    assert "concern — wrong word → suggested: Y." in block


def test_render_verse_block_stale_reads_out_of_date() -> None:
    verse = _verse(1, "X.", verdict="stale")
    block = RM.render_verse_block(1, verse)
    assert "**AI:** out of date" in block


def test_render_verse_block_none_verdict_reads_not_yet_reviewed() -> None:
    verse = _verse(1, "X.", verdict="none")
    block = RM.render_verse_block(1, verse)
    assert "**AI:** not yet reviewed" in block


def test_render_verse_block_omits_flags_line_when_no_flags() -> None:
    verse = _verse(1, "X.")
    block = RM.render_verse_block(1, verse)
    assert "**Flags:**" not in block


def test_render_verse_block_includes_flags_line_when_present() -> None:
    verse = _verse(1, "X.", flags=[{"check": "2b-parity", "level": "warn", "detail": "d"}],
                    fidelity=[{"class": "omission", "urdu_span": "a", "roman_span": "b",
                               "suggestion": "c", "confidence": "high", "note": "n"}])
    block = RM.render_verse_block(1, verse)
    assert "**Flags:**" in block
    assert "2b-parity: warn" in block
    assert "omission (high)" in block


# ---------------------------------------------------------------------------
# bucket_verses
# ---------------------------------------------------------------------------

def test_bucket_verses_concern_and_stale_go_to_needs_eyes() -> None:
    ayahs = [_verse(1, "A.", verdict="concern"), _verse(2, "B.", verdict="stale")]
    result = RM.bucket_verses(ayahs, {})
    assert [v["ayah"] for v in result["needs_eyes"]] == [1, 2]
    assert result["looks_right"] == []


def test_bucket_verses_ok_and_none_go_to_looks_right() -> None:
    ayahs = [_verse(1, "A.", verdict="ok"), _verse(2, "B.", verdict="none")]
    result = RM.bucket_verses(ayahs, {})
    assert [v["ayah"] for v in result["looks_right"]] == [1, 2]
    assert result["needs_eyes"] == []


def test_bucket_verses_approved_with_matching_hash_goes_to_already_approved() -> None:
    roman = "Approved verse."
    ayahs = [_verse(1, roman, verdict="ok")]
    ledger = {1: LedgerRow(1, "approved", sha256_hex(roman), "Abu Rayyan", "2026-09-25", "")}
    result = RM.bucket_verses(ayahs, ledger)
    assert [v["ayah"] for v in result["already_approved"]] == [1]
    assert result["looks_right"] == []
    assert result["needs_eyes"] == []


def test_bucket_verses_approved_with_stale_hash_is_not_already_approved() -> None:
    # Text changed after approval -- the hash no longer matches, so it must
    # re-enter the ordinary AI buckets, not the no-controls approved list.
    ayahs = [_verse(1, "New text.", verdict="ok")]
    ledger = {1: LedgerRow(1, "approved", sha256_hex("Old text."), "Abu Rayyan", "2026-09-01", "")}
    result = RM.bucket_verses(ayahs, ledger)
    assert result["already_approved"] == []
    assert [v["ayah"] for v in result["looks_right"]] == [1]


def test_bucket_verses_counts_prereview_verdicts() -> None:
    ayahs = [
        _verse(1, "A.", verdict="ok"),
        _verse(2, "B.", verdict="ok"),
        _verse(3, "C.", verdict="concern"),
        _verse(4, "D.", verdict="stale"),
        _verse(5, "E.", verdict="none"),
    ]
    result = RM.bucket_verses(ayahs, {})
    assert result["counts"] == {"ok": 2, "concern": 1, "stale": 1, "none": 1}


# ---------------------------------------------------------------------------
# render_surah_md -- full document shape
# ---------------------------------------------------------------------------

def test_render_surah_md_has_title_instructions_summary_and_sections() -> None:
    roman = "Approved."
    ayahs = [
        _verse(1, "Concern verse.", verdict="concern", concern="x", suggestion="y"),
        _verse(2, "OK verse.", verdict="ok"),
        _verse(3, roman, verdict="ok"),
    ]
    ledger = {3: LedgerRow(3, "approved", sha256_hex(roman), "Abu Rayyan", "2026-09-25", "")}
    md = RM.render_surah_md(2, ayahs, ledger, {2: "Al-Baqarah"})

    assert md.startswith("# Surah 2 — Al-Baqarah")
    assert "approval is yours" in md.lower()
    assert "## Needs your eyes" in md
    assert "## Looks right to the AI" in md
    assert "## Already approved" in md
    # ordering: needs your eyes appears before looks right, which appears
    # before already approved
    assert md.index("## Needs your eyes") < md.index("## Looks right to the AI") < md.index("## Already approved")
    assert "### 2:1" in md
    assert "### 2:2" in md
    # already-approved verses are listed compactly, no controls
    approved_section = md[md.index("## Already approved"):]
    assert "3" in approved_section
    assert "- [ ] approve" not in approved_section
    assert "fix:" not in approved_section


def test_render_surah_md_summary_line_counts() -> None:
    ayahs = [
        _verse(1, "A.", verdict="ok"),
        _verse(2, "B.", verdict="concern"),
        _verse(3, "C.", verdict="stale"),
    ]
    md = RM.render_surah_md(1, ayahs, {}, {})
    assert "3 verses" in md
    assert "1 looks right" in md
    assert "1 concern" in md
    assert "1 out of date" in md


def test_render_surah_md_omits_already_approved_section_when_empty() -> None:
    ayahs = [_verse(1, "A.", verdict="ok")]
    md = RM.render_surah_md(1, ayahs, {}, {})
    assert "## Already approved" not in md


# ---------------------------------------------------------------------------
# parse_md -- approve / fix / ambiguous / missing sha / untouched
# ---------------------------------------------------------------------------

def _block(ayah: int, roman: str, *, checked: bool = False, fix: str = "", note: str = "",
           sha: str | None = None, surah: int = 2) -> str:
    sha = sha256_hex(roman) if sha is None else sha
    box = "x" if checked else " "
    return (
        f"### {surah}:{ayah}\n"
        f"**Urdu:** اردو\n"
        f"**Roman:** {roman}\n"
        f"**AI:** looks right\n"
        f"- [{box}] approve\n"
        f"- fix: {fix}\n"
        f"- note: {note}\n"
        f"<!-- sha256:{sha} -->\n"
    )


def _doc(*blocks: str, surah: int = 2, name: str = "Al-Baqarah") -> str:
    header = f"# Surah {surah} — {name}\n\nHow to review...\n\n## Needs your eyes\n\n"
    return header + "\n".join(blocks)


def test_parse_md_approve_row() -> None:
    text = _doc(_block(19, "Roman verse.", checked=True))
    result = RM.parse_md(text)
    assert result.surah == 2
    assert result.approved == 1
    assert result.needs_fix == 0
    assert result.untouched == 0
    row = result.rows[0]
    assert row.ayah == 19
    assert row.decision == "approve"
    assert row.corrected_text == ""
    assert row.seen_sha256 == sha256_hex("Roman verse.")


def test_parse_md_fix_row() -> None:
    text = _doc(_block(19, "Roman verse.", fix="Corrected roman verse.", note="typo"))
    result = RM.parse_md(text)
    assert result.needs_fix == 1
    assert result.approved == 0
    row = result.rows[0]
    assert row.decision == "needs-fix"
    assert row.corrected_text == "Corrected roman verse."
    assert row.note == "typo"


def test_parse_md_ambiguous_checked_and_fix_raises() -> None:
    text = _doc(_block(19, "Roman verse.", checked=True, fix="Corrected."))
    with pytest.raises(RM.AmbiguousDecisionError):
        RM.parse_md(text)


def test_parse_md_missing_sha_raises() -> None:
    block = _block(19, "Roman verse.").replace(
        f"<!-- sha256:{sha256_hex('Roman verse.')} -->\n", ""
    )
    text = _doc(block)
    with pytest.raises(RM.MissingHashError):
        RM.parse_md(text)


def test_parse_md_untouched_is_omitted() -> None:
    text = _doc(_block(19, "Roman verse."))  # unchecked, empty fix
    result = RM.parse_md(text)
    assert result.rows == []
    assert result.untouched == 1
    assert result.approved == 0
    assert result.needs_fix == 0


def test_parse_md_multi_line_fix_is_joined() -> None:
    block = (
        "### 2:1\n"
        "**Urdu:** اردو\n"
        "**Roman:** Roman verse.\n"
        "**AI:** looks right\n"
        "- [ ] approve\n"
        "- fix: This is a long\n"
        "  corrected verse that wraps.\n"
        "- note: because it was wrong\n"
        f"<!-- sha256:{sha256_hex('Roman verse.')} -->\n"
    )
    result = RM.parse_md(_doc(block))
    assert result.rows[0].corrected_text == "This is a long corrected verse that wraps."


# ---------------------------------------------------------------------------
# round trip: export -> import of an untouched file yields zero rows
# ---------------------------------------------------------------------------

def test_round_trip_export_import_untouched_yields_zero_rows() -> None:
    ayahs = [
        _verse(1, "One.", verdict="ok"),
        _verse(2, "Two.", verdict="concern", concern="x", suggestion="y"),
        _verse(3, "Three.", verdict="stale"),
    ]
    ledger = {i: _pending_row(i) for i in (1, 2, 3)}
    md = RM.render_surah_md(7, ayahs, ledger, {})

    result = RM.parse_md(md)
    assert result.rows == []
    assert result.approved == 0
    assert result.needs_fix == 0
    assert result.untouched == 3


# ---------------------------------------------------------------------------
# write_patch produces exactly the TSV apply_review.py expects, and a real
# apply_patch() run accepts it end-to-end.
# ---------------------------------------------------------------------------

def test_write_patch_header_and_rows(tmp_path: Path) -> None:
    result = RM.ImportResult(
        surah=2,
        rows=[
            RM.ImportedRow(ayah=1, decision="approve", corrected_text="", note="", seen_sha256=sha256_hex("One.")),
            RM.ImportedRow(ayah=2, decision="needs-fix", corrected_text="Fixed two.", note="typo",
                            seen_sha256=sha256_hex("Two.")),
        ],
        approved=1, needs_fix=1, untouched=0,
    )
    out_path = tmp_path / "surah-002-patch.tsv"
    RM.write_patch(result, out_path)
    text = out_path.read_text(encoding="utf-8")
    lines = text.splitlines()
    assert lines[0] == "ayah\tdecision\tcorrected_text\tnote\tseen_sha256"
    assert lines[1] == f"1\tapprove\t\t\t{sha256_hex('One.')}"
    assert lines[2] == f"2\tneeds-fix\tFixed two.\ttypo\t{sha256_hex('Two.')}"


def test_patch_is_accepted_by_apply_review_end_to_end(tmp_path: Path) -> None:
    roman_dir = tmp_path / "roman"
    review_dir = tmp_path / "review"
    roman_dir.mkdir()
    surah_path = roman_dir / "surah-002.json"
    surah_path.write_text(
        json.dumps({"surah": 2, "status": "beta-unverified", "ayahs": {"1": "One.", "2": "Two."}}, indent=2) + "\n",
        encoding="utf-8",
    )
    save_ledger(review_dir / "surah-002.tsv", {1: _pending_row(1), 2: _pending_row(2)})

    ayahs = [_verse(1, "One.", verdict="ok"), _verse(2, "Two.", verdict="concern", concern="x", suggestion="y")]
    ledger = {1: _pending_row(1), 2: _pending_row(2)}
    md = RM.render_surah_md(2, ayahs, ledger, {})

    # Owner approves verse 1, fixes verse 2.
    md = md.replace("### 2:1\n**Urdu:** اردو\n**Roman:** One.\n**AI:** looks right\n- [ ] approve",
                     "### 2:1\n**Urdu:** اردو\n**Roman:** One.\n**AI:** looks right\n- [x] approve")
    md = md.replace("- fix:\n- note:\n<!-- sha256:" + sha256_hex("Two."),
                     "- fix: Two, fixed.\n- note: typo\n<!-- sha256:" + sha256_hex("Two."))

    result = RM.parse_md(md)
    assert result.approved == 1
    assert result.needs_fix == 1

    patch_path = tmp_path / "surah-002-patch.tsv"
    RM.write_patch(result, patch_path)

    report = AR.apply_patch(patch_path, surah=2, reviewer="Abu Rayyan", roman_dir=roman_dir,
                             review_dir=review_dir, today="2026-09-26")

    assert report.approved == [1]
    assert report.needs_fix_applied == [2]
    assert report.refused_stale == []

    data = json.loads(surah_path.read_text(encoding="utf-8"))
    assert data["ayahs"]["2"] == "Two, fixed."


def test_section_heading_after_last_verse_does_not_leak_into_note() -> None:
    # Found in orchestrator end-to-end check 2026-09-25: the last verse of
    # "Needs your eyes" picked up the next "## ..." heading as its note.
    from review_md import parse_md

    text = (
        "# Surah 1\n\n## Needs your eyes\n\n### 1:7\n**Roman:** x\n"
        "- [ ] approve\n- fix: Corrected verse.\n- note:\n<!-- sha256:" + "a" * 64 + " -->\n\n"
        "## Looks right to the AI\n\n### 1:1\n**Roman:** y\n- [ ] approve\n- fix:\n- note:\n"
        "<!-- sha256:" + "b" * 64 + " -->\n"
    )
    rows = parse_md(text).rows
    assert len(rows) == 1
    assert rows[0].corrected_text == "Corrected verse."
    assert rows[0].note == ""
