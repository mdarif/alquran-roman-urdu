from __future__ import annotations

from lint_roman_urdu import check_length_outlier


def test_length_outlier_fires_when_roman_much_shorter() -> None:
    urdu = "یہ ایک لمبا جملہ ہے جس میں کئی الفاظ ہیں۔"  # 10 urdu words
    roman = "Yeh jumla hai."  # 3 words -> ratio 0.3 < 0.75
    findings = check_length_outlier(1, 1, urdu, roman)
    assert len(findings) == 1
    assert findings[0].check == "2d-length"
    assert findings[0].level == "warn"


def test_length_outlier_does_not_false_fire_on_short_verse() -> None:
    # Fewer than 6 Urdu words -> excluded regardless of ratio.
    urdu = "الم"
    roman = "Alif Laam Meem."
    findings = check_length_outlier(1, 1, urdu, roman)
    assert findings == []


def test_length_outlier_does_not_false_fire_when_ratio_is_healthy() -> None:
    urdu = "یہ ایک لمبا جملہ ہے جس میں کئی الفاظ ہیں۔"  # 10 words
    roman = "Yeh ek lamba jumla hai jis mein kai alfaz hain."  # 10 words
    findings = check_length_outlier(1, 1, urdu, roman)
    assert findings == []
