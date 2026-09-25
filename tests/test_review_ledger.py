from __future__ import annotations

import json
from pathlib import Path

import pytest

import review_ledger as RL


# ---------------------------------------------------------------------------
# sha256 helper
# ---------------------------------------------------------------------------

def test_sha256_hex_matches_known_vector() -> None:
    # sha256("Bismillah.") -- computed independently with hashlib/openssl.
    assert RL.sha256_hex("Bismillah.") == (
        "5f5d7b8245f0f8dc519d9c5c1876173dce6351b831a927d291796adeb0e940bb"
    )


def test_sha256_hex_is_exact_utf8_bytes_no_normalisation() -> None:
    # Two visually-similar but byte-distinct strings must hash differently --
    # this is what makes the hash catch every byte-level change (design §2).
    assert RL.sha256_hex("nahin") != RL.sha256_hex("nahi")


# ---------------------------------------------------------------------------
# load/save round trip
# ---------------------------------------------------------------------------

def test_save_then_load_round_trip(tmp_path: Path) -> None:
    path = tmp_path / "surah-001.tsv"
    rows = {
        1: RL.LedgerRow(ayah=1, status="pending", sha256="", reviewer="", date="", note=""),
        2: RL.LedgerRow(ayah=2, status="approved", sha256="abc123", reviewer="Abu Rayyan", date="2026-09-25", note="ok"),
    }
    RL.save_ledger(path, rows)
    loaded = RL.load_ledger(path)
    assert loaded == rows


def test_save_writes_tab_separated_header(tmp_path: Path) -> None:
    path = tmp_path / "surah-001.tsv"
    rows = {1: RL.LedgerRow(ayah=1, status="pending", sha256="", reviewer="", date="", note="")}
    RL.save_ledger(path, rows)
    first_line = path.read_text(encoding="utf-8").splitlines()[0]
    assert first_line == "ayah\tstatus\tsha256\treviewer\tdate\tnote"


# ---------------------------------------------------------------------------
# loader rejects gaps / duplicates
# ---------------------------------------------------------------------------

def test_load_ledger_rejects_gap(tmp_path: Path) -> None:
    path = tmp_path / "gap.tsv"
    path.write_text(
        "ayah\tstatus\tsha256\treviewer\tdate\tnote\n"
        "1\tpending\t\t\t\t\n"
        "3\tpending\t\t\t\t\n",
        encoding="utf-8",
    )
    with pytest.raises(RL.LedgerError):
        RL.load_ledger(path)


def test_load_ledger_rejects_duplicate(tmp_path: Path) -> None:
    path = tmp_path / "dup.tsv"
    path.write_text(
        "ayah\tstatus\tsha256\treviewer\tdate\tnote\n"
        "1\tpending\t\t\t\t\n"
        "1\tpending\t\t\t\t\n",
        encoding="utf-8",
    )
    with pytest.raises(RL.LedgerError):
        RL.load_ledger(path)


# ---------------------------------------------------------------------------
# bootstrap
# ---------------------------------------------------------------------------

def test_bootstrap_ledger_creates_all_pending_rows_matching_ayah_count() -> None:
    ayahs = {"1": "one", "2": "two", "3": "three"}
    rows = RL.bootstrap_ledger(surah=1, ayahs=ayahs)
    assert set(rows.keys()) == {1, 2, 3}
    for ayah, row in rows.items():
        assert row.status == "pending"
        assert row.sha256 == ""
        assert row.reviewer == ""
        assert row.date == ""


def test_bootstrap_all_writes_one_ledger_per_surah_file(tmp_path: Path) -> None:
    roman_dir = tmp_path / "roman"
    review_dir = tmp_path / "roman" / "review"
    roman_dir.mkdir()
    (roman_dir / "surah-001.json").write_text(
        json.dumps({"surah": 1, "status": "beta-unverified", "ayahs": {"1": "a", "2": "b"}}),
        encoding="utf-8",
    )
    (roman_dir / "surah-002.json").write_text(
        json.dumps({"surah": 2, "status": "beta-unverified", "ayahs": {"1": "c"}}),
        encoding="utf-8",
    )

    written = RL.bootstrap_all(roman_dir=roman_dir, review_dir=review_dir)

    assert sorted(written) == [1, 2]
    assert (review_dir / "surah-001.tsv").exists()
    assert (review_dir / "surah-002.tsv").exists()
    rows1 = RL.load_ledger(review_dir / "surah-001.tsv")
    assert set(rows1.keys()) == {1, 2}
    assert all(r.status == "pending" for r in rows1.values())


def test_bootstrap_all_does_not_overwrite_existing_ledger(tmp_path: Path) -> None:
    roman_dir = tmp_path / "roman"
    review_dir = tmp_path / "roman" / "review"
    roman_dir.mkdir()
    review_dir.mkdir()
    (roman_dir / "surah-001.json").write_text(
        json.dumps({"surah": 1, "status": "beta-unverified", "ayahs": {"1": "a"}}),
        encoding="utf-8",
    )
    existing = {1: RL.LedgerRow(ayah=1, status="approved", sha256="xyz", reviewer="Abu Rayyan", date="2026-09-25", note="")}
    RL.save_ledger(review_dir / "surah-001.tsv", existing)

    written = RL.bootstrap_all(roman_dir=roman_dir, review_dir=review_dir)

    assert written == []
    reloaded = RL.load_ledger(review_dir / "surah-001.tsv")
    assert reloaded[1].status == "approved"
