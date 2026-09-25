from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

import verify_merge as VM
from review_ledger import LedgerRow, load_ledger, save_ledger, sha256_hex


# ---------------------------------------------------------------------------
# fixtures / helpers
# ---------------------------------------------------------------------------

def _write_surah(roman_dir: Path, surah: int, ayahs: dict[str, str], status: str = "beta-unverified") -> Path:
    roman_dir.mkdir(parents=True, exist_ok=True)
    path = roman_dir / f"surah-{surah:03d}.json"
    path.write_text(json.dumps({"surah": surah, "status": status, "ayahs": ayahs}, indent=2) + "\n", encoding="utf-8")
    return path


def _write_ledger(review_dir: Path, surah: int, rows: dict[int, LedgerRow]) -> Path:
    path = review_dir / f"surah-{surah:03d}.tsv"
    save_ledger(path, rows)
    return path


def _pending(ayah: int) -> LedgerRow:
    return LedgerRow(ayah=ayah, status="pending", sha256="", reviewer="", date="", note="")


def _verdict_tsv(rows: list[tuple]) -> str:
    lines = ["ayah\tverdict\tsha256\tconcern\tsuggestion"]
    for r in rows:
        lines.append("\t".join(str(x) for x in r))
    return "\n".join(lines) + "\n"


def _make_source_db(path: Path, rows: list[tuple[int, int, str]]) -> None:
    con = sqlite3.connect(path)
    con.execute("CREATE TABLE translation (sura INTEGER, ayah INTEGER, ayah_key TEXT, text TEXT)")
    for s, a, text in rows:
        con.execute("INSERT INTO translation VALUES (?, ?, ?, ?)", (s, a, f"{s}:{a}", text))
    con.commit()
    con.close()


def _empty_canonical_and_allowlist(tmp_path: Path) -> tuple[Path, Path]:
    canonical = tmp_path / "canonical.tsv"
    canonical.write_text("variant\tcanonical\tcount_2026_09_24\tstatus\tnote\n", encoding="utf-8")
    allowlist = tmp_path / "allowlist.tsv"
    allowlist.write_text("surah\tayah\tcheck\treason\n", encoding="utf-8")
    return canonical, allowlist


def _base_setup(tmp_path: Path):
    roman_dir = tmp_path / "roman"
    review_dir = tmp_path / "review"
    prereview_dir = tmp_path / "prereview"
    verify2_dir = tmp_path / "verify2"
    canonical, allowlist = _empty_canonical_and_allowlist(tmp_path)
    db = tmp_path / "source.db"
    return roman_dir, review_dir, prereview_dir, verify2_dir, canonical, allowlist, db


# ---------------------------------------------------------------------------
# validate_pass2_file
# ---------------------------------------------------------------------------

def test_validate_pass2_file_accepts_matching_valid_file(tmp_path: Path) -> None:
    ayahs = {"1": "One.", "2": "Two."}
    path = tmp_path / "surah-001.tsv"
    path.write_text(_verdict_tsv([
        (1, "ok", sha256_hex("One."), "", ""),
        (2, "concern", sha256_hex("Two."), "typo", "Too."),
    ]), encoding="utf-8")
    assert VM.validate_pass2_file(path, ayahs) == []


def test_validate_pass2_file_rejects_bad_header(tmp_path: Path) -> None:
    path = tmp_path / "surah-001.tsv"
    path.write_text("ayah\tverdict\tsha\n1\tok\tabc\n", encoding="utf-8")
    problems = VM.validate_pass2_file(path, {"1": "One."})
    assert problems


def test_validate_pass2_file_rejects_missing_ayah_row(tmp_path: Path) -> None:
    ayahs = {"1": "One.", "2": "Two."}
    path = tmp_path / "surah-001.tsv"
    path.write_text(_verdict_tsv([(1, "ok", sha256_hex("One."), "", "")]), encoding="utf-8")
    problems = VM.validate_pass2_file(path, ayahs)
    assert any("missing" in p for p in problems)


def test_validate_pass2_file_rejects_stale_sha256(tmp_path: Path) -> None:
    ayahs = {"1": "One."}
    path = tmp_path / "surah-001.tsv"
    path.write_text(_verdict_tsv([(1, "ok", "0" * 64, "", "")]), encoding="utf-8")
    problems = VM.validate_pass2_file(path, ayahs)
    assert any("sha256" in p for p in problems)


