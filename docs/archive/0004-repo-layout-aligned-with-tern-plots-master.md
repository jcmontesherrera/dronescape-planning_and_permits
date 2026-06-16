# ADR 0004 — Repo layout aligned with tern_plots_master

## Status

Accepted

## Context

Sibling repos (`tern_plots_master`, `dronescape_ard`) use a consistent layout:
`data/` for local databases, `decisions/` for ADRs, `docs/` for guides,
`src/<package>/` for Python. This repo was flat (kanban and scripts at root).

## Decision

```
data/           campaigns.db (gitignored)
decisions/      ADRs
docs/           guides, audits/, drafts/
src/dronescape_planning/   Python modules
scripts/        thin launchers (README commands unchanged)
boards/         Obsidian kanban markdown
templates/      email templates
archive/        retired inputs (property-names.csv)
HANDOFF.md      stays at repo root (linked from tern_plots_master Concept 12)
```

## Consequences

- Easier navigation for anyone used to `tern_plots_master`.
- Obsidian workspace paths updated to `boards/`.
- `CAMPAIGNS` path is `data/campaigns.db` via `src/dronescape_planning/paths.py`.
