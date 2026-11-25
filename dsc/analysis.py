"""Every number of the Daily Sales Check. Python computes, the PDF only shows.

Checks (manager's list):
  1 data is fresh and complete            2 team run-rate on the previous working day
  3 early-warning numbers off track two parts of the month running (parts 1-10, 11-20, 21-end)
  4 team below 70% of pro-rated MTD target after the 15th
  5 high-intent leads not dialled for more than 24 h (callers and numbers)
  6 top three and bottom three callers
Plus: caller calling + revenue table, follow-up levels, monthly / weekly / daily trends and, for every
flagged caller, the funnel step where they fall behind the team's top 3 (the "why").
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta

import numpy as np
import pandas as pd

from dsc.settings import (CFG, TEAMS, add_months, month_first, month_key, month_working_days,
                          previous_working_day)

NUM = {"rev": ["revenue", "enrolments", "payments", "calling_rev", "collection_rev"],
       "agent": ["total_calls", "answered", "calls_3m", "calls_15_20", "calls_20p", "dur_3m", "prod_sec", "break_sec",
                 "break_count", "unique_leads"],
       "call_day": ["talk_sec", "longest_sec"],
       "targets": ["target"]}

# funnel order: an earlier gap explains the later ones
FUNNEL = [
    ("attendance_pct", "Attendance", "of working days with calls", "{:.0f}%",
     "Present {v} of working days vs {b} for the top 3. TL to confirm leave / late log-ins first."),
    ("calls_per_day", "Dialling", "calls per active day", "{:.0f}",
     "Too few dials. Set a daily dial floor at the top-3 level ({b}); review break time ({brk} min a day)."),
    ("connect_pct", "Connectivity", "of dials answered", "{:.0f}%",
     "Calls are not getting answered. Re-time the calling slots, check number quality and dialler."),
    ("conv3_per_day", "Conversations", "3-min+ calls per day", "{:,.0f}",
     "Calls end early. TL to listen to 5 recordings and fix the opening / need discovery."),
    ("deep_per_day", "Counselling depth", "15-min+ calls per day", "{:,.0f}",
     "Few full counselling calls. Book roadmap sessions from connected leads."),
    ("followups_per_day", "Follow-ups", "follow-ups set per day", "{:,.0f}",
     "Pipeline is thin: too few leads moved to Follow Up For Closure."),
    ("enrol_per_100fu", "Closing", "enrolments per 100 follow-ups", "{:,.0f}",
     "Follow-ups are not closing. TL to join closing calls and review objections and payment links."),
    ("ticket", "Ticket size", "revenue per enrolment (Rs)", "{:,.0f}",
     "Enrolments are small. Pitch the higher-value programme or full payment."),
]
FUNNEL_KEYS = [f[0] for f in FUNNEL]
EW_LABEL = {"calls_per_day": "calls/day", "connect_pct": "answered %", "conv3_per_day": "3-min calls/day",
            "deep_per_day": "15-min+ calls/day", "talk_hrs_per_day": "talk min/day", "followups_per_day": "follow-ups/day"}


@dataclass
class Flag:
    check: int
    team: str
    who: str
    what: str
    next_step: str
    level: str = "red"          # red / amber / info


@dataclass
class Result:
    day: date
    month: str
    prev_wd: date
    wd: list
    elapsed: list
    remaining: list
    from_schedule: bool
    teams: pd.DataFrame = None           # one row per team (MTD, run-rate, flags)
    callers: pd.DataFrame = None         # one row per caller (section 8 + root cause)
    daily: pd.DataFrame = None           # team x day (this month)
    weekly_team: pd.DataFrame = None     # team x week
    weekly_caller: pd.DataFrame = None   # caller x week
    monthly: pd.DataFrame = None         # team x month
    pacing: pd.DataFrame = None          # team x month x day-of-month cumulative revenue
    leads: pd.DataFrame = None           # untouched high-intent leads
    early: pd.DataFrame = None           # caller x metric off track
    top_bottom: dict = field(default_factory=dict)
    flags: list = field(default_factory=list)
    quality: list = field(default_factory=list)    # check 1 lines (text, ok?)
    stale: bool = False
    notes: list = field(default_factory=list)


# ------------------------------------------------------------------ helpers
def _num(df: pd.DataFrame, cols) -> pd.DataFrame:
    df = df.copy()
    for c in cols:
        if c in df:
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)
    return df


def _div(a, b):
    a, b = np.asarray(a, float), np.asarray(b, float)
    with np.errstate(divide="ignore", invalid="ignore"):
        out = np.where(b > 0, a / b, np.nan)
    return out if out.ndim else float(out)


def prorate_share(day: date) -> float:
    """Share of the monthly target due by `day`. Same rule as the MTD Revenue Analysis (Amit, 10 Nov 2026):
    calendar days, N / D (N = day of month, D = days in the month). config mtd.prorate = "working_days" switches
    to working days elapsed / working days in the month."""
    if CFG["mtd"].get("prorate", "calendar") == "working_days":
        wd, _ = month_working_days(month_key(day))
        return len([d for d in wd if d <= day]) / len(wd) if wd else 0
    import calendar as _cal
    return day.day / _cal.monthrange(day.year, day.month)[1]


def week_start(d: date) -> date:
    return d - timedelta(days=d.weekday())


def month_parts(day: date, n: int) -> list[tuple[date, date, str]]:
    """The last n parts of the month up to `day`: (first day, last day of the part, label like 'Oct 11-20').
    Parts as in Part Wise: 1-10, 11-20, 21-end of month."""
    out, m = [], add_months(month_first(day), -((n + 2) // 3))
    while m <= day:
        end = add_months(m, 1) - timedelta(days=1)
        for lo, hi in ((1, 10), (11, 20), (21, end.day)):
            a, b = m.replace(day=lo), m.replace(day=hi)
            if a <= day:
                out.append((a, b, f"{a:%b} {lo}-{hi}"))
        m = add_months(m, 1)
    return out[-n:]


def is_lead(role: str) -> bool:
    r = str(role or "").strip().lower()
    return any(r == x.lower() for x in CFG["lead_roles"])


def roster_for(targets: pd.DataFrame, month: str) -> pd.DataFrame:
    """That month's MonthwiseTeamList rows for my teams (latest earlier month if the month is missing)."""
    t = targets[targets["month"] <= month]
    if not len(t):
        return t.iloc[0:0].assign(active=pd.Series(dtype=bool), lead=pd.Series(dtype=bool), target_ok=pd.Series(dtype=bool))
    m = month if (t["month"] == month).any() else t["month"].max()
    r = t[t["month"] == m].copy()
    r["active"] = r["status"].str.lower() == "active"
    r["lead"] = r["role"].map(is_lead)
    r["target"] = pd.to_numeric(r["target"], errors="coerce")
    r["target_ok"] = r["active"] & r["target"].fillna(0).gt(0)
    r = r.sort_values("active", ascending=False).drop_duplicates("caller")
    return r.reset_index(drop=True)


