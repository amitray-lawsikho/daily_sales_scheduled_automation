import numpy as np, datetime as dt, calendar
from analysis import N, D, curm, prevm, PR

MON = lambda m: dt.date(int(m[:4]), int(m[5:]), 1).strftime('%b')
CM, PM = MON(curm), MON(prevm)
FULL = N == D
rs = lambda v: f"Rs {v:,.0f}"


def pct(a, b):
    return (a - b) / b * 100 if b else np.nan


def _facts(S):
    t = S['tot']; T = S['T'].copy(); C = S['C']
    T['d'] = T.rev - T.prev
    priors = sorted([m for m in t['bymon'] if m != curm], reverse=True)
    cw = S['cw']; day = cw.groupby('day').fee_paid.sum().reindex(range(1, N + 1)).fillna(0)
    return t, T, C, priors, day


def _close(t):
    tr = t['trev']  # revenue of target-carrying teams only
    need = max(t['tgt'] - tr, 0)
    if need <= 0:
        return f"The full-month target is **already covered** ({tr / t['tgt'] * 100:.0f}% of {rs(t['tgt'])})."
    if FULL:
        return f"The month closes **{rs(need)} short** of the {rs(t['tgt'])} target, at an average of {rs(tr / N)} a day."
    return (f"Closing the month on target needs **{rs(need)}** more, about **{rs(need / (D - N))} a day** for the last {D - N} days, "
            f"vs {rs(tr / N)} a day so far.")


def narrative(seg, S):
    t, T, C, priors, day = _facts(S)
    s = []
    if t['tgt'] > 0:
        s.append(f"Through {N} {CM} the segment has booked **{rs(t['rev'])}**, **{t['ach'] * 100:.0f}% of the "
                 f"{'full-month' if FULL else 'pro-rated'} target** ({rs(t['tgt'] * PR)}"
                 + ('' if FULL else f"; {rs(t['tgt'])} for the month") + "). " + _close(t))
    else:
        s.append(f"Through {N} {CM} the segment has booked **{rs(t['rev'])}**. No {CM} targets are loaded on the roster for this segment yet, so achievement is not shown.")
    if t.get('notgt') and t['tgt'] > 0:
        s.append(f"Achievement covers target-carrying teams only; no {CM} target on the roster yet for {', '.join(t['notgt'])}.")
    comp = '; '.join(f"{MON(m)} {rs(t['bymon'][m])} ({pct(t['rev'], t['bymon'][m]):+.1f}%)" for m in priors)
    s.append(f"On the same 1-{N} window revenue is **{pct(t['rev'], t['prev']):+.1f}% vs {PM}** — {comp} — and enrollments are "
             f"**{t['enr']} vs {t['penr']}**.")
    big = T.sort_values('rev', ascending=False).iloc[0]
    s.append(f"Largest book: **{big.team}** at {rs(big.rev)}.")
    if len(T) > 1:
        g = T[(T.rev > 0) | (T.prev > 0)].sort_values('d', ascending=False).iloc[0]; dr = T.sort_values('d').iloc[0]
        s.append((f"Biggest gain: **{g.team}** (+{rs(abs(g.d))[3:]} vs {PM}). " if g.d > 0 else
                  f"No team is ahead of its {PM} window; the smallest gap is **{g.team}** ({rs(g.d)}). ")
                 + (f"Biggest drag: **{dr.team}** ({rs(dr.d)} vs {PM})." if dr.d < 0 else f"Every team is at or above its {PM} window."))
    return ' '.join(s)


