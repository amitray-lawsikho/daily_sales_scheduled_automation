import pandas as pd, numpy as np, pickle
d = pickle.load(open('data.pkl', 'rb'))
N, D, hist, win, tm = d['N'], d['D'], d['hist'], d['win'], d['tm']
curm, prevm, PEND = d['curm'], d['prevm'], d['PEND']
# History retention: analyse at most the 12 months ending with the current month (pdf design spec).
_keep = sorted(m for m in d['months'] if m <= curm)[-12:]
win = win[win.mon.isin(_keep)]
ALIAS = d['ALIAS']
tm = tm.copy(); tm['team_c'] = tm['Team Name'].astype(str).str.strip().replace(ALIAS)
tm['Caller Name'] = tm['Caller Name'].astype(str).str.strip()
PR = N / D


def flag(tgt, rev):
    if tgt > 0:
        if rev <= 0: return 'ZERO REVENUE'
        a = rev / (tgt * PR)
        return 'Below 50% pace' if a < .5 else ('Behind pace' if a < 1 else 'On/Ahead of pace')
    return 'No target' if rev > 0 else ''


def ach(tgt, rev):
    return rev / (tgt * PR) if tgt > 0 else np.nan


def leaders(s):
    return ', '.join(sorted(set(str(v).split(' (')[0] for v in s.dropna() if str(v).strip() not in ('', 'nan'))))


def segment(verts):
    w = win[win.vertical.isin(verts)]
    cw, pw = w[w.mon == curm], w[w.mon == prevm]
    ro = tm[tm.Vertical.isin(verts)]
    keys = set(map(tuple, cw[['vertical', 'team']].drop_duplicates().values)) | set(map(tuple, pw[['vertical', 'team']].drop_duplicates().values))
    keys |= set(map(tuple, ro[ro.tgt > 0][['Vertical', 'team_c']].values))
    trows = []
    for v, t in sorted(keys):
        rr = ro[(ro.Vertical == v) & (ro.team_c == t)]
        c1 = cw[(cw.vertical == v) & (cw.team == t)]; p1 = pw[(pw.vertical == v) & (pw.team == t)]
        tg = rr.tgt.sum(); rv = c1.fee_paid.sum()
        trows.append(dict(vertical=v, team=t, leader=leaders(rr['Sales Leader']), tgt=tg, rev=rv, prev=p1.fee_paid.sum(),
                          enr=int(c1.enrollments.sum()), penr=int(p1.enrollments.sum()), pend=rr[PEND].sum(),
                          ach=ach(tg, rv), flag=flag(tg, rv)))
    T = pd.DataFrame(trows)
    T['vo'] = T.vertical.map({v: i for i, v in enumerate(verts)})
    T = T.sort_values(['vo', 'rev'], ascending=[True, False]).reset_index(drop=True)
    V = []
    for v in verts:
        x = T[T.vertical == v]
        V.append(dict(vertical=v, leader=leaders(ro[ro.Vertical == v]['Sales Leader']), tgt=x.tgt.sum(), rev=x.rev.sum(), prev=x.prev.sum(),
                      enr=x.enr.sum(), penr=x.penr.sum(), pend=ro[ro.Vertical == v][PEND].sum(),
                      ach=ach(x.tgt.sum(), x.rev.sum()), flag=flag(x.tgt.sum(), x.rev.sum())))
    V = pd.DataFrame(V)
    cagg = cw[~cw.caller.isin(['Direct', 'Bootcamp - Direct'])].groupby('caller').agg(rev=('fee_paid', 'sum'), enr=('enrollments', 'sum'))
    pagg = pw[~pw.caller.isin(['Direct', 'Bootcamp - Direct'])].groupby('caller').agg(prev=('fee_paid', 'sum'), penr=('enrollments', 'sum'))
    ev = sorted(set(ro[ro.tgt > 0]['Caller Name']) | set(cagg.index))  # sorted: deterministic tie order
    rix = ro.drop_duplicates('Caller Name').set_index('Caller Name')
    C = []
    for c in ev:
        if c in rix.index:
            r = rix.loc[c]; tg = r.tgt; team = r.team_c; v = r.Vertical; ld = leaders(pd.Series([r['Sales Leader']])); pe = r[PEND]; st = r.Status
        else:
            x = cw[cw.caller == c].iloc[0]; tg = 0; team = x.team; v = x.vertical; ld = ''; pe = 0; st = '?'
        rv = cagg.rev.get(c, 0.0)
        C.append(dict(caller=c, team=team, vertical=v, leader=ld, tgt=tg, rev=rv, prev=pagg.prev.get(c, 0.0),
                      enr=int(cagg.enr.get(c, 0)), penr=int(pagg.penr.get(c, 0)), pend=pe, status=st,
                      ach=ach(tg, rv), flag=flag(tg, rv)))
    C = pd.DataFrame(C)
    pace = w.groupby(['mon', 'day']).fee_paid.sum().unstack(0).reindex(range(1, N + 1)).fillna(0).cumsum()
    tot = dict(rev=cw.fee_paid.sum(), prev=pw.fee_paid.sum(), enr=int(cw.enrollments.sum()), penr=int(pw.enrollments.sum()),
               tgt=V.tgt.sum(), pend=V.pend.sum(), rows=int(cw.txns.sum()),
               bymon=w.groupby('mon').fee_paid.sum().to_dict(), enrmon=w.groupby('mon').enrollments.sum().to_dict())
    # Only TEAMS carrying a target count against target (Nov 2026 rule); revenue of no-target teams
    # (e.g. Changemakers with no Nov target) stays in MTD revenue but is excluded from achievement.
    tt = T[T.tgt > 0]
    tot['trev'] = tt.rev.sum()
    tot['ach'] = ach(tot['tgt'], tot['trev'])
    tot['notgt'] = T[(T.tgt <= 0) & (T.rev > 0)].team.tolist()
    return dict(T=T, V=V, C=C, pace=pace, tot=tot, cw=cw, pw=pw, w=w, verts=verts)


