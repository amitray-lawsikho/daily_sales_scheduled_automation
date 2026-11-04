import pandas as pd, numpy as np, pickle, datetime as dt, sys
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.patches import FancyBboxPatch
from matplotlib.lines import Line2D
from analysis import SEG, team_pace, team_callers, N, D, curm, prevm, PR
from keypoints import narrative, bullets

plt.rcParams.update({'font.family': 'DejaVu Sans', 'axes.spines.top': False, 'axes.spines.right': False,
                     'axes.edgecolor': '#C9CED6', 'axes.labelcolor': '#4B5563', 'xtick.color': '#4B5563', 'ytick.color': '#4B5563'})
W, H = 841.68 / 72, 595.44 / 72
LM, RM, TM, BM = .5, .5, .85, .42
CW = W - LM - RM; COL = 5.15; GAP = .35
NAVY_H = '#12253F'; G1 = '#6B7280'; G2 = '#9AA1AC'; RULE = '#D5D9E0'
CUR = '#2E5FA3'; PREVB = '#AFC3DC'; GREEN = '#3E8E5A'; AMBER = '#D68910'; RED = '#C0392B'
CYCLE = ['#0F8C82', '#D2691E', '#7E57C2', '#C2185B', '#6E8B3D', '#00838F', '#8D6E63', '#B8860B', '#4527A0', '#33691E', '#A0522D']
DASH = [(5, 2), (1.6, 1.6), (7, 2, 1.6, 2), (3, 1.5, 1.5, 1.5)]
MON = lambda m: dt.date(int(m[:4]), int(m[5:]), 1).strftime('%b')
MONY = lambda m: dt.date(int(m[:4]), int(m[5:]), 1).strftime('%b %Y')
CM, PM = MON(curm), MON(prevm)
CY = curm[:4]
import os
GEN = os.environ.get('MTD_GEN_DATE') or dt.date.today().strftime('%d %b %Y')
rs = lambda v: f"Rs {v:,.0f}"
FLAGC = {'ZERO REVENUE': RED, 'Below 50% pace': RED, 'Behind pace': AMBER, 'On/Ahead of pace': GREEN, 'No target': G1, '': G1}


def fx(x): return x / W
def fy(y): return 1 - y / H


def ax_at(fig, x, y, w, h):
    return fig.add_axes([fx(x), fy(y + h), w / W, h / H])


def frame(fig, title, seg, page, total, note, prior_months):
    fig.text(fx(LM), fy(.42), title, fontsize=16, fontweight='bold', color=NAVY_H, va='baseline')
    pri = ', '.join(MON(m) for m in reversed(prior_months))
    fig.text(fx(LM), fy(.62), f"Window: 1-{N} {CM} {CY} (last complete day) vs same window {pri} | Generated {GEN} | Playbook v6",
             fontsize=8.3, color=G1, va='baseline')
    fig.add_artist(Line2D([fx(LM), fx(W - RM)], [fy(.70)] * 2, color=RULE, lw=.8))
    fig.text(fx(LM), fy(H - .2), f"{seg} | page {page} of {total}", fontsize=7.5, color=G2)
    fig.text(fx(W - RM), fy(H - .2), note, fontsize=7.5, color=G2, ha='right')


def rich(fig, x, y, width, parts, size=9.5, color='#1F2937', lh=1.45, indent=0.0):
    r = fig.canvas.get_renderer()
    words = []; prev_sp = True
    for t, b, c in parts:
        toks = t.split(' ')
        for i, wd in enumerate(toks):
            if wd == '': continue
            glue = (i == 0 and not t.startswith(' ') and not prev_sp)
            words.append((wd, b, c, glue))
        prev_sp = t.endswith(' ')
    cx = x + indent; cy = y; line_h = size / 72 * lh
    def meas(s_, b_):
        tt = fig.text(0, 0, s_, fontsize=size, fontweight='bold' if b_ else 'normal')
        v = tt.get_window_extent(r).width / fig.dpi; tt.remove(); return v
    spw = meas('a a', False) - meas('aa', False)
    first = True
    for wd, b, c, glue in words:
        wpx = meas(wd, b)
        lead = 0 if (first or glue) else spw
        if cx + lead + wpx > x + width + 0.02 and not first:
            cx = x + indent; cy += line_h; lead = 0
        cx += lead
        fig.text(fx(cx), fy(cy), wd, fontsize=size, fontweight='bold' if b else 'normal', color=c or color, va='baseline')
        cx += wpx; first = False
    return cy + line_h


