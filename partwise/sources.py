"""Where the inputs come from.

* Calls + stage changes: Supabase "Calling Analytics" (the calling dashboard's database), read with
  the service key and shaped exactly like the dashboard's CDR / stage-change downloads (ca_cdr,
  ca_stage_export). Supabase keeps 90 days, so months that are older come from history/*.zip.
* Sales Team Reports (Team Members, BASE DATA) and Team Uzair workbooks: Google Sheets API.
* Local mode (--local DIR): the same inputs from files, for testing or a manual fallback.
"""
from __future__ import annotations

import glob
import io
import json
import os
import time
import zipfile
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta

import pandas as pd
import requests

from partwise.config import ROOT, SETTINGS

HISTORY = os.path.join(ROOT, "history")
CDR_COLS = ["client_number", "call_datetime", "call_starttime_clean", "call_endtime_clean", "call_duration",
            "status", "direction", "service", "reason", "call_owner", "Call Date", "updated_at_ampm",
            "Team Name", "Vertical", "Analyst", "source"]
STAGE_COLS = ["Date", "FirstName", "LastName", "EmailAddress", "Phone", "Alternate_Phone_Number",
              "New_Contact_Stage", "Stage_Changed_By", "Team Name", "Vertical", "StageChangeComment"]


def month_bounds(month: str) -> tuple[date, date]:
    y, m = int(month[:4]), int(month[5:])
    first = date(y, m, 1)
    nxt = date(y + (m == 12), m % 12 + 1, 1)
    return first, nxt - timedelta(days=1)


def prev_months(month: str, n: int) -> list[str]:
    y, m = int(month[:4]), int(month[5:])
    out = []
    for _ in range(n):
        y, m = (y - 1, 12) if m == 1 else (y, m - 1)
        out.append(f"{y}-{m:02d}")
    return out


# ------------------------------------------------------------------ history zips
def history_zip(month: str) -> str:
    return os.path.join(HISTORY, f"LSQ_Partwise_Data_{month}.zip")


def read_zip(path: str, member: str) -> pd.DataFrame | None:
    with zipfile.ZipFile(path) as z:
        names = [n for n in z.namelist() if n.lower().endswith(".csv") and member.lower() in os.path.basename(n).lower()]
        if not names:
            return None
        return pd.concat([pd.read_csv(z.open(n), dtype=str, low_memory=False) for n in names], ignore_index=True)


def write_history_zip(month: str, cdr: pd.DataFrame, stg: pd.DataFrame, path: str | None = None) -> str:
    """One zip per month holding both CSVs, the same layout as the cowork project's zips."""
    path = path or history_zip(month)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for df, name, datecol in [(cdr, f"CDR_LOG_{month}", "Call Date"), (stg, f"Stage_Changed_Report_{month}", "Date")]:
            zf.writestr(f"{name}.csv", df.sort_values(datecol, kind="stable").to_csv(index=False))
    print(f"  wrote {os.path.relpath(path, ROOT)}  {os.path.getsize(path) / 1e6:.1f} MB")
    return path


