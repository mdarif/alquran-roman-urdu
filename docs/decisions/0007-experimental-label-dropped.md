# ADR 0007 — The Experimental label is dropped

- **Status:** ACCEPTED 2026-09-29 by the owner (Abu Rayyan): "let's drop
  experimental after my name 'Abu Rayyan' for Roman Urdu as we did fix all the
  remaining issue"
- **Scope:** the published edition `ur-roman-abu-rayyan` in the app, the web
  and the editions catalogue
- **Fulfils:** ADR 0006 point 7 and ADR 0005 P4 ("Experimental is dropped only
  on the owner's explicit word")

## What changed

- `alquran-data/config/sources.yaml`: `experimental: false` for
  `ur-roman-abu-rayyan`. That one flag drives the app's pill and the web's
  Experimental pill **and** the web's per-verse "suggest a correction" link, so
  the link goes with the label.
- The exporter (`pipeline/roman_urdu/export_simple_db.py`) now refuses any
  surah file whose status is not `verified` or `approved`, so an unreviewed
  file cannot ship unlabelled.
- The bundled seed (`quran.db` in the app) and the web's copy carry
  `resources.experimental = 0` for the edition. The text itself is unchanged.

## What did not change

- The credit stays "Abu Rayyan" only (ADR 0006 point 6). No AI credit.
- The edition stays opt-in and a download (`default_on: false`,
  `bundle: false`).
- Review status is still what `scripts/status.py` reports: 6,046 verses
  `verified`, 190 `approved`. The label is gone; the record is not.

## Still to do to reach readers

Nothing is live from this decision until each step below is done:

1. `alquran-data`: build the editions catalogue and publish it
   (`build_editions.py` then `publish_editions.sh`), so an installed edition
   refreshes its flag.
2. `al-quran-web`: commit the updated `data/quran.db` row and deploy.
3. `alquran-app`: the next release carries the new bundled seed.
