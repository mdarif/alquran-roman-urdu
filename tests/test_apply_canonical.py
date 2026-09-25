from __future__ import annotations

import json
from pathlib import Path

import pytest

import apply_canonical as AC


ROOT = Path(__file__).resolve().parents[1]
ROMAN_DIR = ROOT / "data" / "roman-urdu"


# ---------------------------------------------------------------------------
# apply_rule: whole-word, case-preserving replacement
# ---------------------------------------------------------------------------

def test_apply_rule_lowercase_to_lowercase() -> None:
    text, count = AC.apply_rule("Is mein koi shak nahin hai.", "nahin", "nahi")
    assert text == "Is mein koi shak nahi hai."
    assert count == 1


def test_apply_rule_capitalised_to_capitalised() -> None:
    text, count = AC.apply_rule("Nahin, aisa nahin.", "nahin", "nahi")
    assert text == "Nahi, aisa nahi."
    assert count == 2


def test_apply_rule_upper_to_upper() -> None:
    text, count = AC.apply_rule("NAHIN chalega.", "nahin", "nahi")
    assert text == "NAHI chalega."
    assert count == 1


def test_apply_rule_is_whole_word_not_substring() -> None:
    # "unhe" must not match inside "unhen" -- a different row with a
    # different canonical target (unhein vs unhen->unhein).
    text, count = AC.apply_rule("unhen unhe ko diya.", "unhe", "unhein")
    assert text == "unhen unhein ko diya."
    assert count == 1


def test_apply_rule_no_match_leaves_text_untouched() -> None:
    text, count = AC.apply_rule("Bismillah hi rahman.", "nahin", "nahi")
    assert text == "Bismillah hi rahman."
    assert count == 0


def test_apply_rule_multiple_occurrences_mixed_case() -> None:
    text, count = AC.apply_rule("Kuchh log kuchh nahi jaante KUCHH.", "kuchh", "kuch")
    assert text == "Kuch log kuch nahi jaante KUCH."
    assert count == 3


# ---------------------------------------------------------------------------
# Taala: always capital T regardless of source case (ADR 0005 R2/R5 special case)
# ---------------------------------------------------------------------------

def test_apply_rule_taala_always_capitalised_from_lowercase() -> None:
    text, count = AC.apply_rule("Haq ta'ala ne farmaaya.", "ta'ala", "taala")
    assert text == "Haq Taala ne farmaaya."
    assert count == 1


def test_apply_rule_taala_always_capitalised_even_if_source_uppercase() -> None:
    text, count = AC.apply_rule("HAQ TA'ALA NE FARMAAYA.", "ta'ala", "taala")
    assert "TAALA" not in text
    assert "Taala" in text
    assert count == 1


# ---------------------------------------------------------------------------
# Hyphenated tokens
# ---------------------------------------------------------------------------

def test_apply_rule_does_not_match_variant_inside_hyphenated_compound() -> None:
    # "ne'mat" has its own row (-> nemat), but must not fire inside the
    # separate hyphenated-compound row "ne'mat-o-fazl" (-> nemat-o-fazl).
    text, count = AC.apply_rule("Uski ne'mat-o-fazl bohat hai.", "ne'mat", "nemat")
    assert text == "Uski ne'mat-o-fazl bohat hai."
    assert count == 0


def test_apply_rule_hyphenated_variant_matches_whole_compound() -> None:
    text, count = AC.apply_rule("Uski ne'mat-o-fazl bohat hai.", "ne'mat-o-fazl", "nemat-o-fazl")
    assert text == "Uski nemat-o-fazl bohat hai."
    assert count == 1


def test_apply_rule_hyphenated_variant_preserves_per_segment_capitalisation() -> None:
    text, count = AC.apply_rule(
        "Wahan Mash'ar-e-Haraam ke paas.", "mash'ar-e-haraam", "mashar-e-haraam"
    )
    assert text == "Wahan Mashar-e-Haraam ke paas."
    assert count == 1