def md(s):
    out = []; bold = False
    for i, seg in enumerate(s.split('**')):
        if seg: out.append((seg, bold, None))
        bold = not bold
    return out


def short_team(t, L=26):
    if len(t) <= L: return t
    if ' - ' in t:
        head, tail = t.rsplit(' - ', 1)
        keep = max(3, L - len(tail) - 5)
        return head[:keep].rstrip() + '.. - ' + tail
    return t[:L - 2] + '..'


def pacing(ax, pace, title):
    months = list(pace.columns)
    priors = [m for m in months if m != curm][::-1][:11]
    for i, m in enumerate(priors):
        ax.plot(pace.index, pace[m] / 1e5, color=CYCLE[i], lw=1.7, dashes=DASH[i % 4], label=MONY(m), zorder=2)
    if curm in pace:
        ax.plot(pace.index, pace[curm] / 1e5, color=CUR, lw=2.6, marker='o', ms=3.2, label=MONY(curm) + ' (current)', zorder=5)
    ax.set_title(title, fontsize=9.5, loc='left', color=NAVY_H, fontweight='bold')
    ax.set_xlim(.5, N + .5); ax.set_xticks(range(1, N + 1)); ax.tick_params(labelsize=7)
    ax.set_xlabel('Day of month', fontsize=7.5); ax.set_ylabel('Cumulative revenue (Rs lakh)', fontsize=7.5)
    ax.grid(axis='y', color='#EEF0F3', lw=.7); ax.set_ylim(bottom=0)
    h, l = ax.get_legend_handles_labels()
    order = [l.index(MONY(curm) + ' (current)')] + [i for i in range(len(l)) if not l[i].endswith('(current)')] if curm in pace else list(range(len(l)))
    ax.legend([h[i] for i in order], [l[i] for i in order], fontsize=7.2, handlelength=2.6, frameon=False,
              ncol=2 if len(l) > 5 else 1, loc='upper left')


def bars(ax, labels, prev, cur, title, rot=0):
    x = np.arange(len(labels)); bw = .38
    b1 = ax.bar(x - bw / 2, np.array(prev) / 1e5, bw, color=PREVB, label=f'{PM} 1-{N}')
    b2 = ax.bar(x + bw / 2, np.array(cur) / 1e5, bw, color=CUR, label=f'{CM} 1-{N}')
    fs = 6.6 if len(labels) <= 8 else (5.6 if len(labels) <= 13 else 4.8)
    for bb in (b1, b2):
        for r in bb:
            ax.text(r.get_x() + r.get_width() / 2, r.get_height(), f'{r.get_height():.2f}', ha='center', va='bottom',
                    fontsize=fs, rotation=90 if len(labels) > 8 else 0, color='#374151')
    ax.set_xticks(x); ax.set_xticklabels(labels, rotation=rot, ha='right' if rot else 'center', fontsize=6.8 if len(labels) <= 10 else 6)
    ax.set_ylabel('Revenue (Rs lakh)', fontsize=7.5); ax.tick_params(axis='y', labelsize=7)
    top = max(max(prev, default=0), max(cur, default=0)) / 1e5
    ax.set_ylim(0, top * (1.28 if len(labels) > 8 else 1.18) + .01)
    ax.set_title(title, fontsize=9.5, loc='left', color=NAVY_H, fontweight='bold')
    ax.legend(fontsize=7.2, frameon=False, loc='upper right'); ax.grid(axis='y', color='#EEF0F3', lw=.7); ax.set_axisbelow(True)