def test_validate_pass2_file_rejects_bad_verdict(tmp_path: Path) -> None:
    ayahs = {"1": "One."}
    path = tmp_path / "surah-001.tsv"
    path.write_text(_verdict_tsv([(1, "maybe", sha256_hex("One."), "", "")]), encoding="utf-8")
    problems = VM.validate_pass2_file(path, ayahs)
    assert any("verdict" in p for p in problems)


def test_validate_pass2_file_rejects_duplicate_ayah(tmp_path: Path) -> None:
    ayahs = {"1": "One."}
    path = tmp_path / "surah-001.tsv"
    path.write_text(_verdict_tsv([
        (1, "ok", sha256_hex("One."), "", ""),
        (1, "ok", sha256_hex("One."), "", ""),
    ]), encoding="utf-8")
    problems = VM.validate_pass2_file(path, ayahs)
    assert any("duplicate" in p for p in problems)


# ---------------------------------------------------------------------------
# import_pass2
# ---------------------------------------------------------------------------

def test_import_pass2_copies_valid_files_and_records_source(tmp_path: Path) -> None:
    roman_dir = tmp_path / "roman"
    _write_surah(roman_dir, 1, {"1": "One.", "2": "Two."})
    from_dir = tmp_path / "incoming"
    from_dir.mkdir()
    (from_dir / "surah-001.tsv").write_text(_verdict_tsv([
        (1, "ok", sha256_hex("One."), "", ""),
        (2, "ok", sha256_hex("Two."), "", ""),
    ]), encoding="utf-8")
    verify2_dir = tmp_path / "verify2"

    report = VM.import_pass2(from_dir, source_label="codex gpt-5.5", roman_dir=roman_dir, verify2_dir=verify2_dir)

    assert report.imported == [1]
    assert report.refused == []
    assert (verify2_dir / "surah-001.tsv").exists()
    sources = VM.load_sources(verify2_dir / "SOURCES.tsv")
    assert sources == {1: "codex gpt-5.5"}


def test_import_pass2_refuses_invalid_file_without_copying(tmp_path: Path) -> None:
    roman_dir = tmp_path / "roman"
    _write_surah(roman_dir, 1, {"1": "One."})
    from_dir = tmp_path / "incoming"
    from_dir.mkdir()
    (from_dir / "surah-001.tsv").write_text(_verdict_tsv([(1, "ok", "0" * 64, "", "")]), encoding="utf-8")
    verify2_dir = tmp_path / "verify2"

    report = VM.import_pass2(from_dir, source_label="codex gpt-5.5", roman_dir=roman_dir, verify2_dir=verify2_dir)

    assert report.imported == []
    assert len(report.refused) == 1
    assert not (verify2_dir / "surah-001.tsv").exists()


def test_import_pass2_processes_files_independently(tmp_path: Path) -> None:
    roman_dir = tmp_path / "roman"
    _write_surah(roman_dir, 1, {"1": "One."})
    _write_surah(roman_dir, 2, {"1": "Uno."})
    from_dir = tmp_path / "incoming"
    from_dir.mkdir()
    (from_dir / "surah-001.tsv").write_text(_verdict_tsv([(1, "ok", sha256_hex("One."), "", "")]), encoding="utf-8")
    (from_dir / "surah-002.tsv").write_text(_verdict_tsv([(1, "ok", "0" * 64, "", "")]), encoding="utf-8")
    verify2_dir = tmp_path / "verify2"

    report = VM.import_pass2(from_dir, source_label="claude sonnet", roman_dir=roman_dir, verify2_dir=verify2_dir)

    assert report.imported == [1]
    assert [s for s, _ in report.refused] == [2]
    assert (verify2_dir / "surah-001.tsv").exists()
    assert not (verify2_dir / "surah-002.tsv").exists()


