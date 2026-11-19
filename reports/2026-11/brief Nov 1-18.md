# MTD Report Nov 1-18, 2026 — brief

Window: 1-18 Nov 2026 (last complete day; D = 30) · generated 19 Nov 2026 · playbook v6 / policy v9 (Team Uzair default)

## Headline
- **Team Uzair**: Rs 5,301,993 (-14.1% vs Oct 1-18) · achievement 42% of pro-rated · enrollments 109 vs 136 · pending Rs 1,511,304  
  Same window earlier: Oct Rs 6,172,508 · Sep Rs 7,614,394 · Aug Rs 9,226,857 · Jul Rs 8,921,510 · Jun Rs 8,713,004

## Sanity checks
**Team Uzair**
- 1. Enrollment plausibility: 109 enrollments / 167 revenue rows = 65% — pass
- 2. Enrollments vs revenue direction: revenue x0.86, enrollments x0.80 — pass
- 3. Realisation per enrollment: Rs 48,642 in band — pass
- 5. Roll-up (teams = verticals = segment, revenue and enrollments): exact
**All segments**
- 4. Restatement check: none — days already in history match the workbook to the rupee
- 6. Formula errors: n/a (no xlsx in default policy)

## Data quality (whole workbook window)
- 5,875 revenue rows · Rs 27,509,730 · 859 enrollments (859 unique txn IDs) · negatives: 0
- Duplicate Transaction IDs: 30 IDs / 61 rows / Rs 2,613,496 (1 same-amount) — counted per split-transaction rule
- Convenience/Hardcopy rows: 7 / Rs 3,980 — included
- Text-formatted fees: 0 (Rs 0) — parsed and included
- Lead Details not Available → Direct: 4 row(s) / Rs 183,345
- Workbook last date: 2026-11-18 · history rows now 5,867

## NEW anomalies — questions for you
- Roster: Team Anmol targets +Rs 1,00,000 (one new target holder; active targets Rs 4,48,00,000 / 101). A new vertical **Siddhant** appears on the roster (no target, no revenue) — new vertical or to be mapped? Team Uzair unchanged at Rs 2,08,00,000.
- 18 Nov: **4 rows / Rs 1,83,345** have Team Name *Lead Details not Available* and no caller — counted as Direct (outside all segments) per the standing rule. If ops attributes them later (often within a day or two), the next run will restate them into the right team automatically.

## Still open (raised before, defaults applied)
- 1 duplicate Transaction ID(s) carry the SAME amount on both rows — genuine two-course bookings or double entry? (counted per split-transaction rule)
- Removed team **Team Karman Kaur** (Team Karman Kaur) has Rs 52,135 in history that cannot be re-homed (no live roster team for its callers) — it is not reported.

## Files
- `reports/2026-11/MTD Report Nov 1-18 - Team Uzair.pdf`
- `data/revenue_history.csv` (updated)
