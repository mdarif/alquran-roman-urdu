from __future__ import annotations

import json
from pathlib import Path

import pytest

import apply_review as AR
from review_ledger import LedgerRow, load_ledger, save_ledger, sha256_hex


def _write_surah(roman_dir: Path, surah: int, ayahs: dict[str, str], status: str = "beta-unverified") -> Path:
    roman_dir.mkdir(parents=True, exist_ok=True)
    path = roman_dir / f"surah-{surah:03d}.json"
    path.write_text(json.dumps({"surah": surah, "status": status, "ayahs": ayahs}, indent=2) + "\n", encoding="utf-8")
    return path


def _write_ledger(review_dir: Path, surah: int, rows: dict[int, LedgerRow]) -> Path:
    path = review_dir / f"surah-{surah:03d}.tsv"
    save_ledger(path, rows)
    return path


def _write_patch(path: Path, rows: list[dict]) -> None:
    lines = ["ayah\tdecision\tcorrected_text\tnote\tseen_sha256"]
    for r in rows:
        lines.append("\t".join([
            str(r["ayah"]), r["decision"], r.get("corrected_text", ""), r.get("note", ""), r["seen_sha256"],
        ]))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _pending_row(ayah: int) -> LedgerRow:
    return LedgerRow(ayah=ayah, status="pending", sha256="", reviewer="", date="", note="")


# ---------------------------------------------------------------------------
# approve
# ---------------------------------------------------------------------------

def test_approve_matching_hash_writes_ledger(tmp_path: Path) -> None:
    roman_dir, review_dir = tmp_path / "roman", tmp_path / "review"
    _write_surah(roman_dir, 1, {"1": "Bismillah."})
    _write_ledger(review_dir, 1, {1: _pending_row(1)})
    patch = tmp_path / "surah-001-patch.tsv"
    _write_patch(patch, [{"ayah": 1, "decision": "approve", "seen_sha256": sha256_hex("Bismillah.")}])

    report = AR.apply_patch(patch, surah=1, reviewer="Abu Rayyan", roman_dir=roman_dir, review_dir=review_dir, today="2026-09-26")

    assert report.approved == [1]
    assert report.refused_stale == []
    rows = load_ledger(review_dir / "surah-001.tsv")
    assert rows[1].status == "approved"
    assert rows[1].sha256 == sha256_hex("Bismillah.")
    assert rows[1].reviewer == "Abu Rayyan"
    assert rows[1].date == "2026-09-26"


def test_approve_stale_hash_is_refused_and_ledger_untouched(tmp_path: Path) -> None:
    roman_dir, review_dir = tmp_path / "roman", tmp_path / "review"
    _write_surah(roman_dir, 1, {"1": "Bismillah."})
    _write_ledger(review_dir, 1, {1: _pending_row(1)})
    patch = tmp_path / "surah-001-patch.tsv"
    _write_patch(patch, [{"ayah": 1, "decision": "approve", "seen_sha256": "0" * 64}])

    report = AR.apply_patch(patch, surah=1, reviewer="Abu Rayyan", roman_dir=roman_dir, review_dir=review_dir, today="2026-09-26")

    assert report.approved == []
    assert [ayah for ayah, _reason in report.refused_stale] == [1]
    rows = load_ledger(review_dir / "surah-001.tsv")
    assert rows[1] == _pending_row(1)


# ---------------------------------------------------------------------------
# needs-fix with corrected_text
# ---------------------------------------------------------------------------

def test_needs_fix_matching_text_applies_edit_and_resets_ledger(tmp_path: Path) -> None:
    roman_dir, review_dir = tmp_path / "roman", tmp_path / "review"
    surah_path = _write_surah(roman_dir, 1, {"1": "Bismillah.", "2": "Second."})
    _write_ledger(review_dir, 1, {
        1: LedgerRow(1, "approved", sha256_hex("Bismillah."), "Abu Rayyan", "2026-09-01", "old note"),
        2: _pending_row(2),
    })
    patch = tmp_path / "surah-001-patch.tsv"
    _write_patch(patch, [{
        "ayah": 1, "decision": "needs-fix", "corrected_text": "Bismillah, fixed.",
        "note": "typo", "seen_sha256": sha256_hex("Bismillah."),
    }])

    report = AR.apply_patch(patch, surah=1, reviewer="Abu Rayyan", roman_dir=roman_dir, review_dir=review_dir, today="2026-09-26")

    assert report.needs_fix_applied == [1]
    data = json.loads(surah_path.read_text(encoding="utf-8"))
    assert data["ayahs"]["1"] == "Bismillah, fixed."
    assert data["ayahs"]["2"] == "Second."  # untouched

    rows = load_ledger(review_dir / "surah-001.tsv")
    assert rows[1].status == "pending"
    assert rows[1].reviewer == ""
    assert rows[1].date == ""
    assert "typo" in rows[1].note
    assert rows[1].sha256 == sha256_hex("Bismillah, fixed.")


def test_needs_fix_stale_text_is_refused_and_nothing_applied(tmp_path: Path) -> None:
    roman_dir, review_dir = tmp_path / "roman", tmp_path / "review"
    surah_path = _write_surah(roman_dir, 1, {"1": "Bismillah."})
    _write_ledger(review_dir, 1, {1: _pending_row(1)})
    patch = tmp_path / "surah-001-patch.tsv"
    _write_patch(patch, [{
        "ayah": 1, "decision": "needs-fix", "corrected_text": "Bismillah, fixed.",
        "note": "typo", "seen_sha256": "0" * 64,
    }])

    report = AR.apply_patch(patch, surah=1, reviewer="Abu Rayyan", roman_dir=roman_dir, review_dir=review_dir, today="2026-09-26")

    assert report.needs_fix_applied == []
    assert [ayah for ayah, _reason in report.refused_stale] == [1]
    data = json.loads(surah_path.read_text(encoding="utf-8"))
    assert data["ayahs"]["1"] == "Bismillah."
    rows = load_ledger(review_dir / "surah-001.tsv")
    assert rows[1] == _pending_row(1)


