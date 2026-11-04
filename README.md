# daily_sales_scheduled_automation

Automated **MTD Revenue Analysis** report (Team Uzair by default). It runs every day at
**12:00 PM IST**, reads that month's "Sales Team Reports" Google Sheet, and produces the same PDF
as the Cowork project. It also keeps `data/revenue_history.csv` up to date.

| path | what |
|---|---|
| `RUNBOOK.md` | step-by-step procedure for each run (scheduled or "Run MTD analysis") |
| `docs/RULES.md` | rules in force and decisions since the Cowork project |
| `docs/playbook/` | original playbook, PDF design spec, deliverable policy, memory, anomaly logs |
| `mtd/` | pipeline (`pipeline.py` → `analysis.py` → `keypoints.py` → `build_pdf.py`) and orchestrator `run_mtd.py` |
| `config/monthly_sheets.json` | sheet registry: one Google Sheet per month (supply it on the 1st) |
| `data/revenue_history.csv` | revenue history (Jun 2026 → current month to date) |
| `reports/YYYY-MM/` | delivered PDFs and run briefs |

Local run (with a downloaded workbook):
```bash
pip install -r requirements.txt
python3 mtd/run_mtd.py run --workbook "November 2026- Sales Team Reports.xlsx" [--till 15] [--segments all]
```
