"""LeadSquared (read-only): the Zipteams call data that Zipteams posts into LSQ as a custom activity.

Not mapped yet (5 Nov 2026): the activity code and field names were not reachable from the build
session. Until config "zipteams.activity_event" is set, every run lists the LSQ activity types whose
name mentions the keywords in "zipteams.discover" (with their codes and fields) in the run notes,
so the mapping can be filled in. Once set, activities are read for the report window and counted
per caller (and per level when "level_field" is set).

LSQ API used (both read-only):
  GET  /v2/ProspectActivity.svc/ActivityTypes.Get
  POST /v2/ProspectActivity.svc/CustomActivity/RetrieveByActivityEvent
"""
from __future__ import annotations

import os
from datetime import date, datetime, timedelta

import pandas as pd
import requests

from dsc.settings import CFG

COLS = ["date", "caller", "level", "prospect_id"]


class LSQ:
    def __init__(self):
        host = os.environ.get("LSQ_HOST", "").strip()
        self.ak = os.environ.get("LSQ_ACCESS_KEY", "").strip()
        self.sk = os.environ.get("LSQ_SECRET_KEY", "").strip()
        if not (host and self.ak and self.sk):
            raise RuntimeError("LSQ_HOST / LSQ_ACCESS_KEY / LSQ_SECRET_KEY not set")
        host = host.replace("https://", "").replace("http://", "").split("/")[0]
        self.base = f"https://{host}/v2/"
        self.s = requests.Session()

    def _auth(self):
        return {"accessKey": self.ak, "secretKey": self.sk}

    def activity_types(self) -> list[dict]:
        r = self.s.get(self.base + "ProspectActivity.svc/ActivityTypes.Get", params=self._auth(), timeout=60)
        r.raise_for_status()
        return r.json()

    def activities(self, event: int, lo: datetime, hi: datetime) -> list[dict]:
        out, page = [], 1
        while True:
            body = {"Parameter": {"FromDate": lo.strftime("%Y-%m-%d %H:%M:%S"), "ToDate": hi.strftime("%Y-%m-%d %H:%M:%S"),
                                  "ActivityEvent": int(event), "RemoveEmptyValue": True},
                    "Paging": {"PageIndex": page, "PageSize": 1000},
                    "Sorting": {"ColumnName": "CreatedOn", "Direction": "1"}}
            r = self.s.post(self.base + "ProspectActivity.svc/CustomActivity/RetrieveByActivityEvent",
                            params=self._auth(), json=body, timeout=120)
            r.raise_for_status()
            js = r.json()
            rows = js.get("List") or js.get("ProspectActivities") or (js if isinstance(js, list) else [])
            out += rows
            if len(rows) < 1000 or page >= 200:
                return out
            page += 1


def _field(row: dict, name: str):
    if name in row:
        return row[name]
    for f in row.get("Fields") or row.get("ActivityFields") or []:
        if f.get("SchemaName") == name or f.get("Key") == name or f.get("DisplayName") == name:
            return f.get("Value")
    return None


def load_zipteams(lo: date, hi: date, fresh: dict) -> pd.DataFrame:
    """Zipteams activities per caller-day from LSQ, or an empty frame with a note in fresh['zipteams']."""
    z = CFG.get("zipteams", {})
    try:
        api = LSQ()
    except RuntimeError as e:
        fresh["zipteams"] = f"not read: {e}"
        return pd.DataFrame(columns=COLS)
    try:
        if not z.get("activity_event"):
            words = [w.lower() for w in z.get("discover", ["zip"])]
            hits = [t for t in api.activity_types()
                    if any(w in str(t.get("DisplayName", "")).lower() or w in str(t.get("Name", "")).lower() for w in words)]
            fresh["zipteams"] = ("not mapped yet. LSQ activity types matching "
                                 f"{words}: " + ("; ".join(f"{t.get('DisplayName')} (code {t.get('ActivityEvent')})" for t in hits)
                                                 or "none found") +
                                 ". Set zipteams.activity_event (and level_field) in config/dsc.json.")
            return pd.DataFrame(columns=COLS)
        # LSQ works in UTC
        rows = api.activities(z["activity_event"], datetime.combine(lo, datetime.min.time()) - timedelta(hours=5, minutes=30),
                              datetime.combine(hi, datetime.max.time()) - timedelta(hours=5, minutes=30))
    except requests.RequestException as e:
        fresh["zipteams"] = f"LSQ request failed: {str(e)[:200]}"
        return pd.DataFrame(columns=COLS)
    if not rows:
        fresh["zipteams"] = "mapped; no activities in the window"
        return pd.DataFrame(columns=COLS)
    if z.get("sample_fields_in_notes", True):
        fresh["zipteams_fields"] = sorted({k for r in rows[:20] for k in r.keys()})[:60]
    owner = z.get("owner_field", "CreatedByName")
    level = z.get("level_field")
    df = pd.DataFrame({
        "date": pd.to_datetime([r.get("CreatedOn") for r in rows], errors="coerce", utc=True)
                  .tz_convert("Asia/Kolkata").strftime("%Y-%m-%d"),
        "caller": [str(_field(r, owner) or "").strip() for r in rows],
        "level": [str(_field(r, level) or "").strip().title() if level else "" for r in rows],
        "prospect_id": [r.get("RelatedProspectId") or r.get("ProspectId") for r in rows]})
    fresh["zipteams"] = f"{len(df):,} activities read from LSQ (event {z['activity_event']})"
    return df
