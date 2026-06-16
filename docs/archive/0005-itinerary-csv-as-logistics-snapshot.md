# ADR 0005 — Itinerary CSV as logistics snapshot

## Status

Accepted

## Context

Field teams maintain a shared Excel workbook for day-by-day routing, survey
timing, and accommodation bookings. Coworkers prefer that format over editing
markdown or SQL directly.

The planning repo already tracks **permits** (kanban + `campaigns.db`) and
**plot metadata** (`tern_plots.db`), but `generate_checklist.py` could not show
real visit dates or accommodation until logistics lived in the database.

[ADR 0003](0003-property-names-csv-not-imported.md) rejects auto-import of stale
contact CSVs. The itinerary export is different: it is the operational schedule,
refreshed deliberately when Excel changes.

## Decision

- Store the latest CSV under `docs/itineraries/<trip-id>-itinerary.csv`.
- Import via `scripts/import_itinerary.py`:
  - Parse the two-section Excel export (daily schedule + site master list).
  - Write day-level rows to `itinerary_days`.
  - Set `campaign_plots.visit_date` for plots appearing in the daily schedule.
  - Emit a reconcile report (`docs/audits/<trip-id>-itinerary-import.md`).
- Plot IDs are validated against `tern_plots.db`; they are never taken from
  the CSV coords column as authoritative.
- Kanban remains the source of truth for **access status** and contacts.

## Consequences

- Coworkers can keep using Excel; this repo syncs on CSV download.
- `generate_checklist.py` reads `itinerary_days` for travel, notes, and accom.
- Sites in the master list but not in the daily schedule (e.g. pending access)
  surface as import warnings rather than silent omissions.
- Re-importing the same file is idempotent; `--dry-run` previews diffs.
