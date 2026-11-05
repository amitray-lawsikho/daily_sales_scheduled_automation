"""Daily Sales Check for Amit's teams (Elite, Corporate law - Anas, Corporate law - Jyoti).

    python -m dsc run                          # data to yesterday (IST), live sources
    python -m dsc run --date 2026-11-04        # data to a given day
    python -m dsc run --offline DIR            # from files written by --save (no network)
    python -m dsc run --save DIR               # also keep the loaded inputs (contain phones; git-ignored out/)
    python -m dsc run --publish                # upload the PDF + xlsx to Drive

Writes output/dsc/<date>/: Daily Sales Check <date>.pdf, .xlsx (all tables), High-intent leads not dialled
<date>.xlsx (the call list: phone numbers by team and caller) and brief.md.
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import date, datetime, timedelta, timezone

import pandas as pd

from dsc import analysis as A
from dsc import pdf
from dsc import sources as S
from partwise.config import ROOT

IST = timezone(timedelta(hours=5, minutes=30))


def write_xlsx(res: A.Result, path: str) -> None:
    cols_drop = ["gaps", "bench_json"]
    with pd.ExcelWriter(path, engine="openpyxl") as xw:
        pd.DataFrame([{"check": f.check, "team": f.team, "who": f.who, "finding": f.what, "next step": f.next_step,
                       "level": f.level} for f in res.flags]).to_excel(xw, sheet_name="Flags", index=False)
        res.teams.to_excel(xw, sheet_name="Teams MTD", index=False)
        res.callers.drop(columns=[c for c in cols_drop if c in res.callers], errors="ignore").to_excel(xw, sheet_name="Callers MTD", index=False)
        leads = res.leads.copy()
        leads.to_excel(xw, sheet_name="Leads not dialled", index=False)
        res.weekly_team.to_excel(xw, sheet_name="Weekly teams", index=False)
        res.weekly_caller.to_excel(xw, sheet_name="Weekly callers", index=False)
        res.monthly.to_excel(xw, sheet_name="Monthly", index=False)
        res.daily.to_excel(xw, sheet_name="Daily", index=False)
        e = res.early.copy()
        if len(e):
            e["values"] = e["values"].map(lambda v: " / ".join(f"{x:.2f}" for x in v))
            e["benchmarks"] = e["benchmarks"].map(lambda v: " / ".join(f"{x:.2f}" for x in v))
        e.to_excel(xw, sheet_name="Early warning", index=False)
        pd.DataFrame(res.quality, columns=["check", "ok"]).to_excel(xw, sheet_name="Data check", index=False)
        for ws in xw.book.worksheets:
            for col in ws.columns:
                w = max(len(str(c.value or "")) for c in col[:200])
                ws.column_dimensions[col[0].column_letter].width = min(max(9, w + 2), 60)


def write_leads_xlsx(res: A.Result, path: str) -> None:
    """Call list for check 5: one Summary sheet + one sheet per team, phone numbers as text."""
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter
    from dsc.settings import CFG, TEAMS
    L = res.leads.copy()
    ref = getattr(res, "lead_ref", None)
    head_fill, head_font = PatternFill("solid", fgColor="12253F"), Font(bold=True, color="FFFFFF")
    wb = Workbook()
    ws = wb.active
    ws.title = "Summary"
    note = (f"High-intent leads not dialled for over {CFG['leads']['untouched_hours']} h"
            + (f" before {ref:%d %b %Y %H:%M} IST" if ref is not None else "")
            + f". Latest LSQ stage in the last {CFG['leads']['lookback_days']} days is {' / '.join(CFG['leads']['stages'])}, "
              "still open in LSQ, not enrolled (BASE DATA). Held by the lead owner. Oldest first on each team sheet.")
    ws.append([note])
    ws.append([])
    ws.append(["Team", "Caller", "Leads not dialled", "Roadmap Done", "Follow Up For Closure", "No dial at all",
               "Longest wait (h)"])
    hdr_row = ws.max_row
    for tm in TEAMS:
        g = L[L["team"] == tm]
        for caller, x in g.groupby("caller"):
            rm = int(x["stage"].str.startswith("Roadmap").sum())
            ws.append([tm, caller, len(x), rm, len(x) - rm, int(x["last_call"].isna().sum()),
                       None if x["hours"].isna().all() else round(float(x["hours"].max()))])
    cols = ["Caller", "Phone", "Lead name", "Stage set", "Stage set on", "Last dial (IST)", "Hours since last dial",
            "Current LSQ stage", "Stage checked in", "Zipteams intent (latest)", "Called today? (TL to fill)"]
    sheets = [(ws, hdr_row)]
    # leads that were follow-up / roadmap but are no longer open in LSQ (Not Interested, May buy later, ...)
    Dr = getattr(res, "leads_dropped", pd.DataFrame())
    dcols = ["Team", "Caller", "Phone", "Lead name", "Stage set", "Stage set on", "Stage now in LSQ", "Last dial (IST)",
             "Zipteams intent (latest)"]
    for tm in TEAMS:
        t = wb.create_sheet(tm.replace("Corporate law - ", "CL - ")[:31])
        t.append(cols)
        g = L[L["team"] == tm].sort_values(["caller", "hours"], ascending=[True, False], na_position="first")
        for r in g.itertuples():
            t.append([r.caller, str(r.phone), r.name or "", r.stage, pd.Timestamp(r.stage_date).strftime("%d %b %Y"),
                      "no dial in the window" if pd.isna(r.last_call) else pd.Timestamp(r.last_call).strftime("%d %b %Y %H:%M"),
                      None if pd.isna(r.hours) else round(float(r.hours)), r.current_stage or "", r.stage_source,
                      r.zip_intent or "", ""])
        for c in t["B"][1:]:
            c.number_format = "@"          # keep the number as text: no 9.19E+09, no lost digits
        t.auto_filter.ref = f"A1:{get_column_letter(len(cols))}{max(t.max_row, 1)}"
        t.freeze_panes = "A2"
        sheets.append((t, 1))
    t = wb.create_sheet("Dropped - stage changed")
    t.append(dcols)
    for r in Dr.itertuples():
        t.append([r.team, r.caller, str(r.phone), r.name or "", r.stage, pd.Timestamp(r.stage_date).strftime("%d %b %Y"),
                  r.current_stage or "", "no dial in the window" if pd.isna(r.last_call) else pd.Timestamp(r.last_call).strftime("%d %b %Y %H:%M"),
                  r.zip_intent or ""])
    for c in t["C"][1:]:
        c.number_format = "@"
    t.freeze_panes = "A2"
    sheets.append((t, 1))
    for sh, hr in sheets:
        for c in sh[hr]:
            c.fill, c.font = head_fill, head_font
            c.alignment = Alignment(wrap_text=True, vertical="center")
        for col in sh.iter_cols(min_row=hr):
            w = max(len(str(c.value or "")) for c in col[:300])
            sh.column_dimensions[col[0].column_letter].width = min(max(10, w + 2), 40)
    ws["A1"].alignment = Alignment(wrap_text=True)
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=7)
    ws.row_dimensions[1].height = 45
    wb.save(path)


def brief(res: A.Result, links: dict) -> str:
    out = [f"# Daily Sales Check - data to {res.day:%a %d %b %Y}", ""]
    if res.stale:
        out += ["**DATA NOT FRESH** - " + "; ".join(t for t, ok in res.quality if not ok), ""]
    for name, url in links.items():
        out.append(f"- [{name}]({url})")
    if links:
        out.append("")
    out += ["| Team | MTD | Achv (pro-rated) | " + f"{res.prev_wd:%d %b}" + " vs run-rate | Needed/day |", "|---|---|---|---|---|"]
    for _, t in res.teams.iterrows():
        out.append(f"| {t['team']} | Rs {t['mtd']:,.0f} | {pdf.pct(t['achv_pct'])} | Rs {t['prev_wd_rev']:,.0f} "
                   f"({pdf.pct(t['prev_wd_pct'])}) | Rs {t['required_rr']:,.0f} |")
    out.append("")
    for chk in range(1, 7):
        fl = [f for f in res.flags if f.check == chk]
        if fl:
            out.append(f"### Check {chk}")
            for f in fl[:40]:
                out.append(f"- **{f.team} / {f.who}**: {f.what} Next: {f.next_step}")
            out.append("")
    out.append("### Data check")
    out += [f"- {'OK' if ok else '!'} {t}" for t, ok in res.quality]
    return "\n".join(out) + "\n"


def main():
    ap = argparse.ArgumentParser(prog="python -m dsc")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("run")
    p.add_argument("--date", help="last day of data, YYYY-MM-DD (default: yesterday IST)")
    p.add_argument("--offline", help="read inputs from this folder (written by --save)")
    p.add_argument("--save", help="also save the loaded inputs to this folder")
    p.add_argument("--publish", action="store_true", help="upload PDF + xlsx to Drive")
    p.add_argument("--out", default=os.path.join(ROOT, "output", "dsc"))
    a = ap.parse_args()

    now = datetime.now(IST)
    day = date.fromisoformat(a.date) if a.date else (now.date() - timedelta(days=1))
    if a.offline:
        data = S.load_offline(a.offline, day if a.date else None)
        day = data.day
    else:
        data = S.load_live(day)
    if a.save:
        S.save(data, a.save)
        print(f"inputs saved to {a.save}")

    res = A.run(data)
    res.run_date = now.date() if not a.offline else day + timedelta(days=1)
    folder = os.path.join(a.out, day.isoformat())
    os.makedirs(folder, exist_ok=True)
    base = os.path.join(folder, f"Daily Sales Check {day.isoformat()}")
    pdf.build(res, base + ".pdf")
    write_xlsx(res, base + ".xlsx")
    leads_path = os.path.join(folder, f"High-intent leads not dialled {day.isoformat()}.xlsx")
    write_leads_xlsx(res, leads_path)
    print(f"Wrote {base}.pdf, .xlsx and {os.path.basename(leads_path)}")

    links = {}
    if a.publish:
        from dsc.publish import publish
        links = publish([base + ".pdf", leads_path, base + ".xlsx"])
        for k, v in links.items():
            print(f"  {k}: {v}")
    text = brief(res, links)
    with open(os.path.join(folder, "brief.md"), "w", encoding="utf-8") as f:
        f.write(text)
    print(text[:3000])
    gs = os.environ.get("GITHUB_STEP_SUMMARY")
    if gs:
        with open(gs, "a", encoding="utf-8") as f:
            f.write(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
