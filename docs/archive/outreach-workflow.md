# Permit outreach workflow

How to draft access emails, attach plot maps, and track progress on the kanban.

**Kanban** = access state per property · **Itinerary CSV** = visit dates · **Maps** = PNG attachments for emails

---

## Should you save each email draft?

**No — not in the repo.** Per-property `email.md` files go stale quickly (dates change, co-worker names, which form is attached) and duplicate what the kanban card already holds.

| Keep in repo | Don't commit |
|--------------|--------------|
| `templates/email-template-nationalpark.md` | One-off Gmail drafts |
| Kanban cards (property, plots, dates, channel) | Copy-pasted sent emails |
| Generated map PNGs under `docs/checklists/maps/` | |

**Recommended flow:** stay in **Ask mode**, point the agent at the kanban card (e.g. `boards/02-BRI-BRK-Access-applications.md` → Torrington), get a filled email back, copy-paste into Gmail, send, move the card to **Awaiting Response**.

Regenerate maps only when the itinerary CSV or plot list changes — not per email.

---

## One-time setup per trip

```powershell
# Register trip plots from kanban (reads **Trip:** from the board header)
python scripts/trip_audit.py --trip-kanban boards/02-BRI-BRK-Access-applications.md --register

# Sync visit dates from the approved logistics CSV
python scripts/import_itinerary.py --trip-id 02-BRI-BRK-2026-07 `
    --csv docs/itineraries/02-BRI-BRK-2026-07-itinerary.csv

# Generate OSM basemap PNGs (requires pip install -e ".[maps]")
python scripts/generate_checklist.py --trip-id 02-BRI-BRK-2026-07 --maps
```

Outputs:

```
docs/checklists/02-BRI-BRK-2026-07-checklist.md
docs/checklists/maps/02-BRI-BRK-2026-07-<Property_Name>.png   ← attach to email
docs/checklists/maps/02-BRI-BRK-2026-07-overview.png            ← optional context
```

Map filenames truncate long property names to 40 characters (e.g. `…Jana_Ngalee_Local_Aboriginal_Land_Counci.png`).

---

## Per-property send checklist

1. **Kanban card** in **To Contact** — confirm plot IDs, email, visit date (from itinerary CSV / card Notes).
2. **Map** — attach `docs/checklists/maps/<trip-id>-<Property>.png` matching the card's TERN property name.
3. **Email** — use [templates/email-template-nationalpark.md](../templates/email-template-nationalpark.md) for NPWS / conservation areas; ask the agent to fill placeholders from the card.
4. **Forms** — attach completed Area Manager Approval (and licences / REOC / insurance if they ask).
5. **Send** → move card to **Awaiting Response**.
6. **Reply with forms** → **Documents & Maps** → back to **Awaiting Response** when resubmitted.
7. **Approval** → **Access Confirmed** (add ranger name, phone, gate notes).

One email thread per `tp.plots.property` — even when two parks share an NPWS regional inbox.

---

## Ask-mode prompt (copy-paste)

> Read `boards/02-BRI-BRK-Access-applications.md` and draft the outreach email for **Torrington State Conservation Area** using `templates/email-template-nationalpark.md`. Use dates from `docs/itineraries/02-BRI-BRK-2026-07-itinerary.csv`. Tell me which map PNG to attach from `docs/checklists/maps/`.

Swap the property name for each card in **To Contact**.

---

## Map regeneration

Re-run `--maps` when:

- Itinerary CSV daily rows change (`import_itinerary.py` first).
- Plots are added or removed on the kanban (`trip_audit.py --register`).

No need to re-run for each email.

---

## Related files

| File | Role |
|------|------|
| [templates/email-template-nationalpark.md](../templates/email-template-nationalpark.md) | NPWS email skeleton |
| [planning-guide.md](planning-guide.md) § Step 9 | Where outreach fits in trip planning |
| [itineraries/README.md](itineraries/README.md) | CSV refresh workflow |
| `src/dronescape_planning/generate_checklist.py` | OSM PNG generation (contextily + OpenStreetMap) |