def team_target(roster: pd.DataFrame) -> pd.Series:
    t = roster.loc[roster["target_ok"].astype(bool)].groupby("team")["target"].sum()
    return t.reindex(TEAMS).fillna(0)


def attribute(rev: pd.DataFrame, targets: pd.DataFrame) -> pd.DataFrame:
    """Team of each revenue row = the caller's team in that month's MonthwiseTeamList (so a caller who
    moved teams is counted where their target was); rows of callers not on the list (Direct, leavers)
    keep the dashboard's team."""
    rev = rev.copy()
    rev["month"] = rev["txn_date"].str[:7]
    out = []
    for m, g in rev.groupby("month"):
        r = roster_for(targets, m)
        team_of = dict(zip(r["caller"], r["team"]))
        g = g.copy()
        g["team_m"] = g["caller"].map(team_of).fillna(g["team"])
        out.append(g)
    return pd.concat(out, ignore_index=True) if out else rev.assign(team_m=rev.get("team"))


# ------------------------------------------------------------------ main
def run(data) -> Result:
    D = data.day
    month = month_key(D)
    wd, sched = month_working_days(month)
    elapsed = [d for d in wd if d <= D]
    remaining = [d for d in wd if d > D]
    P = previous_working_day(D + timedelta(days=1))
    res = Result(D, month, P, wd, elapsed, remaining, sched)
    if not sched:
        res.notes.append(f"No working schedule for {month} (config/months/{month}.json): Monday-Saturday assumed.")

    rev = _num(data.rev, NUM["rev"])
    agent = _num(data.agent, NUM["agent"])
    cday = _num(data.call_day, NUM["call_day"])
    targets = _num(data.targets, NUM["targets"])
    targets["target"] = targets["target"].replace(0, np.nan)
    stages = data.stages.copy()
    roster = roster_for(targets, month)
    res.roster = roster
    tt = team_target(roster)

    rev = attribute(rev, targets) if len(rev) else rev.assign(team_m=[], month=[])
    rev["d"] = pd.to_datetime(rev["txn_date"]).dt.date
    agent["d"] = pd.to_datetime(agent["call_date"]).dt.date
    cday["d"] = pd.to_datetime(cday["call_date"]).dt.date
    stages["d"] = pd.to_datetime(stages["date"], errors="coerce").dt.date
    stages = stages.dropna(subset=["d"])
    # one follow-up / roadmap / discovery per lead per caller per day (both sources may carry the same change)
    stages = stages.drop_duplicates(["d", "phone", "stage", "owner"])
    team_of = dict(zip(roster["caller"], roster["team"]))
    agent["team_now"] = agent["caller"].map(team_of).fillna(agent["team"])

    res.fu_zip = followup_zip(stages, data.zip, getattr(data, "lsq_leads", None))
    quality(res, data, rev, agent, roster)
    mtd_rev = rev[(rev["month"] == month) & (rev["d"] <= D)]
    teams_frame(res, mtd_rev, tt, P)
    callers_frame(res, data, rev, agent, cday, stages, roster, P)
    leads_frame(res, data, stages, roster)
    trends(res, data, rev, agent, cday, stages, targets)
    early_warning(res, agent, cday, stages, roster, rev, targets)
    root_cause(res)
    checks(res)
    return res


# ------------------------------------------------------------------ check 1
def _ist(ts: str | None) -> datetime | None:
    if not ts:
        return None
    t = pd.to_datetime(ts, utc=True, errors="coerce")
    return None if pd.isna(t) else t.tz_convert("Asia/Kolkata").tz_localize(None).to_pydatetime()


def quality(res: Result, data, rev, agent, roster):
    f, q = data.fresh, res.quality
    for key, label in (("rev_refresh", "Revenue Analytics"), ("call_refresh", "Calling Analytics")):
        t = _ist(f.get(key))
        if t is None:
            q.append((f"{label}: no successful refresh found", False))
            res.stale = True
            continue
        ok = t.date() > res.day
        q.append((f"{label} last refreshed {t:%d %b %H:%M} IST" + ("" if ok else f" - BEFORE the end of {res.day:%d %b}"), ok))
        res.stale |= not ok
    rl = f.get("rev_last_date")
    q.append((f"Latest revenue date for my teams: {rl}", bool(rl and rl >= (res.prev_wd.isoformat()))))
    cl = f.get("call_last_date")
    q.append((f"Latest calling date: {cl}", bool(cl and cl >= res.day.isoformat())))
    if not (cl and cl >= res.day.isoformat()):
        res.stale = True
    um = f.get("unmapped") or []
    if um:
        top = ", ".join(f"{u['name']} (Rs {float(u.get('fee_paid') or 0):,.0f})" for u in um[:5])
        q.append((f"{len(um)} revenue name(s) not matched to a caller this month: {top}", False))
    else:
        q.append(("Every revenue caller name this month is matched to the Teamlist", True))
    # roster callers with neither revenue nor calls in the month = name mismatch or not working
    m = roster[roster["active"]]
    seen = set(rev.loc[rev["month"] == res.month, "caller"]) | set(agent.loc[agent["d"] >= month_first(res.day), "caller"])
    miss = sorted(set(m["caller"]) - seen)
    if miss:
        q.append((f"On the {res.month} team list but no calls or revenue this month: {', '.join(miss)}", False))
    from dsc.settings import LABEL
    if f.get("uzair_books") and not LABEL:   # the Uzair sheets only matter for Amit's own (Team Uzair) teams
        q.append(("Team Uzair stage sheets read: " + "; ".join(f["uzair_books"]), True))
    if f.get("lsq_leads"):
        q.append(("High-intent leads, current stage: " + f["lsq_leads"], not f["lsq_leads"].startswith("NOT")))
    if f.get("zipteams"):
        q.append(("Zipteams (via LSQ): " + f["zipteams"], "not" not in f["zipteams"]))


