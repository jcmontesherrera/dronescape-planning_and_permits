"""Launcher: python scripts/generate_trip_kml.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from dronescape_planning.generate_kml import main

if __name__ == "__main__":
    main()
