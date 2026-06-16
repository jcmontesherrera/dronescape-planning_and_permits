# HANDOFF — SQL/Python cookbook

SQL queries, schema reference, and Python UDFs for working with the three databases.
For the trip planning workflow, see [docs/workflow.md](docs/workflow.md).

**Read-only rule:** attach `tern_plots.db` and `ard_state.db`; never write to them.
All permit state lives in **`campaigns.db`** (this repo).

---

## 1. Connect to the backbone databases

```python
from pathlib import Path
import sqlite3

REPO_ROOT = Path(__file__).resolve().parent
TERN_MASTER = Path(r"C:/Users/jcmontes/Documents/GitHub/tern_plots_master")
TERN_PLOTS  = TERN_MASTER / "data/tern_plots.db"
ARD_STATE   = Path(r"C:/Users/jcmontes/Documents/GitHub/dronescape_ard/data/ard_state.db")
CAMPAIGNS   = REPO_ROOT / "data" / "campaigns.db"

con = sqlite3.connect(CAMPAIGNS)
con.execute(f"ATTACH DATABASE '{TERN_PLOTS.as_posix()}' AS tp")
if ARD_STATE.exists():
    con.execute(f"ATTACH DATABASE '{ARD_STATE.as_posix()}' AS ard")
con.row_factory = sqlite3.Row
```

A plot is **collected** when it appears in `ard.level0_raw`:
```sql
EXISTS (SELECT 1 FROM ard.level0_raw lr WHERE lr.plot = p.plot)
```
If `ard` is not attached, treat all plots as uncollected for planning purposes.

---

## 2. Uncollected plots shortlist (base query)

```sql
SELECT
    p.plot,
    p.latitude,
    p.longitude,
    p.property,
    p.site_location_name,
    COALESCE(ib.ibra_bioregion_name, '(no IBRA)') AS bioregion,
    COALESCE(nat.nvis_mvg_name, '(no MVG)')       AS mvg,
    COALESCE(nat.nvis_mvs_name, '(no MVS)')       AS mvs,
    p.last_visit_year,
    p.no_of_visits
FROM tp.plots p
LEFT JOIN tp.plot_ibra ib ON ib.plot = p.plot
LEFT JOIN tp.plot_nvis_national nat ON nat.plot = p.plot
WHERE NOT EXISTS (
    SELECT 1 FROM ard.level0_raw lr WHERE lr.plot = p.plot
)
ORDER BY bioregion, p.property, p.plot;
```

