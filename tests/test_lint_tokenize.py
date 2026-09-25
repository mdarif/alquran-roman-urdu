from __future__ import annotations

from lint_roman_urdu import tokenize_urdu


def test_tokenize_urdu_splits_on_punctuation() -> None:
    text = "جو لوگ غیب پر ایمان لاتے ہیں، اور نماز کو قائم رکھتے ہیں۔"
    tokens = tokenize_urdu(text)
    assert tokens == [
        "جو", "لوگ", "غیب", "پر", "ایمان", "لاتے", "ہیں", "اور", "نماز",
        "کو", "قائم", "رکھتے", "ہیں",
    ]


def test_tokenize_urdu_strips_brackets_too() -> None:
    text = "مجھے تو خوف ہے کہ کہیں وه مجھے جھٹلا (نہ) دیں."
    tokens = tokenize_urdu(text)
    assert "نہ" in tokens
    assert "(نہ)" not in tokens
