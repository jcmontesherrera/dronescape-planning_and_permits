# ADR 0003 — property-names.csv is not auto-imported

## Status

Accepted

## Context

Early outreach used `property-names.csv` to fill email templates. Several names
do not match `tp.plots.property` exactly; the file is incomplete and stale.

## Decision

- Keep the file under `archive/property-names.csv` for historical reference.
- Do **not** import it in `seed_campaigns.py` or any default workflow.
- Populate `properties` from confirmed kanban cards or `trip_audit.py --register`.

## Consequences

- Contacts in `campaigns.db` reflect verified outreach, not a one-off CSV.
- Plot IDs always come from `tern_plots.db`, not the CSV.
