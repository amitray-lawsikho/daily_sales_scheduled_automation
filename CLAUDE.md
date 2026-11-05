# Part Wise Connectivity – instructions for Claude sessions on this repo

Scheduled report for Amit Ray (amitray@lawsikho.in). GitHub Actions runs `python -m partwise` at 12:00 IST on
working days. There is no Claude or LLM call in the runs. Claude's job is only to maintain the repo and the
month files. Never compute a report figure by hand.

## The monthly hand-off (most common request)

Amit sends the new month's **Sales Team Reports link** and **working schedule** (for example "1st Nov (Sunday) – Week Off,
2nd Nov to 6th Nov – Working, …"). Then:

1. Write `config/months/YYYY-MM.json` with `sales_sheet` (the link) and `working_days` as day ranges
   (`["2-6", "10-14", "16-20", "23-30"]`). Note the week offs in `_note`.
2. Check the sheet has `Team Members` and `BASE DATA` tabs (Google Sheets connector, header row only).
3. Run `python -m unittest discover -s tests -t .` and `python -m partwise.schedule --today <a working day>`.
4. Commit. The file must reach `main` before the 1st (the schedule only runs from the default branch). Ask Amit
   whether to push to `main` directly or open a PR.

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

## Secrets

Only as GitHub secrets: `CALL_SUPABASE_KEY`, `GOOGLE_OAUTH_CLIENT_ID`, `GOOGLE_OAUTH_CLIENT_SECRET`,
`GOOGLE_OAUTH_REFRESH_TOKEN` (or `GOOGLE_SERVICE_ACCOUNT_JSON`). Never print, commit or paste them.
