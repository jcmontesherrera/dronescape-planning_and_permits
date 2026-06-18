"""
Generate a coworker-friendly itinerary sync summary from an import result.

Output: docs/audits/<trip-id>-itinerary-feedback.md
Includes a plain-text block at the top for Slack / Teams / email.
"""

from __future__ import annotations

import re
import sqlite3
from datetime import datetime
from pathlib import Path

from dronescape_planning.import_itinerary import DailyRow, ImportResult, parse_plot_ids, resolve_trip_id
from dronescape_planning.paths import BOARDS_DIR, CAMPAIGNS, DOCS_AUDITS
from dronescape_planning.trip_audit import parse_kanban


def _plot_ids_from_card(raw_line: str) -> list[str]:
    m = re.search(r"Plot IDs:\s*([^·]+)", raw_line, re.IGNORECASE)
    if not m:
        return []
    return parse_plot_ids(m.group(1))


def default_kanban_path(trip_id: str) -> Path | None:
    base = re.sub(r"-\d{4}-\d{2}$", "", trip_id)
    path = BOARDS_DIR / f"{base}-Access-applications.md"
    return path if path.exists() else None


def _display_date(iso: str) -> str:
    try:
        dt = datetime.strptime(iso, "%Y-%m-%d")
        return f"{dt.day} {dt.strftime('%b %Y')}"
    except ValueError:
        return iso


def _display_date_short(iso: str) -> str:
    try:
        dt = datetime.strptime(iso, "%Y-%m-%d")
        return f"{dt.day} {dt.strftime('%b')}"
    except ValueError:
        return iso


def _field_day_count(daily_rows: list[DailyRow]) -> int:
    return sum(1 for d in daily_rows if d.plots)


def _kanban_plot_columns(kanban_path: Path) -> dict[str, str]:
    """Map plot id -> kanban column name."""
    plot_column: dict[str, str] = {}
    for card in parse_kanban(kanban_path):
        if card.is_instruction or card.is_backup or not card.kanban_property:
            continue
        for plot in _plot_ids_from_card(card.raw_line):
            plot_column[plot] = card.column
    return plot_column


def _kanban_cross_check(
    result: ImportResult,
    kanban_path: Path | None,
) -> tuple[list[str], list[str]]:
    """Return (action_items, informational_notes)."""
    if not kanban_path or not kanban_path.exists():
        return [], []

    plot_columns = _kanban_plot_columns(kanban_path)
    actions: list[str] = []
    notes: list[str] = []

    for plot, date in sorted(result.scheduled_plots.items()):
        column = plot_columns.get(plot)
        if column == "Awaiting Response":
            actions.append(
                f"{plot} is on the daily schedule ({_display_date_short(date)}) "
                f"but kanban access is still **Awaiting Response** — confirm permit "
                f"before fieldwork or remove from Excel."
            )
        elif column and column not in ("Access Confirmed", "Properties"):
            actions.append(
                f"{plot} is scheduled ({_display_date_short(date)}) but kanban column "
                f"is **{column}** — check access status."
            )

    for plot in plot_columns:
        if plot_columns[plot] != "Awaiting Response":
            continue
        if plot not in result.scheduled_plots:
            prop_hint = next(
                (s.property_name for s in result.site_rows if s.plot == plot),
                plot,
            )
            notes.append(
                f"{plot} ({prop_hint}) — access **Awaiting Response**, not on daily route "
                f"(expected if permit not yet confirmed)."
            )

    return actions, notes


def _campaign_meta(trip_id: str) -> dict[str, str]:
    if not CAMPAIGNS.exists():
        return {}
    con = sqlite3.connect(CAMPAIGNS)
    con.row_factory = sqlite3.Row
    row = con.execute(
        "SELECT route_origin, route_dest, start_date, end_date FROM campaigns WHERE trip_id = ?",
        (trip_id,),
    ).fetchone()
    con.close()
    if not row:
        return {}
    return dict(row)


