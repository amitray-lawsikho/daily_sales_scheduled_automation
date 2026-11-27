# MTD Report Nov 1-26, 2026 — brief

Window: 1-26 Nov 2026 (last complete day; D = 30) · generated 27 Nov 2026 · playbook v6 / policy v9 (Team Uzair default)

## Headline
- **Team Uzair**: Rs 8,320,277 (-17.9% vs Oct 1-26) · achievement 46% of pro-rated · enrollments 173 vs 212 · pending Rs 1,625,953  
  Same window earlier: Oct Rs 10,135,167 · Sep Rs 12,213,832 · Aug Rs 14,390,778 · Jul Rs 14,727,878 · Jun Rs 13,278,721

## Sanity checks
**Team Uzair**
- 1. Enrollment plausibility: 173 enrollments / 267 revenue rows = 65% — pass
- 2. Enrollments vs revenue direction: revenue x0.82, enrollments x0.82 — pass
- 3. Realisation per enrollment: Rs 48,094 in band — pass
- 5. Roll-up (teams = verticals = segment, revenue and enrollments): exact
**All segments**
- 4. Restatement check: company revenue matches to the rupee, enrollments −1; 18-19 Nov rows re-attributed (see below)
- 6. Formula errors: n/a (no xlsx in default policy)

## Data quality (whole workbook window)
- 8,663 revenue rows · Rs 46,103,064 · 1240 enrollments (1240 unique txn IDs) · negatives: 0
- Duplicate Transaction IDs: 62 IDs / 125 rows / Rs 5,424,730 (1 same-amount) — counted per split-transaction rule
- Convenience/Hardcopy rows: 10 / Rs 4,790 — included
- Text-formatted fees: 1 (Rs 23,777) — parsed and included
- Lead Details not Available → Direct: 0 row(s) / Rs 0
- Workbook last date: 2026-11-26 · history rows now 6,141

## NEW anomalies — questions for you
- Restatement **out of Team Uzair**: the 19 Nov Rs 55,800 that moved to Simran Kapoor (Corporate law - Anas) on the 23 Nov run is back with **Kanika Verma** (Changemakers). Team Uzair Nov 1-19 is −Rs 55,800 and −1 enrollment vs the last report. Which is correct? Default: follow the sheet.
- Restatement **inside Team Uzair** (total unchanged): Rs 52,561 and 1 enrollment on 18-19 Nov moved from **Neeraj Kumar Singh** (Corporate law - Anas) to **Pooja Sonaniya** (Corporate law - Jyoti).

## Still open (raised before, defaults applied)
- 1 fee value(s) stored as text (Rs 23,777) — parsed and INCLUDED per the Oct rule; ops may want to fix at source.
- 1 duplicate Transaction ID(s) carry the SAME amount on both rows — genuine two-course bookings or double entry? (counted per split-transaction rule)
- Removed team **Team Karman Kaur** (Team Karman Kaur) has Rs 52,135 in history that cannot be re-homed (no live roster team for its callers) — it is not reported.

## Files
- `reports/2026-11/MTD Report Nov 1-26 - Team Uzair.pdf`
- `data/revenue_history.csv` (updated)