def test_import_pass2_missing_surah_json_is_refused(tmp_path: Path) -> None:
    roman_dir = tmp_path / "roman"
    roman_dir.mkdir()
    from_dir = tmp_path / "incoming"
    from_dir.mkdir()
    (from_dir / "surah-005.tsv").write_text(_verdict_tsv([(1, "ok", "x", "", "")]), encoding="utf-8")
    verify2_dir = tmp_path / "verify2"

    report = VM.import_pass2(from_dir, source_label="codex", roman_dir=roman_dir, verify2_dir=verify2_dir)

    assert report.imported == []
    assert len(report.refused) == 1


def test_import_pass2_reimport_overwrites_source_label(tmp_path: Path) -> None:
    roman_dir = tmp_path / "roman"
    _write_surah(roman_dir, 1, {"1": "One."})
    from_dir = tmp_path / "incoming"
    from_dir.mkdir()
    (from_dir / "surah-001.tsv").write_text(_verdict_tsv([(1, "ok", sha256_hex("One."), "", "")]), encoding="utf-8")
    verify2_dir = tmp_path / "verify2"

    VM.import_pass2(from_dir, source_label="codex gpt-5.5", roman_dir=roman_dir, verify2_dir=verify2_dir)
    VM.import_pass2(from_dir, source_label="claude sonnet", roman_dir=roman_dir, verify2_dir=verify2_dir)

    assert VM.load_sources(verify2_dir / "SOURCES.tsv") == {1: "claude sonnet"}


# ---------------------------------------------------------------------------
# mark
# ---------------------------------------------------------------------------

def test_mark_promotes_double_ok_pending_verse_to_verified(tmp_path: Path) -> None:
    roman_dir, review_dir, prereview_dir, verify2_dir, canonical, allowlist, db = _base_setup(tmp_path)
    _write_surah(roman_dir, 1, {"1": "Bismillah."})
    _write_ledger(review_dir, 1, {1: _pending(1)})
    _make_source_db(db, [(1, 1, "بسم اللہ")])
    prereview_dir.mkdir()
    (prereview_dir / "surah-001.tsv").write_text(_verdict_tsv([(1, "ok", sha256_hex("Bismillah."), "", "")]), encoding="utf-8")
    verify2_dir.mkdir()
    (verify2_dir / "surah-001.tsv").write_text(_verdict_tsv([(1, "ok", sha256_hex("Bismillah."), "", "")]), encoding="utf-8")

    report = VM.mark(
        roman_dir=roman_dir, review_dir=review_dir, prereview_dir=prereview_dir, verify2_dir=verify2_dir,
        canonical_path=canonical, allowlist_path=allowlist, source=db, today="2026-09-26",
    )

    assert report.verified == [(1, 1)]
    rows = load_ledger(review_dir / "surah-001.tsv")
    assert rows[1].status == "verified"
    assert rows[1].sha256 == sha256_hex("Bismillah.")
    assert rows[1].reviewer == "AI (double) + owner sample"
    assert rows[1].date == "2026-09-26"
    assert rows[1].note == "ADR 0006"


def test_mark_dry_run_writes_nothing(tmp_path: Path) -> None:
    roman_dir, review_dir, prereview_dir, verify2_dir, canonical, allowlist, db = _base_setup(tmp_path)
    surah_path = _write_surah(roman_dir, 1, {"1": "Bismillah."})
    ledger_path = _write_ledger(review_dir, 1, {1: _pending(1)})
    _make_source_db(db, [(1, 1, "بسم اللہ")])
    prereview_dir.mkdir()
    (prereview_dir / "surah-001.tsv").write_text(_verdict_tsv([(1, "ok", sha256_hex("Bismillah."), "", "")]), encoding="utf-8")
    verify2_dir.mkdir()
    (verify2_dir / "surah-001.tsv").write_text(_verdict_tsv([(1, "ok", sha256_hex("Bismillah."), "", "")]), encoding="utf-8")

    ledger_before = ledger_path.read_text(encoding="utf-8")
    json_before = surah_path.read_text(encoding="utf-8")

    report = VM.mark(
        roman_dir=roman_dir, review_dir=review_dir, prereview_dir=prereview_dir, verify2_dir=verify2_dir,
        canonical_path=canonical, allowlist_path=allowlist, source=db, today="2026-09-26", dry_run=True,
    )

    assert report.verified == [(1, 1)]  # counted...
    assert ledger_path.read_text(encoding="utf-8") == ledger_before  # ...but nothing written
    assert surah_path.read_text(encoding="utf-8") == json_before


