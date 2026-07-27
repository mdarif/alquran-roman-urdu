# STYLE_GUIDE.md — Devanagari orthography for the Urdu-register Quran

**Status:** authoritative for `alquran-roman-urdu` Devanagari output.
**Established:** 2026-07-27, editorial review of the first 8 rendered surahs.
**Companion to:** ADR 0002 (house style), ADR 0003 (Devanagari as a target).

---

## 0. What this text is

A **Devanagari rendering of an Urdu-register Quran translation.** It is not
standard Hindi and must not drift toward it.

The order of priority when rules conflict:

1. **The source text.** Junagarhi's Urdu governs. Where the source and any
   published Hindi disagree, the source wins.
2. **Arabic / Persian morphology.** Preserve the shape of the loanword.
3. **Internal consistency.** One rule applied everywhere beats a better rule
   applied unevenly.
4. **Established Urdu orthography.**
5. Everything else.

**Another published translation is evidence, never authority.** The Suhel Farooq
Khan Hindi translation is a useful witness — 9,331 words of independent
Devanagari in the same register — and `scripts/validate.py` checks against it.
But its house style is its own. Do not adopt a spelling merely because it is
attested there, and do not reject one merely because it is not.

---

## 1. Frozen decisions — do not revisit

| | Rule |
|---|---|
| **Nukta** | Decomposed only: `क` + `़` (U+093C). **Never** the precomposed U+0958–095F. They are Unicode composition exclusions, so precomposed and decomposed never compare equal and search silently fails across them. |
| **Nukta policy** | `faithful` — क़ ख़ ग़ ज़ फ़ are always written. Dropping the nukta is popular style, not Urdu orthography. |
| **Pronouns** | **वो**, **ये** — never वह, यह. |
| **Postpositions** | **Separate**: उस का, उस के, उस की, उस से, हम ने, तुम ने. Do not join them because standard Hindi does. |
| **Oblique plural + ने** | **Joined**: जिन्होंने, उन्होंने. These forms occur only before a postposition, so they are bound; ہم and تو stand alone freely and stay split. |
| **Verb + future auxiliary** | **Joined**: जाएगा, जाएगी, करूँगा. |

---

## 2. Nasalisation — anusvara vs chandrabindu

**Rule.** Chandrabindu `ँ` marks a **nasalised vowel**. Anusvara `ं` marks a
**nasal consonant** before another consonant.

| Write | Not | Why |
|---|---|---|
| हूँ, माँग, लकड़ियाँ | हुं… | The vowel itself is nasalised; nothing follows. |
| अंधेरा, अंधेरी | अँधेरा | A nasal consonant precedes a stop. |
| इन्सान | इंसान | See §3 — this is a cluster, not a nasal. |

**Typographic corollary.** Where a vowel sign already occupies the space above
the letter (ि ी े ै ो ौ), use anusvara: **मैं**, not मैँ. The phoneme is
unchanged; only the mark differs. The renderer does this automatically for `~`;
use the explicit `M` phoneme where a word takes anusvara for orthographic reasons
rather than typographic ones.

**Never add nasalisation the source does not have.** `ونشان` ends in ن (U+0646),
a full noon — so it is **निशान**, not निशाँ. Only ں (U+06BA, noon ghunna)
licenses a chandrabindu. The poetic spelling نشاں exists in Urdu literature; it
is not what Junagarhi wrote.

---

## 3. Arabic-derived words

**Rule. Preserve the consonant cluster.** Arabic and Persian permit clusters that
Hindi would break with an epenthetic vowel. Write the conjunct.

| Write | Not | Source |
|---|---|---|
| इन्सान | इंसान, इनसान | انسان /insān/ — a true न्स cluster |
| मग़्फ़िरत | मग़फ़िरत | مغفرت /maɣfirat/ — /ɣf/ with no vowel between |
| तस्बीह | तसबीह | تسبیح |
| हम्द | हमद | حمد |
| दुश्मन | दुशमन | دشمن |
| बरगश्ता | बरगशता | برگشتہ |
| पोस्त | पोसत | پوست |
| गर्दन | गरदन | گردن |

**Preserve the Arabic vowel.** جہالت is /dʒahālat/ — fatha on the jim — so
**जहालत**, not जिहालत.

**Sibilants.** ث, س and ص all render **स**; ش renders **श**. Devanagari has no
means to distinguish the three s-sounds and inventing one would be pseudo-precise.
So `لاوارث` → **लावारिस**.

---

## 4. Ain (ع)

Ain is a consonant Urdu speakers do not pronounce as one, and Hindi has no letter
for it. Render the **vowel it carries**, positionally:

