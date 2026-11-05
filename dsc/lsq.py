"""LeadSquared (read-only). API use follows the proven client of Amit's sales_automation_01 project.

1. Current stage and owner of the check-5 leads (Amit, 5 Nov 2026: follow-ups since moved to Not Interested /
   May buy later must not be listed):
     GET LeadManagement.svc/Leads.GetById?id=<Prospect ID>              (Prospect ID from the Team Uzair LSQ sheet)
     GET LeadManagement.svc/RetrieveLeadByPhoneNumber?phone=<10 digits>   (the rest)
   Fields ProspectStage, OwnerIdName, FirstName, LastName, ModifiedOn.
2. Zipteams notes = activity 237; intent in mx_Custom_1 (HIGH / MODERATE / NEUTRAL / LOW / NOT_AVAILABLE).
     POST ProspectActivity.svc/CustomActivity/RetrieveByActivityEvent
   The API filters on ModifiedOn, so each day is read with a margin and kept by CreatedOn; a window that does not
   fit in one page is cut into smaller windows (paging a large result skips rows - found 5 Oct 2026).

Load: LSQ allows 30 requests per 5 s for the whole account, shared with diallers and Zipteams. This module
sends one request at a time (about 2-3 a second), the bulk activity read at most once every 2.5 s, and stops
each part at a time budget (config "lsq_budget_minutes") so the 12:00 report is never held up.
"""
from __future__ import annotations

import os
import time
from datetime import date, datetime, timedelta, timezone

import pandas as pd
import requests

from dsc.settings import CFG

IST = timezone(timedelta(hours=5, minutes=30))
STATUS_COLS = ["phone", "prospect_id", "lsq_stage", "lsq_owner", "lsq_name", "how"]
ZIP_COLS = ["date", "prospect_id", "level", "created_ist"]


