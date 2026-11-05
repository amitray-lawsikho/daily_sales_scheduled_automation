"""Does the Daily Sales Check run today? Standard library only.

Runs on the working days in config/months/<this month>.json (the same file Part Wise uses), around
12:00 IST, for data up to yesterday. No month file or a week off -> no run.

    python -m dsc.schedule                    # today, IST
    python -m dsc.schedule --today 2026-11-10
Prints 'run=true date=YYYY-MM-DD' or 'run=false reason=...'; also writes to $GITHUB_OUTPUT.
"""
from __future__ import annotations

import argparse
import os
from datetime import date, datetime, timedelta, timezone

from dsc.settings import month_key, working_days

IST = timezone(timedelta(hours=5, minutes=30))


def decide(today: date) -> dict:
    wd = working_days(month_key(today))
    if wd is None:
        return {"run": "false", "reason": f"no working days in config/months/{month_key(today)}.json"}
    if today not in wd:
        return {"run": "false", "reason": f"{today.isoformat()} is not a working day"}
    return {"run": "true", "date": (today - timedelta(days=1)).isoformat(), "reason": "working day"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--today", help="YYYY-MM-DD (default: today in IST)")
    a = ap.parse_args()
    today = date.fromisoformat(a.today) if a.today else datetime.now(IST).date()
    out = decide(today)
    print(f"{today.isoformat()}: " + " ".join(f"{k}={v}" for k, v in out.items()))
    gh = os.environ.get("GITHUB_OUTPUT")
    if gh:
        with open(gh, "a", encoding="utf-8") as f:
            for k, v in out.items():
                f.write(f"{k}={v}\n")


if __name__ == "__main__":
    main()
