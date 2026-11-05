# MTD Report Nov 1-4, 2026 — brief

Window: 1-4 Nov 2026 (last complete day; D = 30) · generated 05 Nov 2026 · playbook v6 / policy v9 (Team Uzair default)

## Headline
- **Team Uzair**: Rs 1,406,724 (+116.0% vs Oct 1-4) · achievement 51% of pro-rated · enrollments 28 vs 11 · pending Rs 1,123,653  
  Same window earlier: Oct Rs 651,272 · Sep Rs 1,174,633 · Aug Rs 1,027,098 · Jul Rs 1,527,881 · Jun Rs 1,133,278

## Sanity checks
**Team Uzair**
- 1. Enrollment plausibility: 28 enrollments / 41 revenue rows = 68% — pass
- 2. Enrollments vs revenue direction: revenue x2.16, enrollments x2.55 — pass (small early-month counts)
- 3. Realisation per enrollment: Rs 50,240 in band — pass
- 5. Roll-up (teams = verticals = segment, revenue and enrollments): exact
**All segments**
- 4. Restatement check: totals match to the rupee; caller/team re-attributions on 1-3 Nov (see anomalies)
- 6. Formula errors: n/a (no xlsx in default policy)

## Data quality (whole workbook window)
- 1,266 revenue rows · Rs 5,741,572 · 179 enrollments (179 unique txn IDs) · negatives: 0
- Duplicate Transaction IDs: 4 IDs / 8 rows / Rs 350,122 (0 same-amount) — counted per split-transaction rule
- Convenience/Hardcopy rows: 2 / Rs 590 — included
- Text-formatted fees: 0 (Rs 0) — parsed and included
- Lead Details not Available → Direct: 0 row(s) / Rs 0
- Workbook last date: 2026-11-04 · history rows now 5,528

## NEW anomalies — questions for you
- Restatement of Nov 1-3 (company totals unchanged): **Chandan Singh**'s rows (Rs 1,08,276, 3 enrollments) moved from *ID Closure - Darshan* to a new team **ID Closure - Chandan** (Team Darshan). Is ID Closure - Chandan a new live team? Treat it as separate from ID Closure - Darshan?
- Restatement: the 3 Nov **Lead Details not Available** row (Rs 45,276, Direct) is now attributed to **Suhail Showkat (Elite)**, which raises Team Uzair's Nov 1-3 total by Rs 45,276. Applied.

## Still open (raised before, defaults applied)
- Removed team **Team Karman Kaur** (Team Karman Kaur) has Rs 52,135 in history that cannot be re-homed (no live roster team for its callers) — it is not reported.

## Files
- `reports/2026-11/MTD Report Nov 1-4 - Team Uzair.pdf`
- `data/revenue_history.csv` (updated)