def test_mark_never_touches_approved_row(tmp_path: Path) -> None:
    roman_dir, review_dir, prereview_dir, verify2_dir, canonical, allowlist, db = _base_setup(tmp_path)
    _write_surah(roman_dir, 1, {"1": "Bismillah."})
    approved_row = LedgerRow(1, "approved", sha256_hex("Bismillah."), "Abu Rayyan", "2026-09-01", "owner read")
    _write_ledger(review_dir, 1, {1: approved_row})
    _make_source_db(db, [(1, 1, "بسم اللہ")])
    prereview_dir.mkdir()
    (prereview_dir / "surah-001.tsv").write_text(_verdict_tsv([(1, "ok", sha256_hex("Bismillah."), "", "")]), encoding="utf-8")
    verify2_dir.mkdir()
    (verify2_dir / "surah-001.tsv").write_text(_verdict_tsv([(1, "ok", sha256_hex("Bismillah."), "", "")]), encoding="utf-8")

    report = VM.mark(
        roman_dir=roman_dir, review_dir=review_dir, prereview_dir=prereview_dir, verify2_dir=verify2_dir,
        canonical_path=canonical, allowlist_path=allowlist, source=db, today="2026-09-26",
    )

    assert report.verified == []
    assert report.already_approved == 1
    rows = load_ledger(review_dir / "surah-001.tsv")
    assert rows[1] == approved_row


def test_mark_disagreement_when_either_verdict_concern(tmp_path: Path) -> None:
    roman_dir, review_dir, prereview_dir, verify2_dir, canonical, allowlist, db = _base_setup(tmp_path)
    _write_surah(roman_dir, 1, {"1": "Bismillah."})
    _write_ledger(review_dir, 1, {1: _pending(1)})
    _make_source_db(db, [(1, 1, "بسم اللہ")])
    prereview_dir.mkdir()
    (prereview_dir / "surah-001.tsv").write_text(_verdict_tsv([(1, "concern", sha256_hex("Bismillah."), "typo", "fix")]), encoding="utf-8")
    verify2_dir.mkdir()
    (verify2_dir / "surah-001.tsv").write_text(_verdict_tsv([(1, "ok", sha256_hex("Bismillah."), "", "")]), encoding="utf-8")

    report = VM.mark(
        roman_dir=roman_dir, review_dir=review_dir, prereview_dir=prereview_dir, verify2_dir=verify2_dir,
        canonical_path=canonical, allowlist_path=allowlist, source=db, today="2026-09-26",
    )

    assert report.verified == []
    assert report.disagreements == 1
    rows = load_ledger(review_dir / "surah-001.tsv")
    assert rows[1].status == "pending"


def test_mark_stale_when_pass2_missing(tmp_path: Path) -> None:
    roman_dir, review_dir, prereview_dir, verify2_dir, canonical, allowlist, db = _base_setup(tmp_path)
    _write_surah(roman_dir, 1, {"1": "Bismillah."})
    _write_ledger(review_dir, 1, {1: _pending(1)})
    _make_source_db(db, [(1, 1, "بسم اللہ")])
    prereview_dir.mkdir()
    (prereview_dir / "surah-001.tsv").write_text(_verdict_tsv([(1, "ok", sha256_hex("Bismillah."), "", "")]), encoding="utf-8")
    verify2_dir.mkdir()  # no surah-001.tsv at all

    report = VM.mark(
        roman_dir=roman_dir, review_dir=review_dir, prereview_dir=prereview_dir, verify2_dir=verify2_dir,
        canonical_path=canonical, allowlist_path=allowlist, source=db, today="2026-09-26",
    )

    assert report.verified == []
    assert report.stale == 1