# ------------------------------------------------------------------ team MTD / run-rate
def teams_frame(res: Result, mtd_rev, tt, P):
    n_wd, n_el, n_rem = len(res.wd), len(res.elapsed), len(res.remaining)
    rows = []
    for t in TEAMS:
        g = mtd_rev[mtd_rev["team_m"] == t]
        target = float(tt.get(t, 0))
        mtd = float(g["revenue"].sum())
        pro = target * prorate_share(res.day)
        rr = target / n_wd if n_wd else 0
        on_p = float(g.loc[g["d"] == P, "revenue"].sum())
        rows.append({"team": t, "target": target, "mtd": mtd, "prorated": pro,
                     "achv_pct": _div(mtd, pro) * 100 if pro else np.nan,
                     "month_pct": _div(mtd, target) * 100 if target else np.nan,
                     "enrolments": int(g["enrolments"].sum()), "run_rate": rr, "prev_wd_rev": on_p,
                     "prev_wd_pct": _div(on_p, rr) * 100 if rr else np.nan,
                     "required_rr": max(target - mtd, 0) / n_rem if n_rem else np.nan,
                     "gap": max(pro - mtd, 0)})
    res.teams = pd.DataFrame(rows)


# ------------------------------------------------------------------ caller table (section 8)
def _stage_counts(stages, lo, hi):
    s = stages[(stages["d"] >= lo) & (stages["d"] <= hi)]
    c = s.groupby(["owner", "stage"]).size().unstack(fill_value=0)
    for k in ("discovery", "roadmap", "followup"):
        if k not in c:
            c[k] = 0
    return c


def callers_frame(res: Result, data, rev, agent, cday, stages, roster, P):
    D, m0 = res.day, month_first(res.day)
    n_wd, n_el = len(res.wd), len(res.elapsed)
    a = agent[(agent["d"] >= m0) & (agent["d"] <= D)]
    c = cday[(cday["d"] >= m0) & (cday["d"] <= D)]
    r = rev[(rev["month"] == res.month) & (rev["d"] <= D)]
    st = _stage_counts(stages, m0, D)
    fu_phones = stages[(stages["stage"] == "followup") & (stages["d"] >= m0) & (stages["d"] <= D)]
    enrolled = set(data.enrolled["phone"]) if len(data.enrolled) else set()
    issues = a.assign(late=a["issues"].astype(str).str.contains("Late Check-In"))
    rows = []
    callers = roster[roster["active"] | roster["caller"].isin(set(r["caller"]) | set(a["caller"]))]
    for _, x in callers.iterrows():
        name = x["caller"]
        ga, gc, gr = a[a["caller"] == name], c[c["caller"] == name], r[r["caller"] == name]
        active = int((ga["total_calls"] > 0).sum())
        present = int(((ga["total_calls"] > 0) & ga["d"].isin(res.elapsed)).sum())   # working days only
        calls, ans = ga["total_calls"].sum(), ga["answered"].sum()
        talk = gc["talk_sec"].sum()
        target = x["target"] if x["target_ok"] else np.nan
        pro = target * prorate_share(res.day) if pd.notna(target) else np.nan
        mtd = gr["revenue"].sum()
        enr = int(gr["enrolments"].sum())
        fu = int(st.loc[name, "followup"]) if name in st.index else 0
        fph = set(fu_phones.loc[fu_phones["owner"] == name, "phone"])
        rows.append({
            "team": x["team"], "caller": name, "role": x["role"], "lead": bool(x["lead"]), "active_status": x["status"],
            "target": target, "prorated": pro, "mtd": mtd, "achv_pct": _div(mtd, pro) * 100 if pd.notna(pro) else np.nan,
            "prev_wd_rev": gr.loc[gr["d"] == P, "revenue"].sum(), "enrolments": enr,
            "active_days": active, "present_days": present, "attendance_pct": _div(present, n_el) * 100,
            "calls": int(calls), "answered": int(ans), "connect_pct": _div(ans, calls) * 100,
            "calls_3m": int(ga["calls_3m"].sum()), "calls_15_20": int(ga["calls_15_20"].sum()), "calls_20p": int(ga["calls_20p"].sum()),
            "talk_hrs": talk / 3600, "avg_talk_min": _div(talk, ans) / 60, "longest_min": gc["longest_sec"].max() / 60 if len(gc) else np.nan,
            "calls_per_day": _div(calls, active), "conv3_per_day": _div(ga["calls_3m"].sum(), active),
            "deep_per_day": _div(ga["calls_15_20"].sum() + ga["calls_20p"].sum(), active),
            "talk_hrs_per_day": _div(talk / 3600, active), "break_hrs_per_day": _div(ga["break_sec"].sum() / 3600, active),
            "late_days": int(issues.loc[issues["caller"] == name, "late"].sum()),
            "discovery": int(st.loc[name, "discovery"]) if name in st.index else 0,
            "roadmap": int(st.loc[name, "roadmap"]) if name in st.index else 0,
            "followups": fu, "followups_per_day": _div(fu, active),
            "fu_leads": len(fph), "fu_enrolled": len(fph & enrolled),
            "fu_conv_pct": _div(len(fph & enrolled), len(fph)) * 100,
            "enrol_per_100fu": _div(enr * 100, fu), "ticket": _div(mtd, enr),
        })
    df = pd.DataFrame(rows)
    if not len(df):
        res.callers = df
        return
    # follow-up level vs team median (callers only)
    fl = CFG["followup_level"]
    df["followup_level"] = ""
    for t, g in df[~df["lead"]].groupby("team"):
        med = g["followups_per_day"].median()
        for i in g.index:
            v = df.at[i, "followups_per_day"]
            if pd.isna(v) or not med or pd.isna(med):
                lvl = "Low" if (pd.notna(v) and v == 0) else ""
            elif v >= med * fl["high_pct"] / 100:
                lvl = "High"
            elif v < med * fl["low_pct"] / 100:
                lvl = "Low"
            else:
                lvl = "Medium"
            df.at[i, "followup_level"] = lvl
    # Zipteams intent of each follow-up (MTD) per caller
    fz = res.fu_zip[(res.fu_zip["d"] >= m0) & (res.fu_zip["d"] <= D)] if len(res.fu_zip) else res.fu_zip
    for lvl in ZIP_LEVELS:
        col = "zip_" + lvl.lower()
        df[col] = df["caller"].map(fz[fz["zip"] == lvl].groupby("owner").size()).fillna(0).astype(int) if len(fz) else 0
    rated = df[["zip_high", "zip_moderate", "zip_neutral", "zip_low"]].sum(axis=1)
    df["zip_rated"] = rated
    df["zip_himod_pct"] = _div(df["zip_high"] + df["zip_moderate"], rated) * 100
    res.callers = df.sort_values(["team", "lead", "mtd"], ascending=[True, True, False]).reset_index(drop=True)


