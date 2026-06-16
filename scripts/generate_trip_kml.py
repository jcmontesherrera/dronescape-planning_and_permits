"""
Generate KML/KMZ for a DroneScape trip from tern_plots.db coordinates.

Usage:
  python scripts/generate_trip_kml.py --trip-id 02-BRI-BRK-2026-07 --version v2
  python scripts/generate_trip_kml.py --trip-id 01-ADL-BRI-2026-06 \\
      --csv docs/itineraries/01-ADL-BRI-2026-06-itinerary.csv
"""

from __future__ import annotations

import argparse
import re
import sqlite3
import xml.etree.ElementTree as ET
import zipfile
from datetime import datetime
from pathlib import Path

from dronescape_planning.import_itinerary import parse_itinerary_csv
from dronescape_planning.paths import DOCS_ITINERARIES, TERN_PLOTS

KML_NS = "http://www.opengis.net/kml/2.2"
ET.register_namespace("", KML_NS)

# Original coworker itinerary (BRISBANEtoBROKENHILL_V1_orig.xlsx)
TRIP_DAYS_V1: dict[str, list[tuple[str, str]]] = {
    "Day 2 · Tue 21 Jul · SEQ": [
        ("NSASEQ0001", "Pagans Flat"),
        ("NSASEQ0002", "Jana Ngalee LALC"),
    ],
    "Day 3 · Wed 22 Jul · Torrington": [
        ("NSANET0001", "Torrington SCA"),
        ("NSANET0006", "Torrington SCA"),
    ],
    "Day 4 · Thu 23 Jul · Breeza + Wondoba": [
        ("NSABBS0007", "Breeza Station"),
        ("NSABBS0008", "Breeza Station"),
        ("NSABBS0009", "Breeza Station"),
        ("NSABBS0010", "Wondoba SCA"),
    ],
    "Day 5 · Fri 24 Jul · Warrumbungle": [
        ("NSABBS0001", "Warrumbungle National Park"),
        ("NSABBS0002", "Warrumbungle National Park"),
    ],
    "Day 6 · Sat 25 Jul · Paroo Darling": [
        ("NSAMDD0030", "Paroo Darling NP"),
        ("NSAMDD0029", "Paroo Darling NP"),
    ],
    "Day 7 · Sun 26 Jul · Paroo Darling": [
        ("NSAMDD0027", "Paroo Darling NP"),
        ("NSAMDD0028", "Paroo Darling NP"),
        ("NSAMDD0026", "Paroo Darling NP"),
    ],
    "Day 8 · Mon 27 Jul · Paroo → BRK": [
        ("NSAMDD0025", "Paroo Darling NP"),
        ("NSABHC0026", "Melool Station"),
        ("NSABHC0008", "Broken Hill Town Common"),
    ],
    "Day 9 · Tue 28 Jul · Crown / leasehold": [
        ("NSABHC0004", "Glen Idol Station"),
        ("NSABHC0005", "Glen Idol Station"),
        ("NSABHC0006", "K-Tank Station"),
        ("NSABHC0007", "Avondale Station"),
        ("NSABHC0027", "Avondale Station"),
    ],
    "Day 10 · Wed 29 Jul · Town Common": [
        ("NSABHC0003", "Broken Hill Town Common"),
        ("NSABHC0001", "Broken Hill Town Common"),
        ("NSABHC0002", "Broken Hill Town Common"),
    ],
}

# V2 field-lead itinerary: day label -> plot IDs in visit order
TRIP_DAYS_V2: dict[str, list[tuple[str, str]]] = {
    "Day 2 · Tue 21 Jul · SEQ": [
        ("NSASEQ0001", "Pagans Flat"),
        ("NSASEQ0002", "Jana Ngalee LALC"),
    ],
    "Day 3 · Wed 22 Jul · Torrington": [
        ("NSANET0001", "Torrington SCA"),
        ("NSANET0006", "Torrington SCA"),
    ],
    "Day 4 · Thu 23 Jul · Breeza + Wondoba": [
        ("NSABBS0007", "Breeza Station"),
        ("NSABBS0008", "Breeza Station"),
        ("NSABBS0009", "Breeza Station"),
        ("NSABBS0010", "Wondoba SCA"),
    ],
    "Day 5 · Fri 24 Jul · Warrumbungle": [
        ("NSABBS0001", "Warrumbungle National Park"),
        ("NSABBS0002", "Warrumbungle National Park"),
    ],
    "Day 6 · Sat 25 Jul · Paroo Darling": [
        ("NSAMDD0030", "Paroo Darling NP"),
        ("NSAMDD0029", "Paroo Darling NP"),
    ],
    "Day 7 · Sun 26 Jul · Paroo Darling": [
        ("NSAMDD0027", "Paroo Darling NP"),
        ("NSAMDD0028", "Paroo Darling NP"),
        ("NSAMDD0026", "Paroo Darling NP"),
    ],
    "Day 8 · Mon 27 Jul · Paroo → BRK": [
        ("NSAMDD0025", "Paroo Darling NP"),
    ],
    "Day 9 · Tue 28 Jul · Fowlers Gap": [
        ("NSABHC0009", "Fowlers Gap"),
        ("NSABHC0010", "Fowlers Gap"),
        ("NSABHC0011", "Fowlers Gap"),
        ("NSABHC0012", "Fowlers Gap"),
        ("NSABHC0028", "Fowlers Gap"),
        ("NSABHC0029", "Fowlers Gap"),
    ],
    "Day 10 · Wed 29 Jul · Crown / leasehold": [
        ("NSABHC0004", "Glen Idol Station"),
        ("NSABHC0005", "Glen Idol Station"),
        ("NSABHC0006", "K-Tank Station"),
        ("NSABHC0007", "Avondale Station"),
        ("NSABHC0027", "Avondale Station"),
    ],
    "Day 11 · Thu 30 Jul · Town Common": [
        ("NSABHC0001", "Broken Hill Town Common"),
        ("NSABHC0002", "Broken Hill Town Common"),
        ("NSABHC0003", "Broken Hill Town Common"),
        ("NSABHC0008", "Broken Hill Town Common"),
    ],
}

