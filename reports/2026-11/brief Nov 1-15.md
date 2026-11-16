# MTD Report Nov 1-15, 2026 — brief

Window: 1-15 Nov 2026 (last complete day; D = 30) · generated 16 Nov 2026 · playbook v6 / policy v9 (Team Uzair default)

## Headline
- **Team Uzair**: Rs 3,783,519 (-30.3% vs Oct 1-15) · achievement 36% of pro-rated · enrollments 80 vs 119 · pending Rs 1,645,854  
  Same window earlier: Oct Rs 5,429,207 · Sep Rs 5,438,773 · Aug Rs 7,441,268 · Jul Rs 7,078,096 · Jun Rs 6,600,624

## Sanity checks
**Team Uzair**
- 1. Enrollment plausibility: 80 enrollments / 120 revenue rows = 67% — pass
- 2. Enrollments vs revenue direction: revenue x0.70, enrollments x0.67 — pass
- 3. Realisation per enrollment: Rs 47,294 in band — pass
- 5. Roll-up (teams = verticals = segment, revenue and enrollments): exact
**All segments**
- 4. Restatement check: none — days already in history match the workbook to the rupee
- 6. Formula errors: n/a (no xlsx in default policy)

## Data quality (whole workbook window)
- 4,628 revenue rows · Rs 16,364,135 · 691 enrollments (691 unique txn IDs) · negatives: 0
- Duplicate Transaction IDs: 13 IDs / 27 rows / Rs 1,129,169 (1 same-amount) — counted per split-transaction rule
- Convenience/Hardcopy rows: 5 / Rs 3,440 — included
- Text-formatted fees: 0 (Rs 0) — parsed and included
- Lead Details not Available → Direct: 1 row(s) / Rs 51,769
- Workbook last date: 2026-11-15 · history rows now 5,754

## NEW anomalies — questions for you
- none. FYI: company enrollments jumped 294 → 691 because of **341 bootcamp seat bookings on 15 Nov** (Rs 10,23,015, ~Rs 3,000 each: US Accounting, Independent Director, AI for Women bootcamps of 14-16 Nov), all under *Bootcamp - Direct*, outside the three segments. Team Uzair not affected.

## Still open (raised before, defaults applied)
- 1 duplicate Transaction ID(s) carry the SAME amount on both rows — genuine two-course bookings or double entry? (counted per split-transaction rule)
- Removed team **Team Karman Kaur** (Team Karman Kaur) has Rs 52,135 in history that cannot be re-homed (no live roster team for its callers) — it is not reported.

## Files
- `reports/2026-11/MTD Report Nov 1-15 - Team Uzair.pdf`
- `data/revenue_history.csv` (updated)
