"""
Generate KML/KMZ for DroneScape trips (CSV) or collected plot footprint (ARD).

Usage:
  ds-generate-kml --trip-id 01-ADL-BRI-2026-06 \\
      --csv docs/itineraries/01-ADL-BRI-2026-06-itinerary.csv
  ds-generate-kml --collected
"""

from __future__ import annotations

import argparse
import re
import sqlite3
import sys
import xml.etree.ElementTree as ET
import zipfile
from datetime import date, datetime
from pathlib import Path

from dronescape_planning.db import open_planning_db
from dronescape_planning.import_itinerary import parse_itinerary_csv
from dronescape_planning.paths import ARD_STATE, DOCS_ITINERARIES, TERN_PLOTS

KML_NS = "http://www.opengis.net/kml/2.2"
ET.register_namespace("", KML_NS)

_LABEL_RE = re.compile(r"[^a-zA-Z0-9_-]+")

DAY_COLORS = [
    "ff0000ff",
    "ff00a5ff",
    "ff00ff00",
    "ffffff00",
    "ffff0000",
    "ffff00ff",
    "ff800080",
    "ff0080ff",
    "ff4040ff",
    "ff00ff80",
    "ff808000",
]

ANCHORS_BY_TRIP: dict[str, list[tuple[str, float, float]]] = {
    "01-ADL-BRI-2026-06": [
        ("Adelaide / Waite Campus (start)", -34.97, 138.64),
        ("Brisbane (vehicle endpoint)", -27.47, 153.03),
    ],
    "02-BRI-BRK-2026-07": [
        ("Brisbane (start)", -27.47, 153.03),
        ("Broken Hill (vehicle endpoint)", -31.95, 141.45),
        ("Adelaide (fly-out)", -34.93, 138.60),
    ],
}

DEFAULT_ANCHORS = [
    ("Trip start", -34.93, 138.60),
    ("Trip end", -27.47, 153.03),
]

BACKUP_STYLE = "backup-style"
BACKUP_COLOR = "ff808080"
COLLECTED_TRIP_ID = "DroneScape collected"


def sanitize_label(label: str) -> str:
    return _LABEL_RE.sub("", label)


def stem_for_trip(trip_id: str, label: str | None = None) -> str:
    if label:
        return f"{trip_id}-plots-{label}"
    return f"{trip_id}-plots"


def _format_day_label(
    day_number: int | None, visit_date: str, day_name: str, property_visited: str
) -> str:
    try:
        dt = datetime.strptime(visit_date, "%Y-%m-%d")
        date_part = dt.strftime("%a %d %b")
    except ValueError:
        date_part = visit_date
    day_part = f"Day {day_number}" if day_number is not None else day_name or "Field day"
    prop = " · ".join(p.strip() for p in re.split(r"\s{2,}", property_visited) if p.strip())
    if prop:
        return f"{day_part} · {date_part} · {prop[:60]}"
    return f"{day_part} · {date_part}"


def trip_days_from_csv(csv_path: Path) -> tuple[dict[str, list[tuple[str, str]]], list[tuple[str, str]]]:
    daily_rows, site_rows = parse_itinerary_csv(csv_path)
    property_by_plot = {s.plot: s.property_name for s in site_rows}
    trip_days: dict[str, list[tuple[str, str]]] = {}

    for row in daily_rows:
        if not row.plots:
            continue
        label = _format_day_label(
            row.day_number, row.visit_date, row.day_name, row.property_visited
        )
        trip_days[label] = [
            (plot, property_by_plot.get(plot, row.property_visited.strip() or plot))
            for plot in row.plots
        ]

    backup = [
        (s.plot, s.property_name)
        for s in site_rows
        if "BACKUP" in s.trip_tag.upper() or "DEFERRED" in s.trip_tag.upper()
    ]
    return trip_days, backup


def anchors_for_trip(trip_id: str) -> list[tuple[str, float, float]]:
    if trip_id in ANCHORS_BY_TRIP:
        return ANCHORS_BY_TRIP[trip_id]
    for key, anchors in ANCHORS_BY_TRIP.items():
        if trip_id.startswith(key.split("-")[0]) or key in trip_id:
            return anchors
    return DEFAULT_ANCHORS


def _sub(parent: ET.Element, tag: str, text: str | None = None) -> ET.Element:
    el = ET.SubElement(parent, tag)
    if text is not None:
        el.text = text
    return el


def _style_icon(doc: ET.Element, style_id: str, color: str) -> None:
    style = _sub(doc, "Style", None)
    style.set("id", style_id)
    icon_style = _sub(style, "IconStyle")
    _sub(icon_style, "color", color)
    _sub(icon_style, "scale", "1.1")
    icon = _sub(icon_style, "Icon")
    _sub(icon, "href", "http://maps.google.com/mapfiles/kml/paddle/wht-blank.png")
    _sub(_sub(style, "LabelStyle"), "scale", "0.9")


