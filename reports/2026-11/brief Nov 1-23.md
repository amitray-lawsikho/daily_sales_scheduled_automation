# MTD Report Nov 1-23, 2026 — brief

Window: 1-23 Nov 2026 (last complete day; D = 30) · generated 24 Nov 2026 · playbook v6 / policy v9 (Team Uzair default)

## Headline
- **Team Uzair**: Rs 6,831,791 (-22.0% vs Oct 1-23) · achievement 43% of pro-rated · enrollments 140 vs 186 · pending Rs 1,598,255  
  Same window earlier: Oct Rs 8,755,499 · Sep Rs 10,284,571 · Aug Rs 11,940,964 · Jul Rs 12,736,209 · Jun Rs 10,980,218

## Sanity checks
**Team Uzair**
- 1. Enrollment plausibility: 140 enrollments / 218 revenue rows = 64% — pass
- 2. Enrollments vs revenue direction: revenue x0.78, enrollments x0.75 — pass
- 3. Realisation per enrollment: Rs 48,799 in band — pass
- 5. Roll-up (teams = verticals = segment, revenue and enrollments): exact
**All segments**
- 4. Restatement check: none — days already in history match the workbook to the rupee
- 6. Formula errors: n/a (no xlsx in default policy)

## Data quality (whole workbook window)
- 7,621 revenue rows · Rs 38,718,614 · 1170 enrollments (1170 unique txn IDs) · negatives: 0
- Duplicate Transaction IDs: 55 IDs / 111 rows / Rs 4,820,009 (1 same-amount) — counted per split-transaction rule
- Convenience/Hardcopy rows: 8 / Rs 4,250 — included
- Text-formatted fees: 0 (Rs 0) — parsed and included
- Lead Details not Available → Direct: 0 row(s) / Rs 0
- Workbook last date: 2026-11-23 · history rows now 6,022

## NEW anomalies — questions for you
- Roster (active targets Rs 4,48,00,000 / 101 → Rs 4,43,00,000 / 100): **Suryasnata Mukherjee** (SA - Shivam, Team Anmol) now *Resigned* (−Rs 5,00,000). Inside Team Uzair (net zero, total still Rs 2,08,00,000): **Nishita Kumari** (US accounting closures - Sana) now *Resigned* (−Rs 2,00,000) and **Kashish Sabharwal** added with a Rs 2,00,000 target (no revenue yet). Confirm final?

## Still open (raised before, defaults applied)
- 1 duplicate Transaction ID(s) carry the SAME amount on both rows — genuine two-course bookings or double entry? (counted per split-transaction rule)
- Removed team **Team Karman Kaur** (Team Karman Kaur) has Rs 52,135 in history that cannot be re-homed (no live roster team for its callers) — it is not reported.

## Files
- `reports/2026-11/MTD Report Nov 1-23 - Team Uzair.pdf`
- `data/revenue_history.csv` (updated)
