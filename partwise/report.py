"""Part-wise funnel analysis: builds 'Partwise Analysis 1-<till>.xlsx' from data already loaded.

Logic and layout are a straight port of the cowork project's run_analysis.py (rules confirmed by
Amit Sep-Oct 2026). Only the input side changed: data arrives as DataFrames from sources.py
(Supabase + Google Sheets, or local files) instead of a manual inbox.
"""
from __future__ import annotations

import calendar
from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from partwise.core import (CONNECT_SECONDS, GRAINS, STAGE_KEYS, STAGES, TARGET_VERTICALS, UZAIR,
                           decorate, norm_phone, norm_stage, period_of, periods_for, roster_frame,
                           to_dt)


@dataclass
class Inputs:
    month: str                      # 'YYYY-MM'
    till: int                       # last day included
    cdr: pd.DataFrame               # call log (dashboard CDR format), any dates
    stg: pd.DataFrame               # stage-changed report, any dates
    team_members: pd.DataFrame      # Sales Team Reports -> Team Members
    base: pd.DataFrame              # Sales Team Reports -> BASE DATA
    uzair: dict                     # Team Uzair workbook for the month: {'Discovery','Roadmap','Follow Up'} -> df
    lookback_stage: list = field(default_factory=list)   # [(label, stage df)] prior months
    lookback_uzair: list = field(default_factory=list)   # [(label, {'Discovery','Roadmap'} -> df)]
    notes: list = field(default_factory=list)            # [(key, value)] from the loaders


class Report:
    def __init__(self):
        self.qc: list[tuple[str, str]] = []

    def note(self, k, v):
        self.qc.append((k, str(v)))
        print(f"  QC | {k}: {v}")


# ------------------------------------------------------------------ feeds
def month_rows(rep, label, df, datecol, month, till):
    before = len(df)
    df = df.drop_duplicates()
    d = to_dt(df[datecol])
    keep = d.notna() & (d.dt.strftime("%Y-%m") == month) & (d.dt.day <= till)
    df = df[keep].copy()
    df[datecol] = d[keep].dt.strftime("%Y-%m-%d")
    days = sorted(pd.to_datetime(df[datecol]).dt.day.unique().tolist())
    rep.note(f"{label} merged", f"{before:,} rows in -> {len(df):,} after de-duplication; "
                                f"days present: {', '.join(map(str, days))}")
    missing = [x for x in range(1, till + 1) if x not in days]
    if missing:
        rep.note(f"{label} MISSING DAYS", ", ".join(map(str, missing)))
    return df, days


def stage_history(rep, inp: Inputs, stg_month: pd.DataFrame):
    """Every Discovery/Roadmap phone seen this month and in up to three prior months. Used ONLY
    for the two Stage -> Enrollments columns: no roster filter (the question is whether the LEAD
    reached the stage, not who moved it), stage text whitespace-normalised."""
    disc, road, seen = set(), set(), []
    end = pd.Timestamp(f"{inp.month}-{inp.till:02d}")
    for label, df in [(f"Stage report {inp.month}", stg_month)] + list(inp.lookback_stage):
        if df is None or not len(df) or "New_Contact_Stage" not in df.columns:
            continue
        d = to_dt(df["Date"])
        df = df[d.isna() | (d <= end)]
        st = norm_stage(df["New_Contact_Stage"]).map(STAGES)
        ph = norm_phone(df["Phone"])
        ok = ph.str.len() == 10
        disc |= set(ph[ok & (st == "discovery").values])
        road |= set(ph[ok & (st == "roadmap").values])
        seen.append(label)
    books = [(f"Team Uzair {inp.month}", inp.uzair)] + list(inp.lookback_uzair)
    for label, book in books:
        for sheet, tgt in [("Discovery", disc), ("Roadmap", road)]:
            d = (book or {}).get(sheet)
            if d is None or not len(d) or "Phone Number" not in d.columns:
                continue
            if "Date" in d.columns:
                dt = to_dt(d["Date"])
                d = d[dt.isna() | (dt <= end)]
            ph = norm_phone(d["Phone Number"])
            tgt |= set(ph[ph.str.len() == 10])
    rep.note("Stage history for the two Stage -> Enrollments columns",
             f"{len(disc):,} Discovery + {len(road):,} Roadmap unique numbers, from: "
             + "; ".join(seen) + f"; plus {len(books)} Team Uzair workbook(s): "
             + ", ".join(b[0] for b in books))
    return disc, road


