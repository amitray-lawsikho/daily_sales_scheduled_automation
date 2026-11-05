# Part Wise Connectivity + Daily Sales Check – instructions for Claude sessions on this repo

Two scheduled reports for Amit Ray (amitray@lawsikho.in). `.github/workflows/daily-reports.yml` starts at 11:40 IST
every day: on a working day it first makes sure the Revenue and Calling dashboards have refreshed after 11:30 IST
(`python -m dsc.refresh`, which starts and waits for a refresh if needed; both Supabase projects also have an
11:35 IST pg_cron refresh, added 5 Nov 2026 so the 12:00 MTD routine sees fresh dashboards too), then runs
`python -m partwise` and `python -m dsc` side by side. There is no Claude or LLM call in the runs. Claude's job is only to maintain the repo and the
month files. Never compute a report figure by hand.

## The monthly hand-off (most common request)

Amit sends the new month's **Sales Team Reports link** and **working schedule** (for example "1st Nov (Sunday) – Week Off,
2nd Nov to 6th Nov – Working, …"). Then:

1. Write `config/months/YYYY-MM.json` with `sales_sheet` (the link) and `working_days` as day ranges
   (`["2-6", "10-14", "16-20", "23-30"]`). Note the week offs in `_note`.
2. Check the sheet has `Team Members` and `BASE DATA` tabs (Google Sheets connector, header row only).
3. Run `python -m unittest discover -s tests -t .` and `python -m partwise.schedule --today <a working day>`.
4. Commit and push to `main` directly (Amit, 5 Nov 2026: "push to main always, don't ask"). The file must reach
   `main` before the 1st (the schedule only runs from the default branch).

If he says "teams have changed", diff the new Team Members tab against the previous month's, and list the moves and
new resignations before anything else. The latest Team Members sheet applies to the whole month (rule from 9 Oct 2026).

## Layout

- `partwise/report.py`: the analysis and workbook layout (port of the cowork `run_analysis.py`, same rules).
- `partwise/core.py`: definitions (verticals, 40 s connect rule, periods, phone/stage/date normalisation).
- `partwise/sources.py`: Supabase Calling Analytics (`ybkldfcilvibryoxcuvq`) via the service key, Google Sheets/Drive, history zips.
- `partwise/publish.py`: creates or overwrites "<Month>: Part Wise Performance" in Drive folder `1Wdz7FHXLkt1WrDUrjcI8MaI9XERuyWhu`.
- `partwise/schedule.py`: decides whether today runs (standard library only).
- `config/settings.json`: fixed ids. `config/months/*.json`: one per month, written from Amit's hand-off.
- `history/LSQ_Partwise_Data_<month>.zip`: frozen CDR + stage report per month (contains customer phones and emails; the repo is private, as Amit approved on 5 Nov 2026). Never paste its rows into chat.

## Rules (confirmed by Amit; ask before changing any)

- Verticals: Team Uzair, Team Deepanshi, Team Darshan. Don't add new ones (for example Team Abhipsha) unless asked.
- Lead = unique phone (last 10 digits). Connected = longest single call ≥ 40 s, otherwise DNP.
- A lead counts in every stage it reached. Uzair stages come from its own workbook; Deepanshi and Darshan stages come from the stage report.
- Stage changes by people not in Team Members are dropped from the main columns and listed in the run summary.
- Conversions = every "New enrollment" BASE DATA row (split payments count twice, never de-duplicated).
- Discovery → / Roadmap → Enrollments: unique enrolled phones, Roadmap wins, stage at any time this month or in the
  3 prior months, no roster filter, phone match only.
- A percentage with a zero denominator shows 0.0%. There is no Discovery→Roadmap % column.
- Workbook: P1, P2, P3 and Monthly Analysis only. No "Definitions & QC" tab and no frozen panes (Amit,
  5 Nov 2026); the QC notes go to the GitHub Actions run summary.
- Always use `norm_phone` (float `.0` bug) and `norm_stage` (`Roadmap\xa0Done`) on new feeds.

## Daily Sales Check (`dsc/`, Amit 5 Nov 2026)

PDF + two xlsx (all tables; "High-intent leads not dialled <date>" = the check-5 call list with real phone
numbers and lead names, one sheet per team; the PDF shows only per-caller counts, Amit 5 Nov 2026) for Elite,
Corporate law - Anas, Corporate law - Jyoti (`config/dsc.json` `teams`; never other teams),
uploaded to Drive › Team Uzair Performance (Amit) › Daily Sales Check. Data to yesterday, on the working days of
`config/months/<month>.json` (the same file as Part Wise). Python computes every number.

- Checks: 1 data fresh/complete, 2 team revenue on the previous working day vs daily run-rate (target / working
  days), 3 early warning off track 2 complete weeks running (caller below 75% of team median; team weekly revenue
  below run-rate), 4 below 70% of pro-rated MTD target after the 15th, 5 high-intent leads (latest stage Roadmap
  Done / Follow Up For Closure in 14 days, not in BASE DATA, and STILL in one of those stages in LSQ - read live per
  lead with Leads.GetById / RetrieveLeadByPhoneNumber, because the Uzair 'Follow-up Status' sheet goes stale; Amit
  5 Nov 2026) not dialled by anyone for 24 h, with callers and numbers; leads since moved (Not Interested, May buy
  later, ...) go to the "Dropped - stage changed" sheet, 6 top / bottom 3 by achievement of pro-rated target. Check 7 (bootcamp) parked.
- Trends: monthly (4 months, month's own team list), weekly (6 Mon-Sun weeks), daily; follow-ups per caller with a
  High / Medium / Low level vs the team median; the "why" = first funnel step below 75% of the team's top 3.
- Sources: Revenue Analytics `rev_daily`; Calling Analytics `agent_day`, `calls`, `team_map`, `stage_changes`;
  Team Uzair LSQ live sheet + monthly copies (stages, 'Follow-up Status'); MonthwiseTeamList in
  `team_members_data_amit` (targets; Active rows with a Target); BASE DATA (enrolled phones); LSQ for Zipteams.
- Zipteams: "Zipteams Notes" LSQ activity 237, intent in `mx_Custom_1` (HIGH / MODERATE / NEUTRAL / LOW), read with
  the ModifiedOn-margin + window-splitting method of Amit's sales_automation_01 project. Each follow-up takes its
  lead's note within 2 days (Prospect ID match) -> per caller "FU Zip H/M/N/L" and weekly High+Moderate %.
  LSQ load: one request at a time, <= 2/s, bulk activity read <= 1 per 5 s (account limit 30 per 5 s, shared).
- Every threshold is in `config/dsc.json`; ask Amit before changing one. Read-only on every source; the only write
  is the dashboards' own refresh call. `output/` holds phone numbers and is git-ignored.
- Test: `python -m dsc run --offline <folder saved with --save>`; `python -m dsc.schedule --today <date>`.

## Secrets

Only as GitHub secrets: `CALL_SUPABASE_KEY`, `REV_SUPABASE_KEY`, `LSQ_HOST`, `LSQ_ACCESS_KEY`, `LSQ_SECRET_KEY`, `GOOGLE_OAUTH_CLIENT_ID`, `GOOGLE_OAUTH_CLIENT_SECRET`,
`GOOGLE_OAUTH_REFRESH_TOKEN` (or `GOOGLE_SERVICE_ACCOUNT_JSON`). Never print, commit or paste them.