def bullets(seg, S):
    t, T, C, priors, day = _facts(S)
    tg = C[C.tgt > 0]
    out = []
    if t['tgt'] > 0:
        need = max(t['tgt'] - t['trev'], 0)
        vs = S['V']
        vtxt = '; '.join(f"{r.vertical} {r.ach * 100:.0f}%" if r.tgt > 0 else f"{r.vertical} no {CM} target" for r in vs.itertuples()) if len(vs) > 1 else ''
        tail = (f" The monthly target of {rs(t['tgt'])} is exceeded." if need <= 0 else
                (f" Month closes **{rs(need)} short**; average run-rate was **{rs(t['trev'] / N)}/day** vs {rs(t['tgt'] / D)}/day needed." if FULL else
                 f" Needs **{rs(need / (D - N))}/day** for the rest of {CM} vs **{rs(t['trev'] / N)}/day** run-rate so far."))
        out.append(('Pacing', f"**{t['ach'] * 100:.0f}%** of the {'full-month' if FULL else 'pro-rated'} target ({rs(t['trev'])} of {rs(t['tgt'] * PR)})"
                    + (f" — by vertical: {vtxt}." if vtxt else '.') + tail))
    comp = ', '.join(f"{MON(m)} {pct(t['rev'], t['bymon'][m]):+.0f}%" for m in priors)
    enr = ', '.join(f"{MON(m)} {int(t['enrmon'][m])}" for m in priors)
    out.append(('Momentum', f"Same-window revenue {comp}. Enrollments **{t['enr']}** vs {enr}"
                + (" (Jun is still on the old, overstated enrollment definition)." if '2026-06' in priors else '.')))
    g = T[(T.rev > 0) | (T.prev > 0)].sort_values('d', ascending=False).iloc[0]
    gc = C[C.team == g.team].assign(d=lambda x: x.rev - x.prev).sort_values('d', ascending=False)
    gtxt = f" Top caller gain: {gc.iloc[0].caller} (+{rs(abs(gc.iloc[0].d))[3:]})." if len(gc) and gc.iloc[0].d > 0 else ''
    out.append(('Biggest driver', (f"**{g.team}** {rs(g.rev)} vs {rs(g.prev)} (+{rs(abs(g.d))[3:]})" if g.d > 0 else
                                   f"No team beats its {PM} window; closest is **{g.team}** ({rs(g.rev)} vs {rs(g.prev)})")
                + (f", {g.ach * 100:.0f}% of target." if g.tgt > 0 else '.') + gtxt))
    dr = T.sort_values('d').iloc[0]
    dc = C.assign(d=C.rev - C.prev)
    dc = dc[dc.team == dr.team].sort_values('d').head(3)
    dtxt = ', '.join(f"{r.caller} {rs(r.d)}" for r in dc.itertuples() if r.d < 0)
    if dr.d >= 0:
        out.append(('Biggest drag', f"No team is below its {PM} window; the smallest gain is **{dr.team}** {rs(dr.rev)} vs {rs(dr.prev)} (+{rs(dr.d)[3:]}, {pct(dr.rev, dr.prev):+.0f}%)."
                    + (f" Largest caller gaps inside it: {dtxt}." if dtxt else '')))
    else:
        out.append(('Biggest drag', f"**{dr.team}** {rs(dr.rev)} vs {rs(dr.prev)} (**{rs(dr.d)}**, {pct(dr.rev, dr.prev):+.0f}%)."
                    + (f" Largest caller gaps: {dtxt}." if dtxt else '')))
    fl = tg.flag.value_counts()
    topn = tg[tg.ach >= 1].sort_values('ach', ascending=False).head(3)
    if len(tg) == 0:
        out.append(('Caller-level', f"No caller in this segment has a {CM} target on the roster yet. **{(C.rev > 0).sum()}** callers have booked revenue; "
                    + "top books: " + ', '.join(f"{r.caller} {rs(r.rev)}" for r in C.sort_values('rev', ascending=False).head(3).itertuples()) + '.'))
    else: out.append(('Caller-level', f"Of {len(tg)} target holders: **{fl.get('On/Ahead of pace', 0)} on/ahead**, {fl.get('Behind pace', 0)} behind (50-99%), "
                f"**{fl.get('Below 50% pace', 0)} below 50%**, **{fl.get('ZERO REVENUE', 0)} at zero**."
                + (" Leading: " + ', '.join(f"{r.caller} {r.ach * 100:.0f}%" for r in topn.itertuples()) + '.' if len(topn) else ' Nobody reached target.')))
    z = tg[tg.rev <= 0]; b50 = tg[(tg.flag == 'Below 50% pace')]
    risk = (f"**{len(z)} zero-revenue holders** carry {rs(z.tgt.sum())} of monthly target"
            + (f" (largest: {', '.join(f'{r.caller} {rs(r.tgt)}' for r in z.sort_values('tgt', ascending=False).head(3).itertuples())})" if len(z) else '')
            + f"; below-50% callers hold **{rs(b50.tgt.sum())}** ({b50.tgt.sum() / t['tgt'] * 100:.0f}% of target)." if t['tgt'] else '')
    if not t['tgt']:
        risk = f"Targets for {', '.join(S['V'].vertical)} are not on the {CM} roster yet — pace flags and achievement are suppressed until they are."
    lowbooks = T[(T.tgt > 0) & (T.ach < .5)].sort_values('ach')
    if len(lowbooks):
        risk += " Teams under 50%: " + ', '.join(f"{r.team} {r.ach * 100:.0f}%" for r in lowbooks.itertuples()) + '.'
    out.append(('Risk', risk))
    pe = C[C.pend > 0].sort_values('pend', ascending=False).head(4)
    out.append(('Recovery lever', f"Roster pending revenue is **{rs(t['pend'])}** (current + previous month, not comparable MoM). Top holders: "
                + ', '.join(f"{r.caller} {rs(r.pend)}" for r in pe.itertuples()) + '.'))
    if FULL:
        care = (f"This is the complete {CM} month (1-{D}); the comparison months are cut at day {N} for a like-for-like window"
                f" ({PM} has {31 if PM in ('Jan','Mar','May','Jul','Aug','Oct','Dec') else 30} days).")
    else:
        def wd(y, m):
            hol = {(10, 2)}
            return sum(1 for dd in range(1, N + 1) if calendar.weekday(y, m, dd) < 5 and (m, dd) not in hol)
        cy, cmn = int(curm[:4]), int(curm[5:]); py, pmn = int(prevm[:4]), int(prevm[5:])
        care = (f"Day-{N} comparisons are pacing signals, not verdicts (Jul had the weakest opening window yet the best full month). "
                f"1-{N} {CM} had only **{wd(cy, cmn)} working day(s)**" + (" (2 Oct holiday, 3-4 Oct weekend)" if cmn == 10 else '')
                + f" vs {wd(py, pmn)} in 1-{N} {PM}, so the same-window comparison is distorted by the calendar.")
    if 'Collection' in seg:
        care += ((" Collection books front-load after payment cycles, so achievement % against these targets overstates performance;" if t['tgt'] else '') + f" The honest signal is the "
                 f"{pct(t['rev'], t['prev']):+.0f}% same-window gap vs {PM}. {N} {CM} alone was {rs(day.iloc[-1])} and {N-1}-{N} {CM} together {rs(day.iloc[-2:].sum())}.")
    else:
        care += f" {N} {CM} alone added {rs(day.iloc[-1])}; the last 3 days together {rs(day.iloc[-3:].sum())}."
    # teams emptied by a roster move (zero now, prior revenue, callers re-homed on the current roster)
    from analysis import tm as _tm
    home = _tm.drop_duplicates('Caller Name').set_index('Caller Name').team_c
    for r in T[(T.rev <= 0) & (T.prev > 0) & (T.tgt <= 0)].itertuples():
        pc = S['pw'][(S['pw'].team == r.team) & ~S['pw'].caller.isin(['Direct', 'Bootcamp - Direct'])].caller.unique()
        dest = sorted({home[c] for c in pc if c in home.index and home[c] != r.team})
        if dest:
            both = T[T.team.isin([r.team] + dest)]
            care += (f" **{r.team}** callers now sit in {', '.join(dest)} on the {CM} roster, so that team's gain and {r.team}'s "
                     f"{rs(r.rev - r.prev)} are largely the move; combined they are {rs(both.rev.sum())} vs {rs(both.prev.sum())} "
                     f"({pct(both.rev.sum(), both.prev.sum()):+.0f}%).")
    out.append(('Read with care', care))
    return out
