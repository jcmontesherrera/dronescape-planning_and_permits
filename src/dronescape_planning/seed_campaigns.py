"""Bootstrap campaigns.db schema (HANDOFF.md §3)."""

import argparse
import sqlite3
import sys

from dronescape_planning.paths import ARD_STATE, CAMPAIGNS, TERN_PLOTS

SCHEMA = """
CREATE TABLE IF NOT EXISTS properties (
    property_name TEXT PRIMARY KEY,
    email_address TEXT,
    tenure        TEXT,
    jurisdiction  TEXT,
    access_status TEXT DEFAULT 'unknown'
        CHECK (access_status IN ('unknown', 'pending', 'confirmed', 'denied')),
    notes         TEXT
);

CREATE TABLE IF NOT EXISTS campaigns (
    trip_id       TEXT PRIMARY KEY,
    route_origin  TEXT,
    route_dest    TEXT,
    start_date    TEXT,
    end_date      TEXT,
    season        TEXT,
    enso_phase    TEXT,
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
    trip_id            TEXT NOT NULL,
    visit_date         TEXT NOT NULL,
    day_number         INTEGER,
    day_name           TEXT,
    travel             TEXT,
    sites_visited      TEXT,
    property_visited   TEXT,
    notes              TEXT,
    drive_time         TEXT,
    survey_time        TEXT,
    post_survey_time   TEXT,
    redundancy_time    TEXT,
    total_time         TEXT,
    accommodation      TEXT,
    accom_link         TEXT,
    booking_status     TEXT,
    source_csv         TEXT,
    imported_at        TEXT,
    PRIMARY KEY (trip_id, visit_date)
);
"""

DROP_TABLES = [
    "DROP TABLE IF EXISTS campaign_plots",
    "DROP TABLE IF EXISTS campaigns",
    "DROP TABLE IF EXISTS properties",
]


def parse_args():
    p = argparse.ArgumentParser(description="Bootstrap campaigns.db schema.")
    p.add_argument("--reset", action="store_true")
    p.add_argument("--yes", action="store_true")
    p.add_argument("--quiet", action="store_true")
    return p.parse_args()


def confirm_reset():
    answer = input(
        "This will drop all data in properties, campaigns, and campaign_plots. Continue? [y/N] "
    )
    return answer.strip().lower() == "y"


def main():
    args = parse_args()

    if not TERN_PLOTS.exists():
        print(f"ERROR: tern_plots.db not found at {TERN_PLOTS}", file=sys.stderr)
        sys.exit(1)

    CAMPAIGNS.parent.mkdir(parents=True, exist_ok=True)

    if args.reset:
        if not args.yes and not confirm_reset():
            print("Aborted.")
            sys.exit(0)

    con = sqlite3.connect(CAMPAIGNS)
    con.execute("PRAGMA journal_mode=WAL")
    con.execute(f"ATTACH DATABASE '{TERN_PLOTS.as_posix()}' AS tp")
    ard_attached = ARD_STATE.exists()
    if ard_attached:
        con.execute(f"ATTACH DATABASE '{ARD_STATE.as_posix()}' AS ard")

    if args.reset:
        for stmt in DROP_TABLES:
            con.execute(stmt)

    for stmt in SCHEMA.strip().split(";"):
        stmt = stmt.strip()
        if stmt:
            con.execute(stmt)
    con.commit()

    if not args.quiet:
        prop_n = con.execute("SELECT COUNT(*) FROM properties").fetchone()[0]
        camp_n = con.execute("SELECT COUNT(*) FROM campaigns").fetchone()[0]
        plots_n = con.execute("SELECT COUNT(*) FROM campaign_plots").fetchone()[0]
        tp_n = con.execute("SELECT COUNT(*) FROM tp.plots").fetchone()[0]
        print(f"campaigns.db ready at {CAMPAIGNS}")
        print(f"  properties:       {prop_n} rows")
        print(f"  campaigns:        {camp_n} rows")
        print(f"  campaign_plots:   {plots_n} rows")
        print(f"attached tp.plots:       {tp_n} rows")
        if ard_attached:
            ard_n = con.execute("SELECT COUNT(*) FROM ard.level0_raw").fetchone()[0]
            print(f"attached ard.level0_raw: {ard_n} rows")
        else:
            print(f"ard_state.db not found at {ARD_STATE}")

    con.close()


if __name__ == "__main__":
    main()