| Position | Treatment | Example |
|---|---|---|
| Word-initial | independent vowel | عبادت → **इबादत**, عمل → **अमल** |
| Between vowels, lengthening | absorbed | تعریف → **तारीफ़**, یعنی → **यानी** |
| Between vowels, syllable break | independent vowel | تعالیٰ → **तआला** |
| Post-consonantal | silent | بعد → **बाद** |

**Place the vowel where the source has it.** تعالیٰ is /ta'ālā/ — fatha on the
te, then the ain carries the long ā. So **तआला** (ta-ā-lā), never ताअला
(tā-a-lā), which moves the length onto the wrong syllable. Ruled 2026-07-27;
1,532 occurrences.

Never write a letter for the ain itself. The `'` phoneme means *syllable break*,
not "an ain is here".

---

## 5. Perso-Arabic consonants (nukta series)

Always written, never folded to the plain consonant:

| Urdu | Devanagari | Note |
|---|---|---|
| ق | क़ | क़यामत, हक़, क़बूल |
| خ | ख़ | **ख़्वाह** — khe, not an aspirated ख |
| غ | ग़ | ग़ज़ब, मग़्फ़िरत |
| ز ذ ض ظ | ज़ | all four collapse to ज़ |
| ف | फ़ | सिर्फ़, फ़तह |
| ژ | झ़ | **zero occurrences** in this corpus — should never appear |

A published text that drops these is using popular style. That is not a reason to
follow it.

---

## 6. Izafat and compounds

**Izafat.** The Persian `-e-` linker is **unwritten in Urdu** and must be
supplied: `راه حق` → **राह-ए-हक़**. Write it hyphenated.

**There is no detection rule, and none may be invented.** Nothing in the spelling
distinguishes an izafat pair from any two adjacent nouns — the corpus has 55,819
distinct adjacent word-pairs, and `راه` alone is followed by میں 61 times and
حق twice. A heuristic here would insert a linker into phrases that do not have
one, changing the meaning of scripture. **Izafat is found by reading.**

**Lexical compounds** are likewise hyphenated: `بے نام ونشان` →
**बे-नाम-ओ-निशान**, where the و is the Persian *o* conjunction, not a व.

**Consequence.** A surah rendering with no missing words is *not* evidence its
izafat is correct — missing izafat renders as two plausible words and fails
silently.

---

## 7. Homographs — resolved per occurrence, never per word

Urdu drops the short vowels that would distinguish these. One spelling, two
words; only the sentence decides. Resolve with a per-occurrence override
(`data/lexicon/overrides.tsv`), never by picking a better default.

| Urdu | Tokens | Readings |
|---|---|---|
| میں | 3,751 | **मैं** "I" / **में** "in" |
| ان | 3,240 | इन / उन |
| اس | 3,180 | इस / उस |
| کہ | 3,144 | कि "that" / कह "say" |
| تو | 2,661 | **तू** "you" / **तो** "then, so" |

~7% of the corpus. A word-level attestation check **cannot** catch these: इस and
उस are both perfectly attested, and the wrong one is still wrong.

---

## 8. Verb morphology and inflection

**Urdu and Hindi disagree about word boundaries in both directions.**

- Urdu glues what Hindi separates: `ہوگئے` → **हो गए**, `کردیا` → **कर दिया**.
  Use the `_` word-break phoneme. Beware `رضامندی` and `پابندی`, which merely end
  in دی and are single words.
- Urdu splits what Hindi joins — but per §1 we follow **Urdu** for
  pronoun+postposition, and Hindi only for the verb+auxiliary and the oblique
  plural.

**Imperative, honorific.** Write **-िये**: دیجئے → **दीजिये**, کیجئے → **कीजिये**.
Urdu writes the hamza-yeh, so -िये mirrors the source; -िए is the
Sanskritized-Hindi convention.

**Vocative plural drops the nasal.** `کافرو` (waw, no noon) → **काफ़िरो**, not
काफ़िरों. काफ़िरों is the oblique plural — a different form, not a variant
spelling.

---

## 9. Open — needs an owner ruling

1. **`ہ` word-final** — مہربان → मेहरबान. Whether a schwa rule is needed.
3. **Roman Urdu's answer to §1**, which may legitimately differ from Devanagari's.

---

## 10. How a spelling question gets settled

1. **Check the source.** `ونشان` vs `ونشاں` decided निशान in one step.
2. **Run `scripts/validate.py`.** It reports which of our words no independent
   published text has ever written — currently 18 of 502.
3. **Run `scripts/crosscheck.py`.** Disagreement with the Roman Urdu rendering of
   the same verse is a strong signal.
4. **Apply §0's priority order.**
5. **Record it here**, so it is settled once.

Unattested is not wrong. A different translation simply chose a different word.