def test_mark_stale_when_hash_mismatch(tmp_path: Path) -> None:
    roman_dir, review_dir, prereview_dir, verify2_dir, canonical, allowlist, db = _base_setup(tmp_path)
    _write_surah(roman_dir, 1, {"1": "Bismillah, edited."})
    _write_ledger(review_dir, 1, {1: _pending(1)})
    _make_source_db(db, [(1, 1, "بسم اللہ")])
    prereview_dir.mkdir()
    (prereview_dir / "surah-001.tsv").write_text(_verdict_tsv([(1, "ok", sha256_hex("Bismillah."), "", "")]), encoding="utf-8")
    verify2_dir.mkdir()
    (verify2_dir / "surah-001.tsv").write_text(_verdict_tsv([(1, "ok", sha256_hex("Bismillah, edited."), "", "")]), encoding="utf-8")

    report = VM.mark(
        roman_dir=roman_dir, review_dir=review_dir, prereview_dir=prereview_dir, verify2_dir=verify2_dir,
        canonical_path=canonical, allowlist_path=allowlist, source=db, today="2026-09-26",
    )

    assert report.verified == []
    assert report.stale == 1


def test_mark_lint_error_blocks_verification(tmp_path: Path) -> None:
    roman_dir, review_dir, prereview_dir, verify2_dir, canonical, allowlist, db = _base_setup(tmp_path)
    text = "mein ne kiya."  # forbidden phrase (2e) -> lint error
    _write_surah(roman_dir, 1, {"1": text})
    _write_ledger(review_dir, 1, {1: _pending(1)})
    _make_source_db(db, [(1, 1, "میں نے کیا")])
    prereview_dir.mkdir()
    (prereview_dir / "surah-001.tsv").write_text(_verdict_tsv([(1, "ok", sha256_hex(text), "", "")]), encoding="utf-8")
    verify2_dir.mkdir()
    (verify2_dir / "surah-001.tsv").write_text(_verdict_tsv([(1, "ok", sha256_hex(text), "", "")]), encoding="utf-8")

    report = VM.mark(
        roman_dir=roman_dir, review_dir=review_dir, prereview_dir=prereview_dir, verify2_dir=verify2_dir,
        canonical_path=canonical, allowlist_path=allowlist, source=db, today="2026-09-26",
    )

    assert report.verified == []
    assert report.lint_blocked == 1
    rows = load_ledger(review_dir / "surah-001.tsv")
    assert rows[1].status == "pending"


def test_mark_updates_file_level_status_on_success(tmp_path: Path) -> None:
    roman_dir, review_dir, prereview_dir, verify2_dir, canonical, allowlist, db = _base_setup(tmp_path)
    surah_path = _write_surah(roman_dir, 1, {"1": "Bismillah."})
    _write_ledger(review_dir, 1, {1: _pending(1)})
    _make_source_db(db, [(1, 1, "بسم اللہ")])
    prereview_dir.mkdir()
    (prereview_dir / "surah-001.tsv").write_text(_verdict_tsv([(1, "ok", sha256_hex("Bismillah."), "", "")]), encoding="utf-8")
    verify2_dir.mkdir()
    (verify2_dir / "surah-001.tsv").write_text(_verdict_tsv([(1, "ok", sha256_hex("Bismillah."), "", "")]), encoding="utf-8")

    VM.mark(
        roman_dir=roman_dir, review_dir=review_dir, prereview_dir=prereview_dir, verify2_dir=verify2_dir,
        canonical_path=canonical, allowlist_path=allowlist, source=db, today="2026-09-26",
    )

    data = json.loads(surah_path.read_text(encoding="utf-8"))
    assert data["status"] == "verified"


# ---------------------------------------------------------------------------
# build_queue / render_queue_md
# ---------------------------------------------------------------------------

def test_build_queue_includes_concern_and_stale_pending_verses_only(tmp_path: Path) -> None:
    roman_dir, review_dir, prereview_dir, verify2_dir, canonical, allowlist, db = _base_setup(tmp_path)
    _write_surah(roman_dir, 1, {"1": "One.", "2": "Two.", "3": "Three."})
    _write_ledger(review_dir, 1, {1: _pending(1), 2: _pending(2), 3: _pending(3)})
    _make_source_db(db, [(1, 1, "ایک"), (1, 2, "دو"), (1, 3, "تین")])
    prereview_dir.mkdir()
    (prereview_dir / "surah-001.tsv").write_text(_verdict_tsv([
        (1, "concern", sha256_hex("One."), "wrong word", "Uno."),
        (2, "ok", sha256_hex("Two."), "", ""),
        (3, "ok", sha256_hex("Three."), "", ""),
    ]), encoding="utf-8")
    verify2_dir.mkdir()
    (verify2_dir / "surah-001.tsv").write_text(_verdict_tsv([
        (1, "ok", sha256_hex("One."), "", ""),
        # ayah 2 missing entirely -> stale
        (3, "ok", sha256_hex("Three."), "", ""),
    ]), encoding="utf-8")

    entries = VM.build_queue(source=db, roman_dir=roman_dir, review_dir=review_dir, prereview_dir=prereview_dir, verify2_dir=verify2_dir)

    assert [(e.surah, e.ayah, e.reason) for e in entries] == [(1, 1, "concern"), (1, 2, "stale")]


