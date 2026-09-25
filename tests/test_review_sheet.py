from __future__ import annotations

from pathlib import Path

import pytest

from lint_roman_urdu import Finding
from review_ledger import LedgerRow, sha256_hex
from review_sheet import PrereviewError, PrereviewRow, assemble_review_data, load_prereview_rows


def _ledger(ayah: int, status: str, text: str = "", reviewer: str = "", date: str = "", note: str = "") -> LedgerRow:
    sha = sha256_hex(text) if status in ("reviewed", "approved") else ""
    return LedgerRow(ayah=ayah, status=status, sha256=sha, reviewer=reviewer, date=date, note=note)


def test_assemble_review_data_basic_shape() -> None:
    urdu = {1: "بسم اللہ", 2: "دوسری آیت"}
    roman = {1: "Bismillah.", 2: "Dusri ayat."}
    findings = [Finding(1, 1, "2e-forbidden", "error", "digit: '5'")]
    fidelity_rows = [
        {"surah": "1", "ayah": "1", "class": "omission", "urdu_span": "x", "roman_span": "y",
         "suggestion": "z", "confidence": "high", "note": "n"},
    ]
    ledger = {
        1: _ledger(1, "pending"),
        2: _ledger(2, "approved", text="Dusri ayat.", reviewer="Abu Rayyan", date="2026-09-25", note="ok"),
    }

    data = assemble_review_data(
        1, urdu=urdu, roman=roman, findings=findings, fidelity_rows=fidelity_rows, ledger=ledger,
    )

    assert data["surah"] == 1
    assert len(data["ayahs"]) == 2

    v1 = data["ayahs"][0]
    assert v1["ayah"] == 1
    assert v1["urdu"] == "بسم اللہ"
    assert v1["roman"] == "Bismillah."
    assert v1["sha256"] == sha256_hex("Bismillah.")
    assert v1["flags"] == [{"check": "2e-forbidden", "level": "error", "detail": "digit: '5'"}]
    assert v1["fidelity"] == [
        {"class": "omission", "urdu_span": "x", "roman_span": "y", "suggestion": "z", "confidence": "high", "note": "n"}
    ]
    assert v1["status"] == "pending"
    assert v1["note"] == ""

    v2 = data["ayahs"][1]
    assert v2["fidelity"] == []  # no fidelity row for this verse -> empty list, not a missing key
    assert v2["status"] == "approved"
    assert v2["note"] == "ok"


def test_assemble_review_data_excludes_other_surah_findings_and_fidelity() -> None:
    urdu = {1: "ایک"}
    roman = {1: "Ek."}
    findings = [Finding(2, 1, "2e-forbidden", "error", "wrong surah")]
    fidelity_rows = [{"surah": "2", "ayah": "1", "class": "omission", "urdu_span": "a", "roman_span": "b",
                       "suggestion": "c", "confidence": "low", "note": "wrong surah"}]
    ledger: dict[int, LedgerRow] = {}

    data = assemble_review_data(1, urdu=urdu, roman=roman, findings=findings, fidelity_rows=fidelity_rows, ledger=ledger)

    v1 = data["ayahs"][0]
    assert v1["flags"] == []
    assert v1["fidelity"] == []


def test_assemble_review_data_missing_ledger_row_defaults_to_pending() -> None:
    urdu = {1: "ایک"}
    roman = {1: "Ek."}
    data = assemble_review_data(1, urdu=urdu, roman=roman, findings=[], fidelity_rows=[], ledger={})
    v1 = data["ayahs"][0]
    assert v1["status"] == "pending"
    assert v1["note"] == ""


def test_assemble_review_data_sorts_verses_numerically_not_lexically() -> None:
    urdu = {1: "a", 2: "b", 10: "c"}
    roman = {1: "a", 2: "b", 10: "c"}
    data = assemble_review_data(1, urdu=urdu, roman=roman, findings=[], fidelity_rows=[], ledger={})
    assert [v["ayah"] for v in data["ayahs"]] == [1, 2, 10]


# ---------------------------------------------------------------------------
# AI pre-review loader -- data/roman-urdu/prereview/surah-NNN.tsv
# header: ayah  verdict  sha256  concern  suggestion
# ---------------------------------------------------------------------------

def _write_prereview(path: Path, body: str) -> None:
    path.write_text("ayah\tverdict\tsha256\tconcern\tsuggestion\n" + body, encoding="utf-8")


def test_load_prereview_rows_missing_file_returns_empty(tmp_path: Path) -> None:
    assert load_prereview_rows(tmp_path / "surah-001.tsv") == {}