Combine with [Concept 09](https://github.com/jcmontes/tern_plots_master/blob/main/docs/concepts/09_stratified_coverage_and_prioritization.md)
gap queries to filter by MVG/MVS before permit outreach.

---

## 3. Schema (campaigns.db)

```sql
CREATE TABLE IF NOT EXISTS properties (
    property_name TEXT PRIMARY KEY,   -- must match tp.plots.property exactly
    email_address TEXT,
    tenure        TEXT,               -- national park, nature reserve, crown land, private, ...
    jurisdiction  TEXT,               -- LGA name or Unincorporated Area
    access_status TEXT DEFAULT 'unknown'
        CHECK (access_status IN ('unknown','pending','confirmed','denied')),
    notes         TEXT
);

CREATE TABLE IF NOT EXISTS campaigns (
    trip_id       TEXT PRIMARY KEY,   -- e.g. 01-ADL-BRI-2026-06
    route_origin  TEXT,
    route_dest    TEXT,
    start_date    TEXT,
    end_date      TEXT,
    season        TEXT,               -- summer / winter
    enso_phase    TEXT,               -- neutral / nino / nina
    notes         TEXT
);

CREATE TABLE IF NOT EXISTS campaign_plots (
    trip_id      TEXT NOT NULL REFERENCES campaigns(trip_id),
    plot         TEXT NOT NULL,
    access_notes TEXT,
    visit_date   TEXT,
    collected    INTEGER DEFAULT 0,
    PRIMARY KEY (trip_id, plot)
);

CREATE TABLE IF NOT EXISTS itinerary_days (
    trip_id        TEXT NOT NULL,
    visit_date     TEXT NOT NULL,
    travel         TEXT,
    accommodation  TEXT,
    booking_status TEXT,
    notes          TEXT,
    PRIMARY KEY (trip_id, visit_date)
);
```

Property name for a campaign plot is resolved at query time:

```sql
SELECT cp.trip_id, cp.plot, p.property, pr.access_status, pr.email_address
FROM campaign_plots cp
JOIN tp.plots p ON p.plot = cp.plot
LEFT JOIN properties pr ON pr.property_name = p.property;
```

Add contact rows via SQL or `trip_audit --register`:
```sql
INSERT OR REPLACE INTO properties
    (property_name, email_address, tenure, jurisdiction, access_status)
VALUES ('Exact TERN Property Name', 'email@example.com', 'national park', 'NSW NPWS', 'confirmed');
```

---

## 4. Highest-value properties (most uncollected plots per landholder)

```sql
SELECT
    p.property,
    COUNT(*) AS uncollected_plots,
    GROUP_CONCAT(p.plot, ', ') AS plot_ids,
    ROUND(AVG(p.latitude), 4)  AS centroid_lat,
    ROUND(AVG(p.longitude), 4) AS centroid_lon,
    pr.email_address,
    pr.tenure,
    pr.access_status
FROM tp.plots p
LEFT JOIN properties pr ON pr.property_name = p.property
WHERE p.property IS NOT NULL
  AND TRIM(p.property) != ''
  AND NOT EXISTS (SELECT 1 FROM ard.level0_raw lr WHERE lr.plot = p.plot)
GROUP BY p.property
ORDER BY uncollected_plots DESC, p.property;
```

Sort by `uncollected_plots DESC` when building kanban priorities.

---

## 5. Seasonal filters

| Region | Window | Latitude filter |
|--------|--------|----------------|
| Northern Australia | Winter dry (May–Sep) | `p.latitude > -23.5` |
| Southern Australia | Summer (Nov–Mar) | `p.latitude < -30` |

Example — uncollected plots north of the Tropic, winter 2027:
```sql
SELECT p.plot, p.property, p.latitude, p.longitude, ib.ibra_bioregion_name
FROM tp.plots p
LEFT JOIN tp.plot_ibra ib ON ib.plot = p.plot
WHERE p.latitude > -23.5
  AND NOT EXISTS (SELECT 1 FROM ard.level0_raw lr WHERE lr.plot = p.plot)
ORDER BY p.property, p.plot;
```

ENSO posture — update `campaigns.enso_phase` manually each season:

| Phase | Effect on northern windows |
|-------|---------------------------|
| El Niño | Often drier; can extend workable windows — watch heat/fire |
| La Niña | Wetter; tracks may close — add buffer days |
| Neutral | Use seasonal rules above |

---

## 6. Proximity clustering (haversine UDF)

```python
import math

def haversine_km(lat1, lon1, lat2, lon2):
    r = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlon / 2) ** 2
    )
    return r * 2 * math.asin(math.sqrt(min(1.0, a)))

con.create_function("haversine_km", 4, haversine_km)

SEED_LAT, SEED_LON = -31.95, 141.45  # e.g. Broken Hill
MAX_KM = 150

rows = con.execute(
    """
    SELECT
        p.plot,
        p.property,
        p.latitude,
        p.longitude,
        haversine_km(?, ?, p.latitude, p.longitude) AS dist_km
    FROM tp.plots p
    WHERE p.latitude IS NOT NULL
      AND p.longitude IS NOT NULL
      AND NOT EXISTS (SELECT 1 FROM ard.level0_raw lr WHERE lr.plot = p.plot)
    HAVING dist_km < ?
    ORDER BY dist_km
    """,
    (SEED_LAT, SEED_LON, MAX_KM),
).fetchall()
```

Use the last plot collected on a trip as the next seed to chain 10–12 day legs.

---

## 7. Quick reference — join keys

| Database | Alias | Key tables | Join on |
|----------|-------|-----------|---------|
| `tern_plots.db` | `tp` | `plots`, `plot_ibra`, `plot_nvis_national` | `plot` |
| `ard_state.db` | `ard` | `level0_raw` | `plot` |
| `campaigns.db` | (main) | `properties`, `campaigns`, `campaign_plots` | `property_name` ↔ `tp.plots.property` |

---

## 8. Regenerate upstream data

```powershell
cd C:\Users\jcmontes\Documents\GitHub\dronescape_ard
ard scan

cd C:\Users\jcmontes\Documents\GitHub\tern_plots_master
tplots attach-check --db data/tern_plots.db
tplots report --db data/tern_plots.db --output-dir docs/reports
```

Run after each `ard scan` so uncollected counts match disk reality.

---

*Upstream doc: [Concept 12 — Fieldwork planning handoff](https://github.com/jcmontes/tern_plots_master/blob/main/docs/concepts/12_fieldwork_planning_handoff.md)*
