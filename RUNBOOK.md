# MTD Revenue Analysis — Runbook

This runbook is the procedure for **every** MTD run: the daily 12:00 PM IST scheduled run and
any manual "Run MTD analysis" prompt. Claude follows it step by step. The analysis rules are in
`docs/RULES.md`; the full playbook from the Cowork project is in `docs/playbook/`.

Work on branch `claude/epic-hamilton-0k0ar3` (pull it first, push to it at the end).

---

## A. Standard run (scheduled 12:00 PM IST on working days, or "Run MTD analysis" any time)

1. **Sync and set up**
   ```bash
   git pull origin claude/epic-hamilton-0k0ar3
   pip install -q -r requirements.txt
   ```

2. **Plan the window**: `python3 mtd/run_mtd.py plan` (add `--till D` for "run till Dth").
   - N = yesterday (IST). On the 1st of a month, N is the last day of the previous month, so
     that month's own sheet is used and the month closes out.
   - `prev_month_close` present: the previous month is not complete in history (its last day(s)
     fell on a week off, e.g. 30 Nov data when 1 Dec is a holiday). **First** fetch that month's
     sheet (step 3, its `sheet_id`, `--month` = that month) and run
     `python3 mtd/run_mtd.py run --workbook .work/prev.xlsx --month YYYY-MM --history-only`.
     That updates history only, without a PDF. Mention the close and any restatement in the brief. Then continue with the current month.
   - `status: NO_SHEET` means no sheet link is registered for that month. **STOP: produce no
     deliverables.** Notify the user (see step 6, "blocked" message): "Please share the
     *[Month Year]- Sales Team Reports* sheet link." Do not try to guess or search for the sheet.

3. **Fetch the workbook** (the same file you used to download by hand as xlsx):
   call the Google Drive connector `download_file_content` with
   `fileId = <sheet_id from plan>` and
   `exportMimeType = application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`.
   The result is too large for the context and is saved to a tool-results file. Decode it:
   ```bash
   python3 mtd/run_mtd.py decode "<saved tool-results file>" .work/wb.xlsx --month YYYY-MM
   ```
   This refuses a sheet whose title does not name the expected month. If it does, STOP and ask.

4. **Run**: `python3 mtd/run_mtd.py run --workbook .work/wb.xlsx` (plus the same `--till`, if
   any; `--segments` only when asked, see section B).
   | exit | status | action |
   |---|---|---|
   | 0 | OK | continue to step 5 |
   | 3 | NO_SHEET | as in step 2 |
   | 4 | STALE | the sheet is not filled up to day N. **No deliverables, no commit.** Send the "blocked" message with the last date in the sheet; the user will say "Run MTD analysis" later. On a *manual* run, offer "run till [last day]" (`--allow-stale`). |
   | 5 | SANITY_FAIL | an enrollment/realisation/roll-up check failed. No commit. Report the failing check to the user and ask. |

5. **Save**: commit and push the updated history, PDF(s), brief and run state.
   ```bash
   git add data/ reports/
   git commit -m "MTD run <Mon> 1-N"
   git push -u origin claude/epic-hamilton-0k0ar3
   ```

6. **Deliver**
   - `SendUserFile` with the PDF(s) from `reports/YYYY-MM/` (status `proactive` for the
     scheduled run, `normal` for a manual one).
   - Gmail `send_message` to `notify_email` in `config/monthly_sheets.json`:
     subject `MTD Report <Mon> 1-N — Team Uzair`. The plain-text body has the headline, sanity
     check results, NEW anomaly questions and a link to the PDF on GitHub:
     `https://github.com/amitray-lawsikho/daily_sales_scheduled_automation/blob/claude/epic-hamilton-0k0ar3/reports/YYYY-MM/<file name, URL-encoded>`.
     Do not attach the PDF (it is too large to send through the connector reliably).
   - If `plan` returned a `reminder` (last working day of the month), add it at the top of the
     email and chat reply.
   - In-chat reply: **brief only**. Give the headline per produced segment, the sanity-check
     results, and the NEW anomalies phrased as questions. Take these from `reports/YYYY-MM/brief <Mon> 1-N.md`.
   - "Blocked" message (NO_SHEET / STALE / SANITY_FAIL): the same three channels, without a PDF.

7. **Anomalies**: nobody is there to answer at 12:00, so **defaults are applied and the report is
   delivered** (standing rule: "proceed on defaults, don't block on anomalies"). NEW anomalies
   are raised as questions in the chat and email, never inside the PDF. When the user answers,
   update the code or alias map and `docs/RULES.md` (section D).

---

## B. Request modifiers

| user says | do |
|---|---|
| "Run MTD analysis" / "run the analysis" | Section A |
| "run till 15th" | `--till 15` (never beyond the last complete day present in the sheet) |
| "Sales Teams" / "Collection Teams" / "all segments" | `--segments "Sales Teams"` / `--segments "Collection Teams"` / `--segments all` (default is Team Uzair only) |
| "compare with [month]" | Every month in history (up to 12) is already in the pacing lines; mention that |
| "include the xlsx" / "give me all files" | Run Section A, then build the 3 xlsx per `docs/playbook/project_instructions_v6.txt` ("Deliverables every run (7 files)", xlsx part) from `.work/<run>/seg.pkl` |
| "full month for October" / re-upload of a prior month | `--month 2026-10` with that month's sheet registered: rebuilds that month in history and reports the restatement |

---

## C. New month's sheet + working schedule (the user supplies both on the 1st)

The scheduled task fires **only on working days** (the user's monthly working schedule) at 12:00 IST,
so no tokens are spent on week-off days. Each month's schedule must be registered:
1. Turn the user's schedule into day ranges, e.g. Nov 2026 = `2-6,10-14,16-20,23-30` (week-offs excluded).
2. `python3 mtd/run_mtd.py set-workdays YYYY-MM "<ranges>"`. This prints the `cron` expression.
3. Update the scheduled task "Daily MTD report — Team Uzair" (trigger `trig_017iEy7NBbmj4s12zb3CJH3t`)
   with `update_trigger` and that `cron_expression`. The cron names the month explicitly, so it
   never fires in a month whose schedule has not been given.
4. If today is a working day and 12:00 IST has passed, run Section A now.

When the user shares a sheet link such as `https://docs.google.com/spreadsheets/d/<ID>/edit…`:
1. Confirm the title with the Google Sheets connector `get_spreadsheet` (fields `properties.title`).
   It should read "<Month> <Year>- Sales Team Reports" and have `BASE DATA` and `Team Members` tabs.
2. `python3 mtd/run_mtd.py set-sheet YYYY-MM "<link>" --title "<title>"`
3. Commit and push `config/monthly_sheets.json`.
4. If today's 12:00 run was blocked waiting for this link, run Section A now.

---

## D. Changing a rule

Any deviation from `docs/RULES.md` needs the user's confirmation ("Ask before deviating from any
rule"). After a confirmed change, edit the code (the alias map is `ALIAS` in `mtd/pipeline.py`),
add a dated line to `docs/RULES.md`, and commit.