# ------------------------------------------------------------------ Supabase (Calling Analytics)
class Supabase:
    PAGE = 1000

    def __init__(self):
        key = os.environ.get("CALL_SUPABASE_KEY", "").strip()
        if not key:
            raise SystemExit("CALL_SUPABASE_KEY is not set (Calling Analytics service-role key, as a GitHub secret).")
        url = os.environ.get("CALL_SUPABASE_URL", "").strip() or SETTINGS["supabase_url"]
        self.base = url.rstrip("/") + "/rest/v1/"
        self.s = requests.Session()
        self.s.headers.update({"apikey": key, "Authorization": f"Bearer {key}", "Accept": "application/json"})

    def get(self, table: str, params: list) -> list[dict]:
        for attempt in range(5):
            try:
                r = self.s.get(self.base + table, params=params, timeout=120)
                if r.status_code < 500:
                    break
            except requests.RequestException:
                if attempt == 4:
                    raise
            time.sleep(2 ** attempt)
        if r.status_code >= 300:
            raise RuntimeError(f"Supabase {table}: HTTP {r.status_code} {r.text[:300]}")
        return r.json()

    def all_rows(self, table: str, columns: str, filters: list) -> list[dict]:
        """Keyset paging on id; stops on an empty page so a lower server row cap cannot cut it short."""
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

    def by_day(self, table: str, columns: str, datecol: str, lo: date, hi: date) -> list[dict]:
        days = [lo + timedelta(days=i) for i in range((hi - lo).days + 1)]
        with ThreadPoolExecutor(max_workers=6) as ex:
            parts = ex.map(lambda d: self.all_rows(table, columns, [(datecol, f"eq.{d.isoformat()}")]), days)
        return [r for part in parts for r in part]

    def first_date(self, table: str, datecol: str) -> date | None:
        r = self.get(table, [("select", datecol), ("order", f"{datecol}.asc"), ("limit", "1")])
        return date.fromisoformat(r[0][datecol]) if r else None

    def team_map(self) -> pd.DataFrame:
        tm = pd.DataFrame(self.get("team_map", [("select", "merge_key,caller_name,team_name,vertical,analyst"),
                                                ("order", "merge_key.asc"), ("limit", "100000")]))
        return tm.drop_duplicates("merge_key").set_index("merge_key") if len(tm) else tm

    @staticmethod
    def _owner(raw: pd.Series, tm: pd.DataFrame) -> tuple[pd.Series, pd.DataFrame]:
        key = raw.fillna("").astype(str).str.strip().str.lower()
        hit = tm.reindex(key.values) if len(tm) else pd.DataFrame(index=key.values, columns=["caller_name", "team_name", "vertical", "analyst"])
        hit.index = raw.index
        owner = hit["caller_name"].where(hit["caller_name"].notna(), raw)
        return owner, hit

    def cdr(self, lo: date, hi: date, tm: pd.DataFrame) -> pd.DataFrame:
        """Same rows and columns as the dashboard's CDR download (ca_cdr): calls + manual calls,
        call_owner mapped through team_map, rows without an owner dropped."""
        calls = pd.DataFrame(self.by_day("calls", "id,src,client_number,call_datetime,call_duration,status,direction,service,reason,call_owner,call_date",
                                         "call_date", lo, hi))
        man = pd.DataFrame(self.all_rows("manual_calls", "id,client_number,call_duration,call_owner,call_date,approved_by",
                                         [("call_date", f"gte.{lo}"), ("call_date", f"lte.{hi}")]))
        out = []
        if len(calls):
            owner, hit = self._owner(calls["call_owner"], tm)
            dt = pd.to_datetime(calls["call_datetime"], utc=True)
            ist = dt.dt.tz_convert("Asia/Kolkata").dt.tz_localize(None)
            dur = pd.to_timedelta(pd.to_numeric(calls["call_duration"], errors="coerce").fillna(0), unit="s")
            ace = calls["src"] == "A"
            out.append(pd.DataFrame({
                "client_number": calls["client_number"],
                "call_datetime": dt.dt.strftime("%Y-%m-%d %H:%M:%S") + "+00:00",
                "call_starttime_clean": (ist - dur.where(ace, pd.Timedelta(0))).dt.strftime("%Y-%m-%d %H:%M:%S"),
                "call_endtime_clean": (ist + dur.where(~ace, pd.Timedelta(0))).dt.strftime("%Y-%m-%d %H:%M:%S"),
                "call_duration": calls["call_duration"], "status": calls["status"], "direction": calls["direction"],
                "service": calls["service"], "reason": calls["reason"], "call_owner": owner,
                "Call Date": calls["call_date"], "updated_at_ampm": None,
                "Team Name": hit["team_name"], "Vertical": hit["vertical"], "Analyst": hit["analyst"],
                "source": calls["src"].map({"A": "Acefone", "O": "Ozonetel"}).fillna("MCube"),
                "_id": calls["id"]}))
        if len(man):
            owner, hit = self._owner(man["call_owner"], tm)
            out.append(pd.DataFrame({
                "client_number": man["client_number"], "call_datetime": None, "call_starttime_clean": None,
                "call_endtime_clean": None, "call_duration": man["call_duration"], "status": "answered",
                "direction": "outbound", "service": None, "reason": man["approved_by"], "call_owner": owner,
                "Call Date": man["call_date"], "updated_at_ampm": None, "Team Name": hit["team_name"],
                "Vertical": hit["vertical"], "Analyst": hit["analyst"], "source": "Manual", "_id": man["id"]}))
        if not out:
            return pd.DataFrame(columns=CDR_COLS)
        df = pd.concat(out, ignore_index=True)
        df = df[df["call_owner"].fillna("").astype(str) != ""]
        df = df.sort_values(["Call Date", "_id"], kind="stable").drop(columns="_id")
        return df.astype({"call_duration": str}).reset_index(drop=True)[CDR_COLS]

    def stages(self, lo: date, hi: date, tm: pd.DataFrame, columns: str | None = None) -> pd.DataFrame:
        """Same shape as the dashboard's stage-change download (ca_stage_export)."""
        rows = pd.DataFrame(self.all_rows("stage_changes", columns or "id,date,first_name,last_name,email,phone,alt_phone,new_stage,changed_by,comment",
                                          [("date", f"gte.{lo}"), ("date", f"lte.{hi}")]))
        if not len(rows):
            return pd.DataFrame(columns=STAGE_COLS)
        rows = rows.sort_values(["date", "id"], kind="stable")
        owner, hit = self._owner(rows["changed_by"], tm) if "changed_by" in rows else (None, None)
        g = lambda c: rows[c] if c in rows else None
        df = pd.DataFrame({"Date": rows["date"], "FirstName": g("first_name"), "LastName": g("last_name"),
                           "EmailAddress": g("email"), "Phone": rows["phone"], "Alternate_Phone_Number": g("alt_phone"),
                           "New_Contact_Stage": rows["new_stage"], "Stage_Changed_By": owner,
                           "Team Name": None if hit is None else hit["team_name"],
                           "Vertical": None if hit is None else hit["vertical"], "StageChangeComment": g("comment")})
        return df.reset_index(drop=True)