def kpi_cards(fig, tot, y=.95, h=1.0):
    n = 5; gap = .18; w = (CW - gap * (n - 1)) / n
    d = tot['rev'] - tot['prev']; pct = d / tot['prev'] * 100 if tot['prev'] else 0
    a = tot['ach']
    ac = G1 if np.isnan(a) else (RED if a < .5 else AMBER if a < 1 else GREEN)
    cards = [('MTD Revenue', rs(tot['rev']), f'{CM} 1-{N}, {tot["rows"]:,} revenue rows', NAVY_H),
             (f'vs {PM} 1-{N} window', f'{pct:+.1f}%', f'{rs(tot["prev"])} ({"+" if d >= 0 else "-"}{rs(abs(d))[3:]})', GREEN if d >= 0 else RED),
             ('Achievement % (pro-rated)', '—' if np.isnan(a) else f'{a * 100:.0f}%', (f'of {rs(tot["tgt"] * PR)} pro-rated (targeted teams)' if tot.get('notgt') else f'of {rs(tot["tgt"] * PR)} pro-rated (Till {N}/{D})') if tot['tgt'] > 0 else f'No {CM} targets on roster - suppressed', ac),
             ('Enrollments', f'{tot["enr"]:,}', f'{PM} 1-{N}: {tot["penr"]:,}  ("New enrollment" rows)', NAVY_H),
             ('Pending Revenue', rs(tot['pend']), 'Roster, current + previous month', NAVY_H)]
    for i, (lab, val, sub, col) in enumerate(cards):
        x = LM + i * (w + gap)
        fig.add_artist(FancyBboxPatch((fx(x), fy(y + h)), w / W, h / H, boxstyle='round,pad=0,rounding_size=0.012',
                                      transform=fig.transFigure, fc='#F7F9FC', ec='#DCE2EA', lw=.8))
        fig.text(fx(x + .13), fy(y + .24), lab, fontsize=7.8, color=G1)
        fig.text(fx(x + .13), fy(y + .62), val, fontsize=17, fontweight='bold', color=col)
        fig.text(fx(x + .13), fy(y + .86), sub, fontsize=6.3, color=G1)


def ach_bars(ax, df, title, color_fn, legend_loc):
    y = np.arange(len(df))
    vals = df.ach.values * 100
    ax.barh(y, vals, color=[color_fn(v) for v in vals], height=.62)
    for yi, v in zip(y, vals):
        ax.text(v, yi, f' {v:.0f}%', va='center', fontsize=6.8, color='#374151')
    ax.set_yticks(y); ax.set_yticklabels([f'{c}  ({short_team(t, 22)})' for c, t in zip(df.caller, df.team)], fontsize=6.7)
    ax.invert_yaxis(); ax.axvline(100, color='#374151', ls='--', lw=1)
    ax.set_xlim(0, max(110, vals.max() * 1.18 if len(vals) else 110)); ax.tick_params(axis='x', labelsize=7)
    ax.set_xlabel('Achievement % of pro-rated target', fontsize=7.5)
    ax.set_title(title, fontsize=9.5, loc='left', color=NAVY_H, fontweight='bold')
    hs = [plt.Rectangle((0, 0), 1, 1, color=c) for c in ([RED, AMBER] if 'Bottom' in title else [GREEN])]
    ls = ['Below 50%', '50-99%'] if 'Bottom' in title else ['On/ahead (>=100%)']
    ax.legend(hs + [Line2D([0], [0], color='#374151', ls='--')], ls + ['On-pace (100%)'], fontsize=7, frameon=True,
              framealpha=.95, loc=legend_loc)
    ax.grid(axis='x', color='#EEF0F3', lw=.7); ax.set_axisbelow(True)


