"""Inputs of the Daily Sales Check. Read-only: nothing here writes to Supabase, LSQ or Google.

* Revenue Analytics (Supabase oifzauaspvfkmzyutwtj): rev_daily, refresh_log, unmapped_names.
* Calling Analytics (Supabase ybkldfcilvibryoxcuvq): agent_day, calls, team_map, stage_changes, refresh_log.
* Google Sheets: MonthwiseTeamList (targets), Team Uzair LSQ live sheet (stages), BASE DATA (enrolled phones).

Every loader returns plain DataFrames in one fixed shape (``Data``). ``save``/``load_offline`` write and
read the same shape as CSV files, so a run can be repeated without network (``--offline DIR``).
"""
from __future__ import annotations

import json
import os
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta

import pandas as pd
import requests

from dsc.settings import CFG, TARGETS_SHEET_ID, TEAMS, add_months, month_first, month_key, sales_sheet_id
from partwise.core import norm_phone, norm_stage, to_dt

STAGE_KEY = {"Discovery Call Done": "discovery", "Roadmap Done": "roadmap", "Follow Up For Closure": "followup"}
UZ_TABS = {"Discovery": "Discovery Call Done", "Roadmap": "Roadmap Done", "Follow Up": "Follow Up For Closure"}

FILES = {"rev": ["txn_date", "team", "caller", "caller_status", "revenue", "enrolments", "payments", "calling_rev", "collection_rev"],
         "agent": ["call_date", "caller", "team", "total_calls", "answered", "calls_3m", "calls_15_20", "calls_20p", "dur_3m",
                   "prod_sec", "break_sec", "break_count", "unique_leads", "issues"],
         "call_day": ["call_date", "caller", "talk_sec", "longest_sec"],
         "touches": ["phone", "last_call"],
         "stages": ["date", "phone", "stage", "owner", "src", "name", "prospect_id"],
         "targets": ["month", "caller", "team", "role", "status", "target"],
         "enrolled": ["phone"],
         "lead_status": ["phone", "current_stage", "current_owner"],
         "zip": ["date", "prospect_id", "level", "created_ist"],
         "lsq_leads": ["phone", "prospect_id", "lsq_stage", "lsq_owner", "lsq_name", "how"]}


@dataclass
class Data:
    day: date                                   # report day D (MTD window = 1..D)
    rev: pd.DataFrame
    agent: pd.DataFrame
    call_day: pd.DataFrame
    touches: pd.DataFrame
    stages: pd.DataFrame
    targets: pd.DataFrame
    enrolled: pd.DataFrame
    lead_status: pd.DataFrame = None            # current LSQ stage/owner of follow-up leads (Uzair 'Follow-up Status')
    zip: pd.DataFrame = None                    # Zipteams activities from LSQ (empty until mapped)
    lsq_leads: pd.DataFrame = None              # current LSQ stage/owner of the check-5 candidate leads
    fresh: dict = field(default_factory=dict)  # refresh times, latest dates, unmapped names, source notes


def windows(day: date) -> dict:
    """Date windows the loaders need for a report day."""
    t = CFG["trend"]
    weeks_from = day - timedelta(days=day.weekday()) - timedelta(weeks=t["weeks"])
    return {"months_from": add_months(month_first(day), -(t["months"] - 1)),
            "weeks_from": min(weeks_from, month_first(day)),
            "leads_from": day - timedelta(days=CFG["leads"]["lookback_days"])}