def fetch_plots(plot_ids: list[str]) -> dict[str, dict]:
    ph = ",".join("?" * len(plot_ids))
    con = sqlite3.connect(TERN_PLOTS)
    con.row_factory = sqlite3.Row
    rows = con.execute(
        f"""
        SELECT p.plot, p.property, p.latitude, p.longitude,
               COALESCE(nat.nvis_mvs_name, '') AS mvs
        FROM plots p
        LEFT JOIN plot_nvis_national nat ON nat.plot = p.plot
        WHERE p.plot IN ({ph})
        """,
        plot_ids,
    ).fetchall()
    con.close()
    return {r["plot"]: dict(r) for r in rows}


def fetch_collected_plots() -> tuple[dict[str, list[tuple[str, str]]], dict[str, dict]]:
    if not ARD_STATE.exists():
        sys.exit(f"ERROR: ard_state.db not found at {ARD_STATE}")

    con = open_planning_db(attach_ard=True, row_factory=sqlite3.Row)
    try:
        rows = con.execute(
            """
            SELECT p.plot, p.property, p.latitude, p.longitude,
                   COALESCE(nat.nvis_mvs_name, '') AS mvs
            FROM tp.plots p
            JOIN ard.level0_raw lr ON lr.plot = p.plot
            LEFT JOIN tp.plot_nvis_national nat ON nat.plot = p.plot
            WHERE p.latitude IS NOT NULL AND p.longitude IS NOT NULL
            ORDER BY p.property, p.plot
            """
        ).fetchall()
    finally:
        con.close()

    groups: dict[str, list[tuple[str, str]]] = {}
    plot_data: dict[str, dict] = {}
    for row in rows:
        prop = row["property"] or "(Unknown)"
        groups.setdefault(prop, []).append((row["plot"], prop))
        plot_data[row["plot"]] = dict(row)
    return groups, plot_data


def _add_placemark(
    folder: ET.Element,
    plot_id: str,
    display_property: str,
    row: dict | None,
    style_id: str,
    day_label: str,
    route_coords: list[str] | None = None,
) -> None:
    if not row or row["latitude"] is None or row["longitude"] is None:
        pm = _sub(folder, "Placemark")
        _sub(pm, "name", f"{plot_id} (coords missing)")
        return

    lat, lon = float(row["latitude"]), float(row["longitude"])
    pm = _sub(folder, "Placemark")
    _sub(pm, "name", plot_id)
    _sub(pm, "styleUrl", style_id)
    desc = ET.SubElement(pm, "description")
    desc.text = (
        f"{plot_id} | {display_property} | TERN: {row['property'] or display_property} | "
        f"MVS: {row['mvs'] or '(no MVS)'} | {day_label}"
    )
    _sub(_sub(pm, "Point"), "coordinates", f"{lon},{lat},0")
    if route_coords is not None:
        route_coords.append(f"{lon},{lat},0")


def build_kml(
    trip_id: str,
    plot_data: dict[str, dict],
    trip_days: dict[str, list[tuple[str, str]]],
    version_label: str,
    anchors: list[tuple[str, float, float]],
    backup_plots: list[tuple[str, str]] | None = None,
    *,
    include_route: bool = True,
) -> bytes:
    doc = ET.Element("Document")
    _sub(doc, "name", f"{trip_id} ({version_label})")
    _sub(
        doc,
        "description",
        f"DroneScape field plots — {trip_id} ({version_label}). "
        "Folders follow visit order. KML colours are ABGR.",
    )

    _style_icon(doc, "anchor-style", "ff000000")
    _style_icon(doc, BACKUP_STYLE, BACKUP_COLOR)
    for i, color in enumerate(DAY_COLORS):
        _style_icon(doc, f"day-{i}", color)

    if anchors:
        anchors_folder = _sub(doc, "Folder")
        _sub(anchors_folder, "name", "Trip anchors")
        for name, lat, lon in anchors:
            pm = _sub(anchors_folder, "Placemark")
            _sub(pm, "name", name)
            _sub(pm, "styleUrl", "#anchor-style")
            _sub(_sub(pm, "Point"), "coordinates", f"{lon},{lat},0")

    route_coords: list[str] | None = [] if include_route else None
    for day_idx, (day_label, entries) in enumerate(trip_days.items()):
        folder = _sub(doc, "Folder")
        _sub(folder, "name", day_label)
        style_id = f"#day-{day_idx}"
        for plot_id, display_property in entries:
            _add_placemark(
                folder, plot_id, display_property, plot_data.get(plot_id),
                style_id, day_label, route_coords,
            )

    if backup_plots:
        folder = _sub(doc, "Folder")
        _sub(folder, "name", "Backup / deferred (not on daily schedule)")
        for plot_id, display_property in backup_plots:
            _add_placemark(
                folder, plot_id, display_property, plot_data.get(plot_id),
                f"#{BACKUP_STYLE}", "Backup/deferred", route_coords=None,
            )

    if route_coords:
        route_folder = _sub(doc, "Folder")
        _sub(route_folder, "name", "Visit order (straight-line)")
        pm = _sub(route_folder, "Placemark")
        _sub(pm, "name", "Plot visit sequence")
        _sub(pm, "description", "Straight-line path through plots in daily visit order.")
        ls = _sub(pm, "LineString")
        _sub(ls, "tessellate", "1")
        _sub(ls, "coordinates", " ".join(route_coords))

    kml = ET.Element("kml", xmlns=KML_NS)
    kml.append(doc)
    return ET.tostring(kml, encoding="utf-8", xml_declaration=True)


