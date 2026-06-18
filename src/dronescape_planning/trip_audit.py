"""
Cross-reference a trip kanban board against tern_plots.db and ard_state.db.

Usage:
    python scripts/trip_audit.py --trip-kanban boards/01-ADL-BRI-Access-applications.md
    python scripts/trip_audit.py --trip-kanban boards/01-ADL-BRI-Access-applications.md --register
"""

from __future__ import annotations

import argparse
import difflib
import re
import sqlite3
import sys
from dataclasses import dataclass, field
from pathlib import Path

from dronescape_planning.db import open_planning_db
from dronescape_planning.paths import ARD_STATE, CAMPAIGNS, DOCS_AUDITS, REPO_ROOT, TERN_PLOTS

# Kanban title on card -> authoritative TERN property name
PROPERTY_ALIASES: dict[str, str] = {
    "Glen Orton Station": "Glen Orten Station",
    "Brindavan/Russell Reserve": "Russell Reserve",
    "Myall Park Nature Refuge": "Myall Park Private Reserve",
    "NSW Crown Lands – Western Region": "Road Reserve",
}

COLUMN_ACCESS_STATUS = {
    "Access Confirmed": "confirmed",
    "Awaiting Response": "pending",
    "To Contact": "unknown",
    "Documents & Maps": "pending",
    "Properties": "unknown",
    "Landholder template": "unknown",
    "Protected Areas": "unknown",
}

_MONTH_ABBR = {
    "Jan": "01", "Feb": "02", "Mar": "03", "Apr": "04",
    "May": "05", "Jun": "06", "Jul": "07", "Aug": "08",
    "Sep": "09", "Oct": "10", "Nov": "11", "Dec": "12",
}


@dataclass
class TripHeader:
    trip_id: str
    route_origin: str
    route_dest: str
    start_date: str
    end_date: str


def parse_trip_header(path: Path) -> TripHeader | None:
    """Read trip metadata from the Properties header card on a kanban board."""
    for line in path.read_text(encoding="utf-8").splitlines():
        if "**Trip:**" not in line:
            continue
        trip_m = re.search(r"\*\*Trip:\*\*\s*([^\s·]+)", line)
        route_m = re.search(r"\*\*Route:\*\*\s*([^·]+)", line)
        dates_m = re.search(
            r"\*\*Field dates:\*\*\s*(\d{1,2})\s+(\w{3})\s*[–-]\s*(\d{1,2})\s+(\w{3})\s+(\d{4})",
            line,
        )
        if not trip_m:
            return None
        trip_id = trip_m.group(1).strip()
        route_origin, route_dest = "", ""
        if route_m:
            parts = re.split(r"\s*→\s*", route_m.group(1).strip(), maxsplit=1)
            route_origin = parts[0].strip()
            route_dest = parts[1].strip() if len(parts) > 1 else ""
        start_date, end_date = "", ""
        if dates_m:
            d1, m1, d2, m2, year = dates_m.groups()
            start_date = f"{year}-{_MONTH_ABBR.get(m1, '01')}-{int(d1):02d}"
            end_date = f"{year}-{_MONTH_ABBR.get(m2, '01')}-{int(d2):02d}"
        return TripHeader(trip_id, route_origin, route_dest, start_date, end_date)
    return None


@dataclass
class KanbanCard:
    kanban_property: str
    column: str
    raw_line: str
    plots_declared: int | None = None
    is_backup: bool = False
    is_instruction: bool = False
    email: str | None = None


@dataclass
class PropertyAudit:
    kanban_property: str
    column: str
    tern_property: str | None
    plots: list[tuple[str, bool]]  # (plot_id, collected)
    plots_declared: int | None
    fuzzy_suggestions: list[str] = field(default_factory=list)
    email: str | None = None
    is_backup: bool = False

    @property
    def plot_ids(self) -> list[str]:
        return [p for p, _ in self.plots]

    @property
    def uncollected(self) -> list[str]:
        return [p for p, c in self.plots if not c]

    @property
    def count_match(self) -> bool | None:
        if self.plots_declared is None or not self.plots:
            return None
        return len(self.plots) == self.plots_declared