# ------------------------------------------------------------------ Supabase REST
class Rest:
    PAGE = 1000

    def __init__(self, url_env: str, key_env: str, default_url: str, label: str):
        key = os.environ.get(key_env, "").strip()
        if not key:
            raise SystemExit(f"{key_env} is not set ({label} service-role key; GitHub secret or cloud environment variable).")
        self.base = (os.environ.get(url_env, "").strip() or default_url).rstrip("/") + "/rest/v1/"
        self.s = requests.Session()
        self.s.headers.update({"apikey": key, "Authorization": f"Bearer {key}", "Accept": "application/json"})
        self.label = label

    def request(self, method: str, path: str, **kw):
        for attempt in range(5):
            try:
                r = self.s.request(method, self.base + path, timeout=120, **kw)
                if r.status_code < 500:
                    break
            except requests.RequestException:
                if attempt == 4:
                    raise
            time.sleep(2 ** attempt)
        if r.status_code >= 300:
            raise RuntimeError(f"{self.label} {path}: HTTP {r.status_code} {r.text[:300]}")
        return r.json() if r.text else None

    def get(self, table: str, params: list) -> list[dict]:
        return self.request("GET", table, params=params)

    def paged(self, table: str, columns: str, filters: list, order: str) -> list[dict]:
        """Offset paging with a stable order; stops on a short page."""
        rows, off = [], 0
        while True:
            page = self.get(table, [("select", columns), *filters, ("order", order),
                                    ("limit", str(self.PAGE)), ("offset", str(off))])
            rows += page
            if len(page) < self.PAGE:
                return rows
            off += self.PAGE

    def keyset(self, table: str, columns: str, filters: list) -> list[dict]:
        rows, last = [], None
        while True:
            p = [("select", columns), *filters, ("order", "id.asc"), ("limit", str(self.PAGE))]
            if last is not None:
                p.append(("id", f"gt.{last}"))
            page = self.get(table, p)
            if not page:
                return rows
            rows += page
            last = page[-1]["id"]

    def by_day(self, table: str, columns: str, datecol: str, lo: date, hi: date, extra: list | None = None) -> list[dict]:
        days = [lo + timedelta(days=i) for i in range((hi - lo).days + 1)]
        with ThreadPoolExecutor(max_workers=6) as ex:
            parts = ex.map(lambda d: self.keyset(table, columns, [(datecol, f"eq.{d.isoformat()}"), *(extra or [])]), days)
        return [r for part in parts for r in part]

    def last_refresh(self) -> str | None:
        r = self.get("refresh_log", [("select", "run_at,status"), ("status", "eq.ok"), ("order", "run_at.desc"), ("limit", "1")])
        return r[0]["run_at"] if r else None


def rev_db() -> Rest:
    return Rest("REV_SUPABASE_URL", "REV_SUPABASE_KEY", CFG["revenue_supabase_url"], "Revenue Analytics")


def call_db() -> Rest:
    return Rest("CALL_SUPABASE_URL", "CALL_SUPABASE_KEY", CFG["calling_supabase_url"], "Calling Analytics")


def in_list(values) -> str:
    return "in.(" + ",".join('"' + str(v).replace('"', '\\"') + '"' for v in values) + ")"


def ist_naive(s: pd.Series) -> pd.Series:
    return pd.to_datetime(s, utc=True).dt.tz_convert("Asia/Kolkata").dt.tz_localize(None)


# ------------------------------------------------------------------ live loaders
def load_revenue(day: date, w: dict, fresh: dict) -> pd.DataFrame:
    db = rev_db()
    rows = db.paged("rev_daily", ",".join(FILES["rev"]),
                    [("team", in_list(TEAMS)), ("txn_date", f"gte.{w['months_from']}"), ("txn_date", f"lte.{day}")],
                    "txn_date.asc,team.asc,caller.asc")
    fresh["rev_refresh"] = db.last_refresh()
    last = db.get("rev_daily", [("select", "txn_date"), ("team", in_list(TEAMS)), ("order", "txn_date.desc"), ("limit", "1")])
    fresh["rev_last_date"] = last[0]["txn_date"] if last else None
    um = db.get("unmapped_names", [("select", "name,kind,rows,fee_paid,last_seen"),
                                   ("last_seen", f"gte.{month_first(day)}"), ("order", "fee_paid.desc"), ("limit", "50")])
    fresh["unmapped"] = um
    return pd.DataFrame(rows, columns=FILES["rev"])


