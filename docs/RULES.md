# MTD rules in force

The master playbook is `docs/playbook/project_instructions_v6.txt` (v6). On top of it:
`deliverable_policy_v9.txt`, `pdf_design_spec_v6.txt`, the `memory_*.txt` notes and the anomaly
logs. These carried over from the Cowork project unchanged. This file records what is in force
**now**, including changes made since.

## Definitions (unchanged)
- Revenue = `Fee paid`. Enrollment = `Enrollment` exactly "New enrollment" (v6).
- Window: days 1..N of the current month (N = yesterday) vs the same days of every prior month in
  history. Pro-rated target = TARGET × N/D. Achievement = revenue / pro-rated target.
- Caller = `Caller name (for ops) for enrollment link circulation`, matched by name. Blank caller
  → Direct / Bootcamp - Direct. Hierarchy is joined from that month's `Team Members` roster.
- Team alias map and removed-team re-homing: see `ALIAS` and the 09 Oct rule in `mtd/pipeline.py`
  (ID Calling - Uzair → Elite; Academic writing - Sana → US accounting closures - Sana;
  Elite - Trainee → Elite; community-manager team merges).
- Lead Details not Available with a blank caller → Direct (18 Sep 2026).
- Convenience/Hardcopy rows included. Split-transaction duplicate IDs are both counted.

## Changes / decisions recorded in this repo
- **04 Nov 2026: default deliverable = Team Uzair PDF only.** Sales Teams and Collection Teams
  PDFs are produced only when the user asks (user: "i just need 1 deliverable for team uzair").
  The pipeline still processes the whole workbook, so history stays complete for all teams.
- **04 Nov 2026: segment achievement counts target-carrying TEAMS only.** Revenue of a team with no
  current-month target (e.g. Changemakers in Nov) stays in MTD revenue but is excluded from
  achievement %, run-rate and the gap to target. Wording: "Achievement covers target-carrying
  teams only; no [Mon] target on the roster yet for [teams]". This matches the Nov 1-3 Cowork
  deliverables (the 19 Oct code worked at vertical level).
- **04 Nov 2026: text-formatted fees are parsed and INCLUDED** (Oct memory note: "Text-fee rows
  must be explicitly parsed"). They are listed in the brief every run. The Sep runs had dropped
  them, so this needs the user's confirmation.
- **04 Nov 2026: analysis covers at most 12 months** (rolling retention in the PDF design spec).
  Older months stay in `data/revenue_history.csv` until they fall outside the retention window.
- **04 Nov 2026: runs only on working days.** The user supplies each month's working schedule on
  the 1st, together with the sheet. The scheduled task's cron lists that month's working days
  (Nov 2026: 2-6, 10-14, 16-20, 23-30). The first run of a new month closes the previous month in
  history when its last day(s) fell on a week off (history only, no PDF). Manual
  "Run MTD analysis" works on any day.
- **10 Nov 2026: one report per month.** Each run replaces that month's earlier PDF, brief and summary
  in `reports/YYYY-MM/`; older versions remain only in git history. The month-close run builds the
  full-month PDF (e.g. Nov 1-30), which becomes that month's single kept report.
- **Automation**: 12:00 PM IST on working days. With no sheet registered for the month, or a sheet not
  updated to yesterday, the run stops and notifies the user (no partial report). Delivery goes to
  the Claude session (PDF), Gmail (brief + GitHub link) and the repo `reports/YYYY-MM/`.
  Anomalies use the defaults and are asked as questions in the brief.

## Open items carried from Cowork
- June 2026 enrollments in history are still on the old (overstated) definition. Upload the June
  2026 workbook to restate.
- Team Karman Kaur: Rs 52,135 of July history with no live team; not reported (removed-team rule).
- The `anomaly log oct.txt` from the Cowork project was corrupt in the uploaded archive and could
  not be recovered. The Oct decisions in `memory_Pipeline_And_Rules.txt` and in the code comments
  are preserved.