def write_kmz(kml_bytes: bytes, kmz_path: Path) -> None:
    with zipfile.ZipFile(kmz_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("doc.kml", kml_bytes)


def write_outputs(
    kml_bytes: bytes, output_dir: Path, stem: str
) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    kml_path = output_dir / f"{stem}.kml"
    kmz_path = output_dir / f"{stem}.kmz"
    kml_path.write_bytes(kml_bytes)
    write_kmz(kml_bytes, kmz_path)
    return kml_path, kmz_path


def generate_from_csv(
    trip_id: str,
    csv_path: Path,
    output_dir: Path,
    label: str | None = None,
) -> tuple[Path, Path, int, int]:
    if not csv_path.exists():
        sys.exit(f"ERROR: CSV not found: {csv_path}")
    if not TERN_PLOTS.exists():
        sys.exit(f"ERROR: tern_plots.db not found at {TERN_PLOTS}")

    clean_label = sanitize_label(label) if label else None
    trip_days, backup_plots = trip_days_from_csv(csv_path)
    if not trip_days:
        sys.exit("ERROR: No field days with plots found in CSV.")

    all_plot_ids = [pid for entries in trip_days.values() for pid, _ in entries]
    all_plot_ids.extend(pid for pid, _ in backup_plots)
    plot_data = fetch_plots(all_plot_ids)
    missing = [p for p in all_plot_ids if p not in plot_data]
    if missing:
        sys.exit(f"Plots not found in tern_plots.db: {', '.join(missing)}")

    version_label = clean_label or f"from {csv_path.name}"
    kml_bytes = build_kml(
        trip_id, plot_data, trip_days, version_label,
        anchors_for_trip(trip_id), backup_plots or None,
    )
    paths = write_outputs(kml_bytes, output_dir, stem_for_trip(trip_id, clean_label))
    active = sum(len(e) for e in trip_days.values())
    return paths[0], paths[1], active, len(backup_plots)


def generate_collected(output_dir: Path) -> tuple[Path, Path, int]:
    groups, plot_data = fetch_collected_plots()
    if not groups:
        sys.exit("ERROR: No collected plots with coordinates found in ARD.")

    n = sum(len(entries) for entries in groups.values())
    version_label = f"{n} plots as of {date.today().isoformat()}"
    kml_bytes = build_kml(
        COLLECTED_TRIP_ID, plot_data, groups, version_label,
        anchors=[], include_route=False,
    )
    paths = write_outputs(kml_bytes, output_dir, "collected-plots")
    return paths[0], paths[1], n


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Generate KML/KMZ from trip CSV or ARD collected plots.")
    p.add_argument("--collected", action="store_true",
                   help="National footprint of all plots in ard.level0_raw.")
    p.add_argument("--trip-id", help="Trip id (required with --csv unless --collected).")
    p.add_argument("--csv", type=Path, help="Logistics CSV (required with --trip-id).")
    p.add_argument("--label", help="Version suffix for output stem, e.g. v1 → {trip-id}-plots-v1.kmz")
    p.add_argument("--output-dir", type=Path, default=DOCS_ITINERARIES / "maps")
    return p.parse_args()


def main() -> None:
    args = parse_args()

    if args.collected:
        if args.trip_id or args.csv:
            sys.exit("ERROR: --collected cannot be combined with --trip-id/--csv.")
        kml_path, kmz_path, n = generate_collected(args.output_dir)
        print(f"KML:  {kml_path}")
        print(f"KMZ:  {kmz_path}")
        print(f"Plots: {n} collected")
        return

    if not args.trip_id or not args.csv:
        sys.exit("ERROR: --trip-id and --csv are required unless --collected is set.")

    kml_path, kmz_path, active, backup_n = generate_from_csv(
        args.trip_id, args.csv, args.output_dir, args.label,
    )
    print(f"KML:  {kml_path}")
    print(f"KMZ:  {kmz_path}")
    print(f"Plots: {active} active" + (f", {backup_n} backup/deferred" if backup_n else ""))


if __name__ == "__main__":
    main()
