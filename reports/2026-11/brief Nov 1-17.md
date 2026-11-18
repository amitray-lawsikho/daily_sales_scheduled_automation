# MTD Report Nov 1-17, 2026 — brief

Window: 1-17 Nov 2026 (last complete day; D = 30) · generated 18 Nov 2026 · playbook v6 / policy v9 (Team Uzair default)

## Headline
- **Team Uzair**: Rs 5,033,284 (-18.4% vs Oct 1-17) · achievement 43% of pro-rated · enrollments 100 vs 134 · pending Rs 1,451,504  
  Same window earlier: Oct Rs 6,166,508 · Sep Rs 6,784,112 · Aug Rs 8,771,283 · Jul Rs 8,456,160 · Jun Rs 8,067,373

## Sanity checks
**Team Uzair**
- 1. Enrollment plausibility: 100 enrollments / 155 revenue rows = 65% — pass
- 2. Enrollments vs revenue direction: revenue x0.82, enrollments x0.75 — pass
- 3. Realisation per enrollment: Rs 50,333 in band — pass
- 5. Roll-up (teams = verticals = segment, revenue and enrollments): exact
**All segments**
- 4. Restatement check: totals match to the rupee; one 15 Nov row re-attributed outside Team Uzair (see below)
- 6. Formula errors: n/a (no xlsx in default policy)

## Data quality (whole workbook window)
- 5,495 revenue rows · Rs 23,981,013 · 824 enrollments (824 unique txn IDs) · negatives: 0
- Duplicate Transaction IDs: 26 IDs / 53 rows / Rs 2,258,187 (1 same-amount) — counted per split-transaction rule
- Convenience/Hardcopy rows: 5 / Rs 3,440 — included
- Text-formatted fees: 0 (Rs 0) — parsed and included
- Lead Details not Available → Direct: 0 row(s) / Rs 0
- Workbook last date: 2026-11-17 · history rows now 5,828

## NEW anomalies — questions for you
- Restatement (totals unchanged, **Team Uzair unchanged**): 15 Nov Rs 3,000 bootcamp booking moved from Bootcamp - Direct to Prateeksha Singh Dhakre (ID Closures - Mudasir, Team Darshan), +1 enrollment there.
- Roster: **Kashish** (SA - Aditya, Team Anmol) now *Resigned*; Rs 3,00,000 target drops out (active targets Rs 4,47,00,000 / 100). Not Team Uzair.

## Still open (raised before, defaults applied)
- 1 duplicate Transaction ID(s) carry the SAME amount on both rows — genuine two-course bookings or double entry? (counted per split-transaction rule)
- Removed team **Team Karman Kaur** (Team Karman Kaur) has Rs 52,135 in history that cannot be re-homed (no live roster team for its callers) — it is not reported.

## Files
- `reports/2026-11/MTD Report Nov 1-17 - Team Uzair.pdf`
- `data/revenue_history.csv` (updated)