# ------------------------------------------------------------------ check 5
ZIP_LEVELS = ["HIGH", "MODERATE", "NEUTRAL", "LOW"]


def followup_zip(stages: pd.DataFrame, z, lsq=None) -> pd.DataFrame:
    """Each follow-up (stage row) with the Zipteams intent of its lead's latest note within match_days of the
    follow-up date, matched by Prospect ID. zip = HIGH / MODERATE / NEUTRAL / LOW, or "" (no rated note).
    A row without a Prospect ID (the LSQ stage report has none) takes it from any other row or LSQ lookup of
    the same phone."""
    st = stages.reset_index(drop=True)
    pid = (st["prospect_id"] if "prospect_id" in st else pd.Series("", index=st.index)).fillna("").astype(str).replace("nan", "")
    by_phone = dict(zip(st.loc[pid.str.len() > 0, "phone"], pid[pid.str.len() > 0]))
    fu = st[st["stage"] == "followup"].copy()
    if lsq is not None and len(lsq):
        ok = lsq["prospect_id"].fillna("").astype(str).str.len() > 0
        by_phone.update(dict(zip(lsq.loc[ok, "phone"], lsq.loc[ok, "prospect_id"].astype(str))))
    own = pid.loc[fu.index]
    fu["prospect_id"] = own.where(own.str.len() > 0, fu["phone"].map(by_phone)).fillna("")
    fu["zip"] = ""
    if z is None or not len(z) or not len(fu):
        return fu
    md = CFG["zipteams"].get("match_days", 2)
    z = z[z["level"].isin(ZIP_LEVELS) & (z["prospect_id"].astype(str).str.len() > 0)].copy()
    z["zd"] = pd.to_datetime(z["date"]).dt.date
    m = fu.reset_index().merge(z[["prospect_id", "zd", "level", "created_ist"]], on="prospect_id", how="inner")
    m = m[(m["zd"] >= m["d"] - timedelta(days=md)) & (m["zd"] <= m["d"] + timedelta(days=md))]
    m = m.sort_values("created_ist").drop_duplicates("index", keep="last").set_index("index")
    fu.loc[m.index, "zip"] = m["level"]
    return fu


LEAD_KEYS = {"Roadmap Done": "roadmap", "Follow Up For Closure": "followup", "Discovery Call Done": "discovery"}


def lead_candidates(day: date, stages: pd.DataFrame, touches: pd.DataFrame, enrolled: pd.DataFrame) -> pd.DataFrame:
    """Check-5 candidates before the current-stage check: latest stage in the look-back is high-intent, not
    enrolled, and no call to the number for more than untouched_hours before the latest call in the data.
    Used by the loader (which leads to look up in LSQ) and by the report."""
    L = CFG["leads"]
    hi_keys = {LEAD_KEYS[x] for x in L["stages"] if x in LEAD_KEYS}
    s = stages.copy()
    if "d" not in s:
        s["d"] = pd.to_datetime(s["date"], errors="coerce").dt.date
    s = s.dropna(subset=["d"])
    s = s[(s["d"] >= day - timedelta(days=L["lookback_days"])) & (s["d"] <= day)].copy()
    for c in ("name", "prospect_id"):
        s[c] = (s[c] if c in s else pd.Series("", index=s.index)).fillna("").astype(str).replace("nan", "")
    pick = lambda c: s[s[c].str.len() > 0].sort_values("d").drop_duplicates("phone", keep="last").set_index("phone")[c]
    name_of, id_of = pick("name"), pick("prospect_id")
    s["r"] = s["stage"].map({"discovery": 0, "roadmap": 1, "followup": 2})
    s = s.sort_values(["phone", "d", "r"]).drop_duplicates("phone", keep="last")
    s = s[s["stage"].isin(hi_keys)]
    s["name"] = s["phone"].map(name_of).fillna("")
    s["prospect_id"] = s["phone"].map(id_of).fillna("")
    enr = set(enrolled["phone"]) if len(enrolled) else set()
    s = s[~s["phone"].isin(enr)]
    t = touches.copy()
    t["last_call"] = pd.to_datetime(t["last_call"], errors="coerce")
    ref = t["last_call"].max() if len(t) else pd.NaT
    if pd.isna(ref):
        ref = pd.Timestamp(datetime.combine(day + timedelta(days=1), datetime.min.time()) + timedelta(hours=11, minutes=30))
    s["last_call"] = s["phone"].map(t.set_index("phone")["last_call"]) if len(t) else pd.NaT
    s["hours"] = (ref - s["last_call"]).dt.total_seconds() / 3600
    s = s[(s["d"] < ref.date()) & (s["last_call"].isna() | (s["hours"] > L["untouched_hours"]))]
    s.attrs["ref"] = ref
    return s


