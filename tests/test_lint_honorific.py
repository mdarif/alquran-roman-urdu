from __future__ import annotations

from lint_roman_urdu import check_honorific_typography


def test_honorific_fires_info_when_adr_unsigned() -> None:
    findings = check_honorific_typography(1, 1, "Moosa (alaihis salaam) ne kaha.", adr_0005_accepted=False)
    honorific = [f for f in findings if f.check == "2g-honorific"]
    assert len(honorific) == 1
    assert honorific[0].level == "info"


def test_honorific_fires_error_when_adr_signed() -> None:
    findings = check_honorific_typography(1, 1, "Moosa (alaihis salaam) ne kaha.", adr_0005_accepted=True)
    honorific = [f for f in findings if f.check == "2g-honorific"]
    assert len(honorific) == 1
    assert honorific[0].level == "error"


def test_honorific_does_not_false_fire_on_canonical_form() -> None:
    findings = check_honorific_typography(1, 1, "Moosa (Alaihis-Salaam) ne kaha.", adr_0005_accepted=False)
    assert [f for f in findings if f.check == "2g-honorific"] == []


def test_honorific_does_not_false_fire_on_canonical_prophet_form() -> None:
    findings = check_honorific_typography(
        1, 1, "Nabi (Sallallahu Alaihi Wasallam) ne farmaaya.", adr_0005_accepted=True
    )
    assert [f for f in findings if f.check == "2g-honorific"] == []


def test_honorific_does_not_touch_non_honorific_brackets() -> None:
    findings = check_honorific_typography(1, 1, "Firaun ne kaha (sardaar) hai.", adr_0005_accepted=True)
    assert [f for f in findings if f.check == "2g-honorific"] == []


def test_unbalanced_parens_fires_as_error_regardless_of_adr() -> None:
    for adr in (False, True):
        findings = check_honorific_typography(1, 1, "Moosa (alaihis salaam ne kaha.", adr_0005_accepted=adr)
        parens = [f for f in findings if f.check == "2g-parens"]
        assert len(parens) == 1
        assert parens[0].level == "error"


def test_balanced_parens_does_not_false_fire() -> None:
    findings = check_honorific_typography(1, 1, "Firaun ne kaha (sardaar) hai.", adr_0005_accepted=False)
    assert [f for f in findings if f.check == "2g-parens"] == []


# ---------------------------------------------------------------------------
# ADR 0005 is now ACCEPTED: standalone non-canonical honorifics are `error`,
# but an honorific embedded inside a longer translator's gloss (the nested-
# honorific question the owner left open, ADR 0005 R4) stays `info` even
# once the ADR is signed -- that specific sub-question is still unresolved.
# ---------------------------------------------------------------------------

def test_gloss_embedded_noncanonical_honorific_is_error() -> None:
    # Owner ruling Q2 (2026-09-25) settled the nested case.
    findings = check_honorific_typography(1, 1, "(Yaqoob alaihis salaam ne) kaha.", adr_0005_accepted=True)
    honorific = [f for f in findings if f.check == "2g-honorific"]
    assert len(honorific) == 1
    assert honorific[0].level == "error"


def test_gloss_embedded_canonical_honorific_does_not_fire() -> None:
    findings = check_honorific_typography(1, 1, "(Ibraheem Alaihis-Salaam ne) dua ki.", adr_0005_accepted=True)
    assert [f for f in findings if f.check == "2g-honorific"] == []


def test_dual_honorific_is_allowed() -> None:
    # Owner ruling Q1 (2026-09-25): dual form (Alaihimas-Salaam).
    findings = check_honorific_typography(1, 1, "Moosa aur Haroon (Alaihimas-Salaam).", adr_0005_accepted=True)
    assert [f for f in findings if f.check == "2g-honorific"] == []


def test_standalone_honorific_is_error_when_adr_signed() -> None:
    findings = check_honorific_typography(1, 1, "Moosa (alaihimas-salaam) ne kaha.", adr_0005_accepted=True)
    honorific = [f for f in findings if f.check == "2g-honorific"]
    assert len(honorific) == 1
    assert honorific[0].level == "error"


def test_module_default_reflects_adr_accepted() -> None:
    import lint_roman_urdu as L

    assert L.ADR_0005_ACCEPTED is True
    for text in ("Moosa (alaihis salaam) ne kaha.", "(Yaqoob alaihis salaam ne) kaha."):
        findings = check_honorific_typography(1, 1, text)
        honorific = [f for f in findings if f.check == "2g-honorific"]
        assert honorific[0].level == "error"