class LSQ:
    GAP, BULK_GAP = 0.35, 2.5

    def __init__(self):
        host = os.environ.get("LSQ_HOST", "").strip()
        self.ak = os.environ.get("LSQ_ACCESS_KEY", "").strip()
        self.sk = os.environ.get("LSQ_SECRET_KEY", "").strip()
        if not (host and self.ak and self.sk):
            raise RuntimeError("LSQ_HOST / LSQ_ACCESS_KEY / LSQ_SECRET_KEY not set")
        host = host.replace("https://", "").replace("http://", "").split("/")[0]
        self.base = f"https://{host}/v2/"
        self.s = requests.Session()
        self._last = {"x": 0.0, "bulk": 0.0}

    def _call(self, method: str, path: str, params: dict | None = None, json=None, bulk=False):
        """One request at a time, spaced out; retries 429 / 5xx (not LSQ's 500 validation errors)."""
        q = {"accessKey": self.ak, "secretKey": self.sk, **(params or {})}
        kind = "bulk" if bulk else "x"
        r = None
        for attempt in range(4):
            wait = self._last[kind] + (self.BULK_GAP if bulk else self.GAP) - time.time()
            if wait > 0:
                time.sleep(wait)
            try:
                r = self.s.request(method, self.base + path, params=q, json=json, timeout=60)
            except requests.RequestException as e:
                self._last[kind] = time.time()
                if attempt == 3:   # never let the keys reach a log
                    raise requests.RequestException(str(e).replace(self.ak, "***").replace(self.sk, "***")) from None
                time.sleep(2 ** attempt)
                continue
            self._last[kind] = time.time()
            if r.status_code == 429 or (r.status_code >= 500 and '"Status":"Error"' not in r.text.replace(" ", "")):
                time.sleep(float(r.headers.get("Retry-After") or 2 ** (attempt + 1)))
                continue
            break
        if r is None or r.status_code >= 300:
            code = r.status_code if r is not None else "-"
            raise requests.RequestException(f"{method} {path} -> HTTP {code}: {(r.text if r is not None else '')[:200]}")
        return r.json() if r.content else None

    # leads
    def lead_by_id(self, pid: str) -> dict | None:
        d = self._call("GET", "LeadManagement.svc/Leads.GetById", {"id": pid})
        return d[0] if d else None

    def leads_by_phone(self, phone: str) -> list[dict]:
        return self._call("GET", "LeadManagement.svc/RetrieveLeadByPhoneNumber", {"phone": phone}) or []

    # activities
    def _window(self, event: int, lo: datetime, hi: datetime, page=1000) -> list[dict]:
        fmt = lambda d: d.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        d = self._call("POST", "ProspectActivity.svc/CustomActivity/RetrieveByActivityEvent", bulk=True,
                       json={"Parameter": {"FromDate": fmt(lo), "ToDate": fmt(hi), "ActivityEvent": int(event)},
                             "Paging": {"PageIndex": 1, "PageSize": page}}) or {}
        rows = d.get("List") or []
        total = max(int(d.get("RecordCount") or 0), len(rows))
        secs = int((hi - lo).total_seconds())
        if total < page or secs < 2:
            return rows
        pieces = min(secs, -(-total * 3 // (page * 2)))
        cuts = [lo + timedelta(seconds=secs * k // pieces) for k in range(pieces)] + [hi]
        return [x for a, b in zip(cuts, cuts[1:]) for x in self._window(event, a, b, page)]

    def activities_created(self, event: int, lo: datetime, hi: datetime, margin=timedelta(days=1),
                           budget_s: float | None = None) -> tuple[list[dict], datetime]:
        """Activities CREATED in [lo, hi] (the filter is on ModifiedOn: read to hi + margin, keep by CreatedOn).
        Newest day first; stops at the time budget. Returns (rows, earliest time covered)."""
        stop = min(hi + margin, datetime.now(timezone.utc))
        seen, out, t0 = set(), [], time.time()
        end = stop
        while end > lo:
            if budget_s and time.time() - t0 > budget_s:
                break
            day = max(end - timedelta(days=1), lo)
            for a in self._window(event, day, end):
                key = a.get("ProspectActivityId") or a.get("Id")
                t = utc(a.get("CreatedOn"))
                if key in seen or not t or not (lo <= t <= hi):
                    continue
                seen.add(key)
                out.append(a)
            end = day
        return out, end


def utc(s) -> datetime | None:
    """LSQ times are UTC without a zone."""
    if not s:
        return None
    try:
        t = pd.to_datetime(s).to_pydatetime()
    except (ValueError, TypeError):
        return None
    return t.replace(tzinfo=timezone.utc) if t.tzinfo is None else t.astimezone(timezone.utc)


# ------------------------------------------------------------------ 1. current stage of check-5 leads
def lead_status(cands: pd.DataFrame, fresh: dict, api: LSQ | None = None) -> pd.DataFrame:
    """cands: phone, prospect_id (may be blank). One row per phone found in LSQ."""
    from partwise.core import norm_stage
    if not len(cands):
        fresh["lsq_leads"] = "no candidate leads to check"
        return pd.DataFrame(columns=STATUS_COLS)
    try:
        api = api or LSQ()
    except RuntimeError as e:
        fresh["lsq_leads"] = f"NOT checked in LSQ ({e}); current stage from the Team Uzair 'Follow-up Status' sheet only"
        return pd.DataFrame(columns=STATUS_COLS)
    rows, errors = [], 0
    cands = cands.drop_duplicates("phone").copy()
    cands["prospect_id"] = cands["prospect_id"].fillna("").astype(str).replace("nan", "")

    def keep(lead, how, phone):
        rows.append({"phone": phone, "prospect_id": lead.get("ProspectID"),
                     "lsq_stage": norm_stage(pd.Series([lead.get("ProspectStage") or ""])).iloc[0],
                     "lsq_owner": str(lead.get("OwnerIdName") or "").strip(),
                     "lsq_name": " ".join(str(lead.get(k) or "").strip() for k in ("FirstName", "LastName")).strip(),
                     "how": how})

    t0 = time.time()
    budget = CFG.get("lsq_budget_minutes", {}).get("stages", 8) * 60
    for r in cands.itertuples():
        if time.time() - t0 > budget:
            fresh["lsq_leads_budget"] = "time budget reached"
            break
        try:
            lead = api.lead_by_id(r.prospect_id) if r.prospect_id else None
            if lead:
                keep(lead, "by Prospect ID", r.phone)
                continue
            leads = api.leads_by_phone(r.phone)
            if leads:   # several leads can share a number: the one changed last decides
                keep(max(leads, key=lambda x: str(x.get("ModifiedOn") or "")), "by phone", r.phone)
        except requests.RequestException:
            errors += 1
            if errors >= 15:
                break
    out = pd.DataFrame(rows, columns=STATUS_COLS)
    n = len(cands)
    fresh["lsq_leads"] = (f"{len(out):,} of {n:,} candidate leads read from LSQ in {time.time() - t0:.0f} s "
                          f"({(out['how'] == 'by Prospect ID').sum():,} by Prospect ID, {(out['how'] == 'by phone').sum():,} by phone)"
                          + (f"; {n - len(out):,} not found or not read (stage from the Follow-up Status sheet)" if n > len(out) else "")
                          + (f"; {errors} request errors" if errors else ""))
    return out


# ------------------------------------------------------------------ 2. Zipteams notes
def load_zipteams(lo: date, hi: date, fresh: dict, api: LSQ | None = None) -> pd.DataFrame:
    """Zipteams notes (activity 237) created lo..hi: date, prospect_id, level. Matched to follow-ups in analysis."""
    z = CFG.get("zipteams", {})
    try:
        api = api or LSQ()
    except RuntimeError as e:
        fresh["zipteams"] = f"not read: {e}"
        return pd.DataFrame(columns=ZIP_COLS)
    ev = int(z.get("activity_event") or 237)
    t0 = time.time()
    try:
        rows, covered = api.activities_created(ev, datetime.combine(lo, datetime.min.time(), IST),
                                               datetime.combine(hi, datetime.max.time(), IST),
                                               budget_s=CFG.get("lsq_budget_minutes", {}).get("zipteams", 6) * 60)
    except requests.RequestException as e:
        fresh["zipteams"] = f"LSQ read failed: {str(e)[:200]}"
        return pd.DataFrame(columns=ZIP_COLS)
    field = z.get("level_field") or "mx_Custom_1"
    df = pd.DataFrame({"created_ist": [utc(r.get("CreatedOn")).astimezone(IST).strftime("%Y-%m-%d %H:%M:%S") for r in rows],
                       "prospect_id": [r.get("RelatedProspectId") or "" for r in rows],
                       "level": [str(r.get(field) or "NOT_AVAILABLE").strip().upper() for r in rows]}, columns=["created_ist", "prospect_id", "level"])
    df["date"] = df["created_ist"].str[:10]
    first = covered.astimezone(IST).date()
    fresh["zipteams"] = (f"{len(df):,} Zipteams notes (activity {ev}) read from LSQ for {max(first, lo)}..{hi} in {time.time() - t0:.0f} s"
                         + (f" (time budget reached: days before {first} not read)" if first > lo else ""))
    return df[ZIP_COLS]
