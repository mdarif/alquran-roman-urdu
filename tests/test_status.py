from __future__ import annotations

import json
from pathlib import Path

from status import (
    compute_review_status,
    compute_status,
    derive_file_status,
    write_status_all,
    write_status_for_surah,
)
from review_ledger import LedgerRow, save_ledger, sha256_hex


def _write_surah(dir_: Path, surah: int, status: str, n_ayahs: int) -> None:
    ayahs = {str(i): f"verse {i}" for i in range(1, n_ayahs + 1)}
    (dir_ / f"surah-{surah:03d}.json").write_text(
        json.dumps({"surah": surah, "status": status, "ayahs": ayahs}), encoding="utf-8"
    )


def test_compute_status_on_fixture_dir(tmp_path: Path) -> None:
    _write_surah(tmp_path, 1, "beta-unverified", 3)
    _write_surah(tmp_path, 2, "beta-unverified", 5)
    _write_surah(tmp_path, 3, "approved", 2)

    report = compute_status(tmp_path)

    assert report["files"] == 3
    assert report["verses"] == 10
    assert report["by_status"]["beta-unverified"] == {"files": 2, "verses": 8}
    assert report["by_status"]["approved"] == {"files": 1, "verses": 2}


def test_compute_status_on_real_corpus_totals_6236() -> None:
    from status import ROMAN_DIR

    report = compute_status(ROMAN_DIR)
    assert report["files"] == 114
    assert report["verses"] == 6236


# ---------------------------------------------------------------------------
# derive_file_status — design §3 derivation table
# ---------------------------------------------------------------------------

def _row(ayah: int, status: str, text: str) -> LedgerRow:
    sha = sha256_hex(text) if status in ("reviewed", "approved") else ""
    return LedgerRow(ayah=ayah, status=status, sha256=sha, reviewer="Abu Rayyan", date="2026-09-25", note="")


def test_derive_file_status_all_approved_hash_clean_is_approved() -> None:
    ayahs = {"1": "one", "2": "two"}
    rows = {1: _row(1, "approved", "one"), 2: _row(2, "approved", "two")}
    assert derive_file_status(rows, ayahs) == "approved"


def test_derive_file_status_all_reviewed_or_approved_none_pending_is_reviewed() -> None:
    ayahs = {"1": "one", "2": "two"}
    rows = {1: _row(1, "reviewed", "one"), 2: _row(2, "approved", "two")}
    assert derive_file_status(rows, ayahs) == "reviewed"


def test_derive_file_status_one_pending_row_is_beta_unverified() -> None:
    ayahs = {"1": "one", "2": "two"}
    rows = {1: _row(1, "pending", "one"), 2: _row(2, "approved", "two")}
    assert derive_file_status(rows, ayahs) == "beta-unverified"


def test_derive_file_status_approved_with_stale_hash_is_not_approved() -> None:
    ayahs = {"1": "one-EDITED"}
    rows = {1: _row(1, "approved", "one")}  # hash was computed against the old text
    assert derive_file_status(rows, ayahs) == "reviewed"


def test_derive_file_status_no_ledger_rows_is_beta_unverified() -> None:
    ayahs = {"1": "one"}
    assert derive_file_status({}, ayahs) == "beta-unverified"


# ---------------------------------------------------------------------------
# compute_review_status
# ---------------------------------------------------------------------------

def test_compute_review_status_counts_verses_by_ledger_status(tmp_path: Path) -> None:
    review_dir = tmp_path / "review"
    save_ledger(review_dir / "surah-001.tsv", {
        1: _row(1, "pending", "a"),
        2: _row(2, "approved", "b"),
    })
    save_ledger(review_dir / "surah-002.tsv", {
        1: _row(1, "reviewed", "c"),
    })

    report = compute_review_status(review_dir)

    assert report == {"pending": 1, "reviewed": 1, "approved": 1}


def test_compute_review_status_missing_dir_is_all_zero(tmp_path: Path) -> None:
    report = compute_review_status(tmp_path / "no-such-dir")
    assert report == {"pending": 0, "reviewed": 0, "approved": 0}


# ---------------------------------------------------------------------------
# write_status_for_surah / write_status_all
# ---------------------------------------------------------------------------

def test_write_status_for_surah_rewrites_only_status_key(tmp_path: Path) -> None:
    roman_dir = tmp_path / "roman"
    roman_dir.mkdir()
    review_dir = tmp_path / "review"
    path = roman_dir / "surah-001.json"
    path.write_text(json.dumps({
        "surah": 1, "status": "beta-unverified", "register": "popular",
        "ayahs": {"1": "one", "2": "two"},
    }, indent=2) + "\n", encoding="utf-8")
    save_ledger(review_dir / "surah-001.tsv", {
        1: _row(1, "approved", "one"),
        2: _row(2, "approved", "two"),
    })

    result = write_status_for_surah(1, roman_dir=roman_dir, review_dir=review_dir)

    assert result == ("beta-unverified", "approved")
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["status"] == "approved"
    assert data["register"] == "popular"
    assert data["ayahs"] == {"1": "one", "2": "two"}


def test_write_status_for_surah_no_change_leaves_file_byte_identical(tmp_path: Path) -> None:
    roman_dir = tmp_path / "roman"
    roman_dir.mkdir()
    review_dir = tmp_path / "review"
    path = roman_dir / "surah-001.json"
    raw = json.dumps({"surah": 1, "status": "beta-unverified", "ayahs": {"1": "one"}}, indent=2) + "\n"
    path.write_text(raw, encoding="utf-8")
    save_ledger(review_dir / "surah-001.tsv", {1: _row(1, "pending", "one")})

    write_status_for_surah(1, roman_dir=roman_dir, review_dir=review_dir)

    assert path.read_text(encoding="utf-8") == raw


def test_write_status_all_reports_changes_for_fixture(tmp_path: Path) -> None:
    roman_dir = tmp_path / "roman"
    roman_dir.mkdir()
    review_dir = tmp_path / "review"
    (roman_dir / "surah-001.json").write_text(
        json.dumps({"surah": 1, "status": "beta-unverified", "ayahs": {"1": "one"}}, indent=2) + "\n",
        encoding="utf-8",
    )
    (roman_dir / "surah-002.json").write_text(
        json.dumps({"surah": 2, "status": "beta-unverified", "ayahs": {"1": "two"}}, indent=2) + "\n",
        encoding="utf-8",
    )
    save_ledger(review_dir / "surah-001.tsv", {1: _row(1, "approved", "one")})
    save_ledger(review_dir / "surah-002.tsv", {1: _row(1, "pending", "two")})

    changes = write_status_all(roman_dir=roman_dir, review_dir=review_dir)

    assert changes == [(1, "beta-unverified", "approved")]
    assert json.loads((roman_dir / "surah-001.json").read_text())["status"] == "approved"
    assert json.loads((roman_dir / "surah-002.json").read_text())["status"] == "beta-unverified"


def test_write_status_all_on_real_corpus_with_everything_pending_makes_no_changes() -> None:
    from status import REVIEW_DIR, ROMAN_DIR

    changes = write_status_all(roman_dir=ROMAN_DIR, review_dir=REVIEW_DIR)
    assert changes == []
