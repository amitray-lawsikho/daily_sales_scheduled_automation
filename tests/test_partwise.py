import unittest
from datetime import date

import pandas as pd

from partwise import report as R
from partwise.config import load_month, parse_days, sheet_id
from partwise.core import norm_phone, to_dt
from partwise.schedule import decide


class Schedule(unittest.TestCase):
    def test_november_working_days(self):
        days = load_month("2026-11")["working_dates"]
        self.assertEqual(len(days), 23)
        for off in (1, 7, 8, 9, 15, 21, 22):
            self.assertNotIn(date(2026, 11, off), days)

    def test_decide(self):
        self.assertEqual(decide(date(2026, 11, 5))["till"], "4")
        self.assertEqual(decide(date(2026, 11, 7))["run"], "false")          # Saturday week off
        self.assertEqual(decide(date(2026, 11, 10)), {"run": "true", "month": "2026-11", "till": "9", "reason": "working day"})
        close = decide(date(2026, 12, 1))                                    # closes November, no December file needed
        self.assertEqual((close["run"], close["month"], close["till"]), ("true", "2026-11", "30"))
        self.assertEqual(decide(date(2027, 1, 5))["run"], "false")           # no month file -> nothing runs

    def test_parsing(self):
        self.assertEqual(parse_days("2026-11", ["2-3", 5])[-1], date(2026, 11, 5))
        self.assertEqual(sheet_id("https://docs.google.com/spreadsheets/d/1ovSlQT0iNIoe-uBYJzY4eLExCZfzVh4CAev3G609JqM/edit?gid=1"),
                         "1ovSlQT0iNIoe-uBYJzY4eLExCZfzVh4CAev3G609JqM")


class Normalise(unittest.TestCase):
    def test_phone(self):
        self.assertEqual(norm_phone(pd.Series([918921521876.0, "+91 90520 45245", "9052045245.0", 919372526052])).tolist(),
                         ["8921521876", "9052045245", "9052045245", "9372526052"])

    def test_dates(self):
        d = to_dt(pd.Series([46327, "02/11/2026", "2026-11-03", "04/11/2026 10:16:16", None]))
        self.assertEqual([x.strftime("%Y-%m-%d") if pd.notna(x) else None for x in d],
                         ["2026-11-01", "2026-11-02", "2026-11-03", "2026-11-04", None])


class Report(unittest.TestCase):
    def test_small_month(self):
        tm = pd.DataFrame({"Caller Name": ["Asha", "Ravi", "Uma"], "Status": ["Active", "Active", "Resigned"],
                           "Team Name": ["CL", "Closure", "Elite"], "Vertical": ["Team Darshan", "Team Deepanshi", "Team Uzair"]})
        cdr = pd.DataFrame({"client_number": ["9000000001", "9000000001", "9000000002", "919000000003", "9000000004"],
                            "call_duration": ["10", "45", "5", "60", "70"],
                            "call_owner": ["Asha", "Asha", "Asha", "Ravi", "Uma"],
                            "Call Date": ["2026-11-02", "2026-11-03", "2026-11-12", "2026-11-04", "2026-11-05"]})
        stg = pd.DataFrame({"Date": ["2026-11-03", "2026-11-04", "2026-09-20"], "Phone": ["9000000001", "9000000003", "9000000004"],
                            "New_Contact_Stage": ["Discovery Call Done", "Roadmap\xa0Done", "Roadmap Done"],
                            "Stage_Changed_By": ["Asha", "Ravi", "Pratik Sarkar"]})
        base = pd.DataFrame({"Date": [46331, 46331, 46332], "Name": ["A", "A", "B"], "Contact No": [919000000001, 919000000001, 9000000004],
                             "Caller name         (for ops)": ["Asha", "Asha", "Uma"], "Enrollment": ["New enrollment"] * 3})
        uz = {"Discovery": pd.DataFrame(columns=["Date", "Owner", "Phone Number"]),
              "Roadmap": pd.DataFrame(columns=["Date", "Owner", "Phone Number"]),
              "Follow Up": pd.DataFrame({"Date": ["05/11/2026"], "Owner": ["Uma"], "Phone Number": [9000000004.0]})}
        wb, qc, *_, summary = R.run(R.Inputs("2026-11", 15, cdr, stg, tm, base, uz,
                                                 lookback_stage=[("Sep", stg[stg["Date"] < "2026-10"])]))
        self.assertEqual(summary["Total Calls Made"], 5)
        self.assertEqual(summary["Leads (unique numbers dialled)"], 4)
        self.assertEqual(summary["Connected leads"], 3)              # 9000000002 never reached 40 s
        self.assertEqual(summary["Roadmap Done"], 1)                 # non-breaking space folded
        self.assertEqual(summary["Conversions (enrollments)"], 3)    # split payment = 2 rows
        self.assertEqual(summary["Discovery -> Enrollments"], 1)
        self.assertEqual(summary["Roadmap -> Enrollments"], 1)       # off-roster prior-month stage counts
        self.assertEqual(wb.sheetnames, ["P1 (1-10)", "P2 (11-20)", "P3 (21-30)", "Monthly Analysis"])
        for ws in wb.worksheets:
            self.assertIsNone(ws.freeze_panes)


if __name__ == "__main__":
    unittest.main()


class SupabaseShape(unittest.TestCase):
    def test_cdr_and_stage_like_dashboard_download(self):
        from partwise.sources import Supabase, CDR_COLS, STAGE_COLS
        sb = Supabase.__new__(Supabase)
        calls = [{"id": 2, "src": "A", "client_number": "9000000001", "call_datetime": "2026-11-02T05:00:00+00:00",
                  "call_duration": 30, "status": "answered", "direction": "outbound", "service": "c2c", "reason": None,
                  "call_owner": " asha k ", "call_date": "2026-11-02"},
                 {"id": 1, "src": "M", "client_number": "9000000002", "call_datetime": "2026-11-02T06:00:00+00:00",
                  "call_duration": 50, "status": "answered", "direction": "outbound", "service": None, "reason": None,
                  "call_owner": "", "call_date": "2026-11-02"}]
        manual = [{"id": 9, "client_number": "9000000003", "call_duration": 120, "call_owner": "Ravi",
                   "call_date": "2026-11-02", "approved_by": "TL"}]
        stages = [{"id": 5, "date": "2026-11-02", "phone": "9000000001", "new_stage": "Roadmap Done", "changed_by": "ASHA K"}]
        sb.by_day = lambda *a, **k: calls
        sb.all_rows = lambda table, *a, **k: manual if table == "manual_calls" else stages
        tm = pd.DataFrame([{"merge_key": "asha k", "caller_name": "Asha K", "team_name": "CL", "vertical": "Team Darshan", "analyst": None}]).set_index("merge_key")
        cdr = sb.cdr(date(2026, 11, 1), date(2026, 11, 2), tm)
        self.assertEqual(list(cdr.columns), CDR_COLS)
        self.assertEqual(cdr["call_owner"].tolist(), ["Asha K", "Ravi"])        # mapped; blank owner dropped
        self.assertEqual(cdr["source"].tolist(), ["Acefone", "Manual"])
        self.assertEqual(cdr["call_starttime_clean"].iloc[0], "2026-11-02 10:29:30")   # Acefone: end time minus duration
        st = sb.stages(date(2026, 11, 1), date(2026, 11, 2), tm)
        self.assertEqual(list(st.columns), STAGE_COLS)
        self.assertEqual(st["Stage_Changed_By"].tolist(), ["Asha K"])
