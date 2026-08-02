# ADR 0004 — Roman Urdu working style for coverage

- **Status:** ACCEPTED FOR DRAFTING — not a human review approval
- **Date:** 2026-08-02
- **Scope:** `data/roman-urdu/`
- **Builds on:** ADR 0001, ADR 0002, `out/house-style-popular-DRAFT.md`

## Context

The Roman Urdu track is no longer a renderer output waiting on the Devanagari
lexicon. It is a hand-written text track recovered under `data/roman-urdu/`:
surahs 1, 2 and 108-114, 325 verses total, all `beta-unverified`.

Surah 2 is the strongest exemplar because its note says it was
hand-transliterated in the popular register. Surah 1 says a model produced its
vowelizations, and the short surahs are useful style references but not reviewed
gold. New coverage should therefore follow Surah 2 first, then the draft style
guide.

This ADR records the working rules for adding the remaining surahs. It does not
promote any verse to `reviewed` or `approved`.

## Decision

Use the popular Roman Urdu register already present in Surah 2.

The source is always the Junagarhi Urdu translation. Transliterate it; do not
re-translate it, abbreviate it, or blend it with any third-party Roman Urdu
edition.

Keep each surah file complete. Do not commit a partial `surah-NNN.json`; a
missing verse reads as broken in consumers.

Keep status as `beta-unverified` for newly added text unless a human reviewer
explicitly moves it forward.

## Working Rules

### Pronouns and Postpositions

Follow the Surah 2 Roman Urdu pattern: split pronoun + postposition.

Examples:

- `un ke`, `un ki`, `un se`, `un par`
- `us ke`, `us ki`, `us se`, `us par`
- `hum ne`, `tum ne`, `tu ne`

Keep bound relative forms joined where Surah 2 already does:

- `jinhon ne`
- `unhon ne`

This mirrors the revised Devanagari decision in spirit, but the Roman spelling is
recorded here separately because ADR 0002 left Roman open.

### `میں`

Resolve by context:

- pronoun "I" -> `main`
- postposition "in" -> `mein`
- inflected long-vowel spellings such as `hamein`, `tumhe`, `unhe` follow Surah 2

Never choose this mechanically from the Urdu surface form.

### Ayn

Drop ayn unless an apostrophe helps reading or preserves an established spelling.
Use Surah 2's existing spellings as the local authority:

- `ta'ala`
- `in'aam`
- `ne'mat`
- `sha'oor`
- `shafaa'at`
- `mabood`, `ibaadat`, `ilm`, `amal` without an apostrophe

This is intentionally Roman-specific. ADR 0002's Devanagari ruling absorbs ayn
more aggressively.

### Izafat and Compounds

Mark recognised izafat with hyphenated `-e-`:

- `raah-e-haq`
- `aal-e-Moosa`
- `aal-e-Haaroon`

Do not invent an izafat heuristic. It is found by reading.

Use hyphens for established compounds already seen in Surah 2:

- `khauf-o-gham`
- `fazl-o-karam`
- `mabood-e-bar-haq`
- `janaab-e-baari ta'ala`

### Parenthetical Glosses

Preserve Junagarhi's parenthetical glosses and transliterate their contents.
This follows the pilot. If a later product decision styles or hides glosses, that
should be a consumer-layer change, not a silent deletion from the source text.

### Proper Nouns and Religious Terms

Follow the draft canonical list and Surah 2 spellings:

`Allah`, `Qur'an`, `Rasool`, `Rabb`, `deen`, `ibaadat`, `qayamat`, `jannat`,
`dozakh`, `nabi`, `aakhirat`, `dunya`, `imaan`, `Islam`, `momin`, `kaafir`.

Prophet names follow the Surah 2 style:

`Aadam`, `Moosa`, `Eesa`, `Ibraheem`, `Daaood`, with `(alaihis salaam)` preserved
where Junagarhi includes it.

Reviewer confirmations from the Surah 3 drafting pass:

- `نگہبان` -> `nigehbaan`
- `ذیعزت` -> `zi-izzat`
- `ضابط نفس` -> `zaabit-e-nafs`
- `مردوں کو زندہ کرتا ہوں` -> `murdon ko zinda karta hoon`
- `دین اسلام` -> `deen-e-islam`
- `ظالموں` -> `zaalimon`
- `نصرانی` -> `nasraani`
- `یک طرفہ (خالص)` -> `yak-tarfa (khaalis)`
- `دینار` -> `deenaar`
- `خزانے` -> `khazane`
- `مواخذہ` -> `muakhaza`
- `نبوت` -> `nabuwat`
- `ذمہ` -> `zimma`
- `علیہما السلام` -> `alaihimas-salaam`
- `بہتان` -> `bohtan`
- `حنیف` -> `haneef`
- `حج` -> `hajj`
- `رسول اللہ` -> `Rasoolullah`
- `بلاشبہ` -> `bila-shubha`
- `فلاح ونجات` -> `falah-o-najat`
- `تہس نہس` -> `tahas-nahas`
- `میدان جنگ` -> `maidan-e-jang`
- `جنگ بدر` -> `jang-e-badr`
- `باعث نصرت وامداد` -> `baais-e-nusrat-o-imdad`
- `اطمینان قلب` -> `itminan-e-qalb`
- `امداد الٰہی` -> `imdad-e-ilahi`
- `ناشائستہ` -> `nashaista`
- `فی الواقع` -> `fil-waqe`
- `شکست احد` -> `shikast-e-uhud`
- `ہم رکاب` -> `humrikab`
- `ثابت قدمی` -> `sabit-qadmi`
- `الٰہی` -> `ilahi`
- `باعث` -> `baais`
- `الیمناک` -> `alamnak`
- `بآواز بلند` -> `ba-awaz-e-buland`
- `ہم جنس` -> `humjins`
- `مہمانی` -> `mehmaani`
- `آسمانوں وزمین` -> `aasmanon-o-zameen`
- `بالیقین` -> `bilyaqeen`
- `ثابت قدم رہو` -> `sabit-qadam raho`

## Consequences

This gives the coverage work a stable target without pretending the draft text
is reviewed. The hard errors remain the same as in the rest of the project:
homographs, invisible izafat, and short vowels. Automated checks can catch
missing verses, blanks and stray digits, but reading is still required.

If the owner later changes any of these Roman conventions, update this ADR and
the existing pilot together rather than letting two Roman Urdu styles coexist.