def load_calling(day: date, w: dict, fresh: dict) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    db = call_db()
    fresh["call_refresh"] = db.last_refresh()
    agent = pd.DataFrame(db.paged("agent_day", ",".join(FILES["agent"]),
                                  [("team", in_list(TEAMS)), ("call_date", f"gte.{w['months_from']}"), ("call_date", f"lte.{day}")],
                                  "call_date.asc,caller.asc"), columns=FILES["agent"])
    agent["issues"] = agent["issues"].map(lambda v: "|".join(v) if isinstance(v, list) else (v or ""))
    last = db.get("agent_day", [("select", "call_date"), ("order", "call_date.desc"), ("limit", "1")])
    fresh["call_last_date"] = last[0]["call_date"] if last else None

    tm = pd.DataFrame(db.get("team_map", [("select", "merge_key,caller_name,team_name"), ("limit", "100000")]))
    scope = tm[tm["team_name"].isin(TEAMS)]
    keys = sorted(set(scope["merge_key"].dropna()) | set(scope["caller_name"].dropna()))
    owner_of = dict(zip(tm["merge_key"].str.lower().str.strip(), tm["caller_name"]))

    # this-month + trend-week calls of my teams' callers -> talk time per caller-day, last dial per phone
    lo = w["weeks_from"]
    raw = pd.DataFrame(db.by_day("calls", "id,client_number,call_datetime,call_duration,call_owner", "call_date", lo, day,
                                 extra=[("call_owner", in_list(keys))]))
    # every caller's calls of the last two days: a high-intent lead dialled by anyone counts as touched
    recent = pd.DataFrame(db.by_day("calls", "id,client_number,call_datetime", "call_date", day - timedelta(days=1),
                                    day + timedelta(days=1)))
    call_day = pd.DataFrame(columns=FILES["call_day"])
    if len(raw):
        raw["caller"] = raw["call_owner"].astype(str).str.lower().str.strip().map(owner_of).fillna(raw["call_owner"])
        raw["dt"] = ist_naive(raw["call_datetime"])
        raw["call_date"] = raw["dt"].dt.date.astype(str)
        raw["dur"] = pd.to_numeric(raw["call_duration"], errors="coerce").fillna(0)
        call_day = (raw.groupby(["call_date", "caller"])["dur"].agg(talk_sec="sum", longest_sec="max").reset_index())
    t = pd.concat([raw[["client_number", "call_datetime"]] if len(raw) else None,
                   recent[["client_number", "call_datetime"]] if len(recent) else None], ignore_index=True)
    touches = pd.DataFrame(columns=FILES["touches"])
    if len(t):
        t["phone"] = norm_phone(t["client_number"])
        t = t[t["phone"].str.len() == 10]
        t["last_call"] = ist_naive(t["call_datetime"])
        touches = t.groupby("phone")["last_call"].max().reset_index()
    fresh["latest_call"] = str(touches["last_call"].max()) if len(touches) else None

    st = pd.DataFrame(db.keyset("stage_changes", "id,date,phone,new_stage,changed_by,first_name,last_name",
                                [("date", f"gte.{w['months_from']}"), ("date", f"lte.{day}")]))
    stages = pd.DataFrame(columns=FILES["stages"])
    if len(st):
        st["stage"] = norm_stage(st["new_stage"]).map(STAGE_KEY).values
        st["owner"] = st["changed_by"].astype(str).str.lower().str.strip().map(owner_of).fillna(st["changed_by"])
        stages = pd.DataFrame({"date": st["date"], "phone": norm_phone(st["phone"]), "stage": st["stage"],
                               "owner": st["owner"], "src": "LSQ stage report",
                               "name": (st["first_name"].fillna("").astype(str) + " " + st["last_name"].fillna("").astype(str)).str.strip()
                               }).dropna(subset=["stage"])
    return agent, call_day, touches, stages


