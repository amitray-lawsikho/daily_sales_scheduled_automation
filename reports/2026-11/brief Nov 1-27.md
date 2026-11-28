# MTD Report Nov 1-27, 2026 — brief

Window: 1-27 Nov 2026 (last complete day; D = 30) · generated 28 Nov 2026 · playbook v6 / policy v9 (Team Uzair default)

## Headline
- **Team Uzair**: Rs 8,798,446 (-17.2% vs Oct 1-27) · achievement 47% of pro-rated · enrollments 181 vs 220 · pending Rs 1,492,653  
  Same window earlier: Oct Rs 10,623,333 · Sep Rs 12,487,562 · Aug Rs 14,835,145 · Jul Rs 15,466,792 · Jun Rs 13,816,566

## Sanity checks
**Team Uzair**
- 1. Enrollment plausibility: 181 enrollments / 281 revenue rows = 64% — pass
- 2. Enrollments vs revenue direction: revenue x0.83, enrollments x0.82 — pass
- 3. Realisation per enrollment: Rs 48,610 in band — pass
- 5. Roll-up (teams = verticals = segment, revenue and enrollments): exact
**All segments**
- 4. Restatement check: none — days already in history match the workbook to the rupee
- 6. Formula errors: n/a (no xlsx in default policy)

## Data quality (whole workbook window)
- 8,990 revenue rows · Rs 48,385,617 · 1290 enrollments (1290 unique txn IDs) · negatives: 0
- Duplicate Transaction IDs: 67 IDs / 135 rows / Rs 5,773,629 (1 same-amount) — counted per split-transaction rule
- Convenience/Hardcopy rows: 11 / Rs 5,060 — included
- Text-formatted fees: 3 (Rs 44,427) — parsed and included
- Lead Details not Available → Direct: 0 row(s) / Rs 0
- Workbook last date: 2026-11-27 · history rows now 6,177

## NEW anomalies — questions for you
- 27 Nov: 2 more fees stored as **text** (Rs 1,770 and Rs 18,880, both Direct) — parsed and INCLUDED per the Oct rule (3 such rows in November now, Rs 44,427, all Direct, none in Team Uzair). Ops may want to fix the cell format.
- Roster: **Komal singh** (Women ai, Team Anmol) now *Resigned*; Rs 1,00,000 target drops out (active targets Rs 4,42,00,000 / 99). Not Team Uzair.

## Still open (raised before, defaults applied)
- 1 duplicate Transaction ID(s) carry the SAME amount on both rows — genuine two-course bookings or double entry? (counted per split-transaction rule)
- Removed team **Team Karman Kaur** (Team Karman Kaur) has Rs 52,135 in history that cannot be re-homed (no live roster team for its callers) — it is not reported.

## Files
- `reports/2026-11/MTD Report Nov 1-27 - Team Uzair.pdf`
- `data/revenue_history.csv` (updated)