DAY_COLORS = [
    "ff0000ff",  # red
    "ff00a5ff",  # orange
    "ff00ff00",  # green
    "ffffff00",  # cyan
    "ffff0000",  # blue
    "ffff00ff",  # magenta
    "ff800080",  # purple
    "ff0080ff",  # amber
    "ff4040ff",  # coral
    "ff00ff80",  # spring
    "ff808000",  # teal
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


def _format_day_label(day_number: int | None, visit_date: str, day_name: str, property_visited: str) -> str:
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
    """Return (active day folders, backup plot list) from a logistics CSV."""
    daily_rows, site_rows = parse_itinerary_csv(csv_path)

    property_by_plot = {s.plot: s.property_name for s in site_rows}
    trip_days: dict[str, list[tuple[str, str]]] = {}

    for row in daily_rows:
        if not row.plots:
            continue
        label = _format_day_label(
            row.day_number, row.visit_date, row.day_name, row.property_visited
        )
        entries = [
            (plot, property_by_plot.get(plot, row.property_visited.strip() or plot))
            for plot in row.plots
        ]
        trip_days[label] = entries

    backup = [
        (s.plot, s.property_name)
        for s in site_rows
        if "BACKUP" in s.trip_tag.upper()
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
    label = _sub(style, "LabelStyle")
    _sub(label, "scale", "0.9")


def fetch_plots(plot_ids: list[str]) -> dict[str, dict]:
    ph = ",".join("?" * len(plot_ids))
    con = sqlite3.connect(TERN_PLOTS)
    con.row_factory = sqlite3.Row
    rows = con.execute(
        f"""
        SELECT
            p.plot,
            p.property,
            p.latitude,
            p.longitude,
            COALESCE(nat.nvis_mvs_name, '') AS mvs
        FROM plots p
        LEFT JOIN plot_nvis_national nat ON nat.plot = p.plot
        WHERE p.plot IN ({ph})
        """,
        plot_ids,
    ).fetchall()
    con.close()
    return {r["plot"]: dict(r) for r in rows}


BACKUP_STYLE = "backup-style"
BACKUP_COLOR = "ff808080"


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

    lat = float(row["latitude"])
    lon = float(row["longitude"])
    mvs = row["mvs"] or "(no MVS)"
    tern_property = row["property"] or display_property

    pm = _sub(folder, "Placemark")
    _sub(pm, "name", plot_id)
    _sub(pm, "styleUrl", style_id)
    desc = ET.SubElement(pm, "description")
    desc.text = (
        f"{plot_id} | {display_property} | TERN: {tern_property} | "
        f"MVS: {mvs} | {day_label}"
    )
    pt = _sub(pm, "Point")
    _sub(pt, "coordinates", f"{lon},{lat},0")
    if route_coords is not None:
        route_coords.append(f"{lon},{lat},0")


def build_kml(
    trip_id: str,
    plot_data: dict[str, dict],
    trip_days: dict[str, list[tuple[str, str]]],
    version_label: str,
    anchors: list[tuple[str, float, float]],
    backup_plots: list[tuple[str, str]] | None = None,
) -> bytes:
    doc = ET.Element("Document")
    _sub(doc, "name", f"{trip_id} ({version_label})")
    _sub(
        doc,
        "description",
        f"DroneScape field plots — {trip_id} ({version_label}). "
        "Folders follow daily visit order. KML colours are ABGR.",
    )

    _style_icon(doc, "anchor-style", "ff000000")
    _style_icon(doc, BACKUP_STYLE, BACKUP_COLOR)
    for i, color in enumerate(DAY_COLORS):
        _style_icon(doc, f"day-{i}", color)

    # Anchors
    anchors_folder = _sub(doc, "Folder")
    _sub(anchors_folder, "name", "Trip anchors")
    for name, lat, lon in anchors:
        pm = _sub(anchors_folder, "Placemark")
        _sub(pm, "name", name)
        _sub(pm, "styleUrl", "#anchor-style")
        pt = _sub(pm, "Point")
        _sub(pt, "coordinates", f"{lon},{lat},0")

    route_coords: list[str] = []

    for day_idx, (day_label, entries) in enumerate(trip_days.items()):
        folder = _sub(doc, "Folder")
        _sub(folder, "name", day_label)
        style_id = f"#day-{day_idx}"

        for plot_id, display_property in entries:
            _add_placemark(
                folder,
                plot_id,
                display_property,
                plot_data.get(plot_id),
                style_id,
                day_label,
                route_coords,
            )

    if backup_plots:
        folder = _sub(doc, "Folder")
        _sub(folder, "name", "Backup sites (not on daily schedule)")
        for plot_id, display_property in backup_plots:
            _add_placemark(
                folder,
                plot_id,
                display_property,
                plot_data.get(plot_id),
                f"#{BACKUP_STYLE}",
                "Backup",
                route_coords=None,
            )

    # Visit-order line (active + backup plots, straight segments)
    if route_coords:
        route_folder = _sub(doc, "Folder")
        _sub(route_folder, "name", "Visit order (straight-line)")
        pm = _sub(route_folder, "Placemark")
        _sub(pm, "name", "Plot visit sequence")
        _sub(
            pm,
            "description",
            "Straight-line path through plots in daily visit order (not road routing).",
        )
        ls = _sub(pm, "LineString")
        _sub(ls, "tessellate", "1")
        _sub(ls, "coordinates", " ".join(route_coords))

    kml = ET.Element("kml", xmlns=KML_NS)
    kml.append(doc)
    return ET.tostring(kml, encoding="utf-8", xml_declaration=True)


def write_kmz(kml_bytes: bytes, kmz_path: Path) -> None:
    with zipfile.ZipFile(kmz_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("doc.kml", kml_bytes)


TRIP_VERSIONS = {
    "v1": ("V1 original itinerary (Gowrie removed, Warrumbungle added)", TRIP_DAYS_V1),
    "v2": ("V2 field-lead itinerary", TRIP_DAYS_V2),
}


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate KML/KMZ for a trip.")
    parser.add_argument("--trip-id", default="02-BRI-BRK-2026-07")
    parser.add_argument(
        "--csv",
        type=Path,
        default=None,
        help="Logistics CSV (daily schedule + site master). Overrides --version.",
    )
    parser.add_argument(
        "--version",
        choices=sorted(TRIP_VERSIONS),
        default="v2",
        help="Itinerary version for hardcoded BRI-BRK trips (ignored when --csv is set).",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DOCS_ITINERARIES / "maps",
    )
    args = parser.parse_args()

    backup_plots: list[tuple[str, str]] = []
    if args.csv:
        if not args.csv.exists():
            raise SystemExit(f"CSV not found: {args.csv}")
        trip_days, backup_plots = trip_days_from_csv(args.csv)
        version_label = f"from {args.csv.name}"
        stem_suffix = ""
    else:
        version_label, trip_days = TRIP_VERSIONS[args.version]
        stem_suffix = f"-{args.version}"

    all_plot_ids = [pid for entries in trip_days.values() for pid, _ in entries]
    all_plot_ids.extend(pid for pid, _ in backup_plots)
    plot_data = fetch_plots(all_plot_ids)

    missing = [p for p in all_plot_ids if p not in plot_data]
    if missing:
        raise SystemExit(f"Plots not found in tern_plots.db: {', '.join(missing)}")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    stem = f"{args.trip_id}-plots{stem_suffix}"
    kml_path = args.output_dir / f"{stem}.kml"
    kmz_path = args.output_dir / f"{stem}.kmz"

    kml_bytes = build_kml(
        args.trip_id,
        plot_data,
        trip_days,
        version_label,
        anchors_for_trip(args.trip_id),
        backup_plots=backup_plots or None,
    )
    kml_path.write_bytes(kml_bytes)
    write_kmz(kml_bytes, kmz_path)

    active = sum(len(e) for e in trip_days.values())
    print(f"KML:  {kml_path}")
    print(f"KMZ:  {kmz_path}")
    print(f"Plots: {active} active" + (f", {len(backup_plots)} backup" if backup_plots else ""))


if __name__ == "__main__":
    main()
