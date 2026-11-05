"""Daily Sales Check settings and calendar. Standard library only (the schedule gate imports it
before dependencies are installed)."""
from __future__ import annotations

import calendar
import json
import os
from datetime import date, timedelta

from partwise.config import ROOT, load_month, sheet_id

with open(os.path.join(ROOT, "config", "dsc.json"), encoding="utf-8") as f:
    CFG = json.load(f)

TEAMS: list[str] = CFG["teams"]


def month_key(d: date) -> str:
    return f"{d.year}-{d.month:02d}"


def month_first(d: date) -> date:
    return d.replace(day=1)


def month_last(d: date) -> date:
    return d.replace(day=calendar.monthrange(d.year, d.month)[1])


def add_months(d: date, n: int) -> date:
    y, m = d.year, d.month + n
    while m < 1:
        y, m = y - 1, m + 12
    while m > 12:
        y, m = y + 1, m - 12
    return date(y, m, 1)


def working_days(month: str) -> list[date] | None:
    """Working dates of a month from config/months/<month>.json; None when the month file is missing."""
    cfg = load_month(month)
    if cfg is None or not cfg["working_dates"]:
        return None
    return cfg["working_dates"]


def default_working_days(month: str) -> list[date]:
    """Fallback for past months without a schedule: Monday to Saturday."""
    y, m = int(month[:4]), int(month[5:])
    n = calendar.monthrange(y, m)[1]
    return [date(y, m, d) for d in range(1, n + 1) if date(y, m, d).weekday() < 6]


def month_working_days(month: str) -> tuple[list[date], bool]:
    """(days, from_schedule)."""
    wd = working_days(month)
    return (wd, True) if wd else (default_working_days(month), False)


def previous_working_day(today: date) -> date:
    """Latest working day before today (checks this and last month's schedule)."""
    d = today - timedelta(days=1)
    for _ in range(40):
        wd, _ = month_working_days(month_key(d))
        if d in wd:
            return d
        d -= timedelta(days=1)
    return today - timedelta(days=1)


def sales_sheet_id(month: str) -> str | None:
    cfg = load_month(month)
    return cfg["sales_sheet_id"] if cfg and cfg.get("sales_sheet_id") else None


TARGETS_SHEET_ID = sheet_id(CFG["targets_sheet"])
