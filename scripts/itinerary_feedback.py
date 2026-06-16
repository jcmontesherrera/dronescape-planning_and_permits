"""Launcher for dronescape_planning.itinerary_feedback."""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from dronescape_planning.itinerary_feedback import default_kanban_path, feedback_from_csv
from dronescape_planning.paths import DOCS_ITINERARIES


def main() -> None:
    p = argparse.ArgumentParser(
        description="Generate coworker-friendly itinerary sync feedback (Slack/email ready)."
    )
    p.add_argument("--trip-id", required=True, help="Trip id, e.g. 01-ADL-BRI-2026-06")
    p.add_argument(
        "--csv",
        type=Path,
        default=None,
        help="Itinerary CSV (default: docs/itineraries/<trip-id>-itinerary.csv)",
    )
    p.add_argument(
        "--kanban",
        type=Path,
        default=None,
        help="Kanban board for access cross-check (auto-detected if omitted).",
    )
    p.add_argument(
        "--applied",
        action="store_true",
        help="Label feedback as applied (default: dry-run/preview wording).",
    )
    args = p.parse_args()

    csv_path = args.csv or (DOCS_ITINERARIES / f"{args.trip_id}-itinerary.csv")
    kanban = args.kanban or default_kanban_path(args.trip_id)

    result, out = feedback_from_csv(
        args.trip_id,
        csv_path,
        dry_run=not args.applied,
        kanban_path=kanban,
    )
    print(f"Feedback written to {out}")
    if result.errors:
        print(f"Note: {len(result.errors)} error(s) — share the feedback but fix CSV before import.")
        sys.exit(1)


if __name__ == "__main__":
    main()