# ------------------------------------------------------------------ metrics
ORDER = ["Total Calls Made", "Leads (unique numbers dialled)", "Calls per lead",
         "Connected leads", "Lead->Connectivity %", "DNP leads", "DNP %",
         "Discovery Done", "Connectivity->Discovery %",
         "Roadmap Done", "Connectivity->Roadmap %",
         "Follow-ups", "Connectivity->Follow-up %",
         "Conversions (enrollments)", "Follow-up->Conversion %",
         "Discovery -> Enrollments", "Roadmap -> Enrollments"]
COUNT_COLS = ["Total Calls Made", "Leads (unique numbers dialled)", "Connected leads",
              "DNP leads", "Discovery Done", "Roadmap Done", "Follow-ups",
              "Conversions (enrollments)", "Discovery -> Enrollments", "Roadmap -> Enrollments"]
PCT_MAP = {
    "Lead->Connectivity %": ("Connected leads", "Leads (unique numbers dialled)"),
    "DNP %": ("DNP leads", "Leads (unique numbers dialled)"),
    "Connectivity->Discovery %": ("Discovery Done", "Connected leads"),
    "Connectivity->Roadmap %": ("Roadmap Done", "Connected leads"),
    "Connectivity->Follow-up %": ("Follow-ups", "Connected leads"),
    "Follow-up->Conversion %": ("Conversions (enrollments)", "Follow-ups"),
}


def build(calls, stages, enr, grain, period, road_all=None, disc_all=None):
    """period=None means the whole month. Leads are de-duplicated within whatever window is
    reported, so the monthly Leads total is naturally lower than P1+P2+P3."""
    keys = GRAINS[grain]
    c = calls if period is None else calls[calls["period"] == period]
    s = stages if period is None else stages[stages["period"] == period]
    e = enr if period is None else enr[enr["period"] == period]
    rows = []
    if grain == "all":
        keysets = [()]
    else:
        ks = set(map(tuple, c[keys].dropna().values.tolist()))
        ks |= set(map(tuple, s[keys].dropna().values.tolist()))
        ks |= set(map(tuple, e[keys].dropna().values.tolist()))
        keysets = sorted(ks)
    for k in keysets:
        def m(df):
            sel = np.ones(len(df), bool)
            for col, val in zip(keys, k):
                sel &= (df[col] == val).values
            return sel
        cc = c[m(c)]
        if len(cc):
            best = cc.groupby("phone")["dur"].max()
            leads = len(best)
            conn = int((best >= CONNECT_SECONDS).sum())
            total = len(cc)
        else:
            leads = conn = total = 0
        ss = s[m(s)]
        # Discovery/Roadmap -> Enrollments: unique enrolled numbers whose lead reached that stage
        # anywhere in the stage history, matched on phone regardless of who did the stage.
        # A number that reached Roadmap is counted under Roadmap only, never twice.
        ep = set(e.loc[m(e), "phone"])
        road_enr = len(ep & road_all) if road_all is not None else 0
        disc_enr = len(ep & (disc_all - road_all)) if disc_all is not None else 0
        rec = {col: val for col, val in zip(keys, k)}
        rec.update({
            "Total Calls Made": total, "Leads (unique numbers dialled)": leads,
            "Calls per lead": round(total / leads, 2) if leads else None,
            "Connected leads": conn, "DNP leads": leads - conn,
            "Discovery Done": int(ss.loc[ss["stage"] == "discovery", "phone"].nunique()),
            "Roadmap Done": int(ss.loc[ss["stage"] == "roadmap", "phone"].nunique()),
            "Follow-ups": int(ss.loc[ss["stage"] == "followup", "phone"].nunique()),
            "Conversions (enrollments)": int(m(e).sum()),
            "Discovery -> Enrollments": disc_enr,
            "Roadmap -> Enrollments": road_enr,
        })
        rows.append(rec)
    df = pd.DataFrame(rows)
    if len(df) and keys:
        df = df.sort_values(keys).reset_index(drop=True)
    return df