def test_apply_rule_unrelated_hyphenated_word_untouched() -> None:
    # A word that happens to share a substring with a variant, but is part of
    # an unrelated hyphenated compound not covered by any row, must be left
    # alone entirely.
    text, count = AC.apply_rule("kitab-e-kamil", "kamil", "kaamil")
    assert text == "kitab-e-kamil"
    assert count == 0


# ---------------------------------------------------------------------------
# Honorific normalisation (scope B, R4)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "source,expected",
    [
        ("Moosa (alaihis salaam) ne kaha.", "Moosa (Alaihis-Salaam) ne kaha."),
        ("(alaihis-salaam)", "(Alaihis-Salaam)"),
        ("(alaihimus salaam)", "(Alaihimus-Salaam)"),
        ("(alaihimas-salaam)", "(Alaihimas-Salaam)"),  # dual, owner Q1 2026-09-25
        ("(alaihim salaam)", "(Alaihimus-Salaam)"),
        ("(alaiha salaam)", "(Alaihas-Salaam)"),
        ("(sallallahu alaihi wasallam)", "(Sallallahu Alaihi Wasallam)"),
        ("(Sallallahu Alaihi Wa Sallam)", "(Sallallahu Alaihi Wasallam)"),
    ],
)
def test_apply_honorifics_normalises_standalone_span(source: str, expected: str) -> None:
    text, count = AC.apply_honorifics(source)
    assert text == expected
    assert count == 1


def test_apply_honorifics_leaves_already_canonical_form_untouched() -> None:
    text, count = AC.apply_honorifics("Moosa (Alaihis-Salaam) ne kaha.")
    assert text == "Moosa (Alaihis-Salaam) ne kaha."
    assert count == 0


@pytest.mark.parametrize(
    "source,expected",
    [
        # Owner ruling Q2 (2026-09-25): inside a longer gloss the honorific is
        # capitalised and hyphenated but gets no brackets of its own.
        ("(Yaqoob alaihis salaam ne) kaha.", "(Yaqoob Alaihis-Salaam ne) kaha."),
        ("(Hazrat Yunus alaihis salaam) ko", "(Hazrat Yunus Alaihis-Salaam) ko"),
        ("(Nabi sallallahu alaihi wasallam)", "(Nabi Sallallahu Alaihi Wasallam)"),
        ("(Moosa alaihimas salaam ki)", "(Moosa Alaihimas-Salaam ki)"),
    ],
)
def test_apply_honorifics_normalises_honorific_inside_longer_gloss(source: str, expected: str) -> None:
    text, count = AC.apply_honorifics(source)
    assert text == expected
    assert count == 1


def test_apply_honorifics_leaves_canonical_gloss_honorific_untouched() -> None:
    text, count = AC.apply_honorifics("(Yaqoob Alaihis-Salaam ne) kaha.")
    assert text == "(Yaqoob Alaihis-Salaam ne) kaha."
    assert count == 0


def test_apply_honorifics_does_not_touch_non_honorific_brackets() -> None:
    text, count = AC.apply_honorifics("Firaun ne kaha (sardaar) hai.")
    assert text == "Firaun ne kaha (sardaar) hai."
    assert count == 0


def test_apply_honorifics_multiple_spans_in_one_verse() -> None:
    text, count = AC.apply_honorifics(
        "Ibraheem (alaihis salaam) aur Ismail (alaihis salaam) ne dua ki."
    )
    assert text == "Ibraheem (Alaihis-Salaam) aur Ismail (Alaihis-Salaam) ne dua ki."
    assert count == 2


# ---------------------------------------------------------------------------
# JSON round-trip: formatting must be byte-identical when nothing changes
# ---------------------------------------------------------------------------

def test_json_round_trip_is_byte_identical_for_untouched_file() -> None:
    path = ROMAN_DIR / "surah-114.json"
    raw = path.read_text(encoding="utf-8")
    data = json.loads(raw)
    dumped = AC.dump_json_like(data)
    assert dumped == raw


# ---------------------------------------------------------------------------
# decided-only guard
# ---------------------------------------------------------------------------

def test_load_canonical_real_file_has_decided_rows() -> None:
    mapping = AC.load_canonical()
    assert mapping["nahin"] == ("nahi", "decided")
    assert mapping["par"][1] == "keep"
