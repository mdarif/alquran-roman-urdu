from __future__ import annotations

import json
from pathlib import Path

from lint_roman_urdu import check_hash, run
from review_ledger import LedgerRow, sha256_hex


# ---------------------------------------------------------------------------
# check_hash: the 2f behaviour, unit-tested directly
# ---------------------------------------------------------------------------

def test_check_hash_approved_row_stale_hash_is_error() -> None:
    row = LedgerRow(ayah=1, status="approved", sha256="0" * 64, reviewer="Abu Rayyan", date="2026-09-25", note="")
    findings = check_hash(1, 1, "Bismillah.", row)
    assert len(findings) == 1
    assert findings[0].check == "2f-hash"
    assert findings[0].level == "error"


def test_check_hash_reviewed_row_stale_hash_is_error() -> None:
    row = LedgerRow(ayah=1, status="reviewed", sha256="0" * 64, reviewer="Abu Rayyan", date="2026-09-25", note="")
    findings = check_hash(1, 1, "Bismillah.", row)
    assert len(findings) == 1
    assert findings[0].check == "2f-hash"
    assert findings[0].level == "error"


def test_check_hash_approved_row_matching_hash_is_clean() -> None:
    text = "Bismillah."
    row = LedgerRow(ayah=1, status="approved", sha256=sha256_hex(text), reviewer="Abu Rayyan", date="2026-09-25", note="")
    assert check_hash(1, 1, text, row) == []


def test_check_hash_verified_row_stale_hash_is_error() -> None:
    # ADR 0006: `verified` rows are hash-pinned exactly like `approved` ones --
    # a later text change must drop the verse back to pending re-review.
    row = LedgerRow(ayah=1, status="verified", sha256="0" * 64, reviewer="AI (double) + owner sample", date="2026-09-25", note="ADR 0006")
    findings = check_hash(1, 1, "Bismillah.", row)
    assert len(findings) == 1
    assert findings[0].check == "2f-hash"
    assert findings[0].level == "error"


def test_check_hash_verified_row_matching_hash_is_clean() -> None:
    text = "Bismillah."
    row = LedgerRow(ayah=1, status="verified", sha256=sha256_hex(text), reviewer="AI (double) + owner sample", date="2026-09-25", note="ADR 0006")
    assert check_hash(1, 1, text, row) == []


def test_check_hash_pending_row_never_checked_even_with_stale_hash() -> None:
    row = LedgerRow(ayah=1, status="pending", sha256="0" * 64, reviewer="", date="", note="")
    assert check_hash(1, 1, "Bismillah.", row) == []


def test_check_hash_missing_ledger_row_is_no_finding() -> None:
    assert check_hash(1, 1, "Bismillah.", None) == []


# ---------------------------------------------------------------------------
# run() integration: missing ledger dir -> inert; a stale approved row fires
# ---------------------------------------------------------------------------

def _make_source_db(path: Path, rows: list[tuple[int, int, str]]) -> None:
    import sqlite3
    con = sqlite3.connect(path)
    con.execute("CREATE TABLE translation (sura INTEGER, ayah INTEGER, ayah_key TEXT, text TEXT)")
    for s, a, text in rows:
        con.execute("INSERT INTO translation VALUES (?, ?, ?, ?)", (s, a, f"{s}:{a}", text))
    con.commit()
    con.close()


def _make_roman_dir(path: Path, surah: int, ayahs: dict[str, str]) -> None:
    path.mkdir(parents=True, exist_ok=True)
    (path / f"surah-{surah:03d}.json").write_text(
        json.dumps({"surah": surah, "status": "beta-unverified", "ayahs": ayahs}), encoding="utf-8"
    )


def _empty_canonical_and_allowlist(tmp_path: Path) -> tuple[Path, Path]:
    canonical = tmp_path / "canonical.tsv"
    canonical.write_text("variant\tcanonical\tcount_2026_09_24\tstatus\tnote\n", encoding="utf-8")
    allowlist = tmp_path / "allowlist.tsv"
    allowlist.write_text("surah\tayah\tcheck\treason\n", encoding="utf-8")
    return canonical, allowlist


def test_run_with_no_review_dir_is_inert_for_2f(tmp_path: Path) -> None:
    db = tmp_path / "source.db"
    _make_source_db(db, [(1, 1, "بسم اللہ")])
    roman_dir = tmp_path / "roman"
    _make_roman_dir(roman_dir, 1, {"1": "Bismillah."})
    canonical, allowlist = _empty_canonical_and_allowlist(tmp_path)

    findings, has_unallowed_error = run(
        source=db, roman_dir=roman_dir, canonical_path=canonical, allowlist_path=allowlist,
        review_dir=tmp_path / "no-such-review-dir",
    )
    assert not any(f.check == "2f-hash" for f in findings)
    assert has_unallowed_error is False


def test_run_flags_stale_approved_hash(tmp_path: Path) -> None:
    db = tmp_path / "source.db"
    _make_source_db(db, [(1, 1, "بسم اللہ")])
    roman_dir = tmp_path / "roman"
    _make_roman_dir(roman_dir, 1, {"1": "Bismillah."})
    canonical, allowlist = _empty_canonical_and_allowlist(tmp_path)

    review_dir = tmp_path / "review"
    review_dir.mkdir()
    (review_dir / "surah-001.tsv").write_text(
        "ayah\tstatus\tsha256\treviewer\tdate\tnote\n"
        "1\tapproved\t" + "0" * 64 + "\tAbu Rayyan\t2026-09-25\t\n",
        encoding="utf-8",
    )

    findings, has_unallowed_error = run(
        source=db, roman_dir=roman_dir, canonical_path=canonical, allowlist_path=allowlist,
        review_dir=review_dir,
    )
    assert any(f.check == "2f-hash" and f.level == "error" for f in findings)
    assert has_unallowed_error is True
