# MTD Report Nov 1-22, 2026 — brief

Window: 1-22 Nov 2026 (last complete day; D = 30) · generated 23 Nov 2026 · playbook v6 / policy v9 (Team Uzair default)

## Headline
- **Team Uzair**: Rs 6,477,383 (-21.8% vs Oct 1-22) · achievement 42% of pro-rated · enrollments 132 vs 180 · pending Rs 1,619,355  
  Same window earlier: Oct Rs 8,287,758 · Sep Rs 9,530,053 · Aug Rs 11,825,774 · Jul Rs 11,641,203 · Jun Rs 10,313,382

## Sanity checks
**Team Uzair**
- 1. Enrollment plausibility: 132 enrollments / 205 revenue rows = 64% — pass
- 2. Enrollments vs revenue direction: revenue x0.78, enrollments x0.73 — pass
- 3. Realisation per enrollment: Rs 49,071 in band — pass
- 5. Roll-up (teams = verticals = segment, revenue and enrollments): exact
**All segments**
- 4. Restatement check: company totals match to the rupee and enrollment; 17-19 Nov rows re-attributed (one into Team Uzair, see below)
- 6. Formula errors: n/a (no xlsx in default policy)

## Data quality (whole workbook window)
- 7,271 revenue rows · Rs 36,295,617 · 1102 enrollments (1102 unique txn IDs) · negatives: 0
- Duplicate Transaction IDs: 52 IDs / 105 rows / Rs 4,565,740 (1 same-amount) — counted per split-transaction rule
- Convenience/Hardcopy rows: 8 / Rs 4,250 — included
- Text-formatted fees: 0 (Rs 0) — parsed and included
- Lead Details not Available → Direct: 0 row(s) / Rs 0
- Workbook last date: 2026-11-22 · history rows now 5,984

## NEW anomalies — questions for you
- Restatement **into Team Uzair**: 19 Nov Rs 55,800 moved from Kanika Verma (Changemakers) to **Simran Kapoor** (Corporate law - Anas), +1 enrollment. Team Uzair Nov 1-19 is now Rs 56,76,723 (was Rs 56,20,923). Applied.
- Other 17-19 Nov moves (company revenue unchanged; outside Team Uzair): the 19 Nov *Lead Details not Available* rows (Rs 3,62,296) are now attributed to Dibya Shankar Jha (SA - Shivam), Rahul Kumar & Shweta Pal (SA - Aditya), Akanksha Anand (Women ai); Rs 75,420 moved Yashita Agarwal (Deepanshi) → Yashika Bajpai (Women ai); enrollment flags shifted (net 0).

## Still open (raised before, defaults applied)
- 1 duplicate Transaction ID(s) carry the SAME amount on both rows — genuine two-course bookings or double entry? (counted per split-transaction rule)
- Removed team **Team Karman Kaur** (Team Karman Kaur) has Rs 52,135 in history that cannot be re-homed (no live roster team for its callers) — it is not reported.

## Files
- `reports/2026-11/MTD Report Nov 1-22 - Team Uzair.pdf`
- `data/revenue_history.csv` (updated)
