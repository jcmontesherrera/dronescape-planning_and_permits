"""
Import a two-section logistics CSV (daily schedule + site master list).

Updates campaign_plots.visit_date and stores day-level logistics in
itinerary_days. Writes a reconcile report to docs/audits/.

Usage:
    python scripts/import_itinerary.py --trip-id 01-ADL-BRI-2026-06 \\
        --csv docs/itineraries/01-ADL-BRI-2026-06-itinerary.csv

    python scripts/import_itinerary.py --trip-id 01-ADL-BRI-2026-06 \\
        --csv docs/itineraries/01-ADL-BRI-2026-06-itinerary.csv --dry-run

    python scripts/import_itinerary.py ... --no-feedback   # skip coworker summary
"""

from __future__ import annotations

import argparse
import csv
import re
import sqlite3
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from dronescape_planning.db import open_planning_db
from dronescape_planning.paths import CAMPAIGNS, DOCS_AUDITS, DOCS_ITINERARIES, TERN_PLOTS
from dronescape_planning.seed_campaigns import ITINERARY_DAYS_SCHEMA

SITE_ORDER_MARKER = "SITE ORDER"
NULL_VALUES = {"", "NULL", "null", "None"}


@dataclass
class DailyRow:
    day_number: int | None
    visit_date: str
    day_name: str
    travel: str
    plots: list[str]
    property_visited: str
    notes: str
    drive_time: str
    survey_time: str
    post_survey_time: str
    redundancy_time: str
    total_time: str
    accommodation: str
    accom_link: str
    booking_status: str


@dataclass
class SiteRow:
    site_order: int | None
    plot: str
    property_name: str
    trip_tag: str


@dataclass
class ImportResult:
    trip_id: str
    daily_rows: list[DailyRow]
    site_rows: list[SiteRow]
    scheduled_plots: dict[str, str] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    visit_date_updates: list[tuple[str, str | None, str]] = field(default_factory=list)


def _cell(row: list[str], idx: int) -> str:
    if idx >= len(row):
        return ""
    return row[idx].strip()


def parse_plot_ids(raw: str) -> list[str]:
    if not raw or raw.upper() in NULL_VALUES:
        return []
    return re.findall(r"[A-Z]{2}[A-Z0-9]{6,}", raw.upper())