def parse_kanban(path: Path) -> list[KanbanCard]:
    text = path.read_text(encoding="utf-8")
    cards: list[KanbanCard] = []
    column = ""
    for line in text.splitlines():
        if line.startswith("## "):
            column = line[3:].strip()
            continue
        if not line.strip().startswith("- ["):
            continue
        body = line.split("]", 1)[-1].strip()
        if body.startswith("_") and body.endswith("_"):
            cards.append(
                KanbanCard(
                    kanban_property="",
                    column=column,
                    raw_line=line,
                    is_instruction=True,
                )
            )
            continue
        m = re.search(r"\*\*(.+?)\*\*", body)
        if not m:
            continue
        prop = m.group(1).strip()
        plots_m = re.search(r"Plots:\s*(\d+)", body)
        email_m = re.search(
            r"Email:\s*([^\s·]+@[^\s·]+)|Channel:\s*([^\s·]+@[^\s·]+)",
            body,
        )
        email = None
        if email_m:
            email = (email_m.group(1) or email_m.group(2) or "").strip()
        is_backup = "[BACKUP]" in body or "Status: BACKUP" in body
        if "DEFERRED" in body.upper():
            is_backup = True
        cards.append(
            KanbanCard(
                kanban_property=prop,
                column=column,
                raw_line=line,
                plots_declared=int(plots_m.group(1)) if plots_m else None,
                is_backup=is_backup,
                email=email if email and "@" in email else None,
            )
        )
    return cards


def resolve_property_name(kanban_name: str, all_properties: list[str]) -> tuple[str | None, list[str]]:
    if kanban_name in PROPERTY_ALIASES:
        return PROPERTY_ALIASES[kanban_name], []
    if kanban_name in all_properties:
        return kanban_name, []
    suggestions = difflib.get_close_matches(kanban_name, all_properties, n=5, cutoff=0.6)
    return (suggestions[0] if suggestions else None), suggestions


def query_plots(con: sqlite3.Connection, property_name: str, ard_attached: bool) -> list[tuple[str, bool]]:
    rows = con.execute(
        """
        SELECT p.plot,
               EXISTS(SELECT 1 FROM ard.level0_raw lr WHERE lr.plot = p.plot) AS collected
        FROM tp.plots p
        WHERE p.property = ?
        ORDER BY p.plot
        """,
        (property_name,),
    ).fetchall()
    if ard_attached:
        return [(r[0], bool(r[1])) for r in rows]
    return [(r[0], False) for r in rows]


def audit_cards(cards: list[KanbanCard], con: sqlite3.Connection, ard_attached: bool) -> list[PropertyAudit]:
    all_props = [
        r[0]
        for r in con.execute(
            "SELECT DISTINCT property FROM tp.plots WHERE property IS NOT NULL AND TRIM(property) != ''"
        ).fetchall()
    ]
    audits: list[PropertyAudit] = []
    for card in cards:
        if card.is_instruction or not card.kanban_property:
            continue
        tern_name, suggestions = resolve_property_name(card.kanban_property, all_props)
        plots: list[tuple[str, bool]] = []
        if tern_name:
            plots = query_plots(con, tern_name, ard_attached)
        audits.append(
            PropertyAudit(
                kanban_property=card.kanban_property,
                column=card.column,
                tern_property=tern_name,
                plots=plots,
                plots_declared=card.plots_declared,
                fuzzy_suggestions=suggestions if not tern_name else [],
                email=card.email,
                is_backup=card.is_backup,
            )
        )
    return audits


