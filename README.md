# alquran-roman-urdu

Open, reviewed Roman Urdu lexicon and transliteration pipeline for Quran
translation text. Al Marfa Technologies.

The lexicon is the deliverable, not the app.

**Start here: [AGENTS.md](AGENTS.md)**

## The decision this repo exists to serve (2026-08-02)

**Al Quran ships our own Roman Urdu, or none at all.** Not a third party's.

The alternative was tested rather than assumed. A complete third-party Roman Urdu
(the Al-QuranJino / Muhammad Kazim JSON edition) was fetched and bundled into
`quran.db` as `ur-roman-junagarhi-experimental`, covering all 114 surahs. Set
against our own hand-transliterated pilot on Al-Baqarah 1–7, it loses on every
axis:

| | our pilot | Al-QuranJino |
|---|---|---|
| خ | `kharch`, `aakhirat` | `qarch`, `aaqirath` |
| final ت | `hidayat`, `najaat` | `hidaayath`, `najaath` |
| nasalisation | `hain`, `parhezgaron`, `dilon` | `hai`, `parhezgaaro1`, `dilo` |
| footnote markers | none | fused into words in **309 verses** |
| 2:6 | `darana` | `darsana` (typo) |

The register is wrong too — that text reads as Deccani Roman Urdu, not the
Karachi/Lahore popular register ADR 0001 names as the open question.

**Outcome:** Roman Urdu was gated **off** in both consumers on 2026-08-02 rather
than shipped rough — `FeatureFlags.romanUrdu` in `alquran-app`,
`EDITION_FLAGS['ur-roman-junagarhi-experimental']` in `al-quran-web`. Both are
one-line flips. The bundled row stays in `quran.db`, unused.

This repo is what turns the flag back on. Coverage is the only thing standing
between the pilot and shipping — the quality argument is already settled.

## The text — read this before writing any Roman Urdu

`data/roman-urdu/` holds **all 6,236 verses, all 114 surahs**, popular register,
marked `beta-unverified`. Surah 2 is hand-transliterated and the strongest
exemplar; surah 1 was model-drafted; surahs 3–107 are assistant-drafted per
ADR 0004; 108–114 are house-style references. None of it is reviewed or
approved.

It is **source, not output**. Nothing in `scripts/` generates it — this repo has
`render_devanagari.py` but no Roman renderer, because the phoneme → Latin step
designed in ADR 0001 §2 was never built. Do not overwrite it from a script, and
do not treat the lexicon's review state as gating it; they are separate efforts
that happen to share a source text.

The original 325-verse pilot (surahs 1, 2, 108–114) lived in `al-quran-web`
until 2026-08-02 and was recovered here from that repo's history; the rest
(3–70, then 71–107) was drafted directly in this repo.
→ [`data/roman-urdu/README.md`](data/roman-urdu/README.md)

## Status

- **Source text licensing: cleared.** Junagarhi (d. 1941) is public domain, so
  derivatives need no permission — settled 2026-07-27, see
  [ATTRIBUTION.md](ATTRIBUTION.md). Two `UNVERIFIED` rows remain there for
  sources that are prospective and currently unused; they block only if
  something starts consuming them.
- **Release gate is review completeness, not licensing.** Nothing ships
  unreviewed (AGENTS.md §4).
- **Lexicon:** 13 approved of 201 entries — the Devanagari route's bottleneck.
- **Roman Urdu text:** 6,236 of 6,236 verses drafted (all 114 surahs); 0 reviewed,
  0 approved. Human review is now the sole remaining gate before either flag
  can flip. → §7 of `docs/NEXT-SESSION.md`.