def build(segname, S, path):
    T, C, tot, verts = S['T'], S['C'], S['tot'], S['verts']
    prior_months = [m for m in S['pace'].columns if m != curm]
    teams = T[(T.rev > 0) | (T.prev > 0) | (T.tgt > 0)]
    total = 3 + len(teams)
    with PdfPages(path) as pdf:
        fig = plt.figure(figsize=(W, H))
        frame(fig, f'MTD Report — {CM} 1-{N}, {CY} — {segname}', segname, 1, total,
              'Revenue = Fee paid; Enrollment = "New enrollment" (v6)', prior_months)
        kpi_cards(fig, tot)
        ax = ax_at(fig, LM, 2.2, COL, 3.75); pacing(ax, S['pace'], f'Cumulative revenue pacing, days 1-{N}')
        ax = ax_at(fig, LM + COL + GAP + .1, 2.2, COL - .1, 3.75)
        lab = [short_team(t, 24) + (f' ({v.replace("Team ", "")})' if len(verts) > 1 else '') for t, v in zip(teams.team, teams.vertical)]
        bars(ax, lab, teams.prev.tolist(), teams.rev.tolist(), f'Team revenue: {PM} 1-{N} vs {CM} 1-{N} (Rs lakh)', rot=30)
        rich(fig, LM, 7.0, CW, md(narrative(segname, S)), size=9)
        pdf.savefig(fig); plt.close(fig)
        fig = plt.figure(figsize=(W, H))
        note2 = f'Achievement % = revenue {CM} 1-{N} / (monthly target x {N}/{D})'
        if tot.get('notgt'): note2 += f" | No {CM} targets yet for {', '.join(tot['notgt'])} - target metrics suppressed"
        frame(fig, f'Caller pacing — {segname}', segname, 2, total, note2, prior_months)
        tg = C[C.tgt > 0]
        bot = tg[(tg.rev > 0) & (tg.ach < 1)].sort_values('ach').head(15)
        top = tg[tg.ach >= 1].sort_values('ach', ascending=False).head(10)
        hh = 5.2
        ax = ax_at(fig, LM + 1.85, 1.05, COL - 1.85, hh)
        if len(bot): ach_bars(ax, bot, f'Bottom {len(bot)} pacers (excl. zero-revenue holders)', lambda v: RED if v < 50 else AMBER, 'upper right')
        else: ax.axis('off'); ax.text(.5, .5, 'No revenue-earning target holder is behind pace' if len(tg) else f'No {CM} targets on the roster for this segment yet', ha='center', fontsize=9, color=G1)
        ax = ax_at(fig, LM + COL + GAP + 1.85, 1.05, COL - 1.85, hh * max(len(top), 4) / 15 if len(top) < 15 else hh)
        if len(top): ach_bars(ax, top, f'Top {len(top)} pacers', lambda v: GREEN, 'lower right')
        else: ax.axis('off'); ax.text(.5, .5, 'No target holder is on pace yet' if len(tg) else '', ha='center', fontsize=9, color=G1)
        z = tg[tg.rev <= 0].sort_values(['team', 'caller'])
        y = rich(fig, LM, 6.92, CW, [(f'Zero-revenue target holders ({len(z)}): ', True, RED),
                                     ('; '.join(f'{c} ({short_team(t, 30)})' for c, t in zip(z.caller, z.team)) or 'none', True, RED)], size=8)
        nt = C[(C.tgt <= 0) & (C.rev > 0)].sort_values('rev', ascending=False)
        rich(fig, LM, y + .02, CW, [(f'Revenue but no active target ({len(nt)}, excluded from both charts): ', True, G1),
                                   ('; '.join(f'{c} ({rs(r)})' for c, r in zip(nt.caller, nt.rev)) or 'none', False, G1)], size=7.6)
        pdf.savefig(fig); plt.close(fig)
        fig = plt.figure(figsize=(W, H))
        frame(fig, f'Key points — {segname}', segname, 3, total, 'Analysis only — all data tables live in the matching xlsx', prior_months)
        bl = bullets(segname, S)
        r = fig.canvas.get_renderer()
        widths = []
        for lab_, _ in bl:
            t = fig.text(0, 0, lab_ + ':', fontsize=10, fontweight='bold'); widths.append(t.get_window_extent(r).width / fig.dpi); t.remove()
        ind = max(widths) + .18
        y = 1.2
        for lab_, body in bl:
            fig.text(fx(LM), fy(y), '•', fontsize=10, color=CUR, va='baseline')
            fig.text(fx(LM + .2), fy(y), lab_ + ':', fontsize=10, fontweight='bold', color=NAVY_H, va='baseline')
            y = rich(fig, LM + .2, y, CW - .2, md(body), size=10, indent=ind, lh=1.4) + 11 / 72
        pdf.savefig(fig); plt.close(fig)
        for pg, (_, t) in enumerate(teams.iterrows(), start=4):
            fig = plt.figure(figsize=(W, H))
            ttl = f'Team deep dive — {t.team}' + (f' ({t.vertical})' if len(verts) > 1 else '')
            frame(fig, ttl, segname, pg, total, 'Team deep dive', prior_months)
            dd = t.rev - t.prev; pc = f'{dd / t.prev * 100:+.0f}%' if t.prev else 'new'
            achs = f'{t.ach * 100:.0f}% of pro-rated {rs(t.tgt * PR)}' if t.tgt > 0 else 'no active target'
            parts = [('MTD ', False, None), (rs(t.rev), True, None), ('  |  vs ' + PM + ' window: ', False, None), (f'{rs(t.prev)} ({pc})', True, None),
                     ('  |  Achv: ', False, None), (achs, True, None), ('  |  Enrollments: ', False, None), (f'{t.penr} → {t.enr}', True, None),
                     ('  |  Pending: ', False, None), (rs(t.pend), True, None), ('  |  ', False, None), (t.flag or '—', True, FLAGC.get(t.flag, G1))]
            r = fig.canvas.get_renderer()
            for size in np.arange(9.6, 6.5, -.2):
                tw = 0
                for s_, b_, _ in parts:
                    tt = fig.text(0, 0, s_, fontsize=size, fontweight='bold' if b_ else 'normal'); tw += tt.get_window_extent(r).width / fig.dpi; tt.remove()
                if tw <= CW: break
            cx = LM
            for s_, b_, c_ in parts:
                tt = fig.text(fx(cx), fy(1.0), s_, fontsize=size, fontweight='bold' if b_ else 'normal', color=c_ or '#1F2937', va='baseline')
                cx += tt.get_window_extent(r).width / fig.dpi
            ax = ax_at(fig, LM, 1.35, COL, 4.85); pacing(ax, team_pace(S, t.vertical, t.team), f'{t.team}: cumulative revenue, days 1-{N}')
            tc, ev = team_callers(S, t.vertical, t.team)
            ax = ax_at(fig, LM + COL + GAP + .1, 1.35, COL - .1, 4.85)
            if len(tc): bars(ax, tc.caller.tolist(), tc.prev.tolist(), tc.rev.tolist(), f'Caller revenue: {PM} 1-{N} vs {CM} 1-{N} (Rs lakh)', rot=35)
            else: ax.axis('off')
            zz = ev[(ev.tgt > 0) & (ev.rev <= 0)].caller.sort_values()
            y = rich(fig, LM, 7.05, CW, [(f'Zero-revenue target holders in {t.team} ({len(zz)}): ', True, RED if len(zz) else G1),
                                         (', '.join(zz) if len(zz) else 'none', False, RED if len(zz) else G1)], size=8.4)
            fl = ev.flag.value_counts()
            rich(fig, LM, y + .02, CW, [(f'Callers evaluated: {len(ev)} | on/ahead of pace {fl.get("On/Ahead of pace", 0)} | behind {fl.get("Behind pace", 0)} | '
                                         f'below 50% {fl.get("Below 50% pace", 0)} | zero {fl.get("ZERO REVENUE", 0)} | no target {fl.get("No target", 0)}. '
                                         'Team columns are full-window aggregates and may exceed the sum of listed callers.', False, G2)], size=7.4)
            pdf.savefig(fig); plt.close(fig)
    return total


if __name__ == '__main__':
    # MTD_SEGMENTS: comma-separated segment names to render (default policy: Team Uzair only).
    want = [s.strip() for s in os.environ.get('MTD_SEGMENTS', 'Team Uzair').split(',') if s.strip()]
    outdir = os.environ.get('MTD_OUT', 'out')
    os.makedirs(outdir, exist_ok=True)
    for k in want:
        n = build(k, SEG[k], os.path.join(outdir, f'MTD Report {CM} 1-{N} - {k}.pdf')); print(k, n, 'pages')