def parse_date(raw: str) -> str | None:
    raw = raw.strip()
    if not raw:
        return None
    for fmt in ("%d/%m/%Y", "%d/%m/%y"):
        try:
            return datetime.strptime(raw, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None


def parse_itinerary_csv(path: Path) -> tuple[list[DailyRow], list[SiteRow]]:
    text = path.read_text(encoding="utf-8-sig")
    reader = csv.reader(text.splitlines())
    daily_rows: list[DailyRow] = []
    site_rows: list[SiteRow] = []
    section = "daily"

    for row in reader:
        if not row or all(not c.strip() for c in row):
            continue
        first = _cell(row, 0)
        if first == SITE_ORDER_MARKER:
            section = "sites"
            continue

        if section == "daily":
            if first.lower() == "days":
                continue
            visit_date = parse_date(_cell(row, 1))
            if not visit_date:
                continue
            day_raw = _cell(row, 0)
            daily_rows.append(
                DailyRow(
                    day_number=int(day_raw) if day_raw.isdigit() else None,
                    visit_date=visit_date,
                    day_name=_cell(row, 2),
                    travel=_cell(row, 3),
                    plots=parse_plot_ids(_cell(row, 4)),
                    property_visited=_cell(row, 5),
                    notes=_cell(row, 6),
                    drive_time=_cell(row, 7),
                    survey_time=_cell(row, 8),
                    post_survey_time=_cell(row, 9),
                    redundancy_time=_cell(row, 10),
                    total_time=_cell(row, 11),
                    accommodation=_cell(row, 12),
                    accom_link=_cell(row, 13),
                    booking_status=_cell(row, 14) if len(row) > 14 else "",
                )
            )
        else:
            plot = _cell(row, 1)
            if not plot or plot.upper() in NULL_VALUES:
                continue
            order_raw = _cell(row, 0)
            site_rows.append(
                SiteRow(
                    site_order=int(order_raw) if order_raw.isdigit() else None,
                    plot=plot.upper(),
                    property_name=_cell(row, 2),
                    trip_tag=_cell(row, 9),
                )
            )

    return daily_rows, site_rows


def resolve_trip_id(con: sqlite3.Connection, requested: str) -> str | None:
    candidates: list[str] = [requested]
    if re.match(r"^\d+-", requested):
        candidates.append(re.sub(r"^\d+-", "", requested, count=1))

    for candidate in candidates:
        n = con.execute(
            "SELECT COUNT(*) FROM campaign_plots WHERE trip_id = ?", (candidate,)
        ).fetchone()[0]
        if n:
            return candidate

    core = re.sub(r"^\d+-", "", requested, count=1)
    for (tid,) in con.execute("SELECT trip_id FROM campaigns").fetchall():
        if tid in candidates:
            continue
        if tid == core or tid.endswith(core):
            n = con.execute(
                "SELECT COUNT(*) FROM campaign_plots WHERE trip_id = ?", (tid,)
            ).fetchone()[0]
            if n:
                return tid
    return None


def ensure_itinerary_schema(con: sqlite3.Connection) -> None:
    con.execute(ITINERARY_DAYS_SCHEMA)


def reconcile(
    trip_id: str,
    daily_rows: list[DailyRow],
    site_rows: list[SiteRow],
    con: sqlite3.Connection,
) -> ImportResult:
    result = ImportResult(trip_id=trip_id, daily_rows=daily_rows, site_rows=site_rows)

    tern_plots = {
        r[0]
        for r in con.execute("SELECT plot FROM tp.plots").fetchall()
    }
    campaign_plots = {
        r[0]: r[1]
        for r in con.execute(
            "SELECT plot, visit_date FROM campaign_plots WHERE trip_id = ?", (trip_id,)
        ).fetchall()
    }

    for day in daily_rows:
        for plot in day.plots:
            if plot not in tern_plots:
                result.errors.append(f"Unknown plot ID in daily schedule: {plot} on {day.visit_date}")
                continue
            result.scheduled_plots[plot] = day.visit_date

    active_sites = [s for s in site_rows if not s.trip_tag.upper().startswith("BACKUP")]
    backup_sites = [s for s in site_rows if s.trip_tag.upper().startswith("BACKUP")]
    unnumbered = [s for s in active_sites if s.site_order is None]

    for site in unnumbered:
        if site.plot not in result.scheduled_plots:
            result.warnings.append(
                f"{site.plot} ({site.property_name}) listed in site master but not scheduled "
                f"(no site order / not in daily rows)"
            )

    for plot, date in result.scheduled_plots.items():
        if plot not in campaign_plots:
            result.warnings.append(
                f"{plot} scheduled on {date} but not in campaign_plots for {trip_id}"
            )
        old = campaign_plots.get(plot)
        if old != date:
            result.visit_date_updates.append((plot, old, date))

    scheduled_set = set(result.scheduled_plots)
    for plot in campaign_plots:
        if plot in scheduled_set:
            continue
        site = next((s for s in site_rows if s.plot == plot), None)
        if site and site.trip_tag.upper().startswith("BACKUP"):
            continue
        if site and site.site_order is None:
            continue
        result.warnings.append(
            f"{plot} in campaign_plots but not in daily schedule (visit_date will stay unset)"
        )

    for site in backup_sites:
        if site.plot in scheduled_set:
            result.warnings.append(
                f"{site.plot} marked BACKUP in site list but appears in daily schedule on "
                f"{result.scheduled_plots[site.plot]}"
            )

    return result


def apply_import(
    result: ImportResult,
    csv_path: Path,
    dry_run: bool = False,
) -> None:
    if result.errors:
        return

    con = open_planning_db(attach_ard=False)
    ensure_itinerary_schema(con)
    imported_at = datetime.now().isoformat(timespec="seconds")

    if not dry_run:
        for day in result.daily_rows:
            con.execute(
                """
                INSERT OR REPLACE INTO itinerary_days (
                    trip_id, visit_date, day_number, day_name, travel, sites_visited,
                    property_visited, notes, drive_time, survey_time, post_survey_time,
                    redundancy_time, total_time, accommodation, accom_link, booking_status,
                    source_csv, imported_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    result.trip_id,
                    day.visit_date,
                    day.day_number,
                    day.day_name,
                    day.travel,
                    " ".join(day.plots) if day.plots else None,
                    day.property_visited or None,
                    day.notes or None,
                    day.drive_time or None,
                    day.survey_time or None,
                    day.post_survey_time or None,
                    day.redundancy_time or None,
                    day.total_time or None,
                    day.accommodation or None,
                    day.accom_link or None,
                    day.booking_status or None,
                    str(csv_path),
                    imported_at,
                ),
            )

        for plot, _, new_date in result.visit_date_updates:
            con.execute(
                """
                UPDATE campaign_plots SET visit_date = ?
                WHERE trip_id = ? AND plot = ?
                """,
                (new_date, result.trip_id, plot),
            )

        for plot, date in result.scheduled_plots.items():
            if not any(u[0] == plot for u in result.visit_date_updates):
                con.execute(
                    """
                    UPDATE campaign_plots SET visit_date = ?
                    WHERE trip_id = ? AND plot = ?
                    """,
                    (date, result.trip_id, plot),
                )

        con.commit()
    con.close()


def write_report(result: ImportResult, csv_path: Path, dry_run: bool) -> Path:
    """Technical reconcile report (errors, warnings, visit_date changes only)."""
    DOCS_AUDITS.mkdir(parents=True, exist_ok=True)
    out = DOCS_AUDITS / f"{result.trip_id}-itinerary-import.md"
    lines = [
        f"# Itinerary import: {result.trip_id}",
        "",
        f"- Source: `{csv_path}`",
        f"- Mode: {'dry-run (no DB writes)' if dry_run else 'applied'}",
        f"- Scheduled plots: {len(result.scheduled_plots)}",
        f"- Visit date updates: {len(result.visit_date_updates)}",
        "",
        "See also: "
        f"`docs/audits/{result.trip_id}-itinerary-feedback.md` for the team copy-paste summary.",
        "",
    ]

    if result.errors:
        lines += ["## Errors", ""] + [f"- {e}" for e in result.errors] + [""]

    if result.warnings:
        lines += ["## Warnings", ""] + [f"- {w}" for w in result.warnings] + [""]

    if result.visit_date_updates:
        lines += ["## Visit date changes", "", "| Plot | Old | New |", "|------|-----|-----|"]
        for plot, old, new in sorted(result.visit_date_updates):
            lines.append(f"| {plot} | {old or '—'} | {new} |")
        lines.append("")

    out.write_text("\n".join(lines), encoding="utf-8")
    return out


def import_itinerary(
    trip_id: str,
    csv_path: Path,
    *,
    dry_run: bool = False,
    kanban_path: Path | None = None,
    write_feedback_doc: bool = True,
) -> ImportResult:
    if not csv_path.exists():
        sys.exit(f"ERROR: CSV not found at {csv_path}")
    if not CAMPAIGNS.exists():
        sys.exit(f"ERROR: campaigns.db not found at {CAMPAIGNS}. Run seed_campaigns.py first.")
    if not TERN_PLOTS.exists():
        sys.exit(f"ERROR: tern_plots.db not found at {TERN_PLOTS}")

    daily_rows, site_rows = parse_itinerary_csv(csv_path)

    con = open_planning_db(attach_ard=False)
    resolved = resolve_trip_id(con, trip_id)
    if not resolved:
        con.close()
        sys.exit(
            f"ERROR: trip_id '{trip_id}' not found in campaigns.db "
            f"(no matching row with campaign_plots)."
        )
    if resolved != trip_id:
        print(f"Note: resolved trip_id '{trip_id}' -> '{resolved}'")

    result = reconcile(resolved, daily_rows, site_rows, con)
    con.close()

    apply_import(result, csv_path, dry_run=dry_run)
    report_path = write_report(result, csv_path, dry_run)

    feedback_path = None
    if write_feedback_doc:
        from dronescape_planning.itinerary_feedback import default_kanban_path, write_feedback

        feedback_path = write_feedback(
            result,
            csv_path,
            dry_run=dry_run,
            kanban_path=kanban_path or default_kanban_path(resolved),
        )

    print(f"Parsed {len(daily_rows)} daily rows, {len(site_rows)} site rows.")
    print(f"Scheduled {len(result.scheduled_plots)} plots across field days.")
    if result.errors:
        print(f"ERRORS: {len(result.errors)} — import not applied.")
        for e in result.errors:
            print(f"  ! {e}")
    elif dry_run:
        print(f"Dry-run: {len(result.visit_date_updates)} visit_date updates would be applied.")
    else:
        print(f"Applied {len(result.visit_date_updates)} visit_date updates.")
    if result.warnings:
        print(f"Warnings: {len(result.warnings)}")
        for w in result.warnings:
            print(f"  * {w}")
    print(f"Report: {report_path}")
    if feedback_path:
        print(f"Feedback: {feedback_path}")

    return result


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Import logistics itinerary CSV into campaigns.db.")
    p.add_argument("--trip-id", required=True, help="Trip id, e.g. 01-ADL-BRI-2026-06")
    p.add_argument(
        "--csv",
        type=Path,
        required=True,
        help="Path to itinerary CSV (two-section format from shared Excel).",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse and report only; do not write to campaigns.db.",
    )
    p.add_argument(
        "--no-feedback",
        action="store_true",
        help="Skip coworker feedback markdown (docs/audits/*-itinerary-feedback.md).",
    )
    p.add_argument(
        "--kanban",
        type=Path,
        default=None,
        help="Kanban board for access cross-check in feedback (auto-detected if omitted).",
    )
    return p.parse_args()


def main() -> None:
    args = parse_args()
    result = import_itinerary(
        args.trip_id,
        args.csv,
        dry_run=args.dry_run,
        kanban_path=args.kanban,
        write_feedback_doc=not args.no_feedback,
    )
    if result.errors:
        sys.exit(1)


if __name__ == "__main__":
    main()
