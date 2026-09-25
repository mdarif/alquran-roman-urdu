"""Owner-locked spellings in data/roman-urdu/canonical.tsv.

These tests read the real canonical.tsv on purpose: they guard owner
rulings that are deliberate exceptions to a general rule, so a later
mechanical rule (e.g. an R5 apostrophe sweep) cannot quietly undo them.
"""
from __future__ import annotations

import csv
from pathlib import Path

CANONICAL = Path(__file__).resolve().parents[1] / "data" / "roman-urdu" / "canonical.tsv"


def _rows() -> dict[str, dict[str, str]]:
    with CANONICAL.open(encoding="utf-8") as f:
        return {r["variant"]: r for r in csv.DictReader(f, delimiter="\t")}


def test_taa_eed_is_locked_with_its_apostrophe() -> None:
    # Owner ruling 2026-09-26: تائید is "taa'eed", a deliberate exception to R5.
    rows = _rows()
    assert rows["taa'eed"]["status"] == "keep"
    assert rows["taa'eed"]["canonical"] == "taa'eed"
    for variant in ("taeed", "taaeed", "taayeed"):
        assert rows[variant]["status"] == "decided", variant
        assert rows[variant]["canonical"] == "taa'eed", variant


def test_no_rule_rewrites_taa_eed() -> None:
    rows = _rows()
    offenders = [v for v, r in rows.items()
                 if r["status"] == "decided" and v == "taa'eed" and r["canonical"] != "taa'eed"]
    assert offenders == []
