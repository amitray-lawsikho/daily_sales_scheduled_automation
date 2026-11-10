#!/usr/bin/env python3
"""MTD Revenue Analysis — orchestrator for the daily scheduled run (and manual "Run MTD analysis").

Commands
  plan       [--till D] [--month YYYY-MM] [--today YYYY-MM-DD]
             -> prints JSON: which month/day window is due and which Google Sheet to fetch.
                status READY | NO_SHEET
  decode     <drive_export.json> <out.xlsx> [--month YYYY-MM]
             -> turns the Google Drive connector's xlsx export (JSON with base64 'content')
                into an .xlsx file, and checks the sheet title names the expected month.
  run        --workbook X.xlsx [--till D] [--month YYYY-MM] [--today YYYY-MM-DD]
             [--segments "Team Uzair,Sales Teams,Collection Teams"] [--allow-stale]
             -> runs the full playbook pipeline, renders the PDF(s) into reports/YYYY-MM/,
                updates data/revenue_history.csv, writes the brief. Exit codes:
                0 OK | 3 NO_SHEET | 4 STALE (sheet not updated to day N) | 5 SANITY_FAIL
  set-sheet  <YYYY-MM> <sheet url or id> [--title T]
             -> registers the month's "Sales Team Reports" sheet.

The analysis itself (pipeline.py / analysis.py / keypoints.py / build_pdf.py) is the Cowork
project's pipeline (playbook v6, deliverables policy v9, PDF design spec v6) with the rule
updates recorded in docs/RULES.md.
"""
import argparse, calendar, datetime as dt, json, os, re, shutil, subprocess, sys, base64, pickle

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MTD = os.path.join(REPO, 'mtd')
CFG = os.path.join(REPO, 'config', 'monthly_sheets.json')
HIST = os.path.join(REPO, 'data', 'revenue_history.csv')
STATE = os.path.join(REPO, 'data', 'run_state.json')
WORK = os.path.join(REPO, '.work')
IST = dt.timezone(dt.timedelta(hours=5, minutes=30))
ALL_SEGMENTS = ['Team Uzair', 'Sales Teams', 'Collection Teams']


def load_cfg():
    return json.load(open(CFG))


def today_ist(s=None):
    return dt.date.fromisoformat(s) if s else dt.datetime.now(IST).date()


def window(args):
    """Return (Y, M, N, explicit) — N = last complete day (yesterday) unless --till/--month given."""
    yday = today_ist(args.today) - dt.timedelta(days=1)
    if args.month:
        Y, M = map(int, args.month.split('-'))
    else:
        Y, M = yday.year, yday.month
    D = calendar.monthrange(Y, M)[1]
    if args.till:
        N = int(args.till)
    elif (Y, M) == (yday.year, yday.month):
        N = yday.day
    else:
        N = D
    # never include today's partial day
    if (Y, M) == (yday.year, yday.month):
        N = min(N, yday.day)
    return Y, M, max(1, min(N, D)), bool(args.till or args.month)


def sheet_for(cfg, Y, M):
    return cfg['sheets'].get(f'{Y}-{M:02d}')


def cmd_plan(args):
    cfg = load_cfg(); Y, M, N, _ = window(args)
    sh = sheet_for(cfg, Y, M)
    out = dict(year=Y, month=M, N=N, days_in_month=calendar.monthrange(Y, M)[1], month_key=f'{Y}-{M:02d}',
               month_name=dt.date(Y, M, 1).strftime('%B %Y'))
    if not sh:
        out.update(status='NO_SHEET', message=f"No 'Sales Team Reports' sheet registered for {out['month_name']}. "
                   f"Ask the user for the {out['month_name']} sheet link; do not produce deliverables until it is provided.")
    else:
        out.update(status='READY', sheet_id=sh['id'], sheet_title=sh.get('title', ''))
    # working-day calendar (supplied by the user each month)
    td = today_ist(args.today); wdays = cfg.get('working_days', {}).get(f'{td.year}-{td.month:02d}')
    out['today'] = str(td)
    out['today_is_working_day'] = None if wdays is None else td.day in wdays
    out['last_working_day_of_month'] = bool(wdays) and td.day == max(wdays)
    if out['last_working_day_of_month']:
        nxt = (td.replace(day=28) + dt.timedelta(days=4)).replace(day=1)
        out['reminder'] = (f"Last working day of {td:%B}: please share the {nxt:%B %Y}- Sales Team Reports sheet link "
                           f"and the {nxt:%B} working schedule on 1 {nxt:%b} so the {nxt:%B} runs can be scheduled.")
    # previous-month close: history must hold the previous month to its last day
    pY, pM = (Y, M - 1) if M > 1 else (Y - 1, 12)
    pD = calendar.monthrange(pY, pM)[1]
    pk = f'{pY}-{pM:02d}'
    import csv
    last = max((r['date'] for r in csv.DictReader(open(HIST)) if r['date'].startswith(pk)), default=None)
    if last != f'{pk}-{pD:02d}':
        psh = sheet_for(cfg, pY, pM)
        out['prev_month_close'] = dict(month_key=pk, history_ends=last, sheet_id=psh['id'] if psh else None,
                                       note=('Close the previous month first: fetch its sheet and run '
                                             f'`run --month {pk} --history-only`.') if psh else
                                       f'History for {pk} ends {last} but no sheet is registered for {pk} — ask the user.')
    print(json.dumps(out, indent=2))
    return 0 if sh else 3


