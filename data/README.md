# data/

Local writable database for this repo.

| File | Purpose |
|------|---------|
| `campaigns.db` | Permit state: `properties`, `campaigns`, `campaign_plots`, `itinerary_days` |

Created by `python scripts/seed_campaigns.py`. **Not committed to git.**

## Upstream databases (read-only, attach at query time)

| File | Path on this machine |
|------|----------------------|
| `tern_plots.db` | `C:/Users/jcmontes/Documents/GitHub/tern_plots_master/data/tern_plots.db` |
| `ard_state.db` | `C:/Users/jcmontes/Documents/GitHub/dronescape_ard/data/ard_state.db` |

Never write to upstream databases from this repo. See [HANDOFF.md](../HANDOFF.md).
