"""Daily Sales Check: calendar, targets, run-rate, untouched leads, early warning, the 'why' and the PDF,
on a small synthetic data set (no network)."""
import os
import tempfile
import unittest
from datetime import date, timedelta

import pandas as pd

from dsc import analysis as A
from dsc.schedule import decide
from dsc.settings import previous_working_day
from dsc.sources import Data, targets_frame

D = date(2026, 11, 4)          # Wed; Nov working days 2-6, 10-14, 16-20, 23-30 (23 days)
TEAM = "Elite"


def synthetic() -> Data:
    callers = {"Good One": 1_300_000, "Good Two": 1_300_000, "Good Three": 500_000, "Slow Dialler": 500_000}
    t = []
    for m in ("2026-10", "2026-11"):
        for c, tgt in callers.items():
            t.append({"month": m, "caller": c, "team": TEAM, "role": "Academic Counselor - Closure", "status": "Active", "target": tgt})
        t.append({"month": m, "caller": "Team Lead", "team": TEAM, "role": "TL", "status": "Active", "target": None})
    targets = pd.DataFrame(t)
    rev, agent, cday, stages = [], [], [], []
    day = date(2026, 9, 21)
    while day <= D:
        for c in callers:
            slow = c == "Slow Dialler"
            if day.weekday() < 6:
                agent.append({"call_date": day.isoformat(), "caller": c, "team": TEAM, "total_calls": 60 if slow else 200,
                              "answered": 15 if slow else 60, "calls_3m": 2 if slow else 8, "calls_15_20": 0 if slow else 2,
                              "calls_20p": 0 if slow else 1, "dur_3m": 0, "prod_sec": 0, "break_sec": 3600, "break_count": 3,
                              "unique_leads": 50, "issues": "Late Check-In" if slow else ""})
                cday.append({"call_date": day.isoformat(), "caller": c, "talk_sec": 3000 if slow else 12000, "longest_sec": 1500})
                stages.append({"date": day.isoformat(), "phone": f"9{abs(hash((c, day))) % 10**9:09d}", "stage": "followup",
                               "owner": c, "src": "test"})
                if not slow and day.weekday() == 2:
                    rev.append({"txn_date": day.isoformat(), "team": TEAM, "caller": c, "caller_status": "current", "revenue": 150000,
                                "enrolments": 2, "payments": 2, "calling_rev": 150000, "collection_rev": 0})
        day += timedelta(days=1)
    # one high-intent lead set on 2 Nov, last dialled 2 Nov 10:00 -> untouched; one dialled 4 Nov -> fine
    stages += [{"date": "2026-11-02", "phone": "9000000001", "stage": "roadmap", "owner": "Good One", "src": "test"},
               {"date": "2026-11-02", "phone": "9000000002", "stage": "followup", "owner": "Slow Dialler", "src": "test"},
               {"date": "2026-11-02", "phone": "9000000003", "stage": "followup", "owner": "Slow Dialler", "src": "test"}]
    touches = pd.DataFrame([{"phone": "9000000001", "last_call": "2026-11-02 10:00:00"},
                            {"phone": "9000000002", "last_call": "2026-11-05 10:00:00"},
                            {"phone": "9999999999", "last_call": "2026-11-05 11:30:00"}])
    enrolled = pd.DataFrame({"phone": ["9000000003"]})
    fresh = {"rev_refresh": "2026-11-05T06:10:00+00:00", "call_refresh": "2026-11-05T06:12:00+00:00",
             "rev_last_date": D.isoformat(), "call_last_date": D.isoformat(), "unmapped": []}
    s = lambda rows: pd.DataFrame(rows).astype(str)
    return Data(D, s(rev), s(agent), s(cday), touches.astype(str), s(stages), targets, enrolled,
                pd.DataFrame(columns=["phone", "current_stage", "current_owner"]), pd.DataFrame(), fresh)