def test_build_queue_skips_approved_rows(tmp_path: Path) -> None:
    roman_dir, review_dir, prereview_dir, verify2_dir, canonical, allowlist, db = _base_setup(tmp_path)
    _write_surah(roman_dir, 1, {"1": "One."})
    _write_ledger(review_dir, 1, {1: LedgerRow(1, "approved", sha256_hex("One."), "Abu Rayyan", "2026-09-01", "")})
    _make_source_db(db, [(1, 1, "ایک")])
    prereview_dir.mkdir()
    (prereview_dir / "surah-001.tsv").write_text(_verdict_tsv([(1, "concern", sha256_hex("One."), "x", "y")]), encoding="utf-8")
    verify2_dir.mkdir()

    entries = VM.build_queue(source=db, roman_dir=roman_dir, review_dir=review_dir, prereview_dir=prereview_dir, verify2_dir=verify2_dir)
    assert entries == []


def test_render_queue_md_includes_summary_grouping_and_sha_comment() -> None:
    entries = [
        VM.QueueEntry(surah=1, ayah=1, urdu="ایک", roman="One.", sha256=sha256_hex("One."),
                      pass1="concern — wrong word → suggested: Uno.", pass2="looks right", reason="concern"),
        VM.QueueEntry(surah=2, ayah=5, urdu="دو", roman="Two.", sha256=sha256_hex("Two."),
                      pass1="out of date", pass2="looks right", reason="stale"),
    ]
    md = VM.render_queue_md(entries)
    assert "2 verse(s)" in md
    assert "## Surah 1" in md and "## Surah 2" in md
    assert "### 1:1" in md and "### 2:5" in md
    assert f"<!-- sha256:{sha256_hex('One.')} -->" in md
    assert "- decision:" in md


# ---------------------------------------------------------------------------
# parse_queue_md / write_queue_patches
# ---------------------------------------------------------------------------

def test_parse_queue_md_ok_decision_is_approve() -> None:
    md = (
        "# ADR 0006 disagreement queue\n\n1 verse(s) need a ruling.\n\n"
        "## Surah 1\n\n### 1:7\n**Urdu:** x\n**Roman:** y\n"
        "**Pass 1:** concern\n**Pass 2:** looks right\n"
        "- decision: ok\n"
        f"<!-- sha256:{'a' * 64} -->\n"
    )
    result = VM.parse_queue_md(md)
    assert result.approved == 1
    assert result.rows[0] == VM.QueueImportedRow(surah=1, ayah=7, decision="approve", corrected_text="", seen_sha256="a" * 64)


def test_parse_queue_md_corrected_verse_is_needs_fix() -> None:
    md = (
        "# ADR 0006 disagreement queue\n\n1 verse(s).\n\n"
        "## Surah 1\n\n### 1:7\n**Urdu:** x\n**Roman:** y\n"
        "- decision: The corrected roman verse text.\n"
        f"<!-- sha256:{'b' * 64} -->\n"
    )
    result = VM.parse_queue_md(md)
    assert result.needs_fix == 1
    row = result.rows[0]
    assert row.decision == "needs-fix"
    assert row.corrected_text == "The corrected roman verse text."


def test_parse_queue_md_blank_decision_is_untouched() -> None:
    md = (
        "## Surah 1\n\n### 1:7\n**Urdu:** x\n**Roman:** y\n"
        "- decision:\n"
        f"<!-- sha256:{'c' * 64} -->\n"
    )
    result = VM.parse_queue_md(md)
    assert result.untouched == 1
    assert result.rows == []


