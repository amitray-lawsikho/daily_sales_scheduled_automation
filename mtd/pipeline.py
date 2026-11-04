import pandas as pd, numpy as np, pickle, calendar, os
# Run parameters come from run_mtd.py (env vars); cwd is the run's work directory.
N = int(os.environ['MTD_N']); Y, M = int(os.environ['MTD_Y']), int(os.environ['MTD_M'])
D = calendar.monthrange(Y, M)[1]
ALIAS = {'DSV- Aditya': 'SA - Aditya', 'DSV- Shivam': 'SA - Shivam', 'ID Closure': 'ID Closure - Darshan',
         'US accounting - Closures': 'US accounting closures - Deepanshi',
         'ID - Community Manager': 'ID - Community', 'Criminal - Community Manager': 'Criminal - Community',
         'CD - Community Manager': 'CD - Community',
         'ID Calling - Uzair': 'Elite',  # 07 Oct 2026: ID Calling - Uzair dissolved into Elite (user)
         'Academic writing - Sana': 'US accounting closures - Sana',
         'Elite - Trainee': 'Elite'}  # 09 Oct 2026: removed teams are never reported (user)
SEGMENTS = {'Team Uzair': ['Team Uzair'],
            'Sales Teams': ['Team Uzair', 'Team Deepanshi', 'Team Darshan'],
            'Collection Teams': ['Team Anmol', 'Team Mayur']}

x = pd.ExcelFile('wb.xlsx')
bd = pd.read_excel(x, 'BASE DATA'); bd.columns = [' '.join(str(c).split()) for c in bd.columns]
tm = pd.read_excel(x, 'Team Members'); tm.columns = [' '.join(str(c).split()) for c in tm.columns]
CALLER = 'Caller name (for ops) for enrollment link circulation'
PEND = 'Pending Revenue (Total of Current and previous month)'

bd['Date'] = pd.to_datetime(bd['Date'], errors='coerce', dayfirst=True)
# Text-formatted fees (e.g. "3,000.00" stored as text) are parsed and INCLUDED (Oct 2026 rule:
# "Text-fee rows must be explicitly parsed"); they are still listed as an anomaly every run.
_num = pd.to_numeric(bd['Fee paid'], errors='coerce')
txtfee = bd['Fee paid'].notna() & _num.isna() & (bd['Fee paid'].astype(str).str.strip() != '')
_parsed = pd.to_numeric(bd['Fee paid'].astype(str).str.replace(',', '').str.replace('₹', '').str.replace('Rs', '').str.strip(), errors='coerce')
bd['fee'] = _num.fillna(_parsed.where(txtfee))
b = bd[bd['Date'].notna() & bd['fee'].notna()].copy()
b = b[(b['Date'].dt.year == Y) & (b['Date'].dt.month == M)]
b = b[b['Date'].dt.day <= N]
b['team'] = b['Team Name'].astype(str).str.strip().replace(ALIAS)
c = b[CALLER].astype(str).str.strip().str.split().str.join(' ')
c = c.where(~c.str.lower().isin(['nan', '', 'none']), None)
b['caller'] = np.where(c.isna(), np.where(b['team'] == 'Bootcamp - Direct', 'Bootcamp - Direct', 'Direct'), c)
b['enr'] = (b['Enrollment'].astype(str).str.strip() == 'New enrollment').astype(int)

tm['cn'] = tm['Caller Name'].astype(str).str.strip().str.lower()
tm['TARGET'] = pd.to_numeric(tm['TARGET'], errors='coerce').fillna(0)
tm[PEND] = pd.to_numeric(tm[PEND], errors='coerce').fillna(0)
tm['active'] = tm['Status'].astype(str).str.strip().str.lower() == 'active'
tm['tgt'] = np.where(tm['active'], tm['TARGET'], 0)
ros = tm.drop_duplicates('cn').set_index('cn')
b['cn'] = b['caller'].str.lower()
b['vertical'] = b['cn'].map(ros['Vertical'])
b.loc[b.caller == 'Direct', 'vertical'] = 'Direct'
b.loc[b.caller == 'Bootcamp - Direct', 'vertical'] = 'Bootcamp - Direct'
unmapped = b[b.vertical.isna()][['caller', 'team', 'fee']]
b['vertical'] = b['vertical'].fillna('(unmapped)')
b['caller'] = np.where(b.cn.isin(ros.index), b.cn.map(ros['Caller Name'].astype(str).str.strip()), b.caller)

