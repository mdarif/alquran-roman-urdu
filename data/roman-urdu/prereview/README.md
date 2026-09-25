# prereview/

AI pre-review of the Roman Urdu text, verse by verse, comparing
`data/roman-urdu/surah-NNN.json` against the Junagarhi Urdu translation. This
is a suggestion only — it never approves anything and the text here is never
edited. Owner approval, once given, is recorded separately in
`data/roman-urdu/review/`.

## Columns

- `ayah` — verse number within the surah.
- `verdict` — `ok` (Roman matches the Urdu word for word, follows ADR 0005,
  no typo) or `concern` (anything else: omission, addition, wrong word, wrong
  vowel, mein/main, invented/missing izafat, lost plural, miscapitalisation,
  punctuation, typo, or an R1-R6 house-style violation).
- `sha256` — hash of the exact Roman verse string this verdict was read
  against, computed from the JSON.
- `concern` — for `concern` rows, a short, concrete description of the
  problem. Empty for `ok`.
- `suggestion` — for `concern` rows, a corrected Roman span (transliterated,
  never re-translated). Empty for `ok`.

## Staleness

If a verse's `sha256` no longer matches `hashlib.sha256(roman_text.encode
("utf-8")).hexdigest()` of the current text in the surah JSON, that row is
out of date — the verse changed since it was reviewed and needs re-review.