def write_audit_report(
    audits: list[PropertyAudit],
    kanban_path: Path,
    out_path: Path,
    trip_id: str,
    header: TripHeader | None = None,
) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    active = [a for a in audits if not a.is_backup]
    backup = [a for a in audits if a.is_backup]
    total_plots = sum(len(a.plot_ids) for a in active)
    uncollected = sum(len(a.uncollected) for a in active)

    lines = [
        f"# Trip audit: {trip_id}",
        "",
        f"- Kanban: `{kanban_path.as_posix()}`",
        f"- Generated from `tern_plots.db` + `ard_state.db`",
        "",
        "## Summary",
        "",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| Active properties | {len(active)} |",
        f"| Backup properties | {len(backup)} |",
        f"| Active plots (TERN) | {total_plots} |",
        f"| Uncollected (active) | {uncollected} |",
        "",
        "### By column",
        "",
    ]
    by_col: dict[str, list[PropertyAudit]] = {}
    for a in audits:
        by_col.setdefault(a.column, []).append(a)
    for col, items in by_col.items():
        n_props = len([i for i in items if i.tern_property])
        n_plots = sum(len(i.plot_ids) for i in items)
        lines.append(f"- **{col}**: {len(items)} card(s), {n_plots} plot(s)")

    lines += ["", "## Active properties", ""]
    for a in active:
        lines.extend(_audit_section(a))

    if backup:
        lines += ["", "## Backup properties (no campaign_plots unless promoted)", ""]
        for a in backup:
            lines.extend(_audit_section(a))

    lines += ["", "## Registration SQL (--register applies this)", "", "```sql"]
    route_origin = header.route_origin if header else ""
    route_dest = header.route_dest if header else ""
    start_date = header.start_date if header else ""
    end_date = header.end_date if header else ""
    lines.append(
        "INSERT INTO campaigns (trip_id, route_origin, route_dest, start_date, end_date, season, enso_phase)"
    )
    lines.append(
        f"VALUES ({repr(trip_id)}, {repr(route_origin)}, {repr(route_dest)}, "
        f"{repr(start_date)}, {repr(end_date)}, 'winter', NULL);"
    )
    lines.append("")
    for a in active:
        if not a.tern_property:
            continue
        status = COLUMN_ACCESS_STATUS.get(a.column, "unknown")
        email_sql = repr(a.email) if a.email else "NULL"
        lines.append(
            f"INSERT OR REPLACE INTO properties (property_name, email_address, access_status) "
            f"VALUES ({repr(a.tern_property)}, {email_sql}, '{status}');"
        )
    lines.append("")
    for a in active:
        for plot in a.plot_ids:
            lines.append(
                f"INSERT OR IGNORE INTO campaign_plots (trip_id, plot) "
                f"VALUES ({repr(trip_id)}, '{plot}');"
            )
    lines.append("```")

    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Audit written to {out_path}")


def _audit_section(a: PropertyAudit) -> list[str]:
    lines = [f"### {a.kanban_property} ({a.column})"]
    if a.tern_property and a.tern_property != a.kanban_property:
        lines.append(f"- TERN name: **{a.tern_property}** (kanban title differs)")
    elif a.tern_property:
        lines.append(f"- TERN name: {a.tern_property}")
    else:
        lines.append("- TERN name: **NOT FOUND**")
        if a.fuzzy_suggestions:
            lines.append(f"- Suggestions: {', '.join(a.fuzzy_suggestions)}")
    if a.plots_declared is not None:
        match = "OK" if a.count_match else "MISMATCH"
        lines.append(
            f"- Plot count: kanban={a.plots_declared}, TERN={len(a.plot_ids)} ({match})"
        )
    if a.plot_ids:
        lines.append(f"- Plot IDs: {', '.join(a.plot_ids)}")
        if a.uncollected:
            lines.append(f"- Uncollected: {', '.join(a.uncollected)}")
        collected = [p for p, c in a.plots if c]
        if collected:
            lines.append(f"- Already in ard.level0_raw: {', '.join(collected)}")
    else:
        lines.append("- Plot IDs: (none resolved)")
    if a.email:
        lines.append(f"- Email on card: {a.email}")
    suggested = _suggested_card_line(a)
    lines.append(f"- Suggested card fragment: `{suggested}`")
    lines.append("")
    return lines


