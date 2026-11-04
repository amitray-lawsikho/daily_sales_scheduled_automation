# MTD Revenue Analysis (LawSikho / Skill Arbitrage)

Daily month-to-date revenue report for the Sales & Operations team, automated from the Cowork
project "MTD Revenue Analysis".

- **Any MTD request** ("Run MTD analysis", "run till 15th", the 12:00 scheduled prompt, or a new
  month's sheet link): follow `RUNBOOK.md` exactly.
- Rules in force: `docs/RULES.md`. The original playbook, design spec and policies are in `docs/playbook/`.
  Ask the user before deviating from any rule.
- Default deliverable: **Team Uzair PDF only**. Other segments only on request.
- Data: `data/revenue_history.csv` (per day × caller × team × vertical). Never drop a month inside
  the 12-month window. Only the current month (or an explicitly re-uploaded month) is rebuilt.
- The monthly sheet registry and working-day calendar are in `config/monthly_sheets.json`; the scheduled task fires only on working days (RUNBOOK section C).
- The monthly sheet registry is `config/monthly_sheets.json`. With no sheet registered for the month, do not produce deliverables.
- Keep in-chat output brief. The analysis lives in the PDF.
- The workbook contains customer PII (names, phones, emails). Never commit the workbook or
  anything from `.work/`. Commit only `data/`, `reports/` and `config/`.