cur = (b.assign(date=b.Date.dt.strftime('%Y-%m-%d'))
        .groupby(['date', 'caller', 'team', 'vertical'], as_index=False)
        .agg(txns=('fee', 'size'), fee_paid=('fee', 'sum'), enrollments=('enr', 'sum')))
cur['fee_paid'] = cur.fee_paid.round(2)

old = pd.read_csv('hist_old.csv', keep_default_na=False, na_values=[''])
old['team'] = old['team'].replace(ALIAS)  # apply alias map retroactively to held history
held = old[old.date.str[:7] == f'{Y}-{M:02d}']
hist = pd.concat([old[old.date.str[:7] != f'{Y}-{M:02d}'], cur]).sort_values(['date', 'caller']).reset_index(drop=True)
# 09 Oct 2026 (user: "i dont want teams which are removed"): a team with no Active caller on the current
# roster is a removed team. Re-home its rows to the caller's current live team (and vertical); any rows
# that still cannot be placed are reported as anomalies.
live = set(tm[tm.active]['Team Name'].dropna().astype(str).str.strip().replace(ALIAS)) - {'', 'nan', 'None'}  # blank roster teams are never a destination
rteam = ros['Team Name'].astype(str).str.strip().replace(ALIAS); rvert = ros['Vertical']
dead_mask = ~hist.team.isin(live) & ~hist.caller.isin(['Direct', 'Bootcamp - Direct'])
hk = hist.caller.str.lower()
mv = dead_mask & hk.isin(ros.index) & hk.map(rteam).isin(live)
rehomed = hist[mv].groupby(['team']).agg(rows=('fee_paid', 'size'), rev=('fee_paid', 'sum'))
hist.loc[mv, 'vertical'] = hk[mv].map(rvert); hist.loc[mv, 'team'] = hk[mv].map(rteam)
unplaced = hist[~hist.team.isin(live) & ~hist.caller.isin(['Direct', 'Bootcamp - Direct'])].groupby(['vertical', 'team']).fee_paid.sum()
hist = hist.groupby(['date', 'caller', 'team', 'vertical'], as_index=False, dropna=False)[['txns', 'fee_paid', 'enrollments']].sum()
hist['fee_paid'] = hist.fee_paid.round(2)
hist = hist.sort_values(['date', 'caller']).reset_index(drop=True)
cur = hist[hist.date.str[:7] == f'{Y}-{M:02d}'].copy()
hist.to_csv('revenue_history.csv', index=False)
hist['mon'] = hist.date.str[:7]; hist['day'] = hist.date.str[8:].astype(int)

comp = cur[cur.date <= held.date.max()]
rest = {'held_rev': held.fee_paid.sum(), 'new_rev': comp.fee_paid.sum(), 'held_enr': held.enrollments.sum(), 'new_enr': comp.enrollments.sum()}
kk = ['date', 'caller', 'team', 'vertical']
mm = held.merge(comp, on=kk, how='outer', suffixes=('_h', '_n')).fillna(0)
mm['dr'] = (mm.fee_paid_n - mm.fee_paid_h).round(2); mm['de'] = mm.enrollments_n - mm.enrollments_h
rest['diffs'] = mm[(mm.dr.abs() > 0.005) | (mm.de != 0)][kk + ['fee_paid_h', 'fee_paid_n', 'enrollments_h', 'enrollments_n', 'dr', 'de']]
dayh = held.groupby('date')[['fee_paid', 'enrollments']].sum(); dayn = comp.groupby('date')[['fee_paid', 'enrollments']].sum()
rest['daydiff'] = (dayn - dayh).round(2)
rest['daydiff'] = rest['daydiff'][(rest['daydiff'].fee_paid.abs() > .005) | (rest['daydiff'].enrollments != 0)]

