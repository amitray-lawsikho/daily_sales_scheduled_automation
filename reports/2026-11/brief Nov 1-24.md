# MTD Report Nov 1-24, 2026 — brief

Window: 1-24 Nov 2026 (last complete day; D = 30) · generated 25 Nov 2026 · playbook v6 / policy v9 (Team Uzair default)

## Headline
- **Team Uzair**: Rs 7,318,737 (-20.0% vs Oct 1-24) · achievement 44% of pro-rated · enrollments 148 vs 195 · pending Rs 1,754,455  
  Same window earlier: Oct Rs 9,144,980 · Sep Rs 10,625,893 · Aug Rs 12,574,093 · Jul Rs 13,383,489 · Jun Rs 12,031,667

## Sanity checks
**Team Uzair**
- 1. Enrollment plausibility: 148 enrollments / 232 revenue rows = 64% — pass
- 2. Enrollments vs revenue direction: revenue x0.80, enrollments x0.76 — pass
- 3. Realisation per enrollment: Rs 49,451 in band — pass
- 5. Roll-up (teams = verticals = segment, revenue and enrollments): exact
**All segments**
- 4. Restatement check: none — days already in history match the workbook to the rupee
- 6. Formula errors: n/a (no xlsx in default policy)

## Data quality (whole workbook window)
- 7,996 revenue rows · Rs 40,780,395 · 1192 enrollments (1192 unique txn IDs) · negatives: 0
- Duplicate Transaction IDs: 57 IDs / 115 rows / Rs 4,993,242 (1 same-amount) — counted per split-transaction rule
- Convenience/Hardcopy rows: 8 / Rs 4,250 — included
- Text-formatted fees: 1 (Rs 23,777) — parsed and included
- Lead Details not Available → Direct: 2 row(s) / Rs 37,877
- Workbook last date: 2026-11-24 · history rows now 6,061

## NEW anomalies — questions for you
- 24 Nov: a fee of **"23,777.00" stored as text** (no caller, Team Name *Lead Details not Available*) — parsed and INCLUDED per the Oct rule, counted as Direct (outside Team Uzair) until ops attributes it. Ops may want to fix the cell format. 2 *Lead Details not Available* rows in total (Rs 37,877), both expected to be attributed in the next day or two.

## Still open (raised before, defaults applied)
- 1 duplicate Transaction ID(s) carry the SAME amount on both rows — genuine two-course bookings or double entry? (counted per split-transaction rule)
- Removed team **Team Karman Kaur** (Team Karman Kaur) has Rs 52,135 in history that cannot be re-homed (no live roster team for its callers) — it is not reported.

## Files
- `reports/2026-11/MTD Report Nov 1-24 - Team Uzair.pdf`
- `data/revenue_history.csv` (updated)