def scope_total(vert):
    if not len(vert):
        return None
    t = {c: int(vert[c].fillna(0).sum()) for c in COUNT_COLS if c in vert}
    leads = t.get("Leads (unique numbers dialled)", 0)
    t["Calls per lead"] = round(t.get("Total Calls Made", 0) / leads, 2) if leads else None
    return t


# ------------------------------------------------------------------ output
FONT = "Arial"
HDR = PatternFill("solid", fgColor="1F3864")
TOTF = PatternFill("solid", fgColor="FFF2CC")
TITLE = PatternFill("solid", fgColor="EAEFF7")
T = Side(style="thin", color="BFBFBF")
B = Border(left=T, right=T, top=T, bottom=T)


def write_table(ws, row, title, df, label_cols, total_row=None, total_label="TOTAL"):
    ws.cell(row=row, column=1, value=title).font = Font(name=FONT, bold=True, size=12, color="1F3864")
    cols = label_cols + ORDER
    for j in range(1, len(cols) + 1):
        ws.cell(row=row, column=j).fill = TITLE
    hdr = row + 1
    for j, n in enumerate(cols, 1):
        c = ws.cell(row=hdr, column=j, value=n)
        c.font = Font(name=FONT, bold=True, color="FFFFFF", size=10)
        c.fill = HDR
        c.alignment = Alignment(wrap_text=True, vertical="center", horizontal="center")
        c.border = B
    ws.row_dimensions[hdr].height = 46
    idx = {n: get_column_letter(j) for j, n in enumerate(cols, 1)}

    def emit(rr, data, bold=False, fill=None, label=None):
        for j, n in enumerate(cols, 1):
            c = ws.cell(row=rr, column=j)
            if label is not None and j == 1:
                c.value = label
            elif n in PCT_MAP:
                num, den = PCT_MAP[n]
                c.value = f"=IFERROR({idx[num]}{rr}/{idx[den]}{rr},0)"
                c.number_format = "0.0%"
            elif label is not None and j <= len(label_cols):
                c.value = None
            else:
                v = data.get(n)
                c.value = None if (v is None or (isinstance(v, float) and pd.isna(v))) else v
                c.number_format = ("#,##0" if n in COUNT_COLS
                                   else "0.00" if n == "Calls per lead" else "General")
            c.font = Font(name=FONT, size=10, bold=bold)
            c.border = B
            if fill:
                c.fill = fill
            c.alignment = Alignment(horizontal="left" if j <= len(label_cols) else "center")

    r = hdr
    for _, d in df.iterrows():
        r += 1
        emit(r, d)
    if total_row is not None:
        r += 1
        emit(r, total_row, bold=True, fill=TOTF, label=total_label)
    return r, hdr


