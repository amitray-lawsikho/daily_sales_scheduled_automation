# MTD Report Nov 1-19, 2026 — brief

Window: 1-19 Nov 2026 (last complete day; D = 30) · generated 20 Nov 2026 · playbook v6 / policy v9 (Team Uzair default)

## Headline
- **Team Uzair**: Rs 5,620,923 (-14.9% vs Oct 1-19) · achievement 43% of pro-rated · enrollments 115 vs 144 · pending Rs 1,612,604  
  Same window earlier: Oct Rs 6,608,175 · Sep Rs 7,874,203 · Aug Rs 10,051,608 · Jul Rs 9,280,218 · Jun Rs 9,388,098

## Sanity checks
**Team Uzair**
- 1. Enrollment plausibility: 115 enrollments / 179 revenue rows = 64% — pass
- 2. Enrollments vs revenue direction: revenue x0.85, enrollments x0.80 — pass
- 3. Realisation per enrollment: Rs 48,878 in band — pass
- 5. Roll-up (teams = verticals = segment, revenue and enrollments): exact
**All segments**
- 4. Restatement check: revenue matches to the rupee; 18 Nov rows re-attributed / enrollment flags added outside Team Uzair (see below)
- 6. Formula errors: n/a (no xlsx in default policy)

## Data quality (whole workbook window)
- 6,225 revenue rows · Rs 30,444,991 · 892 enrollments (892 unique txn IDs) · negatives: 0
- Duplicate Transaction IDs: 40 IDs / 81 rows / Rs 3,537,452 (1 same-amount) — counted per split-transaction rule
- Convenience/Hardcopy rows: 8 / Rs 4,250 — included
- Text-formatted fees: 0 (Rs 0) — parsed and included
- Lead Details not Available → Direct: 7 row(s) / Rs 362,296
- Workbook last date: 2026-11-19 · history rows now 5,901

## NEW anomalies — questions for you
- Restatement of 18 Nov (**Team Uzair unchanged**): the 4 *Lead Details not Available* rows (Rs 1,83,345) are now attributed — Abhinav Lorenzo & Anurita Shukla (SA - Shivam), Rahul Kumar (SA - Aditya), Aishwarya Popli (US accounting closures - Deepanshi); plus 5 extra *New enrollment* flags on existing 18 Nov rows in Collection (Prawal Singh 2, Shikha Chahar 1, Chandana Shivanand 1, Anurita Shukla 1). Company enrollments +6, revenue unchanged.
- Now **7 rows / Rs 3,62,296** sit under *Lead Details not Available* (counted as Direct) — expected to be attributed by ops in the next day or two; the next run restates them automatically.

## Still open (raised before, defaults applied)
- 1 duplicate Transaction ID(s) carry the SAME amount on both rows — genuine two-course bookings or double entry? (counted per split-transaction rule)
- Removed team **Team Karman Kaur** (Team Karman Kaur) has Rs 52,135 in history that cannot be re-homed (no live roster team for its callers) — it is not reported.

## Files
- `reports/2026-11/MTD Report Nov 1-19 - Team Uzair.pdf`
- `data/revenue_history.csv` (updated)
