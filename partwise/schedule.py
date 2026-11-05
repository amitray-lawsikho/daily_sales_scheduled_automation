"""Decide whether today's 12:00 IST run should happen. Standard library only.

Rules (Amit, 5 Nov 2026):
  * Nothing runs for a month until config/months/YYYY-MM.json exists (sales sheet + working days).
  * The report runs only on that month's working days and covers day 1 to yesterday.
  * On the 1st of the next month it runs once more to close the previous month (1 to last day),
    so the final working day is included even before next month's file is added.

    python -m partwise.schedule                 # today, IST
    python -m partwise.schedule --today 2026-11-10
Prints 'run=true month=YYYY-MM till=N' or 'run=false reason=...'; writes the same to $GITHUB_OUTPUT.
"""
from __future__ import annotations

import argparse
import os
from datetime import date, datetime, timedelta, timezone

from partwise.config import load_month

IST = timezone(timedelta(hours=5, minutes=30))


def decide(today: date) -> dict:
    y = today - timedelta(days=1)
    report_month = f"{y.year}-{y.month:02d}"
    cfg = load_month(report_month)
    if cfg is None:
        return {"run": "false", "reason": f"no config/months/{report_month}.json"}
    if today.month != y.month:
        return {"run": "true", "month": report_month, "till": str(y.day), "reason": "month close"}
    if today not in cfg["working_dates"]:
        return {"run": "false", "reason": f"{today.isoformat()} is not a working day"}
    return {"run": "true", "month": report_month, "till": str(y.day), "reason": "working day"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--today", help="YYYY-MM-DD (default: today in IST)")
    a = ap.parse_args()
    today = date.fromisoformat(a.today) if a.today else datetime.now(IST).date()
    out = decide(today)
    line = " ".join(f"{k}={v}" for k, v in out.items())
    print(f"{today.isoformat()}: {line}")
    gh = os.environ.get("GITHUB_OUTPUT")
    if gh:
        with open(gh, "a", encoding="utf-8") as f:
            for k, v in out.items():
                f.write(f"{k}={v}\n")


if __name__ == "__main__":
    main()