def _date_moves(result: ImportResult) -> list[tuple[str, str, str]]:
    return [(p, o, n) for p, o, n in result.visit_date_updates if o and o != n]


def _newly_scheduled(result: ImportResult) -> list[tuple[str, str]]:
    return [(p, n) for p, o, n in result.visit_date_updates if not o]


def render_feedback(
    result: ImportResult,
    csv_path: Path,
    *,
    dry_run: bool = False,
    kanban_path: Path | None = None,
) -> str:
    meta = _campaign_meta(result.trip_id)
    route = ""
    if meta.get("route_origin") and meta.get("route_dest"):
        route = f"{meta['route_origin']} → {meta['route_dest']}"
    dates = ""
    if meta.get("start_date") and meta.get("end_date"):
        dates = f"{_display_date(meta['start_date'])} – {_display_date(meta['end_date'])}"

    field_days = _field_day_count(result.daily_rows)
    scheduled = len(result.scheduled_plots)
    kanban = kanban_path or default_kanban_path(result.trip_id)
    actions, kanban_notes = _kanban_cross_check(result, kanban)

    status_line = "BLOCKED — fix errors in Excel and re-export CSV" if result.errors else (
        "DRY-RUN — not applied to DB yet" if dry_run else "OK — imported and checklist can be regenerated"
    )

    # --- Plain-text block for copy-paste ---
    paste: list[str] = [
        f"Itinerary sync — {result.trip_id}" + (f" ({route})" if route else ""),
    ]
    if dates:
        paste.append(f"Dates: {dates}")
    paste.append("")
    paste.append(f"Status: {status_line}")
    if not result.errors:
        paste.append(
            f"Scheduled: {scheduled} plots across {field_days} field days "
            f"({len(result.daily_rows)} calendar days in CSV)"
        )
    paste.append("")

    if result.errors:
        paste.append("ERRORS — import blocked:")
        for e in result.errors:
            paste.append(f"  • {e}")
        paste.append("")

    moves = _date_moves(result)
    if moves:
        paste.append("Date changes since last sync:")
        for plot, old, new in moves:
            paste.append(f"  • {plot}: {_display_date_short(old)} → {_display_date_short(new)}")
        paste.append("")

    confirm: list[str] = []
    for w in result.warnings:
        confirm.append(f"  • {w}")
    for a in actions:
        confirm.append(f"  • {a}")
    if confirm:
        paste.append("Please confirm or fix in Excel:")
        paste.extend(confirm)
        paste.append("")

    if kanban_notes and not result.errors:
        paste.append("Notes (access vs logistics):")
        for n in kanban_notes:
            paste.append(f"  • {n.replace('**', '')}")
        paste.append("")

    if not result.errors:
        paste.append("Daily plan:")
        for day in result.daily_rows:
            if day.plots:
                props = day.property_visited.strip() or ", ".join(day.plots)
                accom = f" — {day.accommodation}" if day.accommodation else ""
                book = f" ({day.booking_status})" if day.booking_status else ""
                paste.append(
                    f"  • {_display_date_short(day.visit_date)}: {props} "
                    f"({len(day.plots)} plot{'s' if len(day.plots) != 1 else ''})"
                    f"{accom}{book}"
                )
            elif day.travel or day.notes:
                extra = day.notes or day.travel
                paste.append(f"  • {_display_date_short(day.visit_date)}: {extra}")
        paste.append("")
        paste.append(
            "If this looks correct, no Excel changes needed. "
            "Otherwise update Sheet 1 and re-download the CSV."
        )

    paste_text = "\n".join(paste)

    # --- Markdown document ---
    md: list[str] = [
        f"# Itinerary sync feedback — {result.trip_id}",
        "",
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"Source CSV: `{csv_path.as_posix()}`",
        f"Mode: {'dry-run' if dry_run else 'applied' if not result.errors else 'blocked'}",
        "",
        "## Copy-paste (Slack / Teams / email)",
        "",
        "```text",
        paste_text,
        "```",
        "",
    ]

    if meta:
        md += [
            "## Trip",
            "",
            f"- Route: {route or '—'}",
            f"- Dates: {dates or '—'}",
            "",
        ]

    md += [
        "## Summary",
        "",
        f"- Status: **{status_line}**",
        f"- Scheduled plots: {scheduled}",
        f"- Field days (with plots): {field_days}",
        f"- Daily rows parsed: {len(result.daily_rows)}",
        "",
    ]

    if result.errors:
        md += ["## Errors", ""] + [f"- {e}" for e in result.errors] + [""]

    if moves:
        md += ["## Date changes", "", "| Plot | From | To |", "|------|------|-----|"]
        for plot, old, new in moves:
            md.append(f"| {plot} | {_display_date_short(old)} | {_display_date_short(new)} |")
        md.append("")

    new_plots = _newly_scheduled(result)
    if new_plots and not moves:
        md += ["## Newly scheduled", ""]
        for plot, date in sorted(new_plots, key=lambda x: x[1]):
            md.append(f"- {plot} → {_display_date_short(date)}")
        md.append("")

    if result.warnings or actions:
        md += ["## Action needed", ""]
        for a in actions:
            md.append(f"- ⚠️ {a}")
        for w in result.warnings:
            md.append(f"- ⚠️ {w}")
        md.append("")

    if kanban_notes:
        md += ["## Access vs logistics (informational)", ""]
        for n in kanban_notes:
            md.append(f"- ℹ️ {n}")
        md.append("")

    if not result.errors:
        md += [
            "## Daily plan",
            "",
            "| Date | Travel | Plots | Property / sites | Accommodation |",
            "|------|--------|-------|------------------|---------------|",
        ]
        for day in result.daily_rows:
            plots = ", ".join(day.plots) if day.plots else "—"
            prop = day.property_visited.strip() or "—"
            accom = day.accommodation or "—"
            if day.booking_status:
                accom += f" ({day.booking_status})"
            md.append(
                f"| {day.visit_date} | {day.travel or '—'} | {plots} | {prop} | {accom} |"
            )
        md.append("")

        md += [
            "## Next steps",
            "",
            "1. Share the copy-paste block above with the team.",
            "2. If OK: no Excel changes; optionally regenerate checklist:",
            f"   `python scripts/generate_checklist.py --trip-id {result.trip_id}`",
            "3. If not OK: fix Sheet 1 in Excel, re-download CSV, run import again.",
            "",
        ]

    return "\n".join(md)


