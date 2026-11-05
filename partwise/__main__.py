"""Part Wise Connectivity report.

    python -m partwise run --month 2026-11 --till 4 --publish     # live: Supabase + Google, upload to Drive
    python -m partwise run --month 2026-10 --till 30 --local DIR  # from files (zips/CSVs + the two xlsx)

The report is written to output/Partwise Analysis 1-<till>.xlsx. On a month-close run (till = last
day) the month's calls + stage changes are frozen into history/LSQ_Partwise_Data_<month>.zip,
because the dashboard only keeps 90 days and the next three months need that stage history.
"""
from __future__ import annotations

import argparse
import calendar
import glob
import os
import sys
from datetime import date

import pandas as pd

from partwise import report as R
from partwise import sources as S
from partwise.config import ROOT, SETTINGS, load_month
from partwise.core import to_dt

OUT = os.path.join(ROOT, "output")
UZ_TABS = ("Discovery", "Roadmap", "Follow Up")


def rows_in_month(book: dict, month: str, till: int) -> int:
    n = 0
    for d in book.values():
        if d is not None and len(d) and "Date" in d.columns:
            dt = to_dt(d["Date"])
            n += int(((dt.dt.strftime("%Y-%m") == month) & (dt.dt.day <= till)).sum())
    return n


def load_live(month: str, till: int, notes: list) -> tuple[R.Inputs, str]:
    cfg = load_month(month)
    if cfg is None or not cfg["sales_sheet_id"]:
        raise SystemExit(f"config/months/{month}.json is missing or has no sales_sheet.")
    first, last = S.month_bounds(month)
    hi = date(first.year, first.month, till)

    sb = S.Supabase()
    tm = sb.team_map()
    call_from, stage_from = sb.first_date("calls", "call_date"), sb.first_date("stage_changes", "date")
    zp = S.history_zip(month)
    if call_from and call_from <= first:
        cdr, csrc = sb.cdr(first, hi, tm), "supabase"
    elif os.path.isfile(zp):
        cdr, csrc = S.read_zip(zp, "CDR"), "history"
    else:
        raise SystemExit(f"Calls for {month} are no longer in Supabase (kept from {call_from}) and {zp} is missing.")
    if stage_from and stage_from <= first:
        stg = sb.stages(first, hi, tm)
    elif os.path.isfile(zp):
        stg = S.read_zip(zp, "Stage")
    else:
        raise SystemExit(f"Stage changes for {month} are not in Supabase (kept from {stage_from}) and {zp} is missing.")
    notes.append(("Calls / stage source", "Calling Analytics dashboard (Supabase)" if csrc == "supabase"
                  else f"history/{os.path.basename(zp)}"))

    look, missing = [], []
    for pm in S.prev_months(month, SETTINGS["lookback_months"]):
        plo, phi = S.month_bounds(pm)
        got = False
        if os.path.isfile(S.history_zip(pm)):
            look.append((f"history/{os.path.basename(S.history_zip(pm))}", S.read_zip(S.history_zip(pm), "Stage")))
            got = True
        if stage_from and stage_from <= phi:
            look.append((f"Supabase stage changes {max(plo, stage_from)}..{phi}",
                         sb.stages(max(plo, stage_from), phi, tm, columns="id,date,phone,new_stage")))
            got = True
        if not got:
            missing.append(pm)
    if missing:
        notes.append(("Stage lookback MISSING", f"no stage history for {', '.join(missing)} - add "
                      "history/LSQ_Partwise_Data_<month>.zip, or the two Stage -> Enrollments columns under-report"))

    g = S.Google()
    team = g.tab(cfg["sales_sheet_id"], "Team Members")
    base = g.tab(cfg["sales_sheet_id"], "BASE DATA")
    if team is None or base is None:
        raise SystemExit("The sales sheet has no 'Team Members' or 'BASE DATA' tab.")

    if cfg.get("uzair_sheet_id"):
        uz_id, uz_label = cfg["uzair_sheet_id"], "config uzair_sheet"
    else:
        arch = g.uzair_archive(month)
        uz_id, uz_label = (arch["id"], arch["name"]) if arch else (SETTINGS["uzair_live_sheet_id"], "live sheet")
    uz = g.uzair_book(uz_id, UZ_TABS)
    n = rows_in_month(uz, month, till)
    notes.append(("Team Uzair workbook", f"{uz_label}: {n:,} stage rows dated {month} 1-{till}"))
    if n == 0 and till >= 5:
        raise SystemExit(f"The Team Uzair workbook ({uz_label}) has no rows for {month} 1-{till}. If the live "
                         "sheet was already reset for the new month, rename the old copy '... Team Uzair (<Month>)' "
                         "or set uzair_sheet in the month file, then re-run.")
    luz = []
    for pm in S.prev_months(month, SETTINGS["lookback_months"]):
        arch = g.uzair_archive(pm)
        if arch:
            luz.append((arch["name"], g.uzair_book(arch["id"], ("Discovery", "Roadmap"))))
        else:
            notes.append((f"Team Uzair workbook for {pm}", "not found in Drive (lookback only)"))
    return R.Inputs(month, till, cdr, stg, team, base, uz, look, luz, notes), csrc


