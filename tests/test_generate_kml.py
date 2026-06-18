"""Tests for KML/KMZ generation."""

import zipfile
from pathlib import Path

from dronescape_planning.generate_kml import (
    build_kml,
    sanitize_label,
    stem_for_trip,
    trip_days_from_csv,
    write_kmz,
)

FIXTURE = Path(__file__).parent / "fixtures" / "minimal-itinerary.csv"


def test_sanitize_label():
    assert sanitize_label("v1-coworker") == "v1-coworker"
    assert sanitize_label("v2 (draft)") == "v2draft"


def test_stem_for_trip():
    assert stem_for_trip("02-BRI-BRK-2026-07") == "02-BRI-BRK-2026-07-plots"
    assert stem_for_trip("02-BRI-BRK-2026-07", "v1") == "02-BRI-BRK-2026-07-plots-v1"


def test_trip_days_from_csv():
    trip_days, backup = trip_days_from_csv(FIXTURE)
    assert len(trip_days) == 1
    day_label = next(iter(trip_days))
    assert "NSAMDD0024" in [p for p, _ in trip_days[day_label]]
    assert backup == []  # fixture has no BACKUP/DEFERRED tags


def test_build_kml_csv_mode(tmp_path):
    plot_data = {
        "NSAMDD0024": {
            "plot": "NSAMDD0024",
            "property": "Kajuligah Nature Reserve",
            "latitude": -32.68,
            "longitude": 144.62,
            "mvs": "Test MVS",
        },
    }
    trip_days = {"Day 2 · Wed 24 Jun · Kajuligah": [("NSAMDD0024", "Kajuligah Nature Reserve")]}
    kml_bytes = build_kml(
        "TEST-TRIP",
        plot_data,
        trip_days,
        "v1",
        [("Start", -34.0, 138.0)],
    )
    text = kml_bytes.decode("utf-8")
    assert "NSAMDD0024" in text
    assert "Visit order (straight-line)" in text
    assert "Trip anchors" in text

    kmz_path = tmp_path / "test.kmz"
    write_kmz(kml_bytes, kmz_path)
    with zipfile.ZipFile(kmz_path) as zf:
        assert "doc.kml" in zf.namelist()
        assert "NSAMDD0024" in zf.read("doc.kml").decode("utf-8")


def test_build_kml_collected_mode():
    plot_data = {
        "NSAMDD0024": {
            "plot": "NSAMDD0024",
            "property": "Kajuligah Nature Reserve",
            "latitude": -32.68,
            "longitude": 144.62,
            "mvs": "Test MVS",
        },
    }
    groups = {"Kajuligah Nature Reserve": [("NSAMDD0024", "Kajuligah Nature Reserve")]}
    kml_bytes = build_kml(
        "DroneScape collected",
        plot_data,
        groups,
        "1 plots as of 2026-06-17",
        anchors=[],
        include_route=False,
    )
    text = kml_bytes.decode("utf-8")
    assert "NSAMDD0024" in text
    assert "Kajuligah Nature Reserve" in text
    assert "Visit order (straight-line)" not in text
    assert "Trip anchors" not in text
