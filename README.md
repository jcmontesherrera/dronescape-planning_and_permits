# dronescape-planning_and_permits

Permit tracking, trip logistics, and corridor shortlisting for the
[DroneScape](https://www.utas.edu.au/research/projects/terraluma/research/dronescape)
field campaign. Downstream of [tern_plots_master](https://github.com/jcmontes/tern_plots_master) —
see [Concept 12](https://github.com/jcmontes/tern_plots_master/blob/main/docs/concepts/12_fieldwork_planning_handoff.md).

**Parallel branch:** [dronescape-lidar-quicklook](https://github.com/jcmontes/dronescape-lidar-quicklook)
assesses LiDAR capture quality — complementary, not a dependency.

---

## The cycle

```mermaid
flowchart LR
    refresh["Refresh upstream\nard scan + tplots report"] --> shortlist["scripts/shortlist.py\n(rank properties)"]
    shortlist --> kanban["boards/ kanban\n(permit tracking)"]
    kanban --> emails["Outreach emails\ndocs/outreach.md"]
    emails --> checklist["scripts/generate_checklist.py\n(logistics doc)"]
    checklist --> field["Field"]
    field --> refresh
```

After fieldwork: `ds transfer` → `ard scan` → `tplots report` → re-run shortlist.

---

## What do you want to do?

| Goal | Open this |
|------|-----------|
| Plan or prep a trip end-to-end | [docs/workflow.md](docs/workflow.md) |
| Track permits on an active trip | `boards/NN-ORIG-DEST-Access-applications.md` in Obsidian |
| Draft or send an access email | [docs/outreach.md](docs/outreach.md) |
| SQL schema, queries, haversine UDF | [HANDOFF.md](HANDOFF.md) |
| 2026–2028 corridor roadmap | [docs/campaign-roadmap.md](docs/campaign-roadmap.md) |

---

## Database paths

| Database | Alias | Path | Writable? |
|----------|-------|------|-----------|
| `tern_plots.db` | `tp` | `C:/Users/jcmontes/Documents/GitHub/tern_plots_master/data/tern_plots.db` | No |
| `ard_state.db` | `ard` | `C:/Users/jcmontes/Documents/GitHub/dronescape_ard/data/ard_state.db` | No |
| `campaigns.db` | (main) | `./data/campaigns.db` | Yes |

Never write to `tp.*` or `ard.*` from this repo.

---

## Install

```powershell
# Full install (maps + DOCX generation) — recommended
pip install -e ".[all]"

# Bootstrap the local DB schema (once)
python scripts/seed_campaigns.py
```

Core scripts work via `scripts/` launchers or installed CLI commands (`ds-shortlist`, `ds-trip-audit`, `ds-seed`, `ds-import-itinerary`, `ds-checklist`, `ds-generate-kml`).
Stdlib-only unless you install `[maps]` or `[docx]` extras.

### KMZ maps (`ds-generate-kml`)

Outputs land in `docs/itineraries/maps/`. Open `.kmz` in Google Earth.

```powershell
# Upcoming trip route (from logistics CSV)
ds-generate-kml --trip-id 02-BRI-BRK-2026-07 `
    --csv docs/itineraries/02-BRI-BRK-2026-07-itinerary.csv

# Planning iteration — keep versions side by side
ds-generate-kml --trip-id 02-BRI-BRK-2026-07 `
    --csv docs/itineraries/02-BRI-BRK-2026-07-itinerary-v1-coworker.csv --label v1-coworker

# National collected footprint (boss map; regenerate after ard scan)
ds-generate-kml --collected
```

Trip KMZ = daily route for planning and upcoming-trip previews. Collected KMZ = every plot in `ard.level0_raw`. Checklist `--maps` PNGs are separate (email attachments).

---

## Repository layout

```
README.md                       ← you are here
HANDOFF.md                      ← SQL/Python cookbook
data/
  campaigns.db                  ← permit state (gitignored)
boards/                         ← Obsidian kanban per trip
docs/
  workflow.md                   ← end-to-end trip planning steps
  outreach.md                   ← email drafting guide
  campaign-roadmap.md           ← 2026–2028 corridor chain
  itineraries/                  ← CSV exports from shared Excel
  checklists/                   ← generated output (gitignored)
  access/                       ← credential PDFs + filled forms (gitignored contents)
  drafts/                       ← shortlist briefs (gitignored)
  audits/                       ← trip_audit + feedback reports (gitignored)
scripts/                        ← CLI launchers
src/dronescape_planning/        ← Python modules
templates/                      ← email skeleton
```
