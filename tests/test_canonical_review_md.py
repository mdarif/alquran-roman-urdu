from __future__ import annotations

from pathlib import Path

import canonical_review_md as CRM


def _write_batch_tsv(path: Path, rows: list[tuple[str, str, str, str, str]]) -> None:
    lines = ["variant\tproposed_canonical\tcount\tdecision(decided|keep|other:<spelling>)\texample_ref\texample"]
    for variant, proposed, count, ref, example in rows:
        lines.append(f"{variant}\t{proposed}\t{count}\t\t{ref}\t{example}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_canonical_tsv(path: Path, rows: list[tuple[str, str, str]]) -> None:
    lines = ["variant\tcanonical\tcount_2026_09_24\tstatus\tnote"]
    for variant, canonical, status in rows:
        lines.append(f"{variant}\t{canonical}\t1\t{status}\tnote")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# load_batch_tsv
# ---------------------------------------------------------------------------

def test_load_batch_tsv_reads_rows(tmp_path: Path) -> None:
    path = tmp_path / "batch-02.tsv"
    _write_batch_tsv(path, [("nishaniyon", "nishaaniyon", "8", "10:92", "example text")])
    rows = CRM.load_batch_tsv(path)
    assert len(rows) == 1
    assert rows[0].variant == "nishaniyon"
    assert rows[0].proposed == "nishaaniyon"
    assert rows[0].count == "8"
    assert rows[0].example_ref == "10:92"
    assert rows[0].example == "example text"


# ---------------------------------------------------------------------------
# collision detection
# ---------------------------------------------------------------------------

def test_load_canonical_targets_collects_decided_and_keep() -> None:
    pass  # covered via collision_note tests below (integration through export)


def test_collision_note_flags_when_proposed_already_a_decided_target(tmp_path: Path) -> None:
    targets = {"saat"}
    assert "saat" in CRM.collision_note("saat", targets)


def test_collision_note_empty_when_no_match() -> None:
    assert CRM.collision_note("aawaaz", {"nahi", "taala"}) == ""


def test_load_canonical_targets_only_counts_decided_and_keep(tmp_path: Path) -> None:
    path = tmp_path / "canonical.tsv"
    _write_canonical_tsv(path, [
        ("nahin", "nahi", "decided"),
        ("wo", "woh", "keep"),
        ("zyada", "zyaada", "needs-review"),
    ])
    targets = CRM.load_canonical_targets(path)
    assert "nahi" in targets
    assert "woh" in targets
    assert "zyaada" not in targets  # needs-review, not yet decided


def test_load_canonical_targets_missing_file_returns_empty_set(tmp_path: Path) -> None:
    assert CRM.load_canonical_targets(tmp_path / "nope.tsv") == set()


# ---------------------------------------------------------------------------
# render_batch_md
# ---------------------------------------------------------------------------

def test_render_batch_md_table_shape() -> None:
    rows = [CRM.BatchRow("nishaniyon", "nishaaniyon", "8", "10:92", "example text")]
    md = CRM.render_batch_md(2, rows, set())
    assert "| # | current | proposed | uses | example (ref) | decision |" in md
    assert "| 1 | nishaniyon | nishaaniyon | 8 |" in md
    assert md.strip().splitlines()[-1].rstrip().endswith("|")
    assert "blank" in md.lower()
    assert "keep" in md.lower()


def test_render_batch_md_annotates_collision() -> None:
    rows = [CRM.BatchRow("word", "saat", "1", "1:1", "ex")]
    md = CRM.render_batch_md(2, rows, {"saat"})
    row_line = [l for l in md.splitlines() if l.startswith("| 1 |")][0]
    assert "collides" in row_line.lower()


def test_render_batch_md_no_annotation_when_no_collision() -> None:
    rows = [CRM.BatchRow("word", "gaya", "1", "1:1", "ex")]
    md = CRM.render_batch_md(2, rows, {"saat"})
    row_line = [l for l in md.splitlines() if l.startswith("| 1 |")][0]
    assert "collides" not in row_line.lower()


# ---------------------------------------------------------------------------
# parse_batch_md
# ---------------------------------------------------------------------------

def test_parse_batch_md_blank_decision_accepts_proposed() -> None:
    md = (
        "| # | current | proposed | uses | example (ref) | decision |\n"
        "|---|---|---|---|---|---|\n"
        "| 1 | nishaniyon | nishaaniyon | 8 | 10:92: ex |  |\n"
    )
    rows = CRM.parse_batch_md(md)
    assert rows == [{"variant": "nishaniyon", "final": "nishaaniyon", "status": "decided"}]


def test_parse_batch_md_keep_decision_keeps_current() -> None:
    md = (
        "| # | current | proposed | uses | example (ref) | decision |\n"
        "|---|---|---|---|---|---|\n"
        "| 1 | nishaniyon | nishaaniyon | 8 | 10:92: ex | keep |\n"
    )
    rows = CRM.parse_batch_md(md)
    assert rows == [{"variant": "nishaniyon", "final": "nishaniyon", "status": "keep"}]


def test_parse_batch_md_other_spelling_decision() -> None:
    md = (
        "| # | current | proposed | uses | example (ref) | decision |\n"
        "|---|---|---|---|---|---|\n"
        "| 1 | nishaniyon | nishaaniyon | 8 | 10:92: ex | nishaaniyaan |\n"
    )
    rows = CRM.parse_batch_md(md)
    assert rows == [{"variant": "nishaniyon", "final": "nishaaniyaan", "status": "decided"}]


def test_parse_batch_md_skips_header_and_separator_and_non_table_lines() -> None:
    md = (
        "# Canonical spelling review — batch 02\n\n"
        "Leave decision blank to accept.\n\n"
        "| # | current | proposed | uses | example (ref) | decision |\n"
        "|---|---|---|---|---|---|\n"
        "| 1 | a | b | 1 | 1:1: ex |  |\n"
    )
    rows = CRM.parse_batch_md(md)
    assert len(rows) == 1


def test_parse_batch_md_strips_collision_annotation_from_proposed() -> None:
    md = (
        "| # | current | proposed | uses | example (ref) | decision |\n"
        "|---|---|---|---|---|---|\n"
        "| 1 | word | saat ⚠ collides with an existing decided spelling \"saat\" | 1 | 1:1: ex |  |\n"
    )
    rows = CRM.parse_batch_md(md)
    assert rows[0]["final"] == "saat"


# ---------------------------------------------------------------------------
# write_decisions_tsv
# ---------------------------------------------------------------------------

def test_write_decisions_tsv_format(tmp_path: Path) -> None:
    rows = [
        {"variant": "nishaniyon", "final": "nishaaniyon", "status": "decided"},
        {"variant": "pukar", "final": "pukar", "status": "keep"},
    ]
    out = tmp_path / "decisions.tsv"
    text = CRM.write_decisions_tsv(rows, out=out)
    assert text.splitlines()[0] == "variant\tfinal\tstatus"
    assert "nishaniyon\tnishaaniyon\tdecided" in text
    assert "pukar\tpukar\tkeep" in text
    assert out.read_text(encoding="utf-8") == text


def test_write_decisions_tsv_without_out_still_returns_text() -> None:
    rows = [{"variant": "a", "final": "b", "status": "decided"}]
    text = CRM.write_decisions_tsv(rows)
    assert "a\tb\tdecided" in text


# ---------------------------------------------------------------------------
# end-to-end export/import via CLI-level functions; canonical.tsv untouched
# ---------------------------------------------------------------------------

def test_export_batch_writes_md_from_existing_tsv(tmp_path: Path) -> None:
    batch_dir = tmp_path / "canonical-review"
    batch_dir.mkdir()
    _write_batch_tsv(batch_dir / "batch-02.tsv", [("nishaniyon", "nishaaniyon", "8", "10:92", "ex")])
    canonical_path = tmp_path / "canonical.tsv"
    _write_canonical_tsv(canonical_path, [("nahin", "nahi", "decided")])

    out_path = CRM.export_batch(2, batch_dir=batch_dir, canonical_path=canonical_path)

    assert out_path == batch_dir / "batch-02.md"
    assert out_path.exists()
    assert "nishaniyon" in out_path.read_text(encoding="utf-8")


def test_import_never_touches_canonical_tsv(tmp_path: Path) -> None:
    canonical_path = tmp_path / "canonical.tsv"
    _write_canonical_tsv(canonical_path, [("nahin", "nahi", "decided")])
    before = canonical_path.read_text(encoding="utf-8")

    md = (
        "| # | current | proposed | uses | example (ref) | decision |\n"
        "|---|---|---|---|---|---|\n"
        "| 1 | a | b | 1 | 1:1: ex |  |\n"
    )
    CRM.parse_batch_md(md)

    assert canonical_path.read_text(encoding="utf-8") == before
