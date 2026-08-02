# Roman Urdu pilot — recovered hand-transliterated text

325 verses: surahs **1**, **2** (all 286), **108–114**. Popular register.

## What this is

The hand-transliterated Roman Urdu pilot, rendered from the Junagarhi Urdu
translation. **Hand-authored, not generated** — nothing in `scripts/` produces
it, which is why this repo has `render_devanagari.py` but no Roman renderer. The
phoneme → Latin step designed in ADR 0001 §2 was never built; this text was
written directly.

Treat it as **source**, not output. Do not overwrite it from a script.

## Where it came from

It originally lived in the **al-quran-web** repo at `data/roman-urdu/`, added in
`cd3efaa` (2026-07-20) and deleted in `05ff07c` when the reader was reworked for
mobile parity. Recovered here 2026-08-02 from `05ff07c^`, byte-exact, verified
complete (no gaps, no blank verses). The JSON was never modified after the
initial commit; only `docs/roman-urdu-pilot.md` was (in `5dd8a42`).

## Status

Each file carries `"status": "beta-unverified"` — not reviewed, not approved.
That label is accurate and should stay until a human review pass.

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
pilot is finished and reviewed rather than by patching the third-party text.

Remaining work is the obvious one: 325 of 6,236 verses are done.
