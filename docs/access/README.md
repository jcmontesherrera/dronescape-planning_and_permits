# Access attachments

Local-only PDFs for permit outreach. Nothing here is committed — drop files on each
machine and attach manually in Gmail/Outlook.

## credentials/ — reuse every email

Stable filenames so `docs/outreach.md` and the agent prompt can reference them:

| File | Purpose |
|------|---------|
| `jcmontes-casa-licence.pdf` | Juan Carlos — CASA remote pilot licence |
| `tbektas-casa-licence.pdf` | Troy Bektas — CASA remote pilot licence |
| `reoc-certificate.pdf` | REOC |
| `public-liability-insurance.pdf` | Organisational public liability insurance |
| `utas-support-letter.pdf` | UTAS letter of support (if you have one) |

Refresh when licences or insurance renew. Delete superseded copies locally.

## submissions/ — per trip / per property

Filled **Application for Area Manager Approval: External Third-Party RPA Operation**
and any authority-specific forms returned to you.

Suggested layout:

```
submissions/
  02-BRI-BRK-2026-07/
    Warrumbungle-National-Park-area-manager.pdf
    Pilliga-SCA-area-manager.pdf
```

One folder per `trip_id`; one PDF per property when the form is property-specific.

## Generated elsewhere (not in this folder)

| Attachment | Source |
|------------|--------|
| Site map PNG | `docs/checklists/maps/<trip-id>-<Property>.png` — run `generate_checklist.py --maps` |

## Cold-email attachment set (typical NPWS)

1. Site map PNG (from checklists)
2. Completed Area Manager form (from `submissions/<trip-id>/`)
3. All files in `credentials/` (or only what the authority asks for)

## Later (not implemented)

Official branded **DroneScape access pack** PDF (project intro, links, one attachment
instead of many). Until then: short email + the files above.