def load_google(day: date, w: dict, fresh: dict) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    from partwise.sources import Google, month_bounds
    g = Google()
    tl = g.tab(TARGETS_SHEET_ID, CFG["targets_tab"])
    if tl is None:
        raise SystemExit(f"Tab {CFG['targets_tab']} not found in the targets sheet.")
    targets = targets_frame(tl)

    # The live sheet holds the running month (and, until it is reset, the last one); each past month
    # is kept as a renamed copy "... Team Uzair (<Month>)". Read both and keep each row's own month.
    frames, notes = [], []
    books = [(_uzair_live(), "live sheet", None)]
    m = w["months_from"]
    while m <= day:
        arch = g.uzair_archive(month_key(m))
        if arch:
            books.append((arch["id"], arch["name"], month_key(m)))
        m = add_months(m, 1)
    for sid, label, mk in books:
        n = 0
        for tab, stage in UZ_TABS.items():
            d = g.tab(sid, tab)
            if d is None or not len(d) or "Phone Number" not in d.columns:
                continue
            f = uzair_frame(d, stage, mk)
            f = f[(f["date"] >= w["months_from"].isoformat()) & (f["date"] <= day.isoformat())]
            frames.append(f)
            n += len(f)
        notes.append(f"{label}: {n:,} stage rows")
    fresh["uzair_books"] = notes
    fs = g.tab(_uzair_live(), "Follow-up Status")
    lead_status = status_frame(fs) if fs is not None and len(fs) else pd.DataFrame(columns=FILES["lead_status"])
    uz = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=FILES["stages"])

    phones = []
    for mk in {month_key(day), month_key(add_months(month_first(day), -1))}:
        sid = sales_sheet_id(mk)
        if not sid:
            continue
        b = g.tab(sid, "BASE DATA")
        if b is not None and len(b):
            phones.append(enrolled_frame(b))
    enrolled = pd.concat(phones, ignore_index=True).drop_duplicates() if phones else pd.DataFrame(columns=["phone"])
    return targets, uz, enrolled, lead_status


def status_frame(fs: pd.DataFrame) -> pd.DataFrame:
    """'Follow-up Status' tab: the lead's stage and owner in LSQ now (e.g. 'Actually Enrolled')."""
    stage_col = "New contact Stage" if "New contact Stage" in fs.columns else "Contact Stage"
    owner_col = "LSQ Contact Owner" if "LSQ Contact Owner" in fs.columns else "Owner"
    out = pd.DataFrame({"phone": norm_phone(fs["Phone Number"]), "current_stage": norm_stage(fs[stage_col]),
                        "current_owner": fs[owner_col].astype(str).str.strip()})
    return out[out["phone"].str.len() == 10].drop_duplicates("phone", keep="last")


def _uzair_live() -> str:
    from partwise.config import SETTINGS
    return SETTINGS["uzair_live_sheet_id"]


def targets_frame(tl: pd.DataFrame) -> pd.DataFrame:
    tl = tl.copy()
    tl.columns = [str(c).strip() for c in tl.columns]
    role_col = next(c for c in tl.columns if c.lower().startswith("academic counselor") or c.lower() == "designation")
    mon = to_dt(tl["Month"])
    tgt = pd.to_numeric(tl["Target"].astype(str).str.replace(",", "").str.strip().replace({"": None, "nan": None, "None": None}),
                        errors="coerce")
    out = pd.DataFrame({"month": mon.dt.strftime("%Y-%m"), "caller": tl["Caller Name"].astype(str).str.strip(),
                        "team": tl["Team Name"].astype(str).str.strip(), "role": tl[role_col].astype(str).str.strip(),
                        "status": tl["Status"].astype(str).str.strip(), "target": tgt})
    return out[out["month"].notna() & out["team"].isin(TEAMS)].reset_index(drop=True)