def team_pace(S, v, t):
    w = S['w']; w = w[(w.vertical == v) & (w.team == t)]
    return w.groupby(['mon', 'day']).fee_paid.sum().unstack(0).reindex(range(1, N + 1)).fillna(0).cumsum()


def team_callers(S, v, t):
    C = S['C']; pw = S['pw']
    ev = C[(C.vertical == v) & (C.team == t)]
    pc = pw[(pw.vertical == v) & (pw.team == t) & ~pw.caller.isin(['Direct', 'Bootcamp - Direct'])].groupby('caller').fee_paid.sum()
    names = set(ev[(ev.rev > 0) | (ev.prev > 0)].caller) | set(pc.index)
    cw = S['cw']; cc = cw[(cw.vertical == v) & (cw.team == t)].groupby('caller').fee_paid.sum()
    out = pd.DataFrame({'caller': sorted(names)})
    out['prev'] = out.caller.map(pc).fillna(0); out['rev'] = out.caller.map(cc).fillna(0)
    return out.sort_values('rev', ascending=False), ev


SEG = {k: segment(v) for k, v in d['SEGMENTS'].items()}
if __name__ == '__main__':
    pd.set_option('display.width', 250)
    for k, S in SEG.items():
        t = S['tot']
        print('=====', k, {a: (round(b, 3) if isinstance(b, float) else b) for a, b in t.items() if a not in ('bymon', 'enrmon')})
        print({m: round(v) for m, v in t['bymon'].items()}, t['enrmon'])
        print(S['V'].round(3).to_string())
        print(S['T'].drop(columns=['leader']).round(3).to_string())
        # sanity
        cw = S['cw']; print('rollup rev', round(S['V'].rev.sum() - t['rev'], 2), 'enr', S['V'].enr.sum() - t['enr'],
                            'enr share', round(t['enr'] / t['rows'], 3), 'realisation', round(t['rev'] / t['enr']) if t['enr'] else None)
    pickle.dump(SEG, open('seg.pkl', 'wb'))