months = sorted(hist.mon.unique())
curm = f'{Y}-{M:02d}'; prevm = months[months.index(curm) - 1]
win = hist[hist.day <= N]
anom = {'unmapped': unmapped, 'txtfee': bd[txtfee][['Date', 'Fee paid', 'fee', CALLER, 'Team Name']],
        'blank_dropped': int((bd['Date'].isna() | bd['fee'].isna()).sum()),
        'other_month_rows': int(((bd['Date'].dt.month != M) & bd['Date'].notna()).sum())}
wb = b
dup = wb[wb['Transaction ID'].notna()].groupby('Transaction ID').agg(n=('fee', 'size'), s=('fee', 'sum'), u=('fee', 'nunique'))
dup = dup[dup.n > 1]; anom['dup'] = (len(dup), int(dup.n.sum()), dup.s.sum(), int((dup.u < dup.n).sum()))
conv = wb[wb['Course'].astype(str).str.contains('convenience|hardcopy|hard copy', case=False, na=False)]
anom['conv'] = (len(conv), conv.fee.sum())
anom['teams_unknown'] = sorted(set(wb.team) - set(tm['Team Name'].astype(str).str.strip().replace(ALIAS)) - {'Direct', 'Bootcamp - Direct'})
en = wb[wb.enr == 1]; anom['enr_ids'] = (len(en), en['Transaction ID'].nunique())
anom['rows'] = len(wb); anom['rev'] = wb.fee.sum(); anom['enr'] = int(wb.enr.sum()); anom['neg'] = int((wb.fee < 0).sum())
anom['roster'] = (len(tm), tm.tgt.sum(), int((tm.tgt > 0).sum()))
anom['lead_na'] = wb[wb['Team Name'] == 'Lead Details not Available'][['Date', 'caller', 'fee', 'Enrollment', 'Course']]
anom['dayN'] = wb[wb.Date.dt.day == N].groupby('vertical').agg(r=('fee', 'sum'), e=('enr', 'sum'), n=('fee', 'size'))
t2 = wb[wb.cn.isin(ros.index)].copy(); t2['rt'] = t2.cn.map(ros['Team Name'].astype(str).str.strip().replace(ALIAS))
anom['team_mismatch'] = t2[t2.rt != t2.team].groupby(['caller', 'team', 'rt']).fee.sum()
anom['rehomed'] = rehomed; anom['unplaced_dead_team_rev'] = unplaced
anom['enr_vals'] = wb['Enrollment'].astype(str).str.strip().value_counts()
anom['columns'] = list(bd.columns)
anom['last_date'] = str(bd[(bd['Date'].dt.year == Y) & (bd['Date'].dt.month == M) & bd['fee'].notna()]['Date'].max())[:10]

pickle.dump(dict(N=N, D=D, Y=Y, M=M, hist=hist, win=win, months=months, curm=curm, prevm=prevm, tm=tm,
                 SEGMENTS=SEGMENTS, rest=rest, anom=anom, ALIAS=ALIAS, PEND=PEND), open('data.pkl', 'wb'))
print('rows', len(wb), 'rev', round(wb.fee.sum(), 2), 'enr', wb.enr.sum(), 'hist rows', len(hist), 'max date', wb.Date.max())
for k, v in rest.items():
    print(k, v if not isinstance(v, pd.DataFrame) else '\n' + v.to_string())
for k, v in anom.items():
    print('--', k, v if not isinstance(v, (pd.DataFrame, pd.Series)) else '\n' + v.to_string())
