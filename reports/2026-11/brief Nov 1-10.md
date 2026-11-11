# MTD Report Nov 1-10, 2026 — brief

Window: 1-10 Nov 2026 (last complete day; D = 30) · generated 11 Nov 2026 · playbook v6 / policy v9 (Team Uzair default)

## Headline
- **Team Uzair**: Rs 2,423,943 (-15.3% vs Oct 1-10) · achievement 35% of pro-rated · enrollments 53 vs 72 · pending Rs 1,361,204  
  Same window earlier: Oct Rs 2,861,864 · Sep Rs 3,438,283 · Aug Rs 4,288,531 · Jul Rs 4,435,393 · Jun Rs 4,053,061

## Sanity checks
**Team Uzair**
- 1. Enrollment plausibility: 53 enrollments / 77 revenue rows = 69% — pass
- 2. Enrollments vs revenue direction: revenue x0.85, enrollments x0.74 — pass
- 3. Realisation per enrollment: Rs 45,735 in band — pass
- 5. Roll-up (teams = verticals = segment, revenue and enrollments): exact
**All segments**
- 4. Restatement check: none — days already in history match the workbook to the rupee
- 6. Formula errors: n/a (no xlsx in default policy)

## Data quality (whole workbook window)
- 2,773 revenue rows · Rs 10,529,261 · 254 enrollments (254 unique txn IDs) · negatives: 0
- Duplicate Transaction IDs: 9 IDs / 19 rows / Rs 808,596 (1 same-amount) — counted per split-transaction rule
- Convenience/Hardcopy rows: 3 / Rs 910 — included
- Text-formatted fees: 0 (Rs 0) — parsed and included
- Lead Details not Available → Direct: 0 row(s) / Rs 0
- Workbook last date: 2026-11-10 · history rows now 5,636

## NEW anomalies — questions for you
- Roster grew 236 → 248 rows with **no target change** (Rs 4,56,33,000 / 103 holders; Team Uzair still Rs 2,08,00,000). It includes a vertical **Sreya** (2 active callers, no target, no revenue) — new vertical, or should ops map these callers to an existing one?

## Still open (raised before, defaults applied)
- 1 duplicate Transaction ID(s) carry the SAME amount on both rows — genuine two-course bookings or double entry? (counted per split-transaction rule)
- Removed team **Team Karman Kaur** (Team Karman Kaur) has Rs 52,135 in history that cannot be re-homed (no live roster team for its callers) — it is not reported.

## Files
- `reports/2026-11/MTD Report Nov 1-10 - Team Uzair.pdf`
- `data/revenue_history.csv` (updated)
