from __future__ import annotations

import pytest

import apply_canonical as AC
from lint_roman_urdu import check_misl, lint_verse

# Owner ruling Q19 (2026-09-25), following Q6 at 70:8: "misl X ke", never
# "misl-e-X ke". The Urdu writes no izafat.


@pytest.mark.parametrize(
    "source,expected",
    [
        ("misl-e-mahal ke", "misl mahal ke"),
        ("Misl-e-tez garam paani", "Misl tez garam paani"),
        ("ek misl-e-rangeen oon ke aur misl-e-talchhat ke", "ek misl rangeen oon ke aur misl talchhat ke"),
    ],
)
def test_drop_misl_izafat(source: str, expected: str) -> None:
    text, count = AC.drop_misl_izafat(source)
    assert text == expected
    assert count == source.lower().count("misl-e-")


def test_drop_misl_izafat_leaves_other_izafat() -> None:
    text = "raah-e-raast aur misl tel ki talchhat ke"
    assert AC.drop_misl_izafat(text) == (text, 0)


def test_lint_flags_misl_izafat() -> None:
    findings = check_misl(1, 1, "misl-e-mahal ke")
    assert len(findings) == 1 and findings[0].check == "2k-misl" and findings[0].level == "error"


def test_lint_misl_does_not_false_fire() -> None:
    assert check_misl(1, 1, "misl tel ki talchhat ke, raah-e-raast") == []


def test_lint_verse_includes_misl() -> None:
    assert any(f.check == "2k-misl" for f in lint_verse(1, 1, "", "misl-e-mahal ke", {}))


def test_cli_misl_rewrites_corpus(tmp_path) -> None:
    import json

    path = tmp_path / "surah-001.json"
    path.write_text(json.dumps({"surah": 1, "ayahs": {"1": "misl-e-mahal ke"}}, indent=2) + "\n", encoding="utf-8")
    assert AC.main(["--misl", "--roman-dir", str(tmp_path)]) == 0
    assert json.loads(path.read_text(encoding="utf-8"))["ayahs"] == {"1": "misl mahal ke"}