def leads_frame(res: Result, data, stages, roster):
    L = CFG["leads"]
    cols = ["team", "caller", "phone", "name", "stage", "stage_date", "last_call", "hours", "current_stage", "stage_source",
            "zip_intent"]
    s = lead_candidates(res.day, stages, data.touches, data.enrolled)
    res.lead_ref = s.attrs.get("ref")
    res.leads_dropped = pd.DataFrame(columns=cols)
    if not len(s):
        res.leads = pd.DataFrame(columns=cols)
        return
    # current stage + owner: LSQ API first (source of truth), else the Team Uzair 'Follow-up Status' sheet
    s["current_stage"], s["current_owner"], s["stage_source"] = "", "", "not checked"
    ls = data.lead_status if data.lead_status is not None else pd.DataFrame(columns=["phone", "current_stage", "current_owner"])
    if len(ls):
        ls = ls.drop_duplicates("phone", keep="last").set_index("phone")
        hit = s["phone"].isin(ls.index)
        s.loc[hit, "current_stage"] = s.loc[hit, "phone"].map(ls["current_stage"]).fillna("")
        s.loc[hit, "current_owner"] = s.loc[hit, "phone"].map(ls["current_owner"]).fillna("")
        s.loc[hit, "stage_source"] = "Follow-up Status sheet"
    lq = data.lsq_leads if getattr(data, "lsq_leads", None) is not None else pd.DataFrame()
    if len(lq):
        lq = lq.drop_duplicates("phone", keep="last").set_index("phone")
        hit = s["phone"].isin(lq.index)
        s.loc[hit, "current_stage"] = s.loc[hit, "phone"].map(lq["lsq_stage"]).fillna("")
        own = s.loc[hit, "phone"].map(lq["lsq_owner"]).fillna("")
        s.loc[hit, "current_owner"] = own.where(own.str.len() > 0, s.loc[hit, "current_owner"])
        nm = s.loc[hit, "phone"].map(lq["lsq_name"]).fillna("")
        s.loc[hit, "name"] = nm.where(nm.str.len() > 0, s.loc[hit, "name"])
        s.loc[hit, "stage_source"] = "LSQ"
        pid = s.loc[hit, "phone"].map(lq["prospect_id"]).fillna("").astype(str)
        s.loc[hit, "prospect_id"] = pid.where(pid.str.len() > 0, s.loc[hit, "prospect_id"])
    s["current_stage"] = s["current_stage"].fillna("").astype(str)
    z = data.zip if data.zip is not None else pd.DataFrame()
    if len(z):
        zl = z[z["level"].isin(ZIP_LEVELS)].sort_values("created_ist").drop_duplicates("prospect_id", keep="last")
        s["zip_intent"] = s["prospect_id"].map(zl.set_index("prospect_id")["level"]).fillna("").str.title()
    else:
        s["zip_intent"] = ""
    s["caller"] = s["current_owner"].where(s["current_owner"].astype(str).str.len() > 0, s["owner"])
    team_of = dict(zip(roster["caller"], roster["team"]))
    s["team"] = s["caller"].map(team_of)
    s["stage_date"] = s["d"]
    s["stage"] = s["stage"].map({v: k for k, v in LEAD_KEYS.items()})
    s = s[s["team"].isin(TEAMS)]
    open_ = s["current_stage"].eq("") | s["current_stage"].isin(L["stages"])
    order = dict(by=["team", "caller", "hours"], ascending=[True, True, False], na_position="first")
    res.leads_dropped = s[~open_].sort_values(**order)[cols].reset_index(drop=True)
    res.leads = s[open_].sort_values(**order)[cols].reset_index(drop=True)


# ------------------------------------------------------------------ trends
def _team_rate(targets, month):
    r = roster_for(targets, month)
    wd, _ = month_working_days(month)
    return team_target(r), len(wd), wd


