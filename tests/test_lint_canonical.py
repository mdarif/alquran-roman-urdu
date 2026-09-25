from __future__ import annotations

from pathlib import Path

from lint_roman_urdu import check_canonical, load_canonical

CANONICAL_TSV = """variant\tcanonical\tcount_2026_09_24\tstatus\tnote
nahin\tnahi\t956\tdecided\tR2 negative particle
kuchh\tkuch\t344\tdecided\tR3
farmaaya\tfarmaya\t88\tneeds-review\tR1 cluster candidate
kaam\tkaam\t1\tkeep\thomograph, never rewritten
"""


def _write_canonical(tmp_path: Path) -> Path:
    path = tmp_path / "canonical.tsv"
    path.write_text(CANONICAL_TSV, encoding="utf-8")
    return path


def test_load_canonical_reads_variant_canonical_status(tmp_path: Path) -> None:
    path = _write_canonical(tmp_path)
    mapping = load_canonical(path)
    assert mapping["nahin"] == ("nahi", "decided")
    assert mapping["kaam"] == ("kaam", "keep")


def test_check_canonical_fires_error_for_decided_variant(tmp_path: Path) -> None:
    mapping = load_canonical(_write_canonical(tmp_path))
    findings = check_canonical(2, 3, "Is mein koi shak nahin hai.", mapping)
    assert len(findings) == 1
    assert findings[0].check == "2a-canonical"
    assert findings[0].level == "error"
    assert "nahin" in findings[0].detail


def test_check_canonical_fires_info_for_needs_review_variant(tmp_path: Path) -> None:
    mapping = load_canonical(_write_canonical(tmp_path))
    findings = check_canonical(7, 1, "Allah ne farmaaya ke.", mapping)
    assert len(findings) == 1
    assert findings[0].level == "info"


def test_check_canonical_is_whole_word_case_insensitive(tmp_path: Path) -> None:
    mapping = load_canonical(_write_canonical(tmp_path))
    findings = check_canonical(2, 3, "NAHIN chalega.", mapping)
    assert len(findings) == 1
    assert findings[0].level == "error"


def test_check_canonical_does_not_false_fire_on_keep_or_already_canonical(tmp_path: Path) -> None:
    mapping = load_canonical(_write_canonical(tmp_path))
    # "kaam" is a `keep` row -> never flagged even though it's a canonical.tsv variant.
    findings = check_canonical(1, 1, "Yeh mera kaam hai.", mapping)
    assert findings == []
    # "kuch" is the canonical spelling itself (target of kuchh -> kuch), not the variant.
    findings = check_canonical(1, 1, "Kuch log.", mapping)
    assert findings == []
    # A word that's not in canonical.tsv at all.
    findings = check_canonical(1, 1, "Bismillah hi rahman.", mapping)
    assert findings == []


def test_check_canonical_does_not_false_fire_on_substring_match() -> None:
    # "nahin" must not match inside a longer word like "gunahin" (not real, but
    # proves whole-word boundaries, not substring containment).
    mapping = {"nahin": ("nahi", "decided")}
    findings = check_canonical(1, 1, "gunahin", mapping)
    assert findings == []