class Calendar(unittest.TestCase):
    def test_schedule(self):
        self.assertEqual(decide(date(2026, 11, 5)), {"run": "true", "date": "2026-11-04", "reason": "working day"})
        self.assertEqual(decide(date(2026, 11, 7))["run"], "false")      # week off
        self.assertEqual(decide(date(2026, 11, 10))["date"], "2026-11-09")
        self.assertEqual(decide(date(2027, 3, 2))["run"], "false")       # no month file

    def test_previous_working_day(self):
        self.assertEqual(previous_working_day(date(2026, 11, 10)), date(2026, 11, 6))   # 7-9 Nov week off
        self.assertEqual(previous_working_day(date(2026, 11, 5)), date(2026, 11, 4))


class Targets(unittest.TestCase):
    def test_sheet_rows(self):
        tl = pd.DataFrame([["a@x", "TL", "Lead", TEAM, "Team Uzair", "", "Active", "", "01/11/2026"],
                           ["b@x", "Academic Counselor - Closure", "Caller B", TEAM, "Team Uzair", "", "Active", "1,300,000", "01/11/2026"],
                           ["c@x", "Academic Counselor", "Caller C", "Other team", "Team Uzair", "", "Active", "500,000", "01/11/2026"]],
                          columns=["Email id", "Academic Counselor/TL/ATL", "Caller Name", "Team Name", "Vertical", "Analyst",
                                   "Status", "Target", "Month"])
        t = targets_frame(tl)
        self.assertEqual(t["caller"].tolist(), ["Lead", "Caller B"])     # other teams dropped
        self.assertEqual(t["month"].unique().tolist(), ["2026-11"])
        self.assertEqual(t.loc[t["caller"] == "Caller B", "target"].iloc[0], 1_300_000)


class Checks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.res = A.run(synthetic())

    def test_team_run_rate_and_pro_rating(self):
        t = self.res.teams.set_index("team").loc[TEAM]
        self.assertEqual(t["target"], 3_600_000)                          # TL has no target
        self.assertAlmostEqual(t["run_rate"], 3_600_000 / 23)
        self.assertAlmostEqual(t["prorated"], 3_600_000 * 3 / 23)        # 2, 3, 4 Nov elapsed
        self.assertEqual(t["mtd"], 450_000)                               # 3 callers x 150k on Wed 4 Nov
        self.assertEqual(t["prev_wd_rev"], 450_000)

    def test_untouched_leads(self):
        L = self.res.leads
        L = L[L["phone"].str.startswith("900000000")]                   # the three planted leads
        self.assertEqual(L["phone"].tolist(), ["9000000001"])             # 02: dialled 5 Nov, 03: enrolled
        self.assertEqual(L["caller"].iloc[0], "Good One")
        self.assertGreater(L["hours"].iloc[0], 24)

    def test_early_warning_and_why(self):
        e = self.res.early
        self.assertIn("Slow Dialler", set(e["caller"]))
        self.assertNotIn("Good One", set(e["caller"]))
        c = self.res.callers.set_index("caller")
        self.assertEqual(c.loc["Slow Dialler", "primary_key"], "calls_per_day")
        self.assertEqual(c.loc["Slow Dialler", "late_days"], 3)
        self.assertNotIn("Team Lead", set(e["caller"]))
        self.assertTrue(c.loc["Team Lead", "lead"])

    def test_bottom_three_excludes_leads(self):
        top, bot = self.res.top_bottom[TEAM]
        self.assertEqual(bot["caller"].iloc[0], "Slow Dialler")
        self.assertNotIn("Team Lead", set(top["caller"]) | set(bot["caller"]))

    def test_leads_excel_keeps_phone_as_text(self):
        from openpyxl import load_workbook
        from dsc.__main__ import write_leads_xlsx
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "leads.xlsx")
            write_leads_xlsx(self.res, p)
            ws = load_workbook(p)[TEAM]
            phones = [c.value for c in ws["B"][1:]]
            self.assertIn("9000000001", phones)
            self.assertTrue(all(isinstance(v, str) and len(v) == 10 for v in phones))

    def test_pdf_builds(self):
        from dsc import pdf
        with tempfile.TemporaryDirectory() as d:
            p = pdf.build(self.res, os.path.join(d, "x.pdf"))
            self.assertGreater(os.path.getsize(p), 20_000)


if __name__ == "__main__":
    unittest.main()
