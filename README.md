# Scheduled sales reports (Part Wise Connectivity + Daily Sales Check)

Both run from **Actions › Daily reports (12:00 IST)**: at 11:40 IST (started by a Supabase timer, not
GitHub's schedule, which can skip days) it checks that the Revenue and Calling dashboards
have refreshed after 11:30 (the revenue sheet is complete about then), starts a refresh and waits if not, then
builds both reports. Week-off days stop in seconds.

## Daily Sales Check

PDF (+ xlsx with every table and the full lead list) for **Elite, Corporate law - Anas, Corporate law - Jyoti**, in
Drive › Team performance & Reports › Team Uzair Performance (Amit) › Daily Sales Check, named
`Daily Sales Check <date>.pdf`. Pages: overview of the checks, trends (month / week / day), the checks in detail,
then per team: where it stands (daily revenue vs run-rate, pacing vs earlier months, weekly funnel), callers
(calling, talk time, follow-ups, revenue), **why revenue is not coming** for each flagged caller (funnel vs the
team's top 3, with the next step), and a per-caller count of high-intent leads not dialled for 24 h.
The call list itself is a separate Excel, `High-intent leads not dialled <date>.xlsx`: a summary sheet and one
sheet per team with caller, phone number, lead name, stage, last dial and hours since, sorted oldest first.

```bash
python -m dsc run --date 2026-11-04            # live (needs the keys below)
python -m dsc run --date 2026-11-04 --publish  # and upload to Drive
python -m dsc.refresh --check                  # are both dashboards fresh?
```

Settings and thresholds: `config/dsc.json`. Extra GitHub secrets: `REV_SUPABASE_KEY` (Revenue Analytics
service-role key), `LSQ_HOST`, `LSQ_ACCESS_KEY`, `LSQ_SECRET_KEY` (Zipteams data in LSQ).

# Part Wise Connectivity

Builds **"<Month>: Part Wise Performance"** in the Drive folder *Team performance & Reports › Partwise Data*
every working day at **12:00 IST**, covering the 1st of the month to yesterday. It is the same report the
cowork project produced from manual uploads (P1 1-10, P2 11-20, P3 21-EOM, Monthly Analysis; no frozen rows/columns). The data-quality checks of each run
are on the GitHub Actions run page (Summary),
with the inputs fetched automatically:

| Input | Where it comes from now |
|---|---|
| Call log (CDR) and Stage Changed Report | Calling Analytics dashboard (Supabase, refreshed 23:00 IST nightly), the same rows as its CDR / stage downloads |
| Older months (stage lookback for *Discovery → Enrollments* / *Roadmap → Enrollments*) | `history/LSQ_Partwise_Data_<month>.zip` in this repo (Supabase keeps 90 days) |
| Team Members + BASE DATA | the month's *Sales Team Reports* Google Sheet (link in the month file) |
| Team Uzair stages | *Followup / Discovery / Roadmap Created LSQ Live Sheet of Team Uzair*; past months from its renamed copy *… Team Uzair (<Month>)* |

The run is plain Python on GitHub Actions: **no Claude tokens are used**, and on week-off days the job stops in a
few seconds.

## Every month (Amit)

Before or on the 1st, give the new month's **Sales Team Reports link** and **working schedule**. Either tell
Claude in a session on this repo, or add the file yourself on GitHub (`config/months/2026-12.json`):

```json
{
  "sales_sheet": "https://docs.google.com/spreadsheets/d/<id>/edit",
  "working_days": ["1-5", "8-12", "15-19", "22-31"]
}
```

* No month file → nothing runs for that month.
* Runs on each working day and covers day 1 to yesterday.
* On the 1st of the next month it runs once more to close the month (1 to last day), and freezes that month's
  calls and stage changes into `history/` (committed by the workflow).
* The month's Google Sheet is created on its first run and **overwritten in place** afterwards: same link, and
  Drive's version history keeps every earlier run.
* Optional `"uzair_sheet": "<link>"` in a month file pins the Team Uzair workbook (otherwise it is found by name).

## Run it by hand

GitHub › Actions › **Part Wise Connectivity** › *Run workflow* › month `2026-10`, till `31` (for example).

From a terminal (needs the secrets below in the environment):

```bash
pip install -r requirements.txt
python -m partwise run --month 2026-11 --till 4 --publish
python -m partwise run --month 2026-10 --till 30 --local path/to/folder   # from files: zip(s), *Sales*.xlsx, *Uzair*.xlsx
python -m partwise.schedule --today 2026-11-10                            # what the 12:00 run would do that day
python -m unittest discover -s tests -t .
```

## One-time setup (GitHub › Settings › Secrets and variables › Actions)

| Secret | What |
|---|---|
| `CALL_SUPABASE_KEY` | Calling Analytics service-role key (Supabase › Project Settings › API; the same value the calling-analytics repo uses as `SUPABASE_SERVICE_KEY`) |
| `GOOGLE_OAUTH_CLIENT_ID`, `GOOGLE_OAUTH_CLIENT_SECRET`, `GOOGLE_OAUTH_REFRESH_TOKEN` | lets the run read the sheets and write the report as amitray@lawsikho.in. Create with `scripts/google_refresh_token.py` (steps inside). Make the OAuth consent screen **Internal** so the token does not expire after 7 days. |

`GOOGLE_SERVICE_ACCOUNT_JSON` works instead of the three OAuth secrets if the Drive folder, the Uzair sheets and
each month's sales sheet are shared with the service account. Google may refuse to let a service account
*create* files in a My Drive folder, so OAuth is the safer choice.

The workflow runs from the default branch, so month files must be on `main`.

## Rules

Unchanged from the cowork project (confirmed by Amit Sep–Oct 2026). See `CLAUDE.md`.
