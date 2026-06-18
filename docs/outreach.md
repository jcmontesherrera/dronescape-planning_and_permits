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

Ensure credential PDFs are in `docs/access/credentials/` (see [docs/access/README.md](access/README.md)).

---

## Per-property send checklist

1. **Kanban card in "To Contact"** — confirm plot IDs, email address, and visit date from the itinerary CSV.
2. **Map** — `docs/checklists/maps/<trip-id>-<Property>.png` matching the card's TERN property name.
3. **Area Manager form** — completed PDF in `docs/access/submissions/<trip-id>/`.
4. **Credentials** — attach from `docs/access/credentials/` (licences, REOC, insurance).
5. **Email** — use the agent prompt below; copy-paste into Gmail/Outlook.
6. **Send** → move card to **Awaiting Response**.
7. **Reply with extra forms** → move to **Documents & Maps** → back to **Awaiting Response** when resubmitted.
8. **Approval received** → **Access Confirmed** (ranger name, phone, gate / access notes).

One email thread per `tp.plots.property` — even when two parks share an NPWS regional inbox.

---

## Attachments (typical cold email)

| # | File | Where |
|---|------|-------|
| 1 | Site map | `docs/checklists/maps/<trip-id>-<Property>.png` |
| 2 | Area Manager Approval (filled) | `docs/access/submissions/<trip-id>/` |
| 3 | Pilot licences | `docs/access/credentials/jcmontes-casa-licence.pdf`, `tbektas-casa-licence.pdf` |
| 4 | REOC | `docs/access/credentials/reoc-certificate.pdf` |
| 5 | Public liability insurance | `docs/access/credentials/public-liability-insurance.pdf` |

Full filename list: [docs/access/README.md](access/README.md).

---

## Ask-mode agent prompt (copy-paste)

Replace the property name for each card in **To Contact**:

> Read `boards/02-BRI-BRK-Access-applications.md` and draft the access email for
> **[Property name]** using `templates/email-template-nationalpark.md`. Use dates
> from `docs/itineraries/02-BRI-BRK-2026-07-itinerary.csv` (include `{{VISIT_DATE}}`
> for that property). List attachments: map from `docs/checklists/maps/`, credentials
> from `docs/access/credentials/`, and the Area Manager form from
> `docs/access/submissions/<trip-id>/`. Return copy-paste ready text only — do not
> save a file. Tailor one line if the authority is private land, council, or Crown Lands.

---

## When to regenerate maps

Re-run `--maps` only when:
- The itinerary CSV daily rows change (run `import_itinerary.py` first).
- Plots are added or removed on the kanban (run `trip_audit.py --register` first).

No need to re-run per email.

---

## Email template

`templates/email-template-nationalpark.md` — short cold-outreach skeleton:

`{{RECIPIENT}}`, `{{PROPERTY_OR_PROPERTIES}}`, `{{ROUTE}}`, `{{START_DATE}}`,
`{{END_DATE}}`, `{{VISIT_DATE}}`, `{{PROPERTY_BULLET_LIST}}`.

Fill placeholders manually or ask the agent (prompt above).

---

## Later: official DroneScape access pack

Not built yet. Future work: one branded PDF (project intro, TERN links, credentials
summary) to replace attaching many separate files. Until then: short email + table above.

---

## Related files

| File | Role |
|------|------|
| `templates/email-template-nationalpark.md` | Email skeleton |
| `docs/access/credentials/` | Licences, REOC, insurance (local, gitignored) |
| `docs/access/submissions/` | Filled Area Manager forms per trip (local, gitignored) |
| `boards/NN-ORIG-DEST-Access-applications.md` | Access state per property |
| `docs/itineraries/<trip-id>-itinerary.csv` | Visit dates |
| `docs/checklists/maps/` | PNG attachments for emails |
| [docs/workflow.md](workflow.md) § Steps 8–9 | Where outreach fits in trip planning |