def trends(res: Result, data, rev, agent, cday, stages, targets):
    D = res.day
    t = CFG["trend"]
    m_from = add_months(month_first(D), -(t["months"] - 1))
    # daily, this month
    days = [month_first(D) + timedelta(days=i) for i in range((D - month_first(D)).days + 1)]
    tt, n_wd, _ = _team_rate(targets, res.month)
    rows = []
    fu = stages[stages["stage"] == "followup"]
    team_of_m = {}
    for m in {month_key(d) for d in days}:
        r = roster_for(targets, m)
        team_of_m[m] = dict(zip(r["caller"], r["team"]))
    fu = fu.assign(team=[team_of_m.get(month_key(d), {}).get(o) for d, o in zip(fu["d"], fu["owner"])]) if len(fu) else fu.assign(team=[])
    for tm in TEAMS:
        for d in days:
            g = rev[(rev["team_m"] == tm) & (rev["d"] == d)]
            ga = agent[(agent["team_now"] == tm) & (agent["d"] == d)]
            rows.append({"team": tm, "d": d, "revenue": g["revenue"].sum(), "enrolments": int(g["enrolments"].sum()),
                         "run_rate": tt.get(tm, 0) / n_wd if n_wd else 0, "working": d in res.wd,
                         "calls": int(ga["total_calls"].sum()), "callers": int((ga["total_calls"] > 0).sum()),
                         "followups": int(((fu["team"] == tm) & (fu["d"] == d)).sum()) if len(fu) else 0})
    daily = pd.DataFrame(rows)
    daily["cum"] = daily.groupby("team")["revenue"].cumsum()
    res.daily = daily

    # pacing: cumulative revenue by day of month for each month in the window (same-window comparison)
    pr = []
    m = m_from
    while m <= month_first(D):
        mk = month_key(m)
        g = rev[rev["month"] == mk]
        for tm in TEAMS:
            s = g[g["team_m"] == tm].groupby(pd.to_datetime(g.loc[g["team_m"] == tm, "txn_date"]).dt.day)["revenue"].sum()
            last = D.day if mk == res.month else 31
            s = s.reindex(range(1, last + 1), fill_value=0).cumsum()
            for day_, v in s.items():
                pr.append({"team": tm, "month": mk, "dom": day_, "cum": v})
        m = add_months(m, 1)
    res.pacing = pd.DataFrame(pr)

    # monthly
    mrows = []
    m = m_from
    while m <= month_first(D):
        mk = month_key(m)
        ttm, n_wdm, wdm = _team_rate(targets, mk)
        end = D if mk == res.month else (add_months(m, 1) - timedelta(days=1))
        same = min(D.day, end.day)
        r = roster_for(targets, mk)
        team_of = dict(zip(r["caller"], r["team"]))
        a = agent[(agent["d"] >= m) & (agent["d"] <= end)].copy()
        a["tm"] = a["caller"].map(team_of).fillna(a["team"])
        s = stages[(stages["d"] >= m) & (stages["d"] <= end)].copy()
        s["tm"] = s["owner"].map(team_of)
        for tm in TEAMS:
            g = rev[(rev["month"] == mk) & (rev["team_m"] == tm)]
            ga = a[a["tm"] == tm]
            active = int((ga["total_calls"] > 0).sum())
            el = len([d for d in wdm if d <= end])
            fu_n = int(((s["tm"] == tm) & (s["stage"] == "followup")).sum())
            rd_n = int(((s["tm"] == tm) & (s["stage"] == "roadmap")).sum())
            mrows.append({"team": tm, "month": mk, "revenue": g["revenue"].sum(),
                          "same_window": g.loc[pd.to_datetime(g["txn_date"]).dt.day <= same, "revenue"].sum(),
                          "target": float(ttm.get(tm, 0)), "prorated": float(ttm.get(tm, 0)) * prorate_share(end),
                          "enrolments": int(g["enrolments"].sum()), "partial": mk == res.month,
                          "calls_per_day": _div(ga["total_calls"].sum(), active),
                          "connect_pct": _div(ga["answered"].sum(), ga["total_calls"].sum()) * 100,
                          "deep_per_day": _div(ga["calls_15_20"].sum() + ga["calls_20p"].sum(), active),
                          "conv3_per_day": _div(ga["calls_3m"].sum(), active),
                          "followups": fu_n, "roadmaps": rd_n, "followups_per_day": _div(fu_n, active),
                          "enrol_per_100fu": _div(g["enrolments"].sum() * 100, fu_n), "has_calls": active > 0})
        m = add_months(m, 1)
    mo = pd.DataFrame(mrows)
    mo["achv_pct"] = _div(mo["revenue"], mo["prorated"]) * 100
    res.monthly = mo

    # parts of the month (as in Part Wise: 1-10, 11-20, 21-end), the last N up to the report day.
    # Internally a part is still called a "week" row (week = its first day, week_end = last day used).
    parts = month_parts(D, t.get("parts", 7))
    # talk time comes from the individual calls, which Calling Analytics keeps for 60 days (Amit, 25 Nov 2026): a part that
    # starts before that shows no talk time rather than a figure that is too low
    calls_from = D - timedelta(days=t.get("calls_kept_days", 60) - 1)
    wrows, crows = [], []
    for ws, we_full, label in parts:
        we = min(we_full, D)
        complete = we_full <= D
        wd_part = [d for d in (ws + timedelta(days=i) for i in range((we - ws).days + 1))
                   if d in month_working_days(month_key(d))[0]]
        wdays = [ws + timedelta(days=i) for i in range((we - ws).days + 1)]
        # run-rate of each day = that month's daily run-rate, working days only
        rr = {}
        for d in wdays:
            mk = month_key(d)
            ttm, n_wdm, wdm = _team_rate(targets, mk)
            if d in wdm:
                for tm in TEAMS:
                    rr[tm] = rr.get(tm, 0) + (ttm.get(tm, 0) / n_wdm if n_wdm else 0)
        a = agent[(agent["d"] >= ws) & (agent["d"] <= we)].copy()
        # each caller under the team they were in during that part's month (same rule as the revenue)
        r_part = roster_for(targets, month_key(ws))
        a["team_part"] = a["caller"].map(dict(zip(r_part["caller"], r_part["team"]))).fillna(a["team_now"])
        c = cday[(cday["d"] >= ws) & (cday["d"] <= we)]
        s = stages[(stages["d"] >= ws) & (stages["d"] <= we)]
        fuc = s[s["stage"] == "followup"].groupby("owner").size()
        rc = rev[(rev["d"] >= ws) & (rev["d"] <= we)]
        for tm in TEAMS:
            g = rc[rc["team_m"] == tm]
            ga = a[a["team_part"] == tm]
            callers = ga["caller"].unique()
            active = int((ga["total_calls"] > 0).sum())
            fu_n = int(fuc.reindex(callers).fillna(0).sum())
            wrows.append({"team": tm, "week": ws, "week_end": we, "complete": complete, "label": label,
                          "working_days": len(wd_part), "followups_per_wd": _div(fu_n, len(wd_part)),
                          "revenue": g["revenue"].sum(), "enrolments": int(g["enrolments"].sum()), "run_rate": rr.get(tm, 0),
                          "calls_per_day": _div(ga["total_calls"].sum(), active),
                          "connect_pct": _div(ga["answered"].sum(), ga["total_calls"].sum()) * 100,
                          "conv3_per_day": _div(ga["calls_3m"].sum(), active),
                          "deep_per_day": _div(ga["calls_15_20"].sum() + ga["calls_20p"].sum(), active),
                          "followups": fu_n, "followups_per_day": _div(fu_n, active),
                          "talk_hrs_per_day": np.nan if ws < calls_from else _div(c[c["caller"].isin(callers)]["talk_sec"].sum() / 3600, active),
                          **_zip_mix(res.fu_zip, ws, we, callers)})
        for name, ga in a.groupby("caller"):
            active = int((ga["total_calls"] > 0).sum())
            gc = c[c["caller"] == name]
            fu_n = int(fuc.get(name, 0))
            crows.append({"caller": name, "team": ga["team_part"].iloc[0], "week": ws, "label": label,
                          "complete": complete, "active_days": active,
                          "revenue": rc.loc[rc["caller"] == name, "revenue"].sum(),
                          "calls_per_day": _div(ga["total_calls"].sum(), active),
                          "connect_pct": _div(ga["answered"].sum(), ga["total_calls"].sum()) * 100,
                          "conv3_per_day": _div(ga["calls_3m"].sum(), active),
                          "deep_per_day": _div(ga["calls_15_20"].sum() + ga["calls_20p"].sum(), active),
                          "talk_hrs_per_day": _div(gc["talk_sec"].sum() / 3600, active) if len(gc) and ws >= calls_from else np.nan,
                          "followups": fu_n, "followups_per_day": _div(fu_n, active)})
    res.weekly_team = pd.DataFrame(wrows)
    res.weekly_caller = pd.DataFrame(crows)


