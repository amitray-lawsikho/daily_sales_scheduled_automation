# MTD Report Nov 1-13, 2026 — brief

Window: 1-13 Nov 2026 (last complete day; D = 30) · generated 14 Nov 2026 · playbook v6 / policy v9 (Team Uzair default)

## Headline
- **Team Uzair**: Rs 3,704,232 (-7.3% vs Oct 1-13) · achievement 41% of pro-rated · enrollments 71 vs 96 · pending Rs 1,145,704  
  Same window earlier: Oct Rs 3,994,919 · Sep Rs 4,351,367 · Aug Rs 6,547,901 · Jul Rs 5,816,751 · Jun Rs 5,657,471

## Sanity checks
**Team Uzair**
- 1. Enrollment plausibility: 71 enrollments / 109 revenue rows = 65% — pass
- 2. Enrollments vs revenue direction: revenue x0.93, enrollments x0.74 — pass
- 3. Realisation per enrollment: Rs 52,172 in band — pass
- 5. Roll-up (teams = verticals = segment, revenue and enrollments): exact
**All segments**
- 4. Restatement check: none — days already in history match the workbook to the rupee
- 6. Formula errors: n/a (no xlsx in default policy)

## Data quality (whole workbook window)
- 3,612 revenue rows · Rs 14,516,840 · 294 enrollments (294 unique txn IDs) · negatives: 0
- Duplicate Transaction IDs: 13 IDs / 27 rows / Rs 1,129,169 (1 same-amount) — counted per split-transaction rule
- Convenience/Hardcopy rows: 5 / Rs 3,440 — included
- Text-formatted fees: 0 (Rs 0) — parsed and included
- Lead Details not Available → Direct: 1 row(s) / Rs 51,769
- Workbook last date: 2026-11-13 · history rows now 5,716

## NEW anomalies — questions for you
- Roster: **Mansi Verma** (US accounting closures - Deepanshi) is now *Resigned*, so her Rs 5,33,000 target drops out (active targets Rs 4,56,33,000 / 103 → Rs 4,51,00,000 / 102). 5 rows added. Team Uzair unchanged at Rs 2,08,00,000. Note: the **Sreya** vertical now carries Rs 4,00,000 of target. Which team/segment does Sreya belong to?
- 13 Nov: one *Lead Details not Available* row (Rs 51,769) is bucketed as Direct per the standing rule.

## Still open (raised before, defaults applied)
- 1 duplicate Transaction ID(s) carry the SAME amount on both rows — genuine two-course bookings or double entry? (counted per split-transaction rule)
- Removed team **Team Karman Kaur** (Team Karman Kaur) has Rs 52,135 in history that cannot be re-homed (no live roster team for its callers) — it is not reported.

## Files
- `reports/2026-11/MTD Report Nov 1-13 - Team Uzair.pdf`
- `data/revenue_history.csv` (updated)
