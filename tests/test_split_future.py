from __future__ import annotations

import pytest

import apply_canonical as AC
from lint_roman_urdu import check_split_future, lint_verse

# Owner ruling Q17 (2026-09-25): future verbs are written joined
# ("jaaoge", "kardega"), never split ("jaao ge", "karde ga").


@pytest.mark.parametrize(
    "source,expected",
    [
        ("Tum jaao ge.", "Tum jaaoge."),
        ("Woh tumhein karde ga, phir", "Woh tumhein kardega, phir"),
        ("Kya tum karo ge?", "Kya tum karoge?"),
        ("main bhejoon ga aur", "main bhejoonga aur"),
        ("(jaaye gi,) aur", "(jaayegi,) aur"),
        ("woh kahen ge aur den ge.", "woh kahenge aur denge."),
    ],
)
def test_join_split_futures(source: str, expected: str) -> None:
    text, count = AC.join_split_futures(source)
    assert text == expected
    assert count == source.count(" ga") + source.count(" ge") + source.count(" gi")


@pytest.mark.parametrize(
    "text",
    [
        "Woh chale gaye aur ghaib ki baat ki.",  # gaye, ghaib are not the suffix
        "Woh jaayega aur hum denge.",            # already joined
        "hai, ge",                               # nothing verbal to join to
    ],
)
def test_join_split_futures_leaves_other_text(text: str) -> None:
    assert AC.join_split_futures(text) == (text, 0)


def test_lint_flags_split_future_as_error() -> None:
    findings = check_split_future(1, 1, "Tum jaao ge aur woh karde ga.")
    assert len(findings) == 2
    assert all(f.check == "2j-split-future" and f.level == "error" for f in findings)


def test_lint_split_future_does_not_false_fire() -> None:
    assert check_split_future(1, 1, "Woh chale gaye; tum jaaoge aur woh kardega.") == []


def test_lint_verse_includes_split_future() -> None:
    findings = lint_verse(1, 1, "", "Tum jaao ge.", {})
    assert any(f.check == "2j-split-future" for f in findings)


def test_cli_join_futures_rewrites_corpus(tmp_path) -> None:
    import json

    path = tmp_path / "surah-001.json"
    data = {"surah": 1, "status": "beta-unverified", "ayahs": {"1": "Tum jaao ge.", "2": "Woh gaye."}}
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    assert AC.main(["--join-futures", "--roman-dir", str(tmp_path)]) == 0
    ayahs = json.loads(path.read_text(encoding="utf-8"))["ayahs"]
    assert ayahs == {"1": "Tum jaaoge.", "2": "Woh gaye."}
