# Agent prompts (Cursor)

Copy-paste these into a fresh agent session. Paths assume the repo layout in
[decisions/0004-repo-layout-aligned-with-tern-plots-master.md](../decisions/0004-repo-layout-aligned-with-tern-plots-master.md).

---

## ADL-BRI — full trip audit and register

> Reorganize the repo per decisions/0004, then run trip audit for `boards/01-ADL-BRI-Access-applications.md`, show me `docs/audits/01-ADL-BRI-Access-applications-audit.md`, update the kanban with plot IDs and merge the Properties column, then register `ADL-BRI-2026-06` in `data/campaigns.db` with `access_status` from each column.

Shorter:

> Run `python scripts/trip_audit.py --trip-kanban boards/01-ADL-BRI-Access-applications.md --register` and summarize what still needs a follow-up email.

---

## Plan the next trip (summer, Adelaide)

> Plan the next trip starting from Adelaide for summer 2026/27. Run `scripts/shortlist.py` with `--lat-max -30` and a seed near Renmark (lat -34.18, lon 140.75, max-km 400). Produce a draft brief at `docs/drafts/05-ADL-???-draft.md` and propose 3 candidate routes ranked by uncollected plot count and MVG/MVS gap closure.

---

## Broken Hill — uncontacted multi-plot properties

> Query `tp.plots.property` for all properties within 400 km of Broken Hill (-31.95, 141.45) that have at least 2 uncollected plots and no row in `data/campaigns.db` `properties`. List them sorted by plot count.

---

## Promote next roadmap corridor

> Read `docs/campaign-roadmap.md` and the most recent row in `campaigns`. Tell me which candidate-pool entry should be promoted to the next anchored slot and why, based on vehicle continuity and season.

---

## Compare draft vs kanban

> Compare the draft at `docs/drafts/04-BRK-CAL-ADL-draft.md` against the kanban at `boards/04-BRK-CAL-ADL-Access-applications.md` (when it exists). Which properties are in the draft but not on the board? Which board cards have no contact in `properties`?

---

## Weekly active-trip check-in

> Run `python scripts/trip_audit.py --trip-kanban boards/01-ADL-BRI-Access-applications.md` (no --register). List every card in **Awaiting Response**, note days since the date on the card, and flag any property where plot count on the card does not match `tern_plots.db`.

---

## Sync itinerary CSV from shared Excel

> I downloaded the latest logistics CSV to `docs/itineraries/01-ADL-BRI-2026-06-itinerary.csv`. Run `import_itinerary.py --dry-run`, show me the reconcile report and **itinerary feedback** (`docs/audits/01-ADL-BRI-2026-06-itinerary-feedback.md`), apply the import, regenerate `01-ADL-BRI-2026-06-checklist.md`, and flag any mismatch with the kanban (especially sites in Awaiting Response that are or aren't on the daily schedule).

Shorter:

> Import `docs/itineraries/01-ADL-BRI-2026-06-itinerary.csv` for trip `01-ADL-BRI-2026-06`, regenerate the checklist, and show me the **feedback** file to share with the team.

---

## Draft outreach email for a kanban card

> Read `boards/02-BRI-BRK-Access-applications.md` and `docs/outreach-workflow.md`. Draft the NPWS outreach email for **[Property name]** using `templates/email-template-nationalpark.md`. Dates from `docs/itineraries/02-BRI-BRK-2026-07-itinerary.csv`. List the map PNG to attach from `docs/checklists/maps/`. Return copy-paste ready text only — do not save a draft file.

---

## Late permit — absorb, defer, or skip

> Read `docs/field-day-policy.md` and `docs/campaign-roadmap.md`. A property on `[boards/…]` just moved to Access Confirmed after the itinerary was lead-approved. Tell me whether to absorb on the current CSV, defer to the next anchored leg, or skip — check hour caps (11h weekday / 8h weekend) and permit date window. If absorbing, model in Excel and run `import_itinerary.py --dry-run`; show itinerary feedback.
