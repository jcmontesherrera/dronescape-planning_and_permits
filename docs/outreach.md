# Permit outreach guide

One home for everything related to drafting and sending access emails.

**Rule:** do not save per-property email drafts in the repo. The kanban card +
`templates/email-template-nationalpark.md` + the agent prompt below are enough.

---

## One-time setup per trip

Run these once when the itinerary is settled:

```powershell
# 1. Register trip plots from kanban
python scripts/trip_audit.py --trip-kanban boards/02-BRI-BRK-Access-applications.md --register

# 2. Sync visit dates from the approved logistics CSV
python scripts/import_itinerary.py --trip-id 02-BRI-BRK-2026-07 `
    --csv docs/itineraries/02-BRI-BRK-2026-07-itinerary.csv

# 3. Generate per-property map PNGs (attach to emails)
python scripts/generate_checklist.py --trip-id 02-BRI-BRK-2026-07 --maps
```

Map output: `docs/checklists/maps/02-BRI-BRK-2026-07-<Property_Name>.png`

---

## Per-property send checklist

1. **Kanban card in "To Contact"** — confirm plot IDs, email address, and visit date from the itinerary CSV.
2. **Map** — find `docs/checklists/maps/<trip-id>-<Property>.png` matching the card's TERN property name.
3. **Email** — use the agent prompt below to get a filled draft; copy-paste into Gmail/Outlook.
4. **Forms** — attach the Area Manager Approval form; add licences / REOC / insurance if requested.
5. **Send** → move card to **Awaiting Response**.
6. **Reply with forms** → move to **Documents & Maps** → back to **Awaiting Response** when resubmitted.
7. **Approval received** → **Access Confirmed** (add ranger name, phone, gate / access notes).

One email thread per `tp.plots.property` — even when two parks share an NPWS regional inbox.

---

## Ask-mode agent prompt (copy-paste)

Replace the property name for each card in **To Contact**:

> Read `boards/02-BRI-BRK-Access-applications.md` and draft the access email for
> **[Property name]** using `templates/email-template-nationalpark.md`. Use dates
> from `docs/itineraries/02-BRI-BRK-2026-07-itinerary.csv`. Tell me which map PNG
> to attach from `docs/checklists/maps/`. Return copy-paste ready text only — do
> not save a file.

---

## When to regenerate maps

Re-run `--maps` only when:
- The itinerary CSV daily rows change (run `import_itinerary.py` first).
- Plots are added or removed on the kanban (run `trip_audit.py --register` first).

No need to re-run per email.

---

## Email template

`templates/email-template-nationalpark.md` — lean skeleton with placeholders:
`{{RECIPIENT}}`, `{{PROPERTY_OR_PROPERTIES}}`, `{{ROUTE}}`, `{{START_DATE}}`,
`{{END_DATE}}`, `{{PROPERTY_BULLET_LIST}}`.

Fill placeholders manually or ask the agent (prompt above).

---

## Related files

| File | Role |
|------|------|
| `templates/email-template-nationalpark.md` | Email skeleton |
| `boards/NN-ORIG-DEST-Access-applications.md` | Access state per property |
| `docs/itineraries/<trip-id>-itinerary.csv` | Visit dates |
| `docs/checklists/maps/` | PNG attachments for emails |
| [docs/workflow.md](workflow.md) § Steps 8–9 | Where outreach fits in trip planning |
