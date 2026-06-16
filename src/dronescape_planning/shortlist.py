"""
Shortlist uncollected properties for a DroneScape field trip.

Runs the HANDOFF.md §3 "highest-value uncollected properties" query, optionally
filtered by latitude band, IBRA bioregion, NVIS MVG name, state-code prefix,
and/or proximity to a seed point (HANDOFF §5 haversine UDF).

The ranking unit is tp.plots.property — one row per landholder/park/station.
High uncollected_plots on a single property = one access application covers
many scan days (low permit + logistics complexity).

Email address is a contact detail only; it is not used for ranking or grouping.

Output modes
------------
  (default)   Pretty table to stdout.
  --csv PATH  Write CSV to PATH.
  --draft     Write a planning brief markdown (not a kanban).

Usage examples
--------------
  # Top 15 northern properties (winter corridor):
  python scripts/shortlist.py --lat-min -23.5 --top 15

  # Broken Hill squeeze trip:
  python scripts/shortlist.py --seed-lat -31.95 --seed-lon 141.45 --max-km 400 \\
      --draft docs/drafts/03-BRK-squeeze-draft.md \\
      --trip-id 03-BRK-2026-08 \\
      --route "Broken Hill loop" --dates "2026-08-10..2026-08-22" --season winter

  # Calperum block:
  python scripts/shortlist.py --seed-lat -34.00 --seed-lon 140.70 --max-km 250 \\
      --draft docs/drafts/04-BRK-CAL-ADL-draft.md \\
      --trip-id 04-BRK-CAL-ADL-2026-09 \\
      --route "Broken Hill -> Calperum -> Adelaide" \\
      --dates "2026-09-07..2026-09-25" --season "late winter"
"""

import argparse
import csv
import math
import sqlite3
import sys
from pathlib import Path

from dronescape_planning.paths import ARD_STATE, CAMPAIGNS, DOCS_DRAFTS, REPO_ROOT, TERN_PLOTS


# ---------------------------------------------------------------------------
# Haversine UDF (HANDOFF §5)
# ---------------------------------------------------------------------------

def _haversine_km(lat1, lon1, lat2, lon2):
    if None in (lat1, lon1, lat2, lon2):
        return None
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


# ---------------------------------------------------------------------------
# Query builder
# ---------------------------------------------------------------------------

def build_query(args, ard_attached: bool) -> tuple[str, list]:
    """Return (sql, params) for the highest-value properties query."""

    # Uncollected predicate
    if ard_attached:
        uncollected = "NOT EXISTS (SELECT 1 FROM ard.level0_raw lr WHERE lr.plot = p.plot)"
    else:
        uncollected = "1=1"  # treat all plots as uncollected when ard absent

    # Per-plot filter clauses (applied inside the GROUP BY aggregation)
    plot_filters = [f"p.property IS NOT NULL", "TRIM(p.property) != ''", uncollected]
    params: list = []

    if args.lat_min is not None:
        plot_filters.append("p.latitude >= ?")
        params.append(args.lat_min)
    if args.lat_max is not None:
        plot_filters.append("p.latitude <= ?")
        params.append(args.lat_max)
    if args.state_prefix:
        plot_filters.append("SUBSTR(p.plot, 1, 2) = ?")
        params.append(args.state_prefix.upper())
    if args.seed_lat is not None:
        plot_filters.append(
            "haversine_km(?, ?, p.latitude, p.longitude) <= ?"
        )
        params.extend([args.seed_lat, args.seed_lon, args.max_km])

    # Post-GROUP BY (HAVING) filters
    having_clauses = []
    having_params: list = []

    if args.min_plots > 1:
        having_clauses.append("uncollected_plots >= ?")
        having_params.append(args.min_plots)

    # Bioregion / MVG joins require a sub-select to avoid exploding GROUP BY
    bioregion_join = ""
    mvg_join = ""
    bioregion_filter = ""
    mvg_filter = ""

    if args.bioregion:
        bioregion_join = "JOIN tp.plot_ibra ib ON ib.plot = p.plot"
        bioregion_filter = "AND ib.ibra_bioregion_name LIKE ?"
        params.insert(0, f"%{args.bioregion}%")  # prepend before other params

    if args.mvg:
        mvg_join = "JOIN tp.plot_nvis_national nat2 ON nat2.plot = p.plot"
        mvg_filter = "AND nat2.nvis_mvg_name LIKE ?"
        params.insert(0 if not args.bioregion else 1, f"%{args.mvg}%")

    where = " AND ".join(plot_filters)
    having = ("HAVING " + " AND ".join(having_clauses)) if having_clauses else ""

    sql = f"""
SELECT
    p.property,
    COUNT(*)                            AS uncollected_plots,
    GROUP_CONCAT(p.plot, ', ')          AS plot_ids,
    ROUND(AVG(p.latitude),  4)          AS centroid_lat,
    ROUND(AVG(p.longitude), 4)          AS centroid_lon,
    GROUP_CONCAT(DISTINCT COALESCE(ib.ibra_bioregion_name, ''))  AS bioregions,
    GROUP_CONCAT(DISTINCT COALESCE(nat.nvis_mvg_name, ''))       AS mvgs,
    pr.tenure,
    pr.jurisdiction,
    pr.access_status,
    pr.email_address,
    pr.notes
FROM tp.plots p
{bioregion_join}
{mvg_join}
LEFT JOIN tp.plot_ibra   ib  ON ib.plot  = p.plot
LEFT JOIN tp.plot_nvis_national nat ON nat.plot = p.plot
LEFT JOIN properties     pr  ON pr.property_name = p.property
WHERE {where}
{bioregion_filter}
{mvg_filter}
GROUP BY p.property
{having}
ORDER BY uncollected_plots DESC, p.property
LIMIT ?
"""
    params.extend(having_params)
    params.append(args.top)
    return sql, params


