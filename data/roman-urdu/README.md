# Roman Urdu pilot — recovered hand-transliterated text

**All 6,236 verses, all 114 surahs.** Popular register.

## What this is

Roman Urdu text for all 114 surahs, rendered from the Junagarhi Urdu
translation. **Hand- and assistant-authored, not generated** — nothing in
`scripts/` produces it, which is why this repo has `render_devanagari.py` but
no Roman renderer. The phoneme → Latin step designed in ADR 0001 §2 was never
built; every verse here was written directly, by a person or by an assistant
following ADR 0004, never by a model output shipped as-is.

Treat it as **source**, not output. Do not overwrite it from a script.

Provenance is **not uniform** — see each file's own `note` field before
treating any of it as gold:

| Surahs | Verses | How it was produced |
|---|---|---|
| 2 | 286 | Hand-transliterated in the popular register — the strongest exemplar |
| 1 | 7 | Model-produced vowelizations |
| 3–107 | 5,911 | Assistant-drafted per ADR 0004, following the Surah 2 pattern |
| 108–114 | 32 | House-style reference only, no provenance claim |

## Where it came from

The original 325-verse pilot (surahs 1, 2, 108–114) lived in the
**al-quran-web** repo at `data/roman-urdu/`, added in `cd3efaa` (2026-07-20) and
deleted in `05ff07c` when the reader was reworked for mobile parity. Recovered
here 2026-08-02 from `05ff07c^`, byte-exact, verified complete (no gaps, no
blank verses). The JSON was never modified after the initial commit; only
`docs/roman-urdu-pilot.md` was (in `5dd8a42`) — that file is a historical
snapshot of the web-side coordination doc from before the recovery, not current
status.

Surahs 3–70 and 71–107 were drafted directly in this repo in subsequent
sessions, extending the pilot to full coverage.

## Status

Every file carries `"status": "beta-unverified"` — not reviewed, not approved.
That label is accurate for the entire corpus (all 6,236 verses) and should stay
until a human review pass moves individual surahs to `reviewed` then `approved`.
Coverage is complete; review has not started.

## Why it matters

The shipped alternative — the third-party Al-QuranJino / Muhammad Kazim edition
bundled in `quran.db` as `ur-roman-junagarhi-experimental` — is worse on every
axis compared on Al-Baqarah 1–7:

| | this pilot | Al-QuranJino |
|---|---|---|
| خ | `kharch`, `aakhirat` | `qarch`, `aaqirath` |
| final ت | `hidayat`, `najaat` | `hidaayath`, `najaath` |
| nasalisation | `hain`, `parhezgaron`, `dilon` | `hai`, `parhezgaaro1`, `dilo` |
| footnote markers | none | fused into words in **309 verses** |
| 2:6 | `darana` | `darsana` (typo) |

On that comparison the owner gated Roman Urdu **off** in both app and web on
2026-08-02 (`FeatureFlags.romanUrdu` / `EDITION_FLAGS`), to be restored when this
text is finished and reviewed rather than by patching the third-party text.

Coverage is now complete: 6,236 of 6,236 verses drafted. What remains is human
review (nothing is `reviewed` or `approved` yet) and the `alquran-data` ingestion
pipeline that turns this JSON into a shippable `quran.db` resource — see
`docs/TRANSLITERATION-GUIDE.md` §7.
