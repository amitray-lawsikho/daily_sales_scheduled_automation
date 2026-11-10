# MTD Report Nov 1-9, 2026 — brief

Window: 1-9 Nov 2026 (last complete day; D = 30) · generated 10 Nov 2026 · playbook v6 / policy v9 (Team Uzair default)

## Headline
- **Team Uzair**: Rs 2,307,426 (-14.4% vs Oct 1-9) · achievement 37% of pro-rated · enrollments 49 vs 71 · pending Rs 1,317,704  
  Same window earlier: Oct Rs 2,695,554 · Sep Rs 3,148,146 · Aug Rs 3,452,835 · Jul Rs 3,754,859 · Jun Rs 3,058,482

## Sanity checks
**Team Uzair**
- 1. Enrollment plausibility: 49 enrollments / 71 revenue rows = 69% — pass
- 2. Enrollments vs revenue direction: revenue x0.86, enrollments x0.69 — pass
- 3. Realisation per enrollment: Rs 47,090 in band — pass
- 5. Roll-up (teams = verticals = segment, revenue and enrollments): exact
**All segments**
- 4. Restatement check: Nov 1-8 totals match to the rupee and enrollment; caller moves on 5 Nov listed below
- 6. Formula errors: n/a (no xlsx in default policy)

## Data quality (whole workbook window)
- 2,484 revenue rows · Rs 9,761,176 · 247 enrollments (247 unique txn IDs) · negatives: 0
- Duplicate Transaction IDs: 9 IDs / 19 rows / Rs 808,596 (1 same-amount) — counted per split-transaction rule
- Convenience/Hardcopy rows: 3 / Rs 910 — included
- Text-formatted fees: 0 (Rs 0) — parsed and included
- Lead Details not Available → Direct: 0 row(s) / Rs 0
- Workbook last date: 2026-11-09 · history rows now 5,616

## NEW anomalies — questions for you
- Same-amount duplicate Transaction ID **631099243254** (6 Nov, Rahul Kumar, SA - Aditya, Collection): Rs 43,625 twice, once as a *Community Collections - balance payment* (Independent Director community) and once as a *New enrollment* (iHUB IIT Roorkee Corporate Governance/ESG certification). Genuine two-course booking or a double entry? Counted twice by default (Rs 87,250). Not Team Uzair.
- Restatement of 5 Nov (totals unchanged; Team Uzair unchanged): Rs 13,050 moved from Yamini Hitesh Billore to Himanshi (both Changemakers); a Rs 2,000 Direct row with its enrollment is now attributed to Syed Yusra (CD - Community).
- Roster: active targets Rs 4,52,33,000 / 101 holders → Rs 4,56,33,000 / 103 holders (+Rs 4,00,000, 2 new holders, outside Team Uzair; Team Uzair still Rs 2,08,00,000). Confirm final?

## Still open (raised before, defaults applied)
- Removed team **Team Karman Kaur** (Team Karman Kaur) has Rs 52,135 in history that cannot be re-homed (no live roster team for its callers) — it is not reported.

## Files
- `reports/2026-11/MTD Report Nov 1-9 - Team Uzair.pdf`
- `data/revenue_history.csv` (updated)
