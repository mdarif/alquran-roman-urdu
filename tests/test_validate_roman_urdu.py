from __future__ import annotations

import json
from pathlib import Path

from validate_roman_urdu import (
    DEFAULT_META,
    expected_counts_from_db,
    expected_counts_from_meta,
    validate_file,
)


def test_expected_counts_from_meta_reads_json(tmp_path: Path) -> None:
    meta = tmp_path / "counts.json"
    meta.write_text(json.dumps({"1": 3, "2": 2}), encoding="utf-8")
    assert expected_counts_from_meta(meta) == {1: 3, 2: 2}


def test_default_meta_file_has_114_surahs_summing_to_6236() -> None:
    counts = expected_counts_from_meta(DEFAULT_META)
    assert len(counts) == 114
    assert sum(counts.values()) == 6236


def test_validate_file_with_gap_fails(tmp_path: Path) -> None:
    path = tmp_path / "surah-001.json"
    path.write_text(
        json.dumps({"surah": 1, "status": "beta-unverified", "ayahs": {"1": "a", "3": "c"}}),
        encoding="utf-8",
    )
    ok, line = validate_file(path, {1: 3})
    assert ok is False
    assert "gaps=[2]" in line


def test_validate_file_with_digit_fails(tmp_path: Path) -> None:
    path = tmp_path / "surah-001.json"
    path.write_text(
        json.dumps({"surah": 1, "status": "beta-unverified", "ayahs": {"1": "a1", "2": "b", "3": "c"}}),
        encoding="utf-8",
    )
    ok, line = validate_file(path, {1: 3})
    assert ok is False
    assert "stray-digits" in line


def test_validate_file_correct_passes(tmp_path: Path) -> None:
    path = tmp_path / "surah-001.json"
    path.write_text(
        json.dumps({"surah": 1, "status": "beta-unverified", "ayahs": {"1": "a", "2": "b", "3": "c"}}),
        encoding="utf-8",
    )
    ok, line = validate_file(path, {1: 3})
    assert ok is True
    assert line.endswith("ok")
