# Roman Urdu (web pilot) — shared coordination

Single source of truth for the Roman Urdu BETA on the website. **Any session
(this one, the Baqarah session, a future one) reads this before touching the
feature.** Lives in git so it travels tool-agnostically.

Companion lexicon project: `~/code/alquran-roman-urdu` (the eventual source of
truth for the text). This web pilot is hand-transliterated ahead of it.

## Decisions (locked)

- **Scope:** web only for now. Once it's solid, the same shape ports to the app.
- **Register:** **popular** Roman Urdu (SMS-readable, no scholarly diacritics).
  Owner decision 2026-07-19. → `alquran-roman-urdu/out/house-style-popular-DRAFT.md`.
- **Base text:** the **Junagarhi** Urdu translation, transliterated (never
  re-translated). Its fuller phrasing is the differentiator vs other Roman sites.
- **Coverage model:** pilot surahs, **expanding**. Not the full corpus. Each
  surah is reviewed before it goes live.
- **Status of all pilot text:** `beta-unverified`. Model/hand output, not yet
  reviewed. It ships ONLY behind the visible "Experimental" label (was "Beta"
  — changed 2026-07-20, owner call: more work remains than "beta" implies).
  Never presented as final.

## How it works (so you don't need to read the code)

- **Feature flag:** `ROMAN_URDU_TRANSLATION` in `src/lib/site.ts` is the single
  switch. It gates the pill, the per-verse render, the Credits section, and the
  "coming soon" note. Flip to `false` → the whole feature disappears.
- **Data is drop-in, per surah:** `data/roman-urdu/surah-NNN.json`. Add a file,
  run `npm run export`, done. No code changes. Absent surah = no Roman Urdu there.
- **All-or-nothing per surah:** export omits a surah that is only *partly*
  transliterated (with a console warning showing the count), so a half-done surah
  never renders with blank verses. **Finish all N verses to publish.**
- **Opt-in:** off by default; the reader turns it on via the toolbar pill, so the
  default experience is unchanged.

## Data schema

```json
{
  "surah": 2,
  "status": "beta-unverified",
  "register": "popular",
  "source": "Transliterated from the Urdu translation of Maulana Muhammad Junagarhi.",
  "note": "PILOT / ILLUSTRATIVE. Not reviewed. House style: popular.",
  "ayahs": { "1": "Alif Laam Meem.", "2": "…", "286": "…" }
}
```
Keys are **string ayah numbers**. Only `ayahs` is read by the exporter.

## House style — keep every surah consistent

Drift between sessions (`ke` vs `kay`) is visible to readers. Follow the draft
spec; the load-bearing conventions:

| Urdu | Popular | not |
|---|---|---|
| final `ے` | `ke`, `se`, `ne` | kay / key |
| `ہے` | `hai` | he |
| `میں` | `main` | mein |
| `وہ` | `woh` | wo / vah |
| `ہوں` | `hoon` | hun |
| long `ا`/`ی`/`و` | `aa` / `ee` / `oo` | a / i / u |
| `تعالیٰ` | `ta'ala` (apostrophe for ayn) | taala |
| aspiration `ھ` | keep `bh/kh/th/ph` | drop h |
| Junagarhi `()` glosses | **keep** them | drop |
| footnote markers `(1)` | **strip** | keep |
| proper nouns | Capitalize (Allah, Rabb, Kausar) | lowercase |

Full table + rationale: `alquran-roman-urdu/out/house-style-popular-DRAFT.md`.

## Coverage (update when you add a surah)

| Surah | Verses | State |
|---|---|---|
| 1 Al-Fatiha | 7 | ✅ live (experimental) |
| 108–114 | 32 | ✅ live (experimental) |
| 2 Al-Baqarah | 286 | ✅ all 286 transliterated (experimental) — pending review before deploy |

## Ownership — avoid clobbering (concurrent sessions)

Isolated & safe to add from any session:
- `data/roman-urdu/surah-*.json` (one file per surah)
- **this doc** (append your surah to the coverage table)

Shared code — **one owner per file**, coordinate before editing:
- `src/lib/site.ts`, `src/components/Ayah.astro`, `src/pages/surah/[surah].astro`
- `scripts/export-quran.mjs`, `src/styles/global.css`,
  `src/components/content/CreditsContent.astro`

## Not done — the owner's explicit call

- **Deploy** (`npm run deploy`, Cloudflare Pages) is held until the owner says go.

## Recent changes (this session)

- Pill order fixed to app parity: **Urdu, Hindi, English**, then **Roman
  Urdu** appended last (it has no app equivalent yet). Applied to both the
  toolbar toggles (`ReaderToolbar.astro`) and the per-verse blocks
  (`Ayah.astro`).
- The `[surah].astro` "coming soon" note (`.rur-soon`, previously unused CSS)
  is now wired in: on a surah with no Roman Urdu data, a dashed-border note
  renders above the verses regardless of toggle state — the pill itself stays
  visible on every surah (discoverability), rather than being hidden on
  uncovered ones.
