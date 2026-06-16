# ADR 0002 — tp.plots.property as the permit and logistics unit

## Status

Accepted

## Context

Field trips require one access negotiation per landholder (national park, station,
reserve). TERN stores the authoritative name in `plots.property`. Kanban cards,
shortlists, and emails must align on that name — not on plot ID alone or shared
inbox email.

## Decision

- Rank and group planning output by `tp.plots.property`.
- One kanban card per property; list all plot IDs on that card.
- Do **not** merge cards or rank by `email_address` (NPWS regional inboxes may
  cover unrelated parks).

## Consequences

- `shortlist.py` and `trip_audit.py` use `GROUP BY p.property`.
- `properties.property_name` must match `tp.plots.property` exactly.
- Name mismatches (e.g. Glen Orton vs Glen Orten) are resolved via aliases in
  `trip_audit.py` and corrected on the kanban.