def cmd_decode(args):
    raw = open(args.export).read().strip()
    try:
        d = json.loads(raw)
        content, title = d['content'], d.get('title', '')
    except (json.JSONDecodeError, KeyError):
        content, title = raw, ''          # plain base64
    data = base64.b64decode(content)
    if data[:2] != b'PK':
        sys.exit('decoded content is not an xlsx (zip) file')
    open(args.out, 'wb').write(data)
    if args.month and title:
        Y, M = map(int, args.month.split('-'))
        mn = dt.date(Y, M, 1)
        if not (re.search(mn.strftime('%B'), title, re.I) and str(Y) in title):
            sys.exit(f"Sheet title '{title}' does not look like the {mn:%B %Y} workbook — stop and ask the user.")
    print(json.dumps(dict(ok=True, out=args.out, bytes=len(data), title=title)))


def cmd_set_sheet(args):
    cfg = load_cfg()
    m = re.search(r'/d/([A-Za-z0-9_-]{20,})', args.sheet)
    sid = m.group(1) if m else args.sheet.strip()
    if not re.fullmatch(r'[A-Za-z0-9_-]{20,}', sid):
        sys.exit(f'not a Google Sheet id/url: {args.sheet}')
    Y, M = map(int, args.month.split('-'))
    cfg['sheets'][f'{Y}-{M:02d}'] = dict(id=sid, title=args.title or f"{dt.date(Y, M, 1):%B %Y}- Sales Team Reports",
                                         url=args.sheet if args.sheet.startswith('http') else f'https://docs.google.com/spreadsheets/d/{sid}/edit')
    cfg['sheets'] = dict(sorted(cfg['sheets'].items()))
    json.dump(cfg, open(CFG, 'w'), indent=2); open(CFG, 'a').write('\n')
    print(f'registered {Y}-{M:02d} -> {sid}')


def cmd_set_workdays(args):
    cfg = load_cfg(); Y, M = map(int, args.month.split('-')); D = calendar.monthrange(Y, M)[1]
    days = set()
    for part in args.days.replace(' ', '').split(','):
        a, _, b = part.partition('-'); days |= set(range(int(a), int(b or a) + 1))
    if not days or min(days) < 1 or max(days) > D:
        sys.exit(f'days out of range for {Y}-{M:02d} (1-{D})')
    days = sorted(days)
    cfg.setdefault('working_days', {})[f'{Y}-{M:02d}'] = days
    cfg['working_days'] = dict(sorted(cfg['working_days'].items()))
    json.dump(cfg, open(CFG, 'w'), indent=2); open(CFG, 'a').write('\n')
    # compact ranges for the cron day-of-month field
    rng, st = [], days[0]
    for x, y in zip(days, days[1:] + [None]):
        if y != x + 1:
            rng.append(f'{st}-{x}' if st != x else f'{x}'); st = y
    print(json.dumps(dict(month=f'{Y}-{M:02d}', working_days=days,
                          cron=f'CRON_TZ=Asia/Kolkata 0 12 {",".join(rng)} {M} *')))


def last_date_in_workbook(path, Y, M):
    import pandas as pd
    x = pd.ExcelFile(path)
    bd = pd.read_excel(x, 'BASE DATA', usecols=lambda c: str(c).strip() in ('Date', 'Fee paid'))
    dts = pd.to_datetime(bd['Date'], errors='coerce', dayfirst=True)
    ok = dts.notna() & bd['Fee paid'].notna() & (dts.dt.year == Y) & (dts.dt.month == M)
    return None if not ok.any() else dts[ok].max().date()