def test_parse_queue_md_missing_sha_raises() -> None:
    md = "## Surah 1\n\n### 1:7\n- decision: ok\n"
    with pytest.raises(VM.MissingHashError):
        VM.parse_queue_md(md)


def test_write_queue_patches_splits_by_surah_matching_apply_review_naming(tmp_path: Path) -> None:
    result = VM.QueueImportResult(
        rows=[
            VM.QueueImportedRow(surah=1, ayah=1, decision="approve", corrected_text="", seen_sha256="a" * 64),
            VM.QueueImportedRow(surah=2, ayah=5, decision="needs-fix", corrected_text="Fixed verse.", seen_sha256="b" * 64),
        ],
        approved=1, needs_fix=1, untouched=0,
    )
    out_dir = tmp_path / "out"
    written = VM.write_queue_patches(result, out_dir)

    assert sorted(p.name for p in written) == ["surah-001-patch.tsv", "surah-002-patch.tsv"]
    import apply_review as AR
    assert AR.infer_surah_from_filename(out_dir / "surah-001-patch.tsv") == 1
    text1 = (out_dir / "surah-001-patch.tsv").read_text(encoding="utf-8")
    assert text1.splitlines()[0] == "ayah\tdecision\tcorrected_text\tnote\tseen_sha256"
    assert text1.splitlines()[1].startswith("1\tapprove\t")


def test_queue_import_patch_is_directly_usable_by_apply_review(tmp_path: Path) -> None:
    # End-to-end contract check: queue-import's patch must be exactly what
    # apply_review.py's own parser expects, not just a lookalike TSV.
    roman_dir, review_dir = tmp_path / "roman", tmp_path / "review"
    _write_surah(roman_dir, 1, {"1": "One."})
    _write_ledger(review_dir, 1, {1: _pending(1)})

    result = VM.QueueImportResult(
        rows=[VM.QueueImportedRow(surah=1, ayah=1, decision="approve", corrected_text="", seen_sha256=sha256_hex("One."))],
        approved=1, needs_fix=0, untouched=0,
    )
    out_dir = tmp_path / "patches"
    [patch_path] = VM.write_queue_patches(result, out_dir)

    import apply_review as AR
    report = AR.apply_patch(patch_path, surah=1, reviewer="Abu Rayyan", roman_dir=roman_dir, review_dir=review_dir, today="2026-09-26")
    assert report.approved == [1]


# ---------------------------------------------------------------------------
# collect_verified_verses / stratified_sample / render_sample_md / sample
# ---------------------------------------------------------------------------

def test_collect_verified_verses_only_returns_verified_rows(tmp_path: Path) -> None:
    roman_dir, review_dir = tmp_path / "roman", tmp_path / "review"
    _write_surah(roman_dir, 1, {"1": "One.", "2": "Two."})
    _write_ledger(review_dir, 1, {
        1: LedgerRow(1, "verified", sha256_hex("One."), "AI (double) + owner sample", "2026-09-25", "ADR 0006"),
        2: _pending(2),
    })
    verses = VM.collect_verified_verses(roman_dir=roman_dir, review_dir=review_dir)
    assert verses == [(1, 1, "One.")]


def test_stratified_sample_is_deterministic_for_a_given_seed() -> None:
    verses = [(1, a, f"v{a}") for a in range(1, 21)]
    sources = {1: "codex gpt-5.5"}
    a = VM.stratified_sample(verses, sources, n=5, seed=42)
    b = VM.stratified_sample(verses, sources, n=5, seed=42)
    assert a == b
    assert len(a) == 5


def test_stratified_sample_includes_claude_sonnet_surahs_in_proportion() -> None:
    claude_verses = [(1, a, f"c{a}") for a in range(1, 91)]   # 90 verses, claude sonnet pass-2
    other_verses = [(2, a, f"o{a}") for a in range(1, 11)]    # 10 verses, other pass-2
    verses = claude_verses + other_verses
    sources = {1: "claude sonnet", 2: "codex gpt-5.5"}

    picked = VM.stratified_sample(verses, sources, n=20, seed=1)

    claude_picked = sum(1 for s, _, _ in picked if s == 1)
    other_picked = sum(1 for s, _, _ in picked if s == 2)
    assert len(picked) == 20
    # 90% of the population is claude-sonnet-reviewed -> ~18 of the 20 picks.
    assert claude_picked == 18
    assert other_picked == 2


