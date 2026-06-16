"""Tests for itinerary feedback rendering."""

from pathlib import Path

from dronescape_planning.import_itinerary import ImportResult, parse_itinerary_csv
from dronescape_planning.itinerary_feedback import _plot_ids_from_card, render_feedback

FIXTURE = Path(__file__).parent / "fixtures" / "minimal-itinerary.csv"


def test_plot_ids_from_card_ignores_prose():
    line = (
        "- [ ] **Warrumbungle National Park** · Plots: 2 · "
        "Plot IDs: NSABBS0001, NSABBS0002 · Email: warrumbungle.np@environment.nsw.gov.au"
    )
    assert _plot_ids_from_card(line) == ["NSABBS0001", "NSABBS0002"]


def test_feedback_includes_copy_paste_block():
    daily, sites = parse_itinerary_csv(FIXTURE)
    result = ImportResult(
        trip_id="01-TEST-2026-06",
        daily_rows=daily,
        site_rows=sites,
        scheduled_plots={"NSAMDD0024": "2026-06-24"},
        warnings=[
            "NSABBS0001 (Warrumbungle National Park) listed in site master but not scheduled "
            "(no site order / not in daily rows)"
        ],
    )
    text = render_feedback(result, FIXTURE, dry_run=True)
    assert "## Copy-paste (Slack / Teams / email)" in text
    assert "```text" in text
    assert "Itinerary sync — 01-TEST-2026-06" in text
    assert "NSABBS0001" in text
    assert "24 Jun" in text
