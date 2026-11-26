# MTD Report Nov 1-25, 2026 — brief

Window: 1-25 Nov 2026 (last complete day; D = 30) · generated 26 Nov 2026 · playbook v6 / policy v9 (Team Uzair default)

## Headline
- **Team Uzair**: Rs 7,931,992 (-16.4% vs Oct 1-25) · achievement 46% of pro-rated · enrollments 159 vs 203 · pending Rs 1,187,953  
  Same window earlier: Oct Rs 9,483,902 · Sep Rs 11,150,659 · Aug Rs 13,359,116 · Jul Rs 13,885,719 · Jun Rs 12,605,170

## Sanity checks
**Team Uzair**
- 1. Enrollment plausibility: 159 enrollments / 251 revenue rows = 63% — pass
- 2. Enrollments vs revenue direction: revenue x0.84, enrollments x0.78 — pass
- 3. Realisation per enrollment: Rs 49,887 in band — pass
- 5. Roll-up (teams = verticals = segment, revenue and enrollments): exact
**All segments**
- 4. Restatement check: totals match to the rupee; 24 Nov rows re-attributed (see below)
- 6. Formula errors: n/a (no xlsx in default policy)

## Data quality (whole workbook window)
- 8,355 revenue rows · Rs 43,421,157 · 1212 enrollments (1212 unique txn IDs) · negatives: 0
- Duplicate Transaction IDs: 59 IDs / 119 rows / Rs 5,166,753 (1 same-amount) — counted per split-transaction rule
- Convenience/Hardcopy rows: 9 / Rs 4,520 — included
- Text-formatted fees: 1 (Rs 23,777) — parsed and included
- Lead Details not Available → Direct: 0 row(s) / Rs 0
- Workbook last date: 2026-11-25 · history rows now 6,100

## NEW anomalies — questions for you
- Restatement of 24 Nov (company totals unchanged; **Team Uzair total unchanged**): Rs 40,568 moved from **Swati Singh** to **Swalpi Singh** (both US accounting closures - Sana) — Swati Singh is now a zero-revenue target holder. The two *Lead Details not Available* rows (Rs 37,877) are now Direct (Rs 23,777, the text-formatted fee) and Prawal Singh (Changemakers, Rs 14,100).
- Roster: 4 rows added (254 → 258), **no target change** (Rs 4,43,00,000 / 100; Team Uzair Rs 2,08,00,000).

## Still open (raised before, defaults applied)
- 1 fee value(s) stored as text (Rs 23,777) — parsed and INCLUDED per the Oct rule; ops may want to fix at source.
- 1 duplicate Transaction ID(s) carry the SAME amount on both rows — genuine two-course bookings or double entry? (counted per split-transaction rule)
- Removed team **Team Karman Kaur** (Team Karman Kaur) has Rs 52,135 in history that cannot be re-homed (no live roster team for its callers) — it is not reported.

## Files
- `reports/2026-11/MTD Report Nov 1-25 - Team Uzair.pdf`
- `data/revenue_history.csv` (updated)
