# MTD Report Nov 1-16, 2026 — brief

Window: 1-16 Nov 2026 (last complete day; D = 30) · generated 17 Nov 2026 · playbook v6 / policy v9 (Team Uzair default)

## Headline
- **Team Uzair**: Rs 4,685,005 (-19.1% vs Oct 1-16) · achievement 42% of pro-rated · enrollments 92 vs 131 · pending Rs 1,437,304  
  Same window earlier: Oct Rs 5,792,111 · Sep Rs 6,106,930 · Aug Rs 7,558,964 · Jul Rs 7,901,662 · Jun Rs 7,576,411

## Sanity checks
**Team Uzair**
- 1. Enrollment plausibility: 92 enrollments / 142 revenue rows = 65% — pass
- 2. Enrollments vs revenue direction: revenue x0.81, enrollments x0.70 — pass
- 3. Realisation per enrollment: Rs 50,924 in band — pass
- 5. Roll-up (teams = verticals = segment, revenue and enrollments): exact
**All segments**
- 4. Restatement check: company revenue unchanged, enrollments +1; two rows re-attributed into Team Uzair (see below)
- 6. Formula errors: n/a (no xlsx in default policy)

## Data quality (whole workbook window)
- 5,086 revenue rows · Rs 19,652,410 · 782 enrollments (782 unique txn IDs) · negatives: 0
- Duplicate Transaction IDs: 17 IDs / 35 rows / Rs 1,463,144 (1 same-amount) — counted per split-transaction rule
- Convenience/Hardcopy rows: 5 / Rs 3,440 — included
- Text-formatted fees: 0 (Rs 0) — parsed and included
- Lead Details not Available → Direct: 0 row(s) / Rs 0
- Workbook last date: 2026-11-16 · history rows now 5,792

## NEW anomalies — questions for you
- Restatement **into Team Uzair** (company total unchanged): 13 Nov Rs 51,769 *Lead Details not Available* row is now **Akashdeep Singh** (US accounting closures - Sana, +1 enrollment); 15 Nov Rs 3,000 bootcamp booking moved from Bootcamp - Direct to **Pratishta Yadav** (Elite, +1 enrollment). Team Uzair Nov 1-15 is now **Rs 38,38,288** (was Rs 37,83,519), enrollments 82 (was 80). Applied.
- Roster: **Zeenat Javid** (Women ai, Team Anmol) now *Resigned*; Rs 1,00,000 target drops out (active targets Rs 4,50,00,000 / 101). Not Team Uzair.

## Still open (raised before, defaults applied)
- 1 duplicate Transaction ID(s) carry the SAME amount on both rows — genuine two-course bookings or double entry? (counted per split-transaction rule)
- Removed team **Team Karman Kaur** (Team Karman Kaur) has Rs 52,135 in history that cannot be re-homed (no live roster team for its callers) — it is not reported.

## Files
- `reports/2026-11/MTD Report Nov 1-16 - Team Uzair.pdf`
- `data/revenue_history.csv` (updated)
