from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from lint_roman_urdu import load_allowlist, load_roman, load_source, run


def _make_source_db(path: Path, rows: list[tuple[int, int, str]]) -> None:
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


def test_load_allowlist_reads_tsv(tmp_path: Path) -> None:
    path = tmp_path / "allow.tsv"
    path.write_text("surah\tayah\tcheck\treason\n1\t1\t2e-forbidden\ttest reason\n", encoding="utf-8")
    allowed = load_allowlist(path)
    assert allowed == {(1, 1, "2e-forbidden")}


def test_load_allowlist_missing_file_is_empty(tmp_path: Path) -> None:
    assert load_allowlist(tmp_path / "missing.tsv") == set()


def test_load_source_reads_sqlite(tmp_path: Path) -> None:
    db = tmp_path / "source.db"
    _make_source_db(db, [(1, 1, "بسم اللہ")])
    data = load_source(db)
    assert data[(1, 1)] == "بسم اللہ"


def test_load_roman_reads_json_files(tmp_path: Path) -> None:
    roman_dir = tmp_path / "roman"
    _make_roman_dir(roman_dir, 1, {"1": "Bismillah."})
    data = load_roman(roman_dir)
    assert data[(1, 1)] == "Bismillah."


def test_run_exits_nonzero_on_unallowlisted_error(tmp_path: Path) -> None:
    db = tmp_path / "source.db"
    _make_source_db(db, [(1, 1, "بسم اللہ")])
    roman_dir = tmp_path / "roman"
    _make_roman_dir(roman_dir, 1, {"1": "mein ne kaha."})  # forbidden phrase -> error
    canonical = tmp_path / "canonical.tsv"
    canonical.write_text("variant\tcanonical\tcount_2026_09_24\tstatus\tnote\n", encoding="utf-8")
    allowlist = tmp_path / "allowlist.tsv"
    allowlist.write_text("surah\tayah\tcheck\treason\n", encoding="utf-8")

    findings, has_unallowed_error = run(
        source=db, roman_dir=roman_dir, canonical_path=canonical, allowlist_path=allowlist,
    )
    assert has_unallowed_error is True
    assert any(f.check == "2e-forbidden" for f in findings)


def test_run_allowlisted_error_does_not_fail(tmp_path: Path) -> None:
    db = tmp_path / "source.db"
    _make_source_db(db, [(1, 1, "بسم اللہ")])
    roman_dir = tmp_path / "roman"
    _make_roman_dir(roman_dir, 1, {"1": "mein ne kaha."})
    canonical = tmp_path / "canonical.tsv"
    canonical.write_text("variant\tcanonical\tcount_2026_09_24\tstatus\tnote\n", encoding="utf-8")
    allowlist = tmp_path / "allowlist.tsv"
    allowlist.write_text(
        "surah\tayah\tcheck\treason\n1\t1\t2e-forbidden\tsource glue, verified\n", encoding="utf-8"
    )

    findings, has_unallowed_error = run(
        source=db, roman_dir=roman_dir, canonical_path=canonical, allowlist_path=allowlist,
    )
    assert has_unallowed_error is False
    assert any(f.check == "2e-forbidden" for f in findings)
