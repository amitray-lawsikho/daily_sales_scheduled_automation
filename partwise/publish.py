"""Put the finished workbook in the 'Partwise Data' Drive folder as the month's Google Sheet.

First run of a month: create '<Month>: Part Wise Performance' (xlsx converted to a Google Sheet).
Every later run: replace that same file's content, so the link never changes and Drive's version
history keeps the earlier runs. If Drive refuses the in-place import, fall back to rewriting every
tab through the Sheets API (values and formulas; same file, same link).
"""
from __future__ import annotations

import calendar
import json

from partwise.config import SETTINGS

XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
GSHEET = "application/vnd.google-apps.spreadsheet"
UPLOAD = "https://www.googleapis.com/upload/drive/v3/files"


def report_title(month: str) -> str:
    return SETTINGS["report_title"].format(month_name=calendar.month_name[int(month[5:])], month=month)


def find_report(g, month: str) -> dict | None:
    title = report_title(month).replace("'", "\\'")
    hits = g.find(f"'{SETTINGS['report_folder_id']}' in parents and trashed = false and "
                  f"name = '{title}' and mimeType = '{GSHEET}'")
    return hits[0] if hits else None


def publish(g, month: str, xlsx_path: str, wb) -> str:
    """Returns the Google Sheet URL."""
    with open(xlsx_path, "rb") as f:
        data = f.read()
    hit = find_report(g, month)
    if hit is None:
        meta = {"name": report_title(month), "mimeType": GSHEET, "parents": [SETTINGS["report_folder_id"]]}
        boundary = "partwise-boundary"
        body = (f"--{boundary}\r\nContent-Type: application/json; charset=UTF-8\r\n\r\n{json.dumps(meta)}\r\n"
                f"--{boundary}\r\nContent-Type: {XLSX}\r\n\r\n").encode() + data + f"\r\n--{boundary}--".encode()
        r = g._ok(g.s.post(UPLOAD, params={"uploadType": "multipart", "supportsAllDrives": "true", "fields": "id"},
                           data=body, headers={"Content-Type": f"multipart/related; boundary={boundary}"}))
        fid = r.json()["id"]
        print(f"  created '{report_title(month)}' ({fid})")
    else:
        fid = hit["id"]
        r = g.s.patch(f"{UPLOAD}/{fid}", params={"uploadType": "media", "supportsAllDrives": "true", "fields": "id"},
                      data=data, headers={"Content-Type": XLSX})
        if r.status_code < 300:
            print(f"  replaced '{report_title(month)}' ({fid})")
        else:
            print(f"  Drive import refused ({r.status_code}: {r.text[:200]}); rewriting tabs via the Sheets API")
            rewrite_tabs(g, fid, wb)
            print(f"  rewrote '{report_title(month)}' ({fid})")
    return f"https://docs.google.com/spreadsheets/d/{fid}/edit"


def rewrite_tabs(g, fid: str, wb) -> None:
    base = g.SHEETS + fid
    meta = g._ok(g.s.get(base, params={"fields": "sheets.properties(sheetId,title)"})).json()
    have = {s["properties"]["title"]: s["properties"]["sheetId"] for s in meta.get("sheets", [])}
    want = wb.sheetnames
    reqs = [{"addSheet": {"properties": {"title": t}}} for t in want if t not in have]
    if reqs:
        g._ok(g.s.post(base + ":batchUpdate", json={"requests": reqs}))
    g._ok(g.s.post(base + "/values:batchClear", json={"ranges": [f"'{t}'" for t in want]}))
    data = []
    for ws in wb.worksheets:
        rows = [[("" if v is None else v) for v in row] for row in ws.iter_rows(values_only=True)]
        data.append({"range": f"'{ws.title}'!A1", "values": rows})
    g._ok(g.s.post(base + "/values:batchUpdate", json={"valueInputOption": "USER_ENTERED", "data": data}))
    stale = [have[t] for t in have if t not in want]
    if stale:
        g._ok(g.s.post(base + ":batchUpdate", json={"requests": [{"deleteSheet": {"sheetId": i}} for i in stale]}))