def _suggested_card_line(a: PropertyAudit) -> str:
    ids = ", ".join(a.plot_ids) if a.plot_ids else "—"
    n = len(a.plot_ids) if a.plot_ids else (a.plots_declared or 0)
    name = a.tern_property or a.kanban_property
    backup = " · Status: BACKUP" if a.is_backup else ""
    return f"**{name}** · Plots: {n} · Plot IDs: {ids}{backup}"


def register_trip(
    audits: list[PropertyAudit],
    trip_id: str,
    header: TripHeader | None = None,
) -> None:
    active = [a for a in audits if not a.is_backup and a.tern_property]
    con = sqlite3.connect(CAMPAIGNS)
    route_origin = header.route_origin if header else ""
    route_dest = header.route_dest if header else ""
    start_date = header.start_date if header else ""
    end_date = header.end_date if header else ""
    con.execute(
        """
        INSERT OR REPLACE INTO campaigns
            (trip_id, route_origin, route_dest, start_date, end_date, season, enso_phase)
        VALUES (?, ?, ?, ?, ?, 'winter', NULL)
        """,
        (trip_id, route_origin, route_dest, start_date, end_date),
    )
    for a in active:
        status = COLUMN_ACCESS_STATUS.get(a.column, "unknown")
        con.execute(
            """
            INSERT OR REPLACE INTO properties (property_name, email_address, access_status)
            VALUES (?, ?, ?)
            """,
            (a.tern_property, a.email, status),
        )
    con.execute("DELETE FROM campaign_plots WHERE trip_id = ?", (trip_id,))
    for a in active:
        for plot in a.plot_ids:
            con.execute(
                "INSERT INTO campaign_plots (trip_id, plot) VALUES (?, ?)",
                (trip_id, plot),
            )
    con.commit()
    n_props = len(active)
    n_plots = sum(len(a.plot_ids) for a in active)
    con.close()
    print(f"Registered {trip_id}: {n_props} properties, {n_plots} plots in campaign_plots.")


def parse_args():
    p = argparse.ArgumentParser(description="Audit trip kanban against TERN + ARD databases.")
    p.add_argument(
        "--trip-kanban",
        type=str,
        required=True,
        help="Path to kanban markdown file.",
    )
    p.add_argument(
        "--trip-id",
        type=str,
        default=None,
        help="Trip id for report and --register (default: from kanban **Trip:** header).",
    )
    p.add_argument(
        "--output",
        type=str,
        default=None,
        help="Audit markdown path (default: docs/audits/<stem>-audit.md).",
    )
    p.add_argument(
        "--register",
        action="store_true",
        help="Write campaigns, properties, and campaign_plots rows after audit.",
    )
    return p.parse_args()


def main():
    args = parse_args()
    kanban_path = Path(args.trip_kanban)
    if not kanban_path.is_absolute():
        kanban_path = REPO_ROOT / kanban_path

    if not kanban_path.exists():
        print(f"ERROR: kanban not found: {kanban_path}", file=sys.stderr)
        sys.exit(1)
    if not TERN_PLOTS.exists():
        print(f"ERROR: tern_plots.db not found: {TERN_PLOTS}", file=sys.stderr)
        sys.exit(1)
    if not CAMPAIGNS.exists():
        print(f"ERROR: campaigns.db not found at {CAMPAIGNS}. Run seed_campaigns.py first.", file=sys.stderr)
        sys.exit(1)

    out_path = Path(args.output) if args.output else DOCS_AUDITS / f"{kanban_path.stem}-audit.md"

    header = parse_trip_header(kanban_path)
    trip_id = args.trip_id or (header.trip_id if header else None)
    if not trip_id:
        print(
            "ERROR: No --trip-id and no **Trip:** on kanban Properties card.",
            file=sys.stderr,
        )
        sys.exit(1)

    cards = parse_kanban(kanban_path)
    con = open_planning_db(attach_ard=True)
    ard_attached = ARD_STATE.exists()

    audits = audit_cards(cards, con, ard_attached)
    con.close()

    write_audit_report(audits, kanban_path, out_path, trip_id, header)

    if args.register:
        register_trip(audits, trip_id, header)


if __name__ == "__main__":
    main()
