"""Tests for itinerary CSV parsing."""

from pathlib import Path

from dronescape_planning.import_itinerary import parse_date, parse_itinerary_csv, parse_plot_ids

FIXTURE = Path(__file__).parent / "fixtures" / "minimal-itinerary.csv"


def test_parse_date():
    assert parse_date("23/06/2026") == "2026-06-23"
    assert parse_date("1/07/2026") == "2026-07-01"


def test_parse_plot_ids():
    assert parse_plot_ids("NSAMDD0024 NSAMDD0023 NSAMDD0032") == [
        "NSAMDD0024",
        "NSAMDD0023",
        "NSAMDD0032",
    ]
    assert parse_plot_ids("NULL") == []


def test_parse_two_sections():
    daily, sites = parse_itinerary_csv(FIXTURE)
    assert len(daily) == 2
    assert daily[0].visit_date == "2026-06-23"
    assert daily[1].plots == ["NSAMDD0024"]
    assert len(sites) == 2
    assert sites[0].site_order == 1
    assert sites[1].site_order is None
