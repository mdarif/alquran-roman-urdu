from __future__ import annotations

import apply_canonical as AC
from lint_roman_urdu import check_capital_start, lint_verse

# Owner ruling Q29 (2026-09-25): every verse starts with a capital letter,
# also when it opens with a bracketed gloss.


def test_lowercase_start_is_error() -> None:
    findings = check_capital_start(1, 1, "jang-e-badr mein")
    assert len(findings) == 1 and findings[0].check == "2l-capital" and findings[0].level == "error"


def test_lowercase_after_opening_bracket_is_error() -> None:
    assert len(check_capital_start(1, 1, "(fay ka maal) un ke liye")) == 1


def test_capital_start_does_not_fire() -> None:
    assert check_capital_start(1, 1, "(Musalmano!) Tumhare liye") == []
    assert check_capital_start(1, 1, "Aur hum ne") == []


def test_lint_verse_includes_capital_start() -> None:
    assert any(f.check == "2l-capital" for f in lint_verse(1, 1, "", "aur hum ne", {}))


def test_capitalise_start() -> None:
    assert AC.capitalise_start("jang-e-badr mein") == ("Jang-e-badr mein", 1)
    assert AC.capitalise_start("(fay ka maal) un") == ("(Fay ka maal) un", 1)
    assert AC.capitalise_start("Aur hum") == ("Aur hum", 0)
