from __future__ import annotations

import json
from pathlib import Path

from status import compute_status


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
