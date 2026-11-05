"""Settings and month files. Standard library only: the schedule gate imports this before any
dependency is installed."""
from __future__ import annotations

import json
import os
import re
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MONTHS_DIR = os.path.join(ROOT, "config", "months")

with open(os.path.join(ROOT, "config", "settings.json"), encoding="utf-8") as f:
    SETTINGS = json.load(f)


def sheet_id(value: str) -> str:
    """Accept a bare id or a full docs.google.com link."""
    m = re.search(r"/d/([A-Za-z0-9_-]{20,})", value or "")
    return m.group(1) if m else (value or "").strip()


def parse_days(month: str, spec: list) -> list[date]:
    """["2-6", "10-14", 16, "23-30"] -> dates of that month."""
    y, m = int(month[:4]), int(month[5:])
    out = set()
    for item in spec:
        s = str(item).strip()
        if "-" in s:
            a, b = (int(x) for x in s.split("-", 1))
            out.update(range(a, b + 1))
        elif s:
            out.add(int(s))
    return sorted(date(y, m, d) for d in out)


def load_month(month: str) -> dict | None:
    """config/months/YYYY-MM.json, or None when Amit has not provided that month (then nothing runs)."""
    path = os.path.join(MONTHS_DIR, f"{month}.json")
    if not os.path.isfile(path):
        return None
    with open(path, encoding="utf-8") as f:
        cfg = json.load(f)
    cfg["month"] = month
    cfg["sales_sheet_id"] = sheet_id(cfg.get("sales_sheet", ""))
    if cfg.get("uzair_sheet"):
        cfg["uzair_sheet_id"] = sheet_id(cfg["uzair_sheet"])
    cfg["working_dates"] = parse_days(month, cfg.get("working_days", []))
    return cfg