def rs(v):
    return f"Rs {v:,.0f}"


def run_scripts(env, wd, scripts=('pipeline.py', 'analysis.py', 'build_pdf.py')):
    for s in scripts:
        r = subprocess.run([sys.executable, os.path.join(MTD, s)], cwd=wd, env=env, capture_output=True, text=True)
        open(os.path.join(wd, s.replace('.py', '.log')), 'w').write(r.stdout + '\n' + r.stderr)
        if r.returncode:
            print(r.stdout[-3000:], r.stderr[-3000:], file=sys.stderr)
            sys.exit(f'{s} failed (see {wd}/{s.replace(".py", ".log")})')


def anomaly_items(anom, rest, tot_rows):
    """Return list of (key, text) — key is used to decide whether an anomaly is NEW vs last run."""
    import pandas as pd
    items = []
    if len(anom['unmapped']):
        u = anom['unmapped'].groupby('caller').fee.sum().sort_values(ascending=False)
        for c, v in u.items():
            items.append((f'unmapped:{c}', f"Caller **{c}** has revenue ({rs(v)}) but no match on the Team Members roster — which team/vertical?"))
    for t in anom['teams_unknown']:
        items.append((f'team_unknown:{t}', f"Team name **{t}** is not on the roster or in the alias map — new team or a rename?"))
    tf = anom['txtfee']
    if len(tf):
        items.append((f"txtfee:{len(tf)}:{round(float(tf['fee'].sum()), 2)}", f"{len(tf)} fee value(s) stored as text ({rs(tf['fee'].sum())}) — parsed and INCLUDED per the Oct rule; ops may want to fix at source."))
    n, rows, s, same = anom['dup']
    if same:
        items.append((f'dup_same:{same}', f"{same} duplicate Transaction ID(s) carry the SAME amount on both rows — genuine two-course bookings or double entry? (counted per split-transaction rule)"))
    if anom['neg']:
        items.append((f"neg:{anom['neg']}", f"{anom['neg']} negative fee row(s) — refunds? Counted as-is."))
    if anom['enr_ids'][0] != anom['enr_ids'][1]:
        items.append((f"enr_ids:{anom['enr_ids']}", f"'New enrollment' rows {anom['enr_ids'][0]} vs unique txn IDs {anom['enr_ids'][1]} — possible double-counted enrollment."))
    tmm = anom['team_mismatch']
    tmm = tmm[[c not in ('Direct', 'Bootcamp - Direct') for c, _, _ in tmm.index]] if len(tmm) else tmm
    for (c, t, rt), v in (tmm.items() if len(tmm) else []):
        items.append((f'team_mismatch:{c}:{t}:{rt}', f"{c}: BASE DATA team **{t}** but roster team **{rt}** ({rs(v)}) — reported under the BASE DATA team."))
    for (v, t), amt in anom['unplaced_dead_team_rev'].items():
        items.append((f'unplaced:{v}:{t}', f"Removed team **{t}** ({v}) has {rs(amt)} in history that cannot be re-homed (no live roster team for its callers) — it is not reported."))
    known_enr = {'Other revenue', 'New enrollment', 'Bootcamp collections - balance payments', 'Community Collections - balance payments',
                 'New enrollment - balance payment', 'nan', ''}
    for v in anom['enr_vals'].index:
        if v not in known_enr:
            items.append((f'enr_val:{v}', f"New `Enrollment` value **{v}** ({anom['enr_vals'][v]} rows) — not counted as an enrollment; confirm."))
    if len(rest['diffs']):
        dr = rest['new_rev'] - rest['held_rev']; de = rest['new_enr'] - rest['held_enr']
        days = ', '.join(sorted(set(rest['diffs'].date)))
        df = rest['diffs']
        moves = '; '.join(f"{r.date[5:]} {r.caller} / {r.team}: {r.dr:+,.0f}" + (f" ({int(r.de):+d} enr)" if r.de else '')
                          for r in df.sort_values(['date', 'caller']).itertuples())
        items.append((f"restate:{round(dr, 2)}:{de}:{days}:{len(df)}",
                      f"RESTATEMENT of days already in history: net revenue {dr:+,.2f}, enrollments {de:+d}. Row moves: {moves}"))
    return items