def load_local(folder: str, month: str, till: int, notes: list) -> R.Inputs:
    """DIR holds: zips and/or *CDR*/*Stage* CSVs, one *Sales*.xlsx, one *Uzair*.xlsx, optional
    uzair_history/*.xlsx. Prior months' stages also come from the repo's history/."""
    cdr, stg = S.local_feed(folder, "CDR"), S.local_feed(folder, "Stage")
    if not len(cdr):
        zp = S.history_zip(month)
        if os.path.isfile(zp):
            cdr, stg = S.read_zip(zp, "CDR"), S.read_zip(zp, "Stage")
    sales = (glob.glob(os.path.join(folder, "*Sales*.xlsx")) or [None])[0]
    uzf = (glob.glob(os.path.join(folder, "*Uzair*.xlsx")) or [None])[0]
    if not sales or not uzf:
        raise SystemExit(f"{folder} needs a *Sales*.xlsx and a *Uzair*.xlsx.")
    look = [(f"{os.path.basename(folder)} stage feed (all months)", stg)]
    for pm in S.prev_months(month, SETTINGS["lookback_months"]):
        if os.path.isfile(S.history_zip(pm)):
            look.append((f"history/{os.path.basename(S.history_zip(pm))}", S.read_zip(S.history_zip(pm), "Stage")))
    uz = {t: S.local_xlsx(uzf, t) for t in UZ_TABS}
    luz = [(os.path.basename(p), {t: S.local_xlsx(p, t) for t in ("Discovery", "Roadmap")})
           for p in sorted(glob.glob(os.path.join(folder, "uzair_history", "*.xlsx")))]
    notes.append(("Inputs", f"local folder {folder}"))
    return R.Inputs(month, till, cdr, stg, S.local_xlsx(sales, "Team Members"), S.local_xlsx(sales, "BASE DATA"),
                    uz, look, luz, notes)


def main():
    ap = argparse.ArgumentParser(prog="python -m partwise")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("run")
    p.add_argument("--month", required=True, help="YYYY-MM")
    p.add_argument("--till", type=int, required=True, help="last day to include")
    p.add_argument("--local", help="read inputs from this folder instead of Supabase/Google")
    p.add_argument("--publish", action="store_true", help="create/replace the month's Google Sheet in Drive")
    p.add_argument("--write-history", choices=["auto", "yes", "no"], default="auto",
                   help="freeze this month's data into history/ (auto = only on the month-close run, live mode)")
    a = ap.parse_args()

    month, till = a.month, a.till
    eom = calendar.monthrange(int(month[:4]), int(month[5:]))[1]
    if not 1 <= till <= eom:
        raise SystemExit(f"--till must be 1..{eom}")
    notes: list = []
    if a.local:
        inp, src = load_local(a.local, month, till, notes), "local"
    else:
        inp, src = load_live(month, till, notes)

    wb, qc, cdr, stg, summary = R.run(inp)
    os.makedirs(OUT, exist_ok=True)
    out = os.path.join(OUT, f"Partwise Analysis 1-{till}.xlsx")
    wb.save(out)
    print(f"\nWrote {out}")

    if a.write_history == "yes" or (a.write_history == "auto" and src == "supabase" and till == eom):
        S.write_history_zip(month, cdr, stg)

    url = None
    if a.publish:
        from partwise.publish import publish
        url = publish(S.Google(), month, out, wb)
        print(f"  {url}")

    gs = os.environ.get("GITHUB_STEP_SUMMARY")
    if gs:
        with open(gs, "a", encoding="utf-8") as f:
            f.write(f"## Part Wise Connectivity - {month}, 1-{till}\n\n")
            if url:
                f.write(f"Sheet: {url}\n\n")
            f.write("| Total calls | Leads | Connected | Conversions | Discovery->Enr | Roadmap->Enr |\n|---|---|---|---|---|---|\n")
            f.write(f"| {summary.get('Total Calls Made', 0):,} | {summary.get('Leads (unique numbers dialled)', 0):,} | "
                    f"{summary.get('Connected leads', 0):,} | {summary.get('Conversions (enrollments)', 0):,} | "
                    f"{summary.get('Discovery -> Enrollments', 0):,} | {summary.get('Roadmap -> Enrollments', 0):,} |\n\n")
            f.write("### Checks\n\n" + "\n".join(f"- **{k}**: {v}" for k, v in qc) + "\n")


if __name__ == "__main__":
    sys.exit(main())
