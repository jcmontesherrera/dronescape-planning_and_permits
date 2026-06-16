# Field day policy — hour caps, itinerary flex, and deferral

Operational rules for day-by-day logistics when permits land before or after the
lead-approved itinerary. Complements [ADR 0005](../decisions/0005-itinerary-csv-as-logistics-snapshot.md)
(kanban = access, CSV = schedule) and [ADR 0006](../decisions/0006-late-permit-itinerary-flex.md).

---

## Hour caps

Total **working time per field day** (all columns in the shared Excel itinerary):

| Day type | Cap |
|----------|-----|
| Weekdays (Mon–Fri) | **≤ 11 hours** |
| Weekends (Sat–Sun) | **≤ 8 hours** |

Includes: driving, survey, post-survey tasks, and redundancy. Check the
`Total Estimated Working Time` column before committing a day.

Excel is the calculator; this doc is the rule. `import_itinerary.py` does not
enforce caps yet — review manually or via itinerary feedback after each CSV sync.

---

## Two layers when the Team Lead approves

The Team Lead approves the **corridor and anchors**, not every plot on a fixed day.

1. **Locked core** — confirmed access on the daily schedule; booked accommodation;
   hard anchors (trailer pickup, fly-out, travel days).
2. **Conditional add-ons** — pending or late-confirmed sites in the site master
   only (no site order / not on daily rows). Each add-on needs an insertion
   corridor and a stated fallback.

Pending sites not on the daily route are **expected** until access confirms —
see `itinerary_feedback.py` informational notes.

---

## Outcomes when access confirms (or a day is full)

| Outcome | Use when |
|---------|----------|
| **Absorb** | Site fits the current corridor and the day stays under the hour cap |
| **Defer** | Current trip is over cap or blocked by an anchor; site lies on the **next anchored leg** outbound corridor; permit covers (or can cover) that window |
| **Skip** | No corridor fit, permit cannot cover the window, or science/logistics priority is low |
| **Re-approve** | Absorb or defer changes accommodation, trip dates, hard anchors, or needs a permit amendment |

---

## Tier framework (governance)

| Tier | Condition | Action |
|------|-----------|--------|
| **0** | Absorb under caps, or defer was pre-declared and next-leg corridor is in [campaign-roadmap.md](campaign-roadmap.md) | Update Excel + kanban; run `import_itinerary.py --dry-run`; share feedback |
| **1** | Minor shuffle (redundancy trim, plot order) or defer expands next trip slightly | One-line Team Lead notification, then proceed |
| **2** | New overnight stop, exceeds hour caps with no flex, misses hard anchor, or permit date amendment | Escalate before committing Excel |

---

## Defer to the next anchored leg

Vehicle continuity is a hard constraint — defer only to the **next trip in the
chain** that passes the site without backtracking. See
[campaign-roadmap.md](campaign-roadmap.md).

**Good defer candidates** (example: ADL-BRI → BRI-BRK): inland NSW or early QLD
sites tight on the current trip but on Brisbane → Broken Hill outbound corridor
(e.g. Warrumbungle, Irongate, Russell Reserve).

**Poor defer targets**: western NSW backups better suited to a later Broken Hill
loop (e.g. Mungo, Mallee Cliffs) — defer to the leg that actually routes there.

### Defer checklist

1. **Corridor** — next trip route passes the property outbound, not as a detour.
2. **Permit** — approval window covers the next trip dates; email ranger if the
   visit month shifted.
3. **ADL-BRI kanban** — `Access Confirmed · Deferred → <next-trip-id>` on the
   source board (audit trail).
4. **Next kanban** — carryover card: `Carryover from <prior-trip-id> · permit granted <date>`.
5. **`campaign_plots`** — when the next trip is registered, move plot rows to the
   new `trip_id`; clear `visit_date` on the prior trip.
6. **Excel** — tag site master `DEFERRED → <trip-id>`; remove from current daily rows.
7. **Roadmap** — note carryovers on the next trip entry.

---

## Late-approval workflow

```
Kanban → Access Confirmed (+ ranger / gate notes)
  → Excel: model ONE day, recalc Total Estimated Working Time
  → import_itinerary.py --dry-run
  → Read docs/audits/<trip>-itinerary-feedback.md
  → Absorb | Defer | Skip | Tier 2 escalate
  → Apply import + regenerate checklist if absorbing
```

**Dangerous mismatch** (action, not informational): plot **on the daily schedule**
while kanban is still **Awaiting Response** — do not field until confirmed or removed
from Excel.

---

## Team Lead one-liner (template)

> *[Property]* approved. [Absorb on DATE / Defer to TRIP-ID / Skip — reason].
> [No accommodation change / Tier 1 notify / Tier 2 — needs sign-off].

---

## Repo map

| Concern | Source of truth |
|---------|-----------------|
| Access status, contacts | `boards/` kanban |
| Daily route, times, accommodation | `docs/itineraries/*.csv` |
| Cross-check | `itinerary_feedback.py` (on import) |
| Vehicle chain & defer targets | `docs/campaign-roadmap.md` |