def segment_line(name, S, N, CM, PM):
    t = S['tot']
    priors = sorted([m for m in t['bymon'] if m != S_cur(S)], reverse=True)
    comp = ' · '.join(f"{dt.date(int(m[:4]), int(m[5:]), 1):%b} {rs(t['bymon'][m])}" for m in priors)
    ach = '—' if t['tgt'] <= 0 else f"{t['ach'] * 100:.0f}%"
    d = (t['rev'] - t['prev']) / t['prev'] * 100 if t['prev'] else float('nan')
    return (f"**{name}**: {rs(t['rev'])} ({d:+.1f}% vs {PM} 1-{N}) · achievement {ach} of pro-rated · "
            f"enrollments {t['enr']} vs {t['penr']} · pending {rs(t['pend'])}  \n  Same window earlier: {comp}")


_CUR = {}
def S_cur(S):
    return _CUR['curm']


def sanity(S):
    t = S['tot']; out = []; block = False
    share = t['enr'] / t['rows'] if t['rows'] else 0
    ok1 = share < 0.9; block |= not ok1
    out.append(f"1. Enrollment plausibility: {t['enr']} enrollments / {t['rows']} revenue rows = {share:.0%} — {'pass' if ok1 else 'FAIL (wrong column?)'}")
    rr = t['rev'] / t['prev'] if t['prev'] else None; er = t['enr'] / t['penr'] if t['penr'] else None
    wild = er is not None and rr is not None and (er > 2 or er < .5) and .67 < rr < 1.5 and t['penr'] >= 20
    out.append(f"2. Enrollments vs revenue direction: revenue x{rr:.2f}, enrollments x{er:.2f}" if rr and er else
               "2. Enrollments vs revenue direction: no prior-window base")
    out[-1] += ' — WARN (check definition)' if wild else ' — pass' + (' (small early-month counts)' if er and (er > 2 or er < .5) else '')
    real = t['rev'] / t['enr'] if t['enr'] else None
    ok3 = real is None or real >= 5000; block |= not ok3
    band = '' if real is None else ('in band' if 20000 <= real <= 90000 else 'outside Rs 20k–90k band')
    out.append(f"3. Realisation per enrollment: {rs(real) if real else 'n/a'} {band} — {'pass' if ok3 else 'FAIL (balance payments counted?)'}")
    V, T = S['V'], S['T']
    ok5 = abs(V.rev.sum() - t['rev']) < 1 and abs(T.rev.sum() - V.rev.sum()) < 1 and V.enr.sum() == T.enr.sum() == t['enr']
    out.append(f"5. Roll-up (teams = verticals = segment, revenue and enrollments): {'exact' if ok5 else 'MISMATCH'}")
    block |= not ok5
    return out, block


