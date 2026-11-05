"""Make sure both dashboards have refreshed after the revenue sheet is complete (about 11:30 IST)
before any 12:00 report runs. Used by the daily workflow ahead of Part Wise and the Daily Sales Check.

For each dashboard (Revenue Analytics, Calling Analytics):
  1. done already: a successful refresh_log run after <fresh_after_ist> today -> nothing to do;
  2. else, if no refresh was requested after that time, start one (the dashboard's own
     _dispatch_refresh, the same call as its Update button and its pg_cron jobs);
  3. wait until refresh_log shows a run after the request, up to <wait_minutes>.

    python -m dsc.refresh                # what the workflow runs
    python -m dsc.refresh --check        # report only, start nothing

Never fails the workflow: if a dashboard does not finish in time the reports still run and say the
data is not fresh. Standard library + requests only.
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from datetime import datetime, timedelta, timezone

import requests

from dsc.settings import CFG

IST = timezone(timedelta(hours=5, minutes=30))
BOARDS = [("Revenue Analytics", "REV_SUPABASE_URL", "REV_SUPABASE_KEY", CFG["revenue_supabase_url"]),
          ("Calling Analytics", "CALL_SUPABASE_URL", "CALL_SUPABASE_KEY", CFG["calling_supabase_url"])]


class Board:
    def __init__(self, name, url_env, key_env, default):
        self.name = name
        self.key = os.environ.get(key_env, "").strip()
        self.base = (os.environ.get(url_env, "").strip() or default).rstrip("/") + "/rest/v1/"
        self.h = {"apikey": self.key, "Authorization": f"Bearer {self.key}", "Content-Type": "application/json"}

    def _get(self, table, params):
        r = requests.get(self.base + table, params=params, headers=self.h, timeout=60)
        r.raise_for_status()
        return r.json()

    def last_run(self):
        r = self._get("refresh_log", [("select", "run_at,status"), ("order", "run_at.desc"), ("limit", "1")])
        return (parse(r[0]["run_at"]), r[0]["status"]) if r else (None, None)

    def last_ok(self):
        r = self._get("refresh_log", [("select", "run_at"), ("status", "eq.ok"), ("order", "run_at.desc"), ("limit", "1")])
        return parse(r[0]["run_at"]) if r else None

    def last_request(self):
        r = self._get("refresh_requests", [("select", "requested_at,source"), ("order", "requested_at.desc"), ("limit", "1")])
        return (parse(r[0]["requested_at"]), r[0]["source"]) if r else (None, None)

    def start(self):
        r = requests.post(self.base + "rpc/_dispatch_refresh", headers=self.h,
                          json={"p_source": "12:00 reports", "p_full": False}, timeout=60)
        r.raise_for_status()


def parse(ts: str) -> datetime:
    return datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone(IST)


def ensure(check_only=False, now=None) -> list[tuple[str, bool, str]]:
    now = now or datetime.now(IST)
    hh, mm = (int(x) for x in CFG["refresh"]["fresh_after_ist"].split(":"))
    after = now.replace(hour=hh, minute=mm, second=0, microsecond=0)
    if now < after:            # a run before 11:30 (manual) only needs this morning's refresh
        after = now.replace(hour=0, minute=0, second=0, microsecond=0)
    deadline = time.time() + CFG["refresh"]["wait_minutes"] * 60
    out, waiting = [], []
    for name, u, k, d in BOARDS:
        b = Board(name, u, k, d)
        if not b.key:
            out.append((name, False, "key not set - not checked"))
            continue
        try:
            ok = b.last_ok()
            if ok and ok >= after:
                out.append((name, True, f"refreshed {ok:%H:%M} IST"))
                continue
            req, src = b.last_request()
            if req and req >= after:
                print(f"{name}: refresh already requested at {req:%H:%M} IST ({src}); waiting")
                since = req
            elif check_only:
                out.append((name, False, f"last refresh {ok:%d %b %H:%M} IST - not after {after:%H:%M}" if ok else "never refreshed"))
                continue
            else:
                b.start()
                since = datetime.now(IST) - timedelta(seconds=5)
                print(f"{name}: refresh started {since:%H:%M} IST")
            waiting.append((b, since))
        except requests.RequestException as e:
            out.append((name, False, f"could not check: {str(e)[:160]}"))
    for b, since in waiting:
        msg = None
        while time.time() < deadline:
            try:
                run, status = b.last_run()
            except requests.RequestException:
                run, status = None, None
            if run and run >= since:
                msg = (b.name, status == "ok", f"refreshed {run:%H:%M} IST" + ("" if status == "ok" else f" with status {status}"))
                break
            time.sleep(30)
        out.append(msg or (b.name, False, f"not finished after {CFG['refresh']['wait_minutes']} min - reports use the previous refresh"))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="report only, start nothing")
    a = ap.parse_args()
    res = ensure(a.check)
    lines = [f"- {'OK' if ok else 'NOT FRESH'} **{n}**: {m}" for n, ok, m in res]
    print("\n".join(lines))
    gs = os.environ.get("GITHUB_STEP_SUMMARY")
    if gs:
        with open(gs, "a", encoding="utf-8") as f:
            f.write("## Dashboards before the 12:00 reports\n\n" + "\n".join(lines) + "\n\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