# ------------------------------------------------------------------ Google
SCOPES = ["https://www.googleapis.com/auth/drive"]


def google_session():
    """OAuth refresh token (preferred: files are owned by Amit) or a service account JSON."""
    from google.auth.transport.requests import AuthorizedSession
    if os.environ.get("GOOGLE_OAUTH_REFRESH_TOKEN", "").strip():
        from google.oauth2.credentials import Credentials
        creds = Credentials(None, refresh_token=os.environ["GOOGLE_OAUTH_REFRESH_TOKEN"].strip(),
                            client_id=os.environ["GOOGLE_OAUTH_CLIENT_ID"].strip(),
                            client_secret=os.environ["GOOGLE_OAUTH_CLIENT_SECRET"].strip(),
                            token_uri="https://oauth2.googleapis.com/token", scopes=SCOPES)
    elif os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON", "").strip():
        from google.oauth2 import service_account
        creds = service_account.Credentials.from_service_account_info(
            json.loads(os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"]), scopes=SCOPES)
    else:
        raise SystemExit("No Google credentials: set GOOGLE_OAUTH_CLIENT_ID / _CLIENT_SECRET / _REFRESH_TOKEN "
                         "(or GOOGLE_SERVICE_ACCOUNT_JSON) as GitHub secrets.")
    return AuthorizedSession(creds)


class Google:
    SHEETS = "https://sheets.googleapis.com/v4/spreadsheets/"
    DRIVE = "https://www.googleapis.com/drive/v3/files"

    def __init__(self):
        self.s = google_session()

    def _ok(self, r):
        if r.status_code >= 300:
            raise RuntimeError(f"Google API {r.request.method} {r.url.split('?')[0]} -> {r.status_code}: {r.text[:400]}")
        return r

    def sheet_titles(self, sid: str) -> list[str]:
        r = self._ok(self.s.get(self.SHEETS + sid, params={"fields": "sheets.properties.title"}))
        return [x["properties"]["title"] for x in r.json().get("sheets", [])]

    def tab(self, sid: str, title: str) -> pd.DataFrame | None:
        """A whole tab as a DataFrame (row 1 = header). Raw values: dates arrive as serial numbers
        (core.to_dt converts them), phones as plain numbers."""
        if title not in self.sheet_titles_cached(sid):
            return None
        rng = "'" + title.replace("'", "''") + "'"
        r = self._ok(self.s.get(self.SHEETS + sid + "/values/" + requests.utils.quote(rng, safe=""),
                                params={"valueRenderOption": "UNFORMATTED_VALUE", "dateTimeRenderOption": "SERIAL_NUMBER"}))
        vals = r.json().get("values", [])
        if not vals:
            return pd.DataFrame()
        hdr = [str(h) if h is not None else "" for h in vals[0]]
        # blank / duplicate header cells get unique names so pandas keeps every column
        seen = {}
        for i, h in enumerate(hdr):
            h = h or f"_col{i}"
            seen[h] = seen.get(h, 0) + 1
            hdr[i] = h if seen[h] == 1 else f"{h}.{seen[h] - 1}"
        n = len(hdr)
        body = [(row + [None] * n)[:n] for row in vals[1:]]
        df = pd.DataFrame(body, columns=hdr)
        return df.replace("", None)

    _titles: dict = {}

    def sheet_titles_cached(self, sid):
        if sid not in self._titles:
            self._titles[sid] = self.sheet_titles(sid)
        return self._titles[sid]

    def find(self, q: str) -> list[dict]:
        r = self._ok(self.s.get(self.DRIVE, params={"q": q, "fields": "files(id,name,createdTime,modifiedTime)",
                                                   "orderBy": "createdTime desc", "pageSize": 50,
                                                   "supportsAllDrives": "true", "includeItemsFromAllDrives": "true"}))
        return r.json().get("files", [])

    def uzair_book(self, sid: str, sheets=("Discovery", "Roadmap", "Follow Up")) -> dict:
        return {s: self.tab(sid, s) for s in sheets}

    def uzair_archive(self, month: str) -> dict | None:
        """The renamed copy of a past month's Uzair live sheet, e.g.
        'Followup / Discovery / Roadmap Created LSQ - Team Uzair (October)', created after that month began."""
        import calendar
        name = calendar.month_name[int(month[5:])]
        first, _ = month_bounds(month)
        q = (f"'{SETTINGS['uzair_folder_id']}' in parents and trashed = false and "
             f"name contains 'Team Uzair ({name})' and createdTime > '{first.isoformat()}T00:00:00'")
        hits = self.find(q)
        return hits[0] if hits else None


# ------------------------------------------------------------------ local files (testing / fallback)
def local_xlsx(path: str, sheet: str) -> pd.DataFrame | None:
    try:
        return pd.read_excel(path, sheet_name=sheet)
    except ValueError:
        return None


def local_feed(folder: str, member: str) -> pd.DataFrame:
    frames = []
    for f in sorted(glob.glob(os.path.join(folder, "*.zip"))):
        df = read_zip(f, member)
        if df is not None:
            frames.append(df)
    for f in sorted(glob.glob(os.path.join(folder, f"*{member}*.csv"))):
        frames.append(pd.read_csv(f, dtype=str, low_memory=False))
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
