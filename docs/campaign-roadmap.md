# Campaign Roadmap — DroneScape 2026–2028

Horizon: June 2026 → early 2028. Target: 6–8 field trips per year.

Two tiers:
1. **Anchored near-term trips** — confirmed or near-confirmed, vehicle continuity locked in.
2. **Candidate pool** — corridors grouped by season. Promote to anchored only when the previous trip's vehicle endpoint is known.

Routing rules: each trip starts where the previous one's vehicle was parked (unless a deliberate fly-in). 10–12 day vehicle blocks; park car, fly home, fly back to resume. Seasonal latitude rule and ENSO posture: see [HANDOFF.md §5](../HANDOFF.md).

---

## Anchored near-term chain

### `01-ADL-BRI-2026-06` — in flight

- Route: Adelaide → Brisbane via inland NSW
- Season: winter 2026 | ENSO: El Niño
- Vehicle endpoint: Brisbane area, early July 2026
- Kanban: [01-ADL-BRI-Access-applications.md](../boards/01-ADL-BRI-Access-applications.md)
- Properties: ~14 (NSW NPWS Central West, Riverina, Barwon groups; Pilliga SCA; Broken Hill Council; Crown Lands Western Region)

### `02-BRI-BRK-2026-07` — drafted

- Route: Brisbane → Broken Hill
- Season: winter 2026 (continuation)
- Vehicle endpoint: **Broken Hill**, late July 2026
- Kanban: [02-BRI-BRK-Access-applications.md](../boards/02-BRI-BRK-Access-applications.md)
- Properties: Broken Hill City Council (Willyama Common), NSW Crown Lands Western Region

### `03-BRK-<TBD>-2026-08` — sites TBD

- Route: Broken Hill area loop (~10–12 days)
- Season: winter 2026 (late)
- Vehicle endpoint: Broken Hill / western NSW, late August 2026
- Generate draft:
  ```powershell
  python scripts/shortlist.py `
      --seed-lat -31.95 --seed-lon 141.45 --max-km 400 `
      --draft docs/drafts/03-BRK-squeeze-draft.md `
      --trip-id 03-BRK-2026-08 `
      --route "Broken Hill loop" --dates "2026-08-10..2026-08-22" --season winter
  ```
- Likely candidates (≤400 km of BRK): Calperum Reserve (7 plots), Murnpeowie Station (7), Boolcoomatta Reserve (6), Fowlers Gap (6), Mungo NP, Mallee Cliffs NP, Kinchega NP, Sturt NP
- Draft brief: [docs/drafts/03-BRK-squeeze-draft.md](drafts/03-BRK-squeeze-draft.md)

### `04-BRK-CAL-ADL-2026-09` — confirmed

- Route: Broken Hill → Calperum Reserve → Adelaide
- Dates: ~7–25 September 2026
- Season: late winter / early spring
- Calperum Reserve: 18 uncollected plots — single largest cluster. One permit covers all 18.
- Vehicle endpoint: **Adelaide**, late September 2026
- Generate draft:
  ```powershell
  python scripts/shortlist.py `
      --seed-lat -34.00 --seed-lon 140.70 --max-km 250 `
      --draft docs/drafts/04-BRK-CAL-ADL-draft.md `
      --trip-id 04-BRK-CAL-ADL-2026-09 `
      --route "Broken Hill -> Calperum -> Adelaide" `
      --dates "2026-09-07..2026-09-25" --season "late winter"
  ```

---

## Candidate pool (post-Sep 2026 Adelaide return)

Counts from `tp.plots.property` as at May 2026 — rerun `shortlist.py` after each `ard scan` to refresh.

### Summer 2026/27 (Dec–Feb) — southern (south of -30°)

- **Alpine National Park** (17 plots, NSW/Vic border) + Tas Midlands top-up
- Mallee / SE SA: Calperum extension, Murray-Sunset NP

### Autumn 2027 (Mar–May) — WA goldfields + Nullarbor

- **Credo Conservation Park** (18) + Bon Bon Station Reserve (8) + Yellabinna (fly-in Perth)

### Winter 2027 (Jun–Aug) — pick one

- **NT Centre:** Owen Springs Reserve (14), Henbury Station (12), Witjira NP (11), Simpson Desert (11), Ethabuka Reserve (10) — fly-in Alice Springs
- **Top End:** Kakadu NP (17), Litchfield NP, Mary River NP — dry season, fly-in Darwin
- **Planned:** `05-DRW-TOP-2027-06` (25 active plots: Litchfield, Kakadu, Koolpinyah, Manton Dam)

### Spring 2027 (Sep–Nov) — Qld channel country

- Innamincka Regional Reserve (9), Bonney Downs Station (10), Brigalow / Mitchell grass belt

### Summer 2027/28 — gap closure

Determine from post-2027 `ard scan` gap report. Generate fresh shortlists at that point.

### Ongoing — property-name disambiguation needed

These `tp.plots.property` values are TERN placeholder names — real plots, but cannot be permitted until the upstream database is corrected:

- `"Not Collected"` — 26 plots
- `"Unallocated Crown Land"` — 12 plots
- `"Crown Land"` — 10 plots

---

## Two-vehicle scenario (optional)

When a second vehicle is available, Vehicle B runs an independent corridor (different base:
Adelaide, Perth, Darwin) with its own `campaigns` rows and kanban. Trip-ids get a `B` suffix
(e.g. `04B-PER-KAL-2027-03`). Nothing is shared except the read-only `tp.plots` data.

---

## Update procedure

1. After each `ard scan` + `tplots report`, re-run `shortlist.py` for the next anchored trip and diff the draft.
2. When a draft is approved, duplicate `00-TRIP-TEMPLATE` → `NN-ORIG-DEST-Access-applications.md`, then insert `campaigns` + `campaign_plots` rows (see [HANDOFF.md](../HANDOFF.md)).
3. Promote a candidate to anchored only once the prior trip's vehicle endpoint is confirmed.
4. Update `campaigns.enso_phase` manually at the start of each season.
