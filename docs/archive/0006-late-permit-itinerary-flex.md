# ADR 0006 — Late permit and itinerary flex

## Status

Accepted

## Context

The Team Lead often approves corridor logistics before every landholder replies. Permits
can confirm days or weeks later — sometimes after the shared Excel itinerary is
frozen. [ADR 0005](0005-itinerary-csv-as-logistics-snapshot.md) splits **access**
(kanban) from **schedule** (CSV) but does not say how to resolve conflicts when
access arrives late or a field day is already at capacity.

Field teams also operate under fixed **hour caps** (11h weekdays, 8h weekends)
and a **vehicle chain** across anchored trips — sites skipped on one leg may
still be visitable on the next outbound corridor.

## Decision

- Treat lead-approved itineraries as **locked core + conditional add-ons**,
  not a fixed plot-by-plot contract.
- Resolve late confirmations using four outcomes: **absorb**, **defer** (to the
  next anchored leg in the roadmap), **skip**, or **re-approve** (Tier 2).
- Hour caps and the full workflow live in
  [docs/field-day-policy.md](../docs/field-day-policy.md) — the operational
  source for humans and agents.

## Consequences

- Pending sites remain in the CSV site master without daily rows; import
  warnings stay informational until access confirms.
- Deferral requires explicit kanban notes on both trips, roadmap carryover
  lines, and eventual `campaign_plots` migration — not silent omission.
- Scripts do not auto-enforce hour caps or deferral; policy is documented until
  validation is added to `itinerary_feedback.py`.
