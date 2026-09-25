from __future__ import annotations

from lint_roman_urdu import check_gloss_parity, extract_bracket_spans

# Real corpus text, copied verbatim from the Urdu source DB and
# data/roman-urdu/surah-{026,012}.json on 2026-09-25, per the plan's
# instruction to use real verse text as the fixture for this check.

VERSES = {
    (26, 12): (
        "موسیٰ (علیہ السلام) نے کہا میرے پروردگار! مجھے تو خوف ہے کہ کہیں وه مجھے جھٹلا (نہ) دیں.",
        "Moosa (alaihis salaam) ne kaha mere Parwardigar! Mujhe to khauf hai ke kahin woh mujhe jhutla na den.",
    ),
    (26, 14): (
        "اور ان کا مجھ پر میرے ایک قصور کا (دعویٰ) بھی ہے مجھے ڈر ہے کہ کہیں وه مجھے مار نہ ڈالیں.",
        "Aur un ka mujh par mere ek qusoor ka dawa bhi hai, mujhe dar hai ke kahin woh mujhe maar na daalen.",
    ),
    (26, 23): (
        "فرعون نے کہا رب العالمین کیا (چیز) ہے؟",
        "Firaun ne kaha Rabbul-Aalameen kya cheez hai?",
    ),
    (26, 49): (
        "فرعون نے کہا کہ میری اجازت سے پہلے تم اس پر ایمان لے آئے؟ یقیناً یہی تمہارا وه بڑا (سردار) ہے جس نے "
        "تم سب کو جادو سکھایا ہے ، سو تمہیں ابھی ابھی معلوم ہوجائے گا، قسم ہے میں ابھی تمہارے ہاتھ پاؤں الٹے "
        "طور پر کاٹ دوں گا اور تم سب کو سولی پر لٹکا دوں گا.",
        "Firaun ne kaha ke meri ijaazat se pehle tum is par imaan le aaye? Yaqeenan yehi tumhara woh bada "
        "sardaar hai jis ne tum sab ko jaadu sikhaaya hai, so tumhein abhi abhi maloom ho jaayega, qasam hai "
        "main abhi tumhare haath paaon ulte taur par kaat doonga aur tum sab ko sooli par latka doonga.",
    ),
    (12, 5): (
        "یعقوب علیہ السلام نے کہا پیارے بچے! اپنے اس خواب کا ذکر اپنے بھائیوں سے نہ کرنا۔ ایسا نہ ہو کہ وه "
        "تیرے ساتھ کوئی فریب کاری کریں ، شیطان تو انسان کا کھلا دشمن ہے.",
        "Yaqoob (alaihis salaam) ne kaha pyare bachche! Apne is khwab ka zikr apne bhaiyon se na karna. Aisa "
        "na ho ke woh tere saath koi fareb-kaari karen, shaitan to insan ka khula dushman hai.",
    ),
    (26, 28): (
        "حضرت موسیٰ علیہ السلام نے فرمایا! وہی مشرق ومغرب کا اور ان کے درمیان کی تمام چیزوں کا رب ہے، اگر تم "
        "عقل رکھتے ہو.",
        "Hazrat Moosa (alaihis salaam) ne farmaaya! Wahi mashriq-o-maghrib ka aur un ke darmiyaan ki tamaam "
        "cheezon ka Rabb hai, agar tum aql rakhte ho.",
    ),
}


def test_extract_bracket_spans_paren() -> None:
    assert extract_bracket_spans("mujhe jhutla (na) den") == ["na"]


def test_extract_bracket_spans_quranic_bracket() -> None:
    assert extract_bracket_spans("﴿چیز﴾ ہے") == ["چیز"]


def test_gloss_parity_fires_on_26_12() -> None:
    urdu, roman = VERSES[(26, 12)]
    findings = check_gloss_parity(26, 12, urdu, roman)
    assert len(findings) == 1
    assert findings[0].check == "2c-gloss"
    assert findings[0].level == "error"


def test_gloss_parity_fires_on_26_14() -> None:
    urdu, roman = VERSES[(26, 14)]
    findings = check_gloss_parity(26, 14, urdu, roman)
    assert len(findings) == 1


def test_gloss_parity_fires_on_26_23() -> None:
    urdu, roman = VERSES[(26, 23)]
    findings = check_gloss_parity(26, 23, urdu, roman)
    assert len(findings) == 1


def test_gloss_parity_fires_on_26_49() -> None:
    urdu, roman = VERSES[(26, 49)]
    findings = check_gloss_parity(26, 49, urdu, roman)
    assert len(findings) == 1


def test_gloss_parity_does_not_false_fire_on_12_5() -> None:
    # Urdu leaves علیہ السلام unbracketed here; Roman adds brackets around the
    # honorific only. Both have zero NON-honorific bracketed spans -> no finding.
    urdu, roman = VERSES[(12, 5)]
    findings = check_gloss_parity(12, 5, urdu, roman)
    assert findings == []


def test_gloss_parity_does_not_false_fire_on_26_28() -> None:
    urdu, roman = VERSES[(26, 28)]
    findings = check_gloss_parity(26, 28, urdu, roman)
    assert findings == []


def test_gloss_parity_ignores_pure_digit_footnote_markers() -> None:
    urdu = "جو لوگ غیب پر ایمان لاتے ہیں(1)۔"
    roman = "Jo log ghaib par imaan laate hain(1)."
    findings = check_gloss_parity(1, 1, urdu, roman)
    assert findings == []