def test_load_prereview_rows_parses_ok_and_concern_rows(tmp_path: Path) -> None:
    path = tmp_path / "surah-001.tsv"
    _write_prereview(
        path,
        f"1\tok\t{sha256_hex('Bismillah.')}\t\t\n"
        f"2\tconcern\t{sha256_hex('Dusri ayat.')}\tsounds off\ttry X\n",
    )
    rows = load_prereview_rows(path)
    assert rows[1] == PrereviewRow(ayah=1, verdict="ok", sha256=sha256_hex("Bismillah."), concern="", suggestion="")
    assert rows[2] == PrereviewRow(
        ayah=2, verdict="concern", sha256=sha256_hex("Dusri ayat."), concern="sounds off", suggestion="try X"
    )


def test_load_prereview_rows_rejects_malformed_verdict(tmp_path: Path) -> None:
    path = tmp_path / "surah-001.tsv"
    _write_prereview(path, "1\tmaybe\t\t\t\n")
    with pytest.raises(PrereviewError):
        load_prereview_rows(path)


def test_load_prereview_rows_short_row_missing_trailing_columns_reads_as_empty_string(tmp_path: Path) -> None:
    # Real-world shape seen in the other agent's output: an `ok` row's
    # trailing tabs for concern/suggestion are omitted entirely rather than
    # written empty, so csv.DictReader's restval (None) would otherwise leak
    # through instead of the spec's "empty for ok".
    path = tmp_path / "surah-001.tsv"
    path.write_text(f"ayah\tverdict\tsha256\tconcern\tsuggestion\n1\tok\t{sha256_hex('Ek.')}\n", encoding="utf-8")
    rows = load_prereview_rows(path)
    assert rows[1].concern == ""
    assert rows[1].suggestion == ""


# ---------------------------------------------------------------------------
# assemble_review_data's per-verse "prereview" entry
# ---------------------------------------------------------------------------

def test_assemble_review_data_prereview_ok() -> None:
    roman = {1: "Ek."}
    prereview = {1: PrereviewRow(ayah=1, verdict="ok", sha256=sha256_hex("Ek."), concern="", suggestion="")}
    data = assemble_review_data(
        1, urdu={1: "a"}, roman=roman, findings=[], fidelity_rows=[], ledger={}, prereview=prereview,
    )
    assert data["ayahs"][0]["prereview"] == {"verdict": "ok", "concern": "", "suggestion": ""}


def test_assemble_review_data_prereview_concern() -> None:
    roman = {1: "Ek."}
    prereview = {
        1: PrereviewRow(ayah=1, verdict="concern", sha256=sha256_hex("Ek."), concern="sounds off", suggestion="try X"),
    }
    data = assemble_review_data(
        1, urdu={1: "a"}, roman=roman, findings=[], fidelity_rows=[], ledger={}, prereview=prereview,
    )
    assert data["ayahs"][0]["prereview"] == {"verdict": "concern", "concern": "sounds off", "suggestion": "try X"}


def test_assemble_review_data_prereview_stale_when_hash_mismatches() -> None:
    # The AI read a different byte-string than what's in the JSON now --
    # the text changed after the pre-review ran.
    roman = {1: "Ek naya."}
    prereview = {1: PrereviewRow(ayah=1, verdict="ok", sha256=sha256_hex("Ek purana."), concern="", suggestion="")}
    data = assemble_review_data(
        1, urdu={1: "a"}, roman=roman, findings=[], fidelity_rows=[], ledger={}, prereview=prereview,
    )
    assert data["ayahs"][0]["prereview"]["verdict"] == "stale"


def test_assemble_review_data_prereview_none_when_no_row_or_file() -> None:
    roman = {1: "Ek."}
    data = assemble_review_data(
        1, urdu={1: "a"}, roman=roman, findings=[], fidelity_rows=[], ledger={}, prereview={},
    )
    assert data["ayahs"][0]["prereview"] == {"verdict": "none", "concern": "", "suggestion": ""}


def test_assemble_review_data_prereview_defaults_to_none_when_omitted() -> None:
    # Callers that don't pass prereview= at all (back-compat) must still get
    # a well-formed entry, never a missing key.
    roman = {1: "Ek."}
    data = assemble_review_data(1, urdu={1: "a"}, roman=roman, findings=[], fidelity_rows=[], ledger={})
    assert data["ayahs"][0]["prereview"] == {"verdict": "none", "concern": "", "suggestion": ""}
