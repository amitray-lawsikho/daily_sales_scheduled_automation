# MTD Report Nov 1-11, 2026 — brief

Window: 1-11 Nov 2026 (last complete day; D = 30) · generated 12 Nov 2026 · playbook v6 / policy v9 (Team Uzair default)

## Headline
- **Team Uzair**: Rs 3,196,610 (+6.0% vs Oct 1-11) · achievement 42% of pro-rated · enrollments 60 vs 77 · pending Rs 994,904  
  Same window earlier: Oct Rs 3,016,730 · Sep Rs 3,767,018 · Aug Rs 4,920,585 · Jul Rs 4,698,766 · Jun Rs 4,796,265

## Sanity checks
**Team Uzair**
- 1. Enrollment plausibility: 60 enrollments / 93 revenue rows = 65% — pass
- 2. Enrollments vs revenue direction: revenue x1.06, enrollments x0.78 — pass
- 3. Realisation per enrollment: Rs 53,277 in band — pass
- 5. Roll-up (teams = verticals = segment, revenue and enrollments): exact
**All segments**
- 4. Restatement check: none — days already in history match the workbook to the rupee
- 6. Formula errors: n/a (no xlsx in default policy)

## Data quality (whole workbook window)
- 3,066 revenue rows · Rs 12,170,155 · 267 enrollments (267 unique txn IDs) · negatives: 0
- Duplicate Transaction IDs: 10 IDs / 21 rows / Rs 874,495 (1 same-amount) — counted per split-transaction rule
- Convenience/Hardcopy rows: 3 / Rs 910 — included
- Text-formatted fees: 0 (Rs 0) — parsed and included
- Lead Details not Available → Direct: 0 row(s) / Rs 0
- Workbook last date: 2026-11-11 · history rows now 5,664

## NEW anomalies — questions for you
- none

## Still open (raised before, defaults applied)
- 1 duplicate Transaction ID(s) carry the SAME amount on both rows — genuine two-course bookings or double entry? (counted per split-transaction rule)
- Removed team **Team Karman Kaur** (Team Karman Kaur) has Rs 52,135 in history that cannot be re-homed (no live roster team for its callers) — it is not reported.

## Files
- `reports/2026-11/MTD Report Nov 1-11 - Team Uzair.pdf`
- `data/revenue_history.csv` (updated)