def uzair_frame(d: pd.DataFrame, stage: str, mk: str | None = None) -> pd.DataFrame:
    dt = to_dt(d["Date"]) if "Date" in d.columns else to_dt(d.get("Timestamp"))
    out = pd.DataFrame({"date": dt.dt.strftime("%Y-%m-%d"), "phone": norm_phone(d["Phone Number"]),
                        "stage": STAGE_KEY[stage], "owner": d["Owner"].astype(str).str.strip(), "src": "Team Uzair LSQ sheet",
                        "name": d["Name"].fillna("").astype(str).str.strip() if "Name" in d.columns else "",
                        "prospect_id": d["Prospect ID"].fillna("").astype(str).str.strip() if "Prospect ID" in d.columns else ""})
    out = out[out["date"].notna()]
    return out if mk is None else out[out["date"].str[:7] == mk]


def enrolled_frame(b: pd.DataFrame) -> pd.DataFrame:
    b = b[b["Enrollment"].astype(str).str.strip().str.lower() == "new enrollment"]
    ph = norm_phone(b["Contact No"])
    return pd.DataFrame({"phone": ph[ph.str.len() == 10]})


def load_live(day: date) -> Data:
    w, fresh = windows(day), {}
    t0 = time.time()
    step = lambda name: print(f"[{time.time() - t0:5.0f} s] {name}", flush=True)
    rev = load_revenue(day, w, fresh)
    step(f"revenue: {len(rev):,} rows")
    agent, call_day, touches, st = load_calling(day, w, fresh)
    step(f"calling: {len(agent):,} caller-days, {len(touches):,} dialled numbers, {len(st):,} stage changes")
    targets, uz, enrolled, lead_status = load_google(day, w, fresh)
    step(f"sheets: {len(targets):,} team-list rows, {len(uz):,} Uzair stage rows, {len(enrolled):,} enrolled phones")
    stages = pd.concat([st, uz], ignore_index=True)
    stages = stages[stages["phone"].str.len() == 10].drop_duplicates(["date", "phone", "stage", "owner"])
    from dsc.analysis import lead_candidates
    from dsc.lsq import lead_status as lsq_lead_status, load_zipteams
    z = load_zipteams(day - timedelta(days=CFG["zipteams"]["days"]), day, fresh)
    step(f"Zipteams: {fresh.get('zipteams')}")
    # only my teams' leads: stage set by a caller on this or last month's team list (LSQ load stays small)
    months = {month_key(day), month_key(add_months(month_first(day), -1))}
    mine = set(targets.loc[targets["month"].isin(months), "caller"])
    cands = lead_candidates(day, stages[stages["owner"].isin(mine)], touches, enrolled)
    lsq = lsq_lead_status(cands[["phone", "prospect_id"]], fresh)
    step(f"LSQ stages: {fresh.get('lsq_leads')}")
    return Data(day, rev, agent, call_day, touches, stages, targets, enrolled, lead_status, z, lsq, fresh)


# ------------------------------------------------------------------ files
def save(data: Data, folder: str) -> None:
    os.makedirs(folder, exist_ok=True)
    for name in FILES:
        getattr(data, name).to_csv(os.path.join(folder, f"{name}.csv"), index=False)
    with open(os.path.join(folder, "fresh.json"), "w", encoding="utf-8") as f:
        json.dump({**data.fresh, "day": data.day.isoformat()}, f, indent=1, default=str)


def load_offline(folder: str, day: date | None = None) -> Data:
    with open(os.path.join(folder, "fresh.json"), encoding="utf-8") as f:
        fresh = json.load(f)
    day = day or date.fromisoformat(fresh["day"])
    dfs = {}
    for name, cols in FILES.items():
        p = os.path.join(folder, f"{name}.csv")
        df = pd.read_csv(p, dtype=str, keep_default_na=False) if os.path.isfile(p) else pd.DataFrame(columns=cols)
        dfs[name] = df
    return Data(day, **dfs, fresh=fresh)