def write_feedback(
    result: ImportResult,
    csv_path: Path,
    *,
    dry_run: bool = False,
    kanban_path: Path | None = None,
) -> Path:
    DOCS_AUDITS.mkdir(parents=True, exist_ok=True)
    out = DOCS_AUDITS / f"{result.trip_id}-itinerary-feedback.md"
    out.write_text(
        render_feedback(result, csv_path, dry_run=dry_run, kanban_path=kanban_path),
        encoding="utf-8",
    )
    return out


def feedback_from_csv(
    trip_id: str,
    csv_path: Path,
    *,
    dry_run: bool = True,
    kanban_path: Path | None = None,
) -> tuple[ImportResult, Path]:
    """Parse CSV, reconcile, and write feedback without applying import."""
    from dronescape_planning.db import open_planning_db
    from dronescape_planning.import_itinerary import parse_itinerary_csv, reconcile

    daily_rows, site_rows = parse_itinerary_csv(csv_path)
    con = open_planning_db(attach_ard=False)
    resolved = resolve_trip_id(con, trip_id)
    if not resolved:
        con.close()
        raise SystemExit(f"ERROR: trip_id '{trip_id}' not found in campaigns.db")
    result = reconcile(resolved, daily_rows, site_rows, con)
    con.close()
    path = write_feedback(result, csv_path, dry_run=dry_run, kanban_path=kanban_path)
    return result, path