# ---------------------------------------------------------------------------
# needs-fix with no corrected_text
# ---------------------------------------------------------------------------

def test_needs_fix_no_text_leaves_text_untouched_and_records_note(tmp_path: Path) -> None:
    roman_dir, review_dir = tmp_path / "roman", tmp_path / "review"
    surah_path = _write_surah(roman_dir, 1, {"1": "Bismillah."})
    _write_ledger(review_dir, 1, {
        1: LedgerRow(1, "approved", sha256_hex("Bismillah."), "Abu Rayyan", "2026-09-01", "old note"),
    })
    patch = tmp_path / "surah-001-patch.tsv"
    _write_patch(patch, [{
        "ayah": 1, "decision": "needs-fix", "note": "awkward phrasing, flagging for later",
        "seen_sha256": sha256_hex("Bismillah."),
    }])

    report = AR.apply_patch(patch, surah=1, reviewer="Abu Rayyan", roman_dir=roman_dir, review_dir=review_dir, today="2026-09-26")

    assert report.needs_fix_flagged == [1]
    data = json.loads(surah_path.read_text(encoding="utf-8"))
    assert data["ayahs"]["1"] == "Bismillah."  # text untouched

    rows = load_ledger(review_dir / "surah-001.tsv")
    assert rows[1].status == "pending"
    assert rows[1].reviewer == ""
    assert rows[1].date == ""
    assert "awkward phrasing" in rows[1].note


# ---------------------------------------------------------------------------
# unknown ayah -> hard error, no writes at all
# ---------------------------------------------------------------------------

def test_unknown_ayah_is_hard_error_and_nothing_written(tmp_path: Path) -> None:
    roman_dir, review_dir = tmp_path / "roman", tmp_path / "review"
    _write_surah(roman_dir, 1, {"1": "Bismillah."})
    ledger_path = _write_ledger(review_dir, 1, {1: _pending_row(1)})
    ledger_before = ledger_path.read_text(encoding="utf-8")
    patch = tmp_path / "surah-001-patch.tsv"
    _write_patch(patch, [{"ayah": 99, "decision": "approve", "seen_sha256": "0" * 64}])

    with pytest.raises(AR.UnknownAyahError):
        AR.apply_patch(patch, surah=1, reviewer="Abu Rayyan", roman_dir=roman_dir, review_dir=review_dir, today="2026-09-26")

    assert ledger_path.read_text(encoding="utf-8") == ledger_before


# ---------------------------------------------------------------------------
# rows not in the patch are never touched
# ---------------------------------------------------------------------------

def test_rows_not_in_patch_are_never_touched(tmp_path: Path) -> None:
    roman_dir, review_dir = tmp_path / "roman", tmp_path / "review"
    _write_surah(roman_dir, 1, {"1": "One.", "2": "Two.", "3": "Three."})
    _write_ledger(review_dir, 1, {1: _pending_row(1), 2: _pending_row(2), 3: _pending_row(3)})
    patch = tmp_path / "surah-001-patch.tsv"
    _write_patch(patch, [{"ayah": 1, "decision": "approve", "seen_sha256": sha256_hex("One.")}])

    AR.apply_patch(patch, surah=1, reviewer="Abu Rayyan", roman_dir=roman_dir, review_dir=review_dir, today="2026-09-26")

    rows = load_ledger(review_dir / "surah-001.tsv")
    assert rows[2] == _pending_row(2)
    assert rows[3] == _pending_row(3)


# ---------------------------------------------------------------------------
# --dry-run writes nothing
# ---------------------------------------------------------------------------

def test_dry_run_writes_nothing(tmp_path: Path) -> None:
    roman_dir, review_dir = tmp_path / "roman", tmp_path / "review"
    surah_path = _write_surah(roman_dir, 1, {"1": "Bismillah."})
    ledger_path = _write_ledger(review_dir, 1, {1: _pending_row(1)})
    json_before = surah_path.read_text(encoding="utf-8")
    ledger_before = ledger_path.read_text(encoding="utf-8")

    patch = tmp_path / "surah-001-patch.tsv"
    _write_patch(patch, [{"ayah": 1, "decision": "approve", "seen_sha256": sha256_hex("Bismillah.")}])

    report = AR.apply_patch(
        patch, surah=1, reviewer="Abu Rayyan", roman_dir=roman_dir, review_dir=review_dir,
        today="2026-09-26", dry_run=True,
    )

    assert report.approved == [1]  # counted...
    assert surah_path.read_text(encoding="utf-8") == json_before  # ...but nothing written
    assert ledger_path.read_text(encoding="utf-8") == ledger_before


# ---------------------------------------------------------------------------
# on success, write-status is invoked for that surah
# ---------------------------------------------------------------------------

def test_successful_apply_updates_file_level_status(tmp_path: Path) -> None:
    roman_dir, review_dir = tmp_path / "roman", tmp_path / "review"
    surah_path = _write_surah(roman_dir, 1, {"1": "Bismillah."})
    _write_ledger(review_dir, 1, {1: _pending_row(1)})
    patch = tmp_path / "surah-001-patch.tsv"
    _write_patch(patch, [{"ayah": 1, "decision": "approve", "seen_sha256": sha256_hex("Bismillah.")}])

    AR.apply_patch(patch, surah=1, reviewer="Abu Rayyan", roman_dir=roman_dir, review_dir=review_dir, today="2026-09-26")

    data = json.loads(surah_path.read_text(encoding="utf-8"))
    assert data["status"] == "approved"
