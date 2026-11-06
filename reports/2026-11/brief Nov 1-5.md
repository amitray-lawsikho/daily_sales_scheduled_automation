# MTD Report Nov 1-5, 2026 — brief

Window: 1-5 Nov 2026 (last complete day; D = 30) · generated 06 Nov 2026 · playbook v6 / policy v9 (Team Uzair default)

## Headline
- **Team Uzair**: Rs 1,557,724 (+49.0% vs Oct 1-5) · achievement 45% of pro-rated · enrollments 35 vs 23 · pending Rs 1,382,353  
  Same window earlier: Oct Rs 1,045,239 · Sep Rs 1,455,202 · Aug Rs 1,468,648 · Jul Rs 1,668,981 · Jun Rs 1,399,069

## Sanity checks
**Team Uzair**
- 1. Enrollment plausibility: 35 enrollments / 49 revenue rows = 71% — pass
- 2. Enrollments vs revenue direction: revenue x1.49, enrollments x1.52 — pass
- 3. Realisation per enrollment: Rs 44,506 in band — pass
- 5. Roll-up (teams = verticals = segment, revenue and enrollments): exact
**All segments**
- 4. Restatement check: revenue matches to the rupee; enrollments -1 (4 Nov flag change, Collection); caller/team moves listed below
- 6. Formula errors: n/a (no xlsx in default policy)

## Data quality (whole workbook window)
- 1,551 revenue rows · Rs 7,098,018 · 220 enrollments (220 unique txn IDs) · negatives: 0
- Duplicate Transaction IDs: 6 IDs / 13 rows / Rs 560,772 (0 same-amount) — counted per split-transaction rule
- Convenience/Hardcopy rows: 3 / Rs 910 — included
- Text-formatted fees: 0 (Rs 0) — parsed and included
- Lead Details not Available → Direct: 0 row(s) / Rs 0
- Workbook last date: 2026-11-06 · history rows now 5,556

## NEW anomalies — questions for you
- Restatement of Nov 2-4 (company revenue unchanged; enrollments -1; **Team Uzair unchanged**):
  - Poorvi Shrivastava, Mudasir Zahoor and S Isra Anjum moved from *ID Closure - Darshan* to a new team **ID Closures - Mudasir** (Team Darshan), Rs 1,38,884, 2 enrollments. Is this a new live team (with yesterday's *ID Closure - Chandan*, it looks like ID Closure - Darshan is being split)?
  - 4 Nov Rs 52,700: Aisha Sami (Changemakers) → Mayank (SA - Shivam); the row lost its New enrollment flag, so company enrollments are 1 lower.
- Roster: active targets Rs 4,17,83,000 / 91 holders → Rs 4,52,33,000 / 101 holders (+Rs 34,50,000, 10 new target holders, all outside Team Uzair). Confirm final?

## Still open (raised before, defaults applied)
- Removed team **Team Karman Kaur** (Team Karman Kaur) has Rs 52,135 in history that cannot be re-homed (no live roster team for its callers) — it is not reported.

## Files
- `reports/2026-11/MTD Report Nov 1-5 - Team Uzair.pdf`
- `data/revenue_history.csv` (updated)
