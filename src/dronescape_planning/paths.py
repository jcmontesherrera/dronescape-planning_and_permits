"""Shared paths for dronescape_planning (edit TERN_PLOTS / ARD_STATE per machine)."""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = REPO_ROOT / "data"
CAMPAIGNS = DATA_DIR / "campaigns.db"
TERN_PLOTS = Path(r"C:/Users/jcmontes/Documents/GitHub/tern_plots_master/data/tern_plots.db")
ARD_STATE = Path(r"C:/Users/jcmontes/Documents/GitHub/dronescape_ard/data/ard_state.db")
BOARDS_DIR = REPO_ROOT / "boards"
DOCS_AUDITS = REPO_ROOT / "docs" / "audits"
DOCS_DRAFTS = REPO_ROOT / "docs" / "drafts"
DOCS_CHECKLISTS = REPO_ROOT / "docs" / "checklists"
DOCS_ITINERARIES = REPO_ROOT / "docs" / "itineraries"

# Default template location — update to wherever the DOCX template lives on your machine.
# Can be overridden via --template on the CLI.
TEMPLATE_DOCX = Path(r"C:/Users/jcmontes/Desktop/Template-UTAS-Dronescape-Trip-Checklist-2026.docx")
