"""Shared definitions for the part-wise funnel analysis (ported unchanged from the cowork project)."""
from __future__ import annotations

import calendar

import numpy as np
import pandas as pd

TARGET_VERTICALS = ["Team Uzair", "Team Deepanshi", "Team Darshan"]
UZAIR = "Team Uzair"           # its stages come from its own workbook, not the CSV
CONNECT_SECONDS = 40           # longest call >= this = connected; below = DNP
PERIODS = [("P1", 1, 10), ("P2", 11, 20), ("P3", 21, 31)]
STAGES = {"Discovery Call Done": "discovery",
          "Roadmap Done": "roadmap",
          "Follow Up For Closure": "followup"}
STAGE_KEYS = ["discovery", "roadmap", "followup"]
GRAINS = {"caller": ["vertical", "team", "caller"],
          "team": ["vertical", "team"],
          "vertical": ["vertical"],
          "all": []}


def norm_stage(s):
    """LSQ sometimes emits 'Roadmap\\xa0Done' with a non-breaking space (4,712 of August 2026's
    roadmap rows). Fold every kind of whitespace to a single space so those rows map correctly."""
    return (pd.Series(s).astype("string").fillna("")
            .str.replace("\xa0", " ", regex=False)
            .str.replace(r"\s+", " ", regex=True).str.strip())


def periods_for(month):
    eom = calendar.monthrange(int(month[:4]), int(month[5:]))[1]
    return [(n, lo, min(hi, eom)) for n, lo, hi in PERIODS]


def period_of(day, month):
    for n, lo, hi in periods_for(month):
        if lo <= day <= hi:
            return n
    return None


def norm_phone(s):
    """Last 10 digits, so 9052045245.0 and '+91 90520 45245' match.
    A float-typed column yields '918921521876.0'; the trailing '.0' MUST be cut before stripping
    non-digits, or the 0 becomes a digit and every number shifts (bug found 4 Oct 2026)."""
    s = pd.Series(s)
    if pd.api.types.is_float_dtype(s):
        s = s.map(lambda v: None if pd.isna(v) else f"{v:.0f}")
    return (s.astype("string").fillna("")
            .str.strip().str.replace(r"\.0+$", "", regex=True)
            .str.replace(r"\D", "", regex=True).str[-10:])


def to_dt(s):
    """Dates from any source: real datetimes (xlsx), Google Sheets serial numbers, ISO text
    ('2026-11-02') or Indian day-first text ('02/11/2026 10:16:16')."""
    s = pd.Series(s)
    if pd.api.types.is_datetime64_any_dtype(s):
        return s.dt.tz_localize(None) if getattr(s.dt, "tz", None) is not None else s
    out = pd.Series(pd.NaT, index=s.index, dtype="datetime64[ns]")
    num = pd.to_numeric(s, errors="coerce")
    isnum = num.notna() & num.between(20000, 80000)        # 1954..2119 as a sheet serial
    out[isnum] = pd.to_datetime(num[isnum], unit="D", origin="1899-12-30")
    rest = s[~isnum & s.notna()]
    if len(rest):
        if pd.api.types.is_object_dtype(rest) and rest.map(lambda v: hasattr(v, "year")).all():
            out[rest.index] = pd.to_datetime(rest, errors="coerce")
        else:
            txt = rest.astype(str).str.strip()
            iso = txt.str.match(r"^\d{4}-\d{2}-\d{2}")
            out[txt[iso].index] = pd.to_datetime(txt[iso].str[:19], errors="coerce", format="mixed")
            other = txt[~iso]
            if len(other):
                out[other.index] = pd.to_datetime(other, errors="coerce", dayfirst=True, format="mixed")
    return out


def roster_frame(tm: pd.DataFrame) -> pd.DataFrame:
    """Everyone in Team Members. Leavers are kept so month totals stay complete; the caller
    table tags them with their status."""
    tm = tm.dropna(subset=["Caller Name"]).copy()
    tm["Caller Name"] = tm["Caller Name"].astype(str).str.strip()
    tm = tm[tm["Caller Name"] != ""]
    # a blank Status cell (seen 11 Nov 2026) is kept as blank, ranked after Active rows, and never crashes
    tm["Status"] = tm["Status"].astype("string").str.strip().fillna("")
    tm["_r"] = (tm["Status"] != "Active").astype(int)
    tm = tm.sort_values("_r", kind="stable").drop_duplicates("Caller Name").set_index("Caller Name")
    for c in ("Team Name", "Vertical"):
        tm[c] = tm[c].replace("", np.nan)
    return tm[["Team Name", "Vertical", "Status"]]


def decorate(df, r, col="caller"):
    out = df.copy()
    out["vertical"] = out[col].map(r["Vertical"])
    # a roster row with a vertical but a blank Team Name (Pranjal Sharma, 19 Oct 2026) would
    # otherwise vanish from the team/caller tables while still counting in the vertical total
    out["team"] = out[col].map(r["Team Name"]).fillna("(no team)")
    return out.dropna(subset=["vertical"])
