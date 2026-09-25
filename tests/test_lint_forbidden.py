from __future__ import annotations

from lint_roman_urdu import check_forbidden


def test_forbidden_fires_on_mein_ne() -> None:
    findings = check_forbidden(1, 1, "mein ne kaha.")
    assert any("mein ne" in f.detail for f in findings)
    assert all(f.level == "error" for f in findings)


def test_forbidden_fires_on_standalone_kay_key_wo() -> None:
    assert check_forbidden(1, 1, "kay log.") != []
    assert check_forbidden(1, 1, "key log.") != []
    assert check_forbidden(1, 1, "wo log.") != []


def test_forbidden_fires_on_digits() -> None:
    findings = check_forbidden(1, 1, "parhezgaro1 the.")
    assert any("digit" in f.detail for f in findings)


def test_forbidden_fires_on_non_ascii() -> None:
    findings = check_forbidden(1, 1, "Yeh farmaaya’.")  # curly apostrophe
    assert any("non-ascii" in f.detail for f in findings)


def test_forbidden_does_not_false_fire_on_clean_text() -> None:
    findings = check_forbidden(1, 1, "Main ne kaha ke kuch nahi tha.")
    assert findings == []


def test_forbidden_does_not_false_fire_on_kay_as_substring() -> None:
    # "kay" embedded inside another word must not trip the standalone check.
    findings = check_forbidden(1, 1, "sikay chamke.")
    assert findings == []