# ------------------------------------------------------------------ main build
def run(inp: Inputs):
    """Returns (workbook, qc rows, cdr_month, stg_month, summary dict)."""
    rep = Report()
    month, till = inp.month, inp.till
    y, mo = int(month[:4]), int(month[5:])
    eom = calendar.monthrange(y, mo)[1]
    r = roster_frame(inp.team_members)
    rep.note("Reporting month", month)
    rep.note("Analysis covers", f"1 to {till} {calendar.month_name[mo]} {y}")
    for k, v in inp.notes:
        rep.note(k, v)

    cdr, cdays = month_rows(rep, "Call log", inp.cdr, "Call Date", month, till)
    stg, _ = month_rows(rep, "Stage report", inp.stg, "Date", month, till)
    if not len(cdr):
        raise SystemExit(f"No call-log rows for {month} 1-{till}: nothing to report.")

    # ---------------- calls
    c = cdr.copy()
    c["caller"] = c["call_owner"].astype(str).str.strip()
    c["phone"] = norm_phone(c["client_number"])
    c["dur"] = pd.to_numeric(c["call_duration"], errors="coerce").fillna(0)
    c["day"] = pd.to_datetime(c["Call Date"]).dt.day
    c = c[c["phone"].str.len() == 10]
    c = decorate(c, r)
    unknown = sorted(set(cdr["call_owner"].astype(str).str.strip()) - set(r.index))
    rep.note("Call-log callers not in Team Members (excluded)",
             f"{len(unknown)}: {', '.join(unknown[:8])}{' ...' if len(unknown) > 8 else ''}")
    c = c[c["vertical"].isin(TARGET_VERTICALS)]
    c["period"] = [period_of(d, month) for d in c["day"]]
    rep.note("Calls in the three verticals", f"{len(c):,}")

    # ---------------- stages: Uzair from its workbook, others from the CSV
    s = stg.copy()
    s["caller"] = s["Stage_Changed_By"].astype(str).str.strip()
    s["phone"] = norm_phone(s["Phone"])
    s["stage"] = norm_stage(s["New_Contact_Stage"]).map(STAGES).values
    s["day"] = pd.to_datetime(s["Date"]).dt.day
    s = s.dropna(subset=["stage"])
    s = s[s["phone"].str.len() == 10]
    dropped = s[~s["caller"].isin(r.index)]["caller"].value_counts()
    s = decorate(s, r)
    s = s[s["vertical"].isin([v for v in TARGET_VERTICALS if v != UZAIR])]
    if len(dropped):
        rep.note("Stage changes by people not in Team Members (excluded)",
                 f"{int(dropped.sum()):,} rows: " + ", ".join(f"{k} ({v})" for k, v in dropped.head(6).items()))

    up = []
    for sheet, key in [("Discovery", "discovery"), ("Roadmap", "roadmap"), ("Follow Up", "followup")]:
        d = inp.uzair.get(sheet)
        if d is None or not len(d):
            rep.note(f"Team Uzair '{sheet}' sheet", "EMPTY or missing")
            continue
        d = d.copy()
        d["dt"] = to_dt(d["Date"])
        d = d[(d["dt"].dt.strftime("%Y-%m") == month) & (d["dt"].dt.day <= till)]
        d["caller"] = d["Owner"].astype(str).str.strip()
        d["phone"] = norm_phone(d["Phone Number"])
        d["stage"] = key
        d["day"] = d["dt"].dt.day
        up.append(d[["caller", "phone", "stage", "day"]])
    u = (pd.concat(up, ignore_index=True).drop_duplicates() if up
         else pd.DataFrame(columns=["caller", "phone", "stage", "day"]))
    u = decorate(u, r)
    u = u[u["vertical"] == UZAIR]
    rep.note("Team Uzair stages (from its own workbook)",
             ", ".join(f"{k}={int((u['stage'] == k).sum())}" for k in STAGE_KEYS))
    cols = ["caller", "phone", "stage", "day", "vertical", "team"]
    stages = pd.concat([s[cols], u[cols]], ignore_index=True)
    stages["period"] = [period_of(int(d), month) for d in stages["day"]]
    disc_all, road_all = stage_history(rep, inp, stg)

    # ---------------- conversions
    b = inp.base.copy()
    b.columns = [str(x) for x in b.columns]
    ccol = [x for x in b.columns if x.startswith("Caller name")][0]
    raw = len(b)
    b = b[b["Enrollment"].astype(str).str.strip() == "New enrollment"].copy()
    b["dt"] = to_dt(b["Date"])
    b = b[(b["dt"].dt.strftime("%Y-%m") == month) & (b["dt"].dt.day <= till)]
    b["caller"] = b[ccol].astype(str).str.strip()
    b["phone"] = norm_phone(b["Contact No"])
    b = decorate(b, r)
    b["period"] = [period_of(d, month) for d in b["dt"].dt.day]
    inscope = b[b["vertical"].isin(TARGET_VERTICALS)]
    other = b[~b["vertical"].isin(TARGET_VERTICALS)]["vertical"].value_counts()
    # every 'New enrollment' row counts - a split payment is two rows and the revenue sheet counts both
    split = inscope[inscope.duplicated(subset=["phone", "dt"], keep=False)]
    if len(split):
        rep.note("Split payments (counted once per row, as in BASE DATA)",
                 "; ".join(f"{n} ({v})" for n, v in split[["Name", "vertical"]].drop_duplicates().values))
    rep.note("New enrollments (BASE DATA)",
             f"{raw:,} rows -> {len(inscope)} in the three verticals"
             + (f"; {int(other.sum())} elsewhere excluded" if len(other) else ""))
    enr = inscope

    lv = r[(r["Vertical"].isin(TARGET_VERTICALS)) & (r["Status"] != "Active")]
    if len(lv):
        rep.note("Non-active roster members counted (tagged in the caller table)",
                 ", ".join(f"{i} [{row['Status']}]" for i, row in lv.iterrows()))

    # ---------------- workbook
    wb = Workbook()
    wb.remove(wb.active)
    summary = {}

    def sheet(title, period, lo, hi, heading):
        ws = wb.create_sheet(title)
        vert = build(c, stages, enr, "vertical", period, road_all, disc_all)
        allr = scope_total(vert)
        if period is None:
            summary.update(allr or {})
        ws["A1"] = heading
        ws["A1"].font = Font(name=FONT, bold=True, size=14, color="1F3864")
        cov = [d for d in cdays if lo <= d <= hi]
        ws["A2"] = (f"Call-log days covered: {len(cov)} of {hi - lo + 1}"
                    + (f" ({', '.join(map(str, cov))})" if cov else " - NO CALL LOG YET")
                    + f"   |   connected = longest call >= {CONNECT_SECONDS}s")
        ws["A2"].font = Font(name=FONT, italic=True, size=10, color="808080")
        row, _ = write_table(ws, 4, "VERTICAL SUMMARY", vert.rename(columns={"vertical": "Vertical"}),
                             ["Vertical"], total_row=allr, total_label="ALL VERTICALS")
        team = build(c, stages, enr, "team", period, road_all, disc_all)
        row, _ = write_table(ws, row + 3, "TEAM-WISE DETAIL",
                             team.rename(columns={"vertical": "Vertical", "team": "Team"}),
                             ["Vertical", "Team"], total_row=allr, total_label="ALL TEAMS")
        cal = build(c, stages, enr, "caller", period, road_all, disc_all)
        if len(cal):
            cal["caller"] = [x if r.loc[x, "Status"] == "Active" else f"{x} [{r.loc[x, 'Status']}]"
                             for x in cal["caller"]]
        row, hdr = write_table(ws, row + 3, "CALLER-WISE DETAIL",
                               cal.rename(columns={"vertical": "Vertical", "team": "Team", "caller": "Caller Name"}),
                               ["Vertical", "Team", "Caller Name"], total_row=allr, total_label="ALL CALLERS")
        ws.freeze_panes = ws.cell(row=hdr + 1, column=4)
        ws.auto_filter.ref = f"A{hdr}:{get_column_letter(3 + len(ORDER))}{row - 1}"
        for j, w in enumerate([18, 34, 26] + [13] * len(ORDER), 1):
            ws.column_dimensions[get_column_letter(j)].width = w

    for name, lo, hi in periods_for(month):
        sheet(f"{name} ({lo}-{hi})", name, lo, hi, f"{name}: {lo}-{hi} {calendar.month_name[mo]} {y}")
    sheet("Monthly Analysis", None, 1, eom, f"MONTHLY ANALYSIS: 1-{till} {calendar.month_name[mo]} {y}")

    ws = wb.create_sheet("Definitions & QC")
    ws["A1"] = "Definitions, rules and data-quality checks"
    ws["A1"].font = Font(name=FONT, bold=True, size=14, color="1F3864")
    rows = [("", ""), ("METRIC DEFINITIONS", ""),
            ("Lead", "One unique phone number in the call log. Dialled 10 times = 1 lead."),
            ("Connected lead", f"A lead whose longest single call reached {CONNECT_SECONDS} seconds."),
            ("DNP lead", f"A lead whose every call was under {CONNECT_SECONDS} seconds - did not pick."),
            ("Discovery / Roadmap / Follow-ups",
             "Unique leads reaching that stage. A lead counts in EVERY stage it reached, so the same lead can appear in all three."),
            ("Discovery -> Enrollments",
             "Unique enrolled phone numbers whose lead reached Discovery but NOT Roadmap. The stage may have happened at ANY time in the stage history - this month or up to three prior months - and it counts whoever did the stage - the row is decided by the caller credited with the enrollment."),
            ("Roadmap -> Enrollments",
             "Unique enrolled phone numbers whose lead reached Roadmap. A number that reached both Discovery and Roadmap is counted here ONLY, never in both columns."),
            ("Why these two do not add up to Conversions",
             "Conversions counts every enrollment ROW (a split payment is two rows); these two columns count UNIQUE numbers. They also exclude enrollments whose lead has no Discovery or Roadmap anywhere in the stage history."),
            ("Conversion", "A 'New enrollment' row in BASE DATA, in the period of its enrollment date. Every row counts - a split payment is two rows and the revenue sheet counts both."),
            ("", ""), ("SOURCES", ""),
            ("Calls", "Calling Analytics dashboard (Acefone, MCube, Ozonetel, manual calls) - the same rows as its CDR download. call_owner is the caller; the log's own Vertical column is ignored."),
            ("Stages - Team Uzair", "Its own live workbook (Discovery / Roadmap / Follow Up sheets)."),
            ("Stages - Deepanshi & Darshan", "Stage_Changed_Report (Calling Analytics dashboard): Stage_Changed_By = caller, New_Contact_Stage = stage."),
            ("Conversions", "Sales Team Reports -> BASE DATA, Enrollment = 'New enrollment', credited to 'Caller name (for ops)'."),
            ("Roster", "Sales Team Reports -> Team Members. Everyone is mapped so totals stay complete; Resigned/Sabbatical are tagged in the caller table."),
            ("", ""), ("RULES", ""),
            ("Periods", "1-10, 11-20, 21 to end of month. No overlapping days."),
            ("Monthly Analysis", "The same three tables for the whole month so far. Leads are re-deduplicated across the month, so its Leads total is normally LOWER than P1+P2+P3 - a number dialled in two periods counts once. Calls, stages and conversions do add up."),
            ("Zero percentages", "A percentage with a zero denominator shows 0.0%, not a blank."),
            ("Why totals differ", "Leads are unique at each level, so a vertical can be lower than the sum of its teams, and a team lower than the sum of its callers."),
            ("", ""), ("CHECKS FROM THIS RUN", "")] + rep.qc
    for i, (k, v) in enumerate(rows, 2):
        ws.cell(row=i, column=1, value=k).font = Font(name=FONT, size=10, bold=(v == "" and k != ""))
        cc = ws.cell(row=i, column=2, value=v)
        cc.font = Font(name=FONT, size=10)
        cc.alignment = Alignment(wrap_text=True, vertical="top")
    ws.column_dimensions["A"].width = 34
    ws.column_dimensions["B"].width = 110
    return wb, rep.qc, cdr, stg, summary
