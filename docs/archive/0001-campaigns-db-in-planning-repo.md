# ADR 0001 — campaigns.db in the planning repo

## Status

Accepted

## Context

Permit workflows, landholder contacts, and trip legs are out of scope for
`tern_plots_master` and `dronescape_ard`. Those repos own plot universes and
scan truth; this repo owns **access and logistics state**.

## Decision

Maintain `data/campaigns.db` in `dronescape-planning_and_permits`. Scripts
`ATTACH` `tern_plots.db` (alias `tp`) and `ard_state.db` (alias `ard`) read-only
for queries. All `INSERT`/`UPDATE`/`DELETE` for permit data go to `campaigns.db` only.

## Consequences

- Clear boundary with upstream repos (Concept 12 / ADR 0004 in tern_plots_master).
- Cross-database SQL works in one session (property grouping + collection status).
- `campaigns.db` is gitignored; schema is recreated via `seed_campaigns.py`.
