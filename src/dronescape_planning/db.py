"""SQLite connection helpers for campaigns.db + attached upstream DBs."""

from __future__ import annotations

import sqlite3
from typing import Any

from dronescape_planning.paths import ARD_STATE, CAMPAIGNS, TERN_PLOTS


def open_planning_db(
    *,
    attach_tp: bool = True,
    attach_ard: bool = True,
    row_factory: Any = None,
) -> sqlite3.Connection:
    """Open campaigns.db; attach tern_plots (tp) and optionally ard_state (ard)."""
    con = sqlite3.connect(CAMPAIGNS)
    if row_factory is not None:
        con.row_factory = row_factory
    if attach_tp:
        con.execute(f"ATTACH DATABASE '{TERN_PLOTS.as_posix()}' AS tp")
    if attach_ard and ARD_STATE.exists():
        con.execute(f"ATTACH DATABASE '{ARD_STATE.as_posix()}' AS ard")
    return con