def cmd_run(args):
    cfg = load_cfg(); Y, M, N, explicit = window(args)
    D = calendar.monthrange(Y, M)[1]; key = f'{Y}-{M:02d}'
    if not sheet_for(cfg, Y, M) and not args.force_no_sheet:
        print(json.dumps(dict(status='NO_SHEET', month_key=key))); return 3
    segs = [s.strip() for s in (args.segments or ','.join(cfg.get('default_segments', ['Team Uzair']))).split(',') if s.strip()]
    if args.segments and args.segments.strip().lower() == 'all':
        segs = ALL_SEGMENTS
    bad = [s for s in segs if s not in ALL_SEGMENTS]
    if bad:
        sys.exit(f'unknown segment(s): {bad}; choose from {ALL_SEGMENTS}')

    last = last_date_in_workbook(args.workbook, Y, M)
    if last is None or last.day < N:
        if args.allow_stale and last is not None:
            N = last.day
        else:
            msg = (f"The {dt.date(Y, M, 1):%B %Y} sheet has data only up to "
                   f"{last:%d %b %Y}" if last else f"The sheet has no {dt.date(Y, M, 1):%B %Y} rows") + \
                  f"; the run needs day {N}. Sheet not updated yet — no deliverables produced."
            print(json.dumps(dict(status='STALE', month_key=key, N=N, last_date=str(last), message=msg))); return 4

    wd = os.path.join(WORK, f'{key}_1-{N}'); shutil.rmtree(wd, ignore_errors=True); os.makedirs(wd)
    shutil.copy(args.workbook, os.path.join(wd, 'wb.xlsx'))
    shutil.copy(HIST, os.path.join(wd, 'hist_old.csv'))
    rep = os.path.join(REPO, 'reports', key); os.makedirs(rep, exist_ok=True)
    gen = (today_ist(args.today)).strftime('%d %b %Y')
    env = dict(os.environ, MTD_N=str(N), MTD_Y=str(Y), MTD_M=str(M), MTD_SEGMENTS=','.join(segs),
               MTD_OUT=os.path.join(wd, 'out'), MTD_GEN_DATE=gen, MPLBACKEND='Agg')
    if args.history_only:
        # month close: rebuild that month in history only (no PDF), report the restatement
        run_scripts(env, wd, ('pipeline.py',))
        d = pickle.load(open(os.path.join(wd, 'data.pkl'), 'rb')); rest = d['rest']
        shutil.copy(os.path.join(wd, 'revenue_history.csv'), HIST)
        print(json.dumps(dict(status='OK', mode='history-only', month_key=key, N=N,
                              revenue=round(float(d['anom']['rev']), 2), enrollments=int(d['anom']['enr']),
                              restated_revenue=round(float(rest['new_rev'] - rest['held_rev']), 2),
                              restated_enrollments=int(rest['new_enr'] - rest['held_enr'])), indent=2))
        return 0
    run_scripts(env, wd)

    # ---- load results for checks + brief
    sys.path.insert(0, MTD); os.chdir(wd)
    d = pickle.load(open('data.pkl', 'rb')); SEG = pickle.load(open('seg.pkl', 'rb'))
    anom, rest = d['anom'], d['rest']; curm, prevm = d['curm'], d['prevm']; _CUR['curm'] = curm
    CM = dt.date(Y, M, 1).strftime('%b'); PM = dt.date(int(prevm[:4]), int(prevm[5:]), 1).strftime('%b')

    checks, block = [], False
    for s in segs:
        c, b = sanity(SEG[s]); checks.append((s, c)); block |= b
    if block:
        print(json.dumps(dict(status='SANITY_FAIL', checks=checks), indent=2)); return 5

    # ---- persist: history + PDFs (only after all checks pass)
    shutil.copy(os.path.join(wd, 'revenue_history.csv'), HIST)
    pdfs = []
    for f in sorted(os.listdir(os.path.join(wd, 'out'))):
        shutil.copy(os.path.join(wd, 'out', f), os.path.join(rep, f)); pdfs.append(os.path.join('reports', key, f))

    # ---- anomalies: NEW vs previous run
    state = json.load(open(STATE)) if os.path.exists(STATE) else {}
    prev_keys = set(state.get(key, {}).get('anomaly_keys', []))
    items = anomaly_items(anom, rest, anom['rows'])
    new = [(k, t) for k, t in items if k not in prev_keys]; old = [(k, t) for k, t in items if k in prev_keys]
    ros = anom['roster']; pros = state.get(key, {}).get('roster')
    if pros and (round(pros[1]) != round(ros[1]) or pros[2] != ros[2] or pros[0] != ros[0]):
        new.append(('roster', f"Roster changed since last run: {pros[0]} → {ros[0]} rows; active targets {rs(pros[1])} / {pros[2]} → {rs(ros[1])} / {ros[2]} holders — confirm final."))
    exp_cols = state.get('columns')
    if exp_cols and exp_cols != anom['columns']:
        add = [c for c in anom['columns'] if c not in exp_cols]; rem = [c for c in exp_cols if c not in anom['columns']]
        new.append(('schema', f"BASE DATA columns changed — added {add or 'none'}, removed {rem or 'none'}. Columns are matched by name; confirm nothing renamed."))

    # ---- brief
    n, drows, dsum, same = anom['dup']
    lead = anom['lead_na']
    L = [f"# MTD Report {CM} 1-{N}, {Y} — brief", '',
         f"Window: 1-{N} {CM} {Y} (last complete day; D = {D}) · generated {gen} · playbook v6 / policy v9 (Team Uzair default)", '',
         '## Headline']
    for s in segs:
        L.append('- ' + segment_line(s, SEG[s], N, CM, PM))
    L += ['', '## Sanity checks']
    for s, c in checks:
        L.append(f'**{s}**'); L += [f'- {x}' for x in c]
    rtxt = ('none — days already in history match the workbook to the rupee'
            if not len(rest['diffs']) else
            f"revenue {rest['new_rev'] - rest['held_rev']:+,.2f}, enrollments {rest['new_enr'] - rest['held_enr']:+d} on {', '.join(sorted(set(rest['diffs'].date)))}")
    L += ['**All segments**', f"- 4. Restatement check: {rtxt}", '- 6. Formula errors: n/a (no xlsx in default policy)', '',
          '## Data quality (whole workbook window)',
          f"- {anom['rows']:,} revenue rows · {rs(anom['rev'])} · {anom['enr']} enrollments ({anom['enr_ids'][1]} unique txn IDs) · negatives: {anom['neg']}",
          f"- Duplicate Transaction IDs: {n} IDs / {drows} rows / {rs(dsum)} ({same} same-amount) — counted per split-transaction rule",
          f"- Convenience/Hardcopy rows: {anom['conv'][0]} / {rs(anom['conv'][1])} — included",
          f"- Text-formatted fees: {len(anom['txtfee'])} ({rs(anom['txtfee']['fee'].sum()) if len(anom['txtfee']) else 'Rs 0'}) — parsed and included",
          f"- Lead Details not Available → Direct: {len(lead)} row(s) / {rs(lead.fee.sum()) if len(lead) else 'Rs 0'}",
          f"- Workbook last date: {anom['last_date']} · history rows now {len(d['hist']):,}", '',
          '## NEW anomalies — questions for you']
    L += [f'- {t}' for _, t in new] or ['- none']
    if old:
        L += ['', '## Still open (raised before, defaults applied)'] + [f'- {t}' for _, t in old]
    L += ['', '## Files'] + [f'- `{p}`' for p in pdfs] + ['- `data/revenue_history.csv` (updated)']
    brief = os.path.join(rep, f'brief {CM} 1-{N}.md')
    open(brief, 'w').write('\n'.join(L) + '\n')
    # machine-readable headline per segment (used by mtd/whatsapp_send.py)
    summ = {'month_key': key, 'N': N, 'D': D, 'period': f'{CM} 1-{N}, {Y}', 'prev_period': f'{PM} 1-{N}', 'generated': gen,
            'segments': {}}
    for s_ in segs:
        t = SEG[s_]['tot']
        summ['segments'][s_] = dict(
            pdf=[p for p in pdfs if p.endswith(f' - {s_}.pdf')][0], revenue=round(float(t['rev']), 2), prev_revenue=round(float(t['prev']), 2),
            vs_prev_pct=None if not t['prev'] else round((t['rev'] - t['prev']) / t['prev'] * 100, 1),
            achievement_pct=None if t['tgt'] <= 0 else round(float(t['ach']) * 100),
            enrollments=int(t['enr']), prev_enrollments=int(t['penr']), pending=round(float(t['pend']), 2))
    json.dump(summ, open(os.path.join(rep, f'summary {CM} 1-{N}.json'), 'w'), indent=2)

    state.setdefault(key, {})
    state[key].update(anomaly_keys=sorted(k for k, _ in items), roster=list(map(lambda v: float(v) if not isinstance(v, int) else v, ros)),
                      last_run=dict(N=N, generated=gen, segments=segs))
    state['columns'] = anom['columns']
    json.dump(state, open(STATE, 'w'), indent=2)
    print(json.dumps(dict(status='OK', month_key=key, N=N, segments=segs, pdfs=pdfs,
                          brief=os.path.relpath(brief, REPO), new_anomalies=len(new)), indent=2))
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest='cmd', required=True)
    for name in ('plan', 'run'):
        p = sp.add_parser(name)
        p.add_argument('--till', type=int); p.add_argument('--month'); p.add_argument('--today')
        if name == 'run':
            p.add_argument('--workbook', required=True); p.add_argument('--segments')
            p.add_argument('--allow-stale', action='store_true'); p.add_argument('--force-no-sheet', action='store_true')
            p.add_argument('--history-only', action='store_true', help='month close: update history only, no PDF')
    p = sp.add_parser('set-workdays', help='store the month working schedule and print the schedule cron')
    p.add_argument('month'); p.add_argument('days', help='e.g. "2-6,10-14,16-20,23-30"')
    p = sp.add_parser('decode'); p.add_argument('export'); p.add_argument('out'); p.add_argument('--month')
    p = sp.add_parser('set-sheet'); p.add_argument('month'); p.add_argument('sheet'); p.add_argument('--title')
    a = ap.parse_args()
    sys.exit({'plan': cmd_plan, 'run': cmd_run, 'decode': cmd_decode, 'set-sheet': cmd_set_sheet,
              'set-workdays': cmd_set_workdays}[a.cmd](a) or 0)


if __name__ == '__main__':
    main()