def _zip_mix(fz, lo, hi, callers) -> dict:
    g = fz[(fz["d"] >= lo) & (fz["d"] <= hi) & fz["owner"].isin(callers)] if len(fz) else fz
    n = {lvl: int((g["zip"] == lvl).sum()) for lvl in ZIP_LEVELS} if len(g) else {lvl: 0 for lvl in ZIP_LEVELS}
    rated = sum(n.values())
    return {"fu_zip_rated": rated, "fu_himod_pct": _div(n["HIGH"] + n["MODERATE"], rated) * 100 if rated else np.nan,
            "fu_zip_low": n["LOW"]}


# ------------------------------------------------------------------ check 3
def early_warning(res: Result, agent, cday, stages, roster, rev, targets):
    E = CFG["early_warning"]
    n, pct = E["weeks_running"], E["off_track_pct_of_benchmark"] / 100
    wc = res.weekly_caller
    rows = []
    if wc is None or not len(wc):
        res.early = pd.DataFrame(columns=["team", "caller", "metric", "values", "benchmarks"])
        return
    done = sorted(wc.loc[wc["complete"], "week"].unique())[-n:]
    res.ew_weeks = done
    leads = set(roster.loc[roster["lead"], "caller"])
    active_now = set(roster.loc[roster["active"], "caller"])
    if len(done) == n:
        w = wc[wc["week"].isin(done) & ~wc["caller"].isin(leads) & wc["caller"].isin(active_now) & (wc["active_days"] > 0)]
        for metric in E["metrics"]:
            bench = w.groupby(["team", "week"])[metric].median()
            for (team, caller), g in w.groupby(["team", "caller"]):
                if len(g) < n:
                    continue
                vals, bs = [], []
                for _, x in g.sort_values("week").iterrows():
                    b = bench.get((team, x["week"]), np.nan)
                    vals.append(x[metric])
                    bs.append(b)
                if all(pd.notna(v) and pd.notna(b) and b > 0 and v < b * pct for v, b in zip(vals, bs)):
                    rows.append({"team": team, "caller": caller, "metric": metric, "values": vals, "benchmarks": bs})
    res.early = pd.DataFrame(rows, columns=["team", "caller", "metric", "values", "benchmarks"])
    # team revenue vs weekly run-rate
    wt = res.weekly_team
    res.team_ew = {}
    for tm in TEAMS:
        g = wt[(wt["team"] == tm) & wt["week"].isin(done)].sort_values("week")
        off = [r["revenue"] < r["run_rate"] for _, r in g.iterrows() if r["run_rate"] > 0]
        res.team_ew[tm] = (len(off) == n and all(off), g)


# ------------------------------------------------------------------ the why
def whole(v) -> int:
    """Whole numbers for call figures (Amit, 5 Nov 2026), rounded half up (2.5 -> 3)."""
    return int(np.floor(float(v) + 0.5))


def _fmt(fmt, v):
    try:
        if pd.notna(v) and fmt.endswith(".0f}") or (pd.notna(v) and ".0f}" in fmt):
            v = whole(v)
        return fmt.format(v) if pd.notna(v) else "-"
    except (ValueError, TypeError):
        return "-"


def root_cause(res: Result):
    df = res.callers
    if df is None or not len(df):
        return
    gap = CFG["root_cause"]["gap_pct"] / 100
    df["primary"] = ""
    df["primary_key"] = ""
    df["gaps"] = [[] for _ in range(len(df))]
    df["next_step"] = ""
    df["trend_note"] = ""
    wc = res.weekly_caller
    for tm, g in df[~df["lead"]].groupby("team"):
        top = g.sort_values("mtd", ascending=False).head(3)
        bench = {k: top[k].median() for k in FUNNEL_KEYS}
        df.loc[g.index, "bench_json"] = str({k: round(float(v), 2) for k, v in bench.items() if pd.notna(v)})
        for i in g.index:
            x = df.loc[i]
            gaps = []
            for key, label, unit, fmt, step in FUNNEL:
                v, b = x[key], bench[key]
                if key == "ticket" and not x["enrolments"]:
                    continue
                if key == "enrol_per_100fu" and not x["followups"]:
                    continue
                if pd.notna(b) and b > 0 and (pd.isna(v) or v < b * gap):
                    gaps.append({"key": key, "label": label, "unit": unit, "v": _fmt(fmt, v), "b": _fmt(fmt, b),
                                 "short": (1 - (v if pd.notna(v) else 0) / b) * 100,
                                 "step": step.format(v=_fmt(fmt, v), b=_fmt(fmt, b),
                                                     brk=_fmt("{:,.0f}", x["break_hrs_per_day"] * 60))})
            df.at[i, "gaps"] = gaps
            if gaps:
                p = gaps[0]
                df.at[i, "primary_key"] = p["key"]
                df.at[i, "primary"] = f"{p['label']}: {p['v']} {p['unit']} vs {p['b']} for the team's top 3"
                df.at[i, "next_step"] = p["step"]
            elif x["mtd"] == 0 and x["active_days"] > 0:
                df.at[i, "primary"] = "Activity in line with the top 3 but no revenue yet"
                df.at[i, "next_step"] = "Check the follow-up list for leads ready to pay; TL to join closing calls."
            # trend: last 2 complete parts vs the 2 before
            if wc is not None and len(wc):
                cw = wc[(wc["caller"] == x["caller"]) & wc["complete"]].sort_values("week")
                if len(cw) >= 4:
                    a, b = cw.iloc[-4:-2], cw.iloc[-2:]
                    notes = []
                    for k, lab in (("calls_per_day", "calls/day"), ("deep_per_day", "15-min+ calls/day"),
                                   ("followups_per_day", "follow-ups/day")):
                        va, vb = a[k].mean(), b[k].mean()
                        if pd.notna(va) and va > 0 and pd.notna(vb):
                            ch = (vb - va) / va * 100
                            if abs(ch) >= 20 and whole(va) != whole(vb):   # whole numbers: skip "1 -> 1"
                                notes.append(f"{lab} {whole(va)} -> {whole(vb)} ({ch:+.0f}%)")
                    df.at[i, "trend_note"] = "; ".join(notes)
    res.callers = df