def test_stratified_sample_caps_at_population_size() -> None:
    verses = [(1, a, f"v{a}") for a in range(1, 6)]
    picked = VM.stratified_sample(verses, {}, n=150, seed=1)
    assert len(picked) == 5


def test_render_sample_md_includes_wrong_line_and_sha_comment() -> None:
    verses = [(1, 1, "One.")]
    md = VM.render_sample_md(verses, {(1, 1): "ایک"})
    assert "### 1:1" in md
    assert "- wrong:" in md
    assert f"<!-- sha256:{sha256_hex('One.')} -->" in md


def test_sample_writes_file_of_requested_size(tmp_path: Path) -> None:
    roman_dir, review_dir, verify2_dir = tmp_path / "roman", tmp_path / "review", tmp_path / "verify2"
    ayahs = {str(i): f"Verse {i}." for i in range(1, 11)}
    _write_surah(roman_dir, 1, ayahs)
    rows = {
        i: LedgerRow(i, "verified", sha256_hex(f"Verse {i}."), "AI (double) + owner sample", "2026-09-25", "ADR 0006")
        for i in range(1, 11)
    }
    _write_ledger(review_dir, 1, rows)
    db = tmp_path / "source.db"
    _make_source_db(db, [(1, i, f"آیت {i}") for i in range(1, 11)])
    out = tmp_path / "sample.md"

    picked = VM.sample(n=3, seed=7, out=out, roman_dir=roman_dir, review_dir=review_dir, verify2_dir=verify2_dir, source=db)

    assert len(picked) == 3
    assert out.exists()
    text = out.read_text(encoding="utf-8")
    # the summary paragraph also mentions "- wrong:" in prose -- count only
    # the per-verse field lines, which stand alone on their own line.
    assert text.count("\n- wrong:\n") == 3


# ---------------------------------------------------------------------------
# parse_sample_md
# ---------------------------------------------------------------------------

def test_parse_sample_md_counts_wrong_and_fine() -> None:
    md = (
        "### 1:1\n**Urdu:** x\n**Roman:** y\n- wrong:\n"
        f"<!-- sha256:{'a' * 64} -->\n\n"
        "### 1:2\n**Urdu:** x\n**Roman:** y\n- wrong: mispronounced vowel, should be 'e' not 'a'\n"
        f"<!-- sha256:{'b' * 64} -->\n"
    )
    result = VM.parse_sample_md(md)
    assert result.total == 2
    assert result.fine == 1
    assert len(result.wrong) == 1
    assert result.wrong[0] == VM.SampleFinding(surah=1, ayah=2, description="mispronounced vowel, should be 'e' not 'a'")


def test_mark_disagreement_when_only_pass2_is_concern(tmp_path: Path) -> None:
    # Found by the orchestrator's sabotage check 2026-09-26: ignoring a
    # pass-2 concern passed every existing test. A verse the second reviewer
    # disputes must never be marked verified.
    roman_dir, review_dir, prereview_dir, verify2_dir, canonical, allowlist, db = _base_setup(tmp_path)
    _write_surah(roman_dir, 1, {"1": "Bismillah."})
    _write_ledger(review_dir, 1, {1: _pending(1)})
    _make_source_db(db, [(1, 1, "بسم اللہ")])
    prereview_dir.mkdir()
    (prereview_dir / "surah-001.tsv").write_text(_verdict_tsv([(1, "ok", sha256_hex("Bismillah."), "", "")]), encoding="utf-8")
    verify2_dir.mkdir()
    (verify2_dir / "surah-001.tsv").write_text(_verdict_tsv([(1, "concern", sha256_hex("Bismillah."), "typo", "fix")]), encoding="utf-8")

    report = VM.mark(
        roman_dir=roman_dir, review_dir=review_dir, prereview_dir=prereview_dir, verify2_dir=verify2_dir,
        canonical_path=canonical, allowlist_path=allowlist, source=db, today="2026-09-26",
    )

    assert report.verified == []
    assert report.disagreements == 1
    assert load_ledger(review_dir / "surah-001.tsv")[1].status == "pending"
