# Trip itineraries (CSV from shared Excel)

Drop the CSV export from Sheet 1 of the shared Excel workbook here, named `<trip-id>-itinerary.csv`.

For planning iteration, save coworker or draft variants with a suffix, e.g.
`02-BRI-BRK-2026-07-itinerary-v1-coworker.csv`, then generate labelled KMZ files:

```powershell
ds-generate-kml --trip-id 02-BRI-BRK-2026-07 `
    --csv docs/itineraries/02-BRI-BRK-2026-07-itinerary-v1-coworker.csv --label v1-coworker
```

Outputs: `docs/itineraries/maps/<trip-id>-plots[-label].kmz`. Open in Google Earth; layer versions to compare.

Full sync workflow (dry-run, apply, regenerate checklist) and field day hour caps:
see **[docs/workflow.md](../workflow.md) § Steps 10 & "Field day caps"**.

KMZ command reference: **[README.md](../../README.md)** § KMZ maps.