# ------------------------------------------------------------------ flags
def checks(res: Result):
    F = res.flags
    tdf, cdf = res.teams, res.callers
    # 1
    if res.stale:
        F.append(Flag(1, "All", "Data", "Data is stale or incomplete (see Data check). Every other check is only as good as this.",
                      "Refresh the dashboards (Update button) and re-run.", "red"))
    for txt, ok in res.quality:
        if not ok and "not matched" in txt:
            F.append(Flag(1, "All", "Revenue sheet", txt, "Fix the caller name in the Combined Revenue Sheet or add an alias.", "amber"))
    # 2
    mp = CFG["run_rate"]["min_pct"]
    for _, t in tdf.iterrows():
        if not t["target"]:
            F.append(Flag(2, t["team"], "Team", "No target on the team list for this month - run-rate not checked.",
                          "Fill the Target column in MonthwiseTeamList.", "amber"))
            continue
        earners = cdf[(cdf["team"] == t["team"]) & (cdf["prev_wd_rev"] > 0)].sort_values("prev_wd_rev", ascending=False)
        who = ", ".join(f"{r.caller} (Rs {r.prev_wd_rev:,.0f})" for r in earners.itertuples()) or "nobody"
        if t["prev_wd_rev"] <= 0:
            F.append(Flag(2, t["team"], "Team", f"No revenue on {res.prev_wd:%a %d %b} (run-rate Rs {t['run_rate']:,.0f}/day).",
                          f"TL to list today's closures; required from now Rs {t['required_rr']:,.0f}/working day.", "red"))
        elif t["prev_wd_rev"] < t["run_rate"] * mp / 100:
            F.append(Flag(2, t["team"], "Team", f"Rs {t['prev_wd_rev']:,.0f} on {res.prev_wd:%a %d %b} = {t['prev_wd_pct']:.0f}% of the "
                                                 f"daily run-rate Rs {t['run_rate']:,.0f}. Earned by: {who}.",
                          f"Required from now Rs {t['required_rr']:,.0f}/working day to close the month on target.", "amber"))
    # 3
    E = CFG["early_warning"]
    for tm, (off, g) in getattr(res, "team_ew", {}).items():
        if off:
            parts = "; ".join(f"{r.label}: Rs {r.revenue:,.0f} vs target Rs {r.run_rate:,.0f}" for r in g.itertuples())
            F.append(Flag(3, tm, "Team", f"Revenue below target {E['weeks_running']} parts of the month running ({parts}).",
                          "Review the follow-up pipeline with the TL; plan closures for this part of the month.", "red"))
    if res.early is not None and len(res.early):
        for (tm, caller), g in res.early.groupby(["team", "caller"]):
            k = lambda r: 60 if r.metric == "talk_hrs_per_day" else 1      # talk shown in minutes
            ms = "; ".join(f"{EW_LABEL[r.metric]} " + " / ".join(str(whole(v * k(r))) for v in r.values) + " vs team "
                           + " / ".join(str(whole(b * k(r))) for b in r.benchmarks) for r in g.itertuples())
            F.append(Flag(3, tm, caller, f"Off track {E['weeks_running']} parts of the month running: {ms}.",
                          "TL 1:1 on these numbers; re-check at the end of this part (10th / 20th / month end).", "amber"))
    # 4
    M = CFG["mtd"]
    if res.day.day > M["after_day"]:
        for _, t in tdf.iterrows():
            if t["target"] and t["achv_pct"] < M["min_pct"]:
                F.append(Flag(4, t["team"], "Team", f"MTD Rs {t['mtd']:,.0f} = {t['achv_pct']:.0f}% of pro-rated target "
                                                     f"Rs {t['prorated']:,.0f} (below {M['min_pct']}%).",
                              f"Needs Rs {t['required_rr']:,.0f} per remaining working day ({len(res.remaining)} left).", "red"))
    # 5
    L = res.leads
    if L is not None and len(L):
        for (tm, caller), g in L.groupby(["team", "caller"]):
            nd = int(g["last_call"].isna().sum())
            F.append(Flag(5, tm, caller, f"{len(g)} high-intent lead(s) not dialled for over {CFG['leads']['untouched_hours']} h"
                                         + (f" ({nd} with no dial in {CFG['leads']['lookback_days']} days)" if nd else "") + ".",
                          "Dial these today before new leads; numbers in the leads Excel.", "amber"))
    # 6
    n = CFG["top_bottom"]["n"]
    ranked = cdf[~cdf["lead"] & cdf["achv_pct"].notna() & (cdf["active_status"].str.lower() == "active")]
    for tm in TEAMS:
        g = ranked[ranked["team"] == tm].sort_values("achv_pct", ascending=False)
        res.top_bottom[tm] = (g.head(n), g.tail(n).iloc[::-1] if len(g) > n else g.iloc[0:0])
        for r in res.top_bottom[tm][1].itertuples():
            F.append(Flag(6, tm, r.caller, f"Bottom {n}: Rs {r.mtd:,.0f} = {r.achv_pct:.0f}% of pro-rated target. Why: {r.primary or 'see page'}.",
                          r.next_step or "TL review.", "info"))
    g = ranked.sort_values("achv_pct", ascending=False)
    res.top_bottom["All"] = (g.head(n), g.tail(n).iloc[::-1] if len(g) > n else g.iloc[0:0])


def flagged_callers(res: Result) -> pd.DataFrame:
    """Callers who get a 'why' card: bottom n, below 70% of pace, early-warning, or zero revenue with a target."""
    df = res.callers
    if df is None or not len(df):
        return df
    names = set()
    for tm, (top, bot) in res.top_bottom.items():
        if tm != "All":
            names |= set(bot["caller"])
    names |= set(df.loc[df["achv_pct"] < CFG["mtd"]["min_pct"], "caller"])
    if res.early is not None:
        names |= set(res.early["caller"])
    sel = df[df["caller"].isin(names) & ~df["lead"]]
    return sel.sort_values(["team", "achv_pct"])
