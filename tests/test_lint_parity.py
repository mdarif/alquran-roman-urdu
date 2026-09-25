from __future__ import annotations

from lint_roman_urdu import check_parity


def test_parity_fires_when_aur_count_mismatches() -> None:
    urdu = "اور نماز اور روزہ."
    roman = "Namaz aur roza."  # Urdu has 2x اور, Roman has 1x aur
    findings = check_parity(1, 1, urdu, roman)
    assert any(f.check == "2b-parity" and "اور" in f.detail for f in findings)
    assert all(f.level == "warn" for f in findings)


def test_parity_does_not_false_fire_when_counts_match() -> None:
    urdu = "اور نماز اور روزہ، وہ نہیں ہیں۔"
    roman = "Aur namaz aur roza, woh nahin hain."
    findings = check_parity(1, 1, urdu, roman)
    assert findings == []


def test_parity_nahin_accepts_nahin_or_nahi() -> None:
    urdu = "وہ نہیں کرتے۔"
    roman = "Woh nahi karte."
    findings = check_parity(1, 1, urdu, roman)
    assert findings == []


def test_parity_allah_counts_compounds_in_roman() -> None:
    urdu = "بیت اللہ اور رسول اللہ۔"
    roman = "Baitullah aur Rasoolullah."
    findings = check_parity(1, 1, urdu, roman)
    assert findings == []


def test_parity_wahi_only_credited_when_urdu_has_woh_hi_bigram() -> None:
    # Urdu has "وه ہی" once -> Roman may fuse it into a single "wahi".
    urdu = "وہ وہ ہی رب ہے۔"
    roman = "Woh wahi Rabb hai."
    findings = check_parity(1, 1, urdu, roman)
    assert findings == []


def test_parity_wahi_not_credited_without_bigram() -> None:
    # No "وه ہی" bigram in the Urdu, so a stray "wahi" in Roman should not
    # silently satisfy the وہ count -- this must still fire.
    urdu = "وہ وہ رب ہے۔"
    roman = "Wahi Rabb hai."
    findings = check_parity(1, 1, urdu, roman)
    assert any("وہ" in f.detail or "وه" in f.detail for f in findings)