# ---------------------------------------------------------------------------
# Output formatters
# ---------------------------------------------------------------------------

COLUMNS = [
    "property", "uncollected_plots", "plot_ids",
    "centroid_lat", "centroid_lon", "bioregions", "mvgs",
    "tenure", "jurisdiction", "access_status", "email_address", "notes",
]


def print_table(rows):
    if not rows:
        print("No results.")
        return

    col_widths = {c: len(c) for c in COLUMNS}
    data = []
    for row in rows:
        d = dict(zip(COLUMNS, row))
        d = {k: str(v) if v is not None else "" for k, v in d.items()}
        data.append(d)
        for c in COLUMNS:
            col_widths[c] = max(col_widths[c], len(d[c]))

    # Print only the most useful columns in the table view
    visible = ["property", "uncollected_plots", "centroid_lat", "centroid_lon",
               "tenure", "access_status", "email_address"]
    header = "  ".join(c.ljust(col_widths[c]) for c in visible)
    sep    = "  ".join("-" * col_widths[c] for c in visible)
    print(header)
    print(sep)
    for d in data:
        print("  ".join(d[c].ljust(col_widths[c]) for c in visible))
    print(f"\n{len(rows)} propert{'y' if len(rows)==1 else 'ies'} shown.")


def write_csv(rows, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(COLUMNS)
        w.writerows(rows)
    print(f"CSV written to {path}")


def write_draft(rows, args):
    trip_id = args.trip_id or "DRAFT"
    route   = args.route   or "TBD"
    dates   = args.dates   or "TBD"
    season  = args.season  or ""
    enso    = args.enso    or ""

    season_enso = ", ".join(x for x in [season, enso] if x)

    # Resolve output path
    if args.draft is None or args.draft == "":
        out = DOCS_DRAFTS / f"{trip_id}-draft.md"
    else:
        out = Path(args.draft)
        if out.suffix == "" or out.is_dir():
            out = out / f"{trip_id}-draft.md"

    out.parent.mkdir(parents=True, exist_ok=True)

    # Build filter summary line
    filter_parts = []
    if args.lat_min is not None or args.lat_max is not None:
        lo = args.lat_min if args.lat_min is not None else "–∞"
        hi = args.lat_max if args.lat_max is not None else "+∞"
        filter_parts.append(f"lat in [{lo}, {hi}]")
    if args.seed_lat is not None:
        filter_parts.append(f"within {args.max_km} km of ({args.seed_lat}, {args.seed_lon})")
    if args.bioregion:
        filter_parts.append(f"bioregion~{args.bioregion}")
    if args.mvg:
        filter_parts.append(f"MVG~{args.mvg}")
    if args.state_prefix:
        filter_parts.append(f"state-prefix={args.state_prefix}")
    if args.min_plots > 1:
        filter_parts.append(f"min_plots={args.min_plots}")
    filter_summary = ", ".join(filter_parts) if filter_parts else "none"

    total_props = len(rows)
    total_uncol = sum(r[1] for r in rows)

    lines = [
        f"# Trip draft: {trip_id} ({route})",
        "",
        f"- Field window: {dates}" + (f" ({season_enso})" if season_enso else ""),
        f"- Filters: {filter_summary}",
        f"- Total candidate properties: {total_props} (uncollected plots: {total_uncol})",
        "",
        "> Each section = one property (one permit workflow). "
        "Prefer trips where top-ranked properties pack many plots each.",
        "",
        "## Properties (ranked by uncollected plot count)",
        "",
    ]

    for i, row in enumerate(rows, 1):
        d = dict(zip(COLUMNS, row))
        prop         = d["property"] or "Unknown"
        n_plots      = d["uncollected_plots"]
        plot_ids     = d["plot_ids"]     or "(none)"
        lat          = d["centroid_lat"] or "?"
        lon          = d["centroid_lon"] or "?"
        bioregions   = d["bioregions"]   or "(unknown)"
        mvgs         = d["mvgs"]         or "(unknown)"
        tenure       = d["tenure"]       or "(unknown)"
        jurisdiction = d["jurisdiction"] or "(unknown)"
        email        = d["email_address"] or "(unknown)"
        status       = d["access_status"] or "unknown"
        notes        = d["notes"]        or ""

        lines += [
            f"### {i}. {prop} -- {n_plots} plot{'s' if n_plots != 1 else ''}  (one permit / one kanban card)",
            f"- Plot IDs: {plot_ids}   (all plots on this landholder; same park = low logistics)",
            f"- Centroid: {lat}, {lon}",
            f"- Bioregion(s): {bioregions}",
            f"- MVG(s): {mvgs}",
            f"- Tenure / jurisdiction: {tenure} / {jurisdiction}",
            f"- Contact: {email}   (outreach channel only — not used for ranking or grouping)",
            f"- Access status: {status}",
        ]
        if notes:
            lines.append(f"- Notes: {notes}")
        lines.append("")

    with open(out, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"Draft written to {out}")
    print(f"  {total_props} properties, {total_uncol} uncollected plots.")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args():
    p = argparse.ArgumentParser(
        description="Shortlist highest-value uncollected properties for a field trip.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # Filters
    p.add_argument("--min-plots",    type=int,   default=1,    metavar="N",
                   help="Minimum uncollected plots per property (default: 1).")
    p.add_argument("--lat-min",      type=float, default=None, metavar="LAT",
                   help="Southernmost latitude to include (e.g. -23.5 for north-of-tropic).")
    p.add_argument("--lat-max",      type=float, default=None, metavar="LAT",
                   help="Northernmost latitude to include (e.g. -30 for southern Australia).")
    p.add_argument("--bioregion",    type=str,   default=None, metavar="NAME",
                   help="LIKE filter on ibra_bioregion_name.")
    p.add_argument("--mvg",          type=str,   default=None, metavar="NAME",
                   help="LIKE filter on nvis_mvg_name.")
    p.add_argument("--state-prefix", type=str,   default=None, metavar="XX",
                   help="2-char plot-ID prefix (e.g. NS, QD, NT, SA, WA).")
    p.add_argument("--seed-lat",     type=float, default=None, metavar="LAT",
                   help="Seed latitude for proximity filter.")
    p.add_argument("--seed-lon",     type=float, default=None, metavar="LON",
                   help="Seed longitude for proximity filter.")
    p.add_argument("--max-km",       type=float, default=300,  metavar="KM",
                   help="Radius from seed point in km (default: 300). Requires --seed-lat/--seed-lon.")
    p.add_argument("--top",          type=int,   default=25,   metavar="N",
                   help="Maximum rows to return (default: 25).")

    # Output modes (mutually exclusive)
    out = p.add_mutually_exclusive_group()
    out.add_argument("--csv",   type=str, default=None, metavar="PATH",
                     help="Write output to CSV file at PATH.")
    out.add_argument("--draft", type=str, default=None, nargs="?", const="",
                     help="Write a planning brief markdown. Path defaults to docs/drafts/<trip-id>-draft.md.")

    # Draft metadata (used with --draft)
    p.add_argument("--trip-id", type=str, default=None, metavar="ID",
                   help="Trip identifier, e.g. 03-BRK-2026-08.")
    p.add_argument("--route",   type=str, default=None, metavar="TEXT",
                   help='Route description, e.g. "Broken Hill loop".')
    p.add_argument("--dates",   type=str, default=None, metavar="RANGE",
                   help='Date range, e.g. "2026-08-10..2026-08-22".')
    p.add_argument("--season",  type=str, default=None, metavar="TEXT",
                   help="Season label, e.g. winter.")
    p.add_argument("--enso",    type=str, default=None, metavar="TEXT",
                   help="ENSO phase, e.g. neutral, nino, nina.")

    return p.parse_args()


def main():
    args = parse_args()

    if (args.seed_lat is None) != (args.seed_lon is None):
        print("ERROR: --seed-lat and --seed-lon must be used together.", file=sys.stderr)
        sys.exit(1)

    if not CAMPAIGNS.exists():
        print(f"ERROR: campaigns.db not found at {CAMPAIGNS}. Run seed_campaigns.py first.", file=sys.stderr)
        sys.exit(1)

    if not TERN_PLOTS.exists():
        print(f"ERROR: tern_plots.db not found at {TERN_PLOTS}.", file=sys.stderr)
        sys.exit(1)

    con = sqlite3.connect(CAMPAIGNS)
    con.execute(f"ATTACH DATABASE '{TERN_PLOTS.as_posix()}' AS tp")

    ard_attached = False
    if ARD_STATE.exists():
        con.execute(f"ATTACH DATABASE '{ARD_STATE.as_posix()}' AS ard")
        ard_attached = True
    else:
        print(
            f"WARNING: ard_state.db not found at {ARD_STATE} — treating all plots as uncollected.",
            file=sys.stderr,
        )

    if args.seed_lat is not None:
        con.create_function("haversine_km", 4, _haversine_km)

    sql, params = build_query(args, ard_attached)
    rows = con.execute(sql, params).fetchall()
    con.close()

    if args.csv:
        write_csv(rows, Path(args.csv))
    elif args.draft is not None:
        write_draft(rows, args)
    else:
        print_table(rows)


if __name__ == "__main__":
    main()
