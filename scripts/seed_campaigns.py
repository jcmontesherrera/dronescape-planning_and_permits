"""Launcher: python scripts/seed_campaigns.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from dronescape_planning.seed_campaigns import main

if __name__ == "__main__":
    main()
