"""PDF of the Daily Sales Check: overview, trends, the checks, then four pages per team
(position + trends, callers, why revenue is not coming, untouched high-intent leads), then definitions.

Landscape A4, the palette and type of the MTD Revenue Analysis report (navy #12253F headers, flag
red/amber/green, current navy #2E5FA3 vs prior light blue). Charts are matplotlib PNGs.
"""
from __future__ import annotations

import io
from datetime import datetime, timedelta, timezone

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from reportlab.lib import colors  # noqa: E402
from reportlab.lib.enums import TA_LEFT  # noqa: E402
from reportlab.lib.pagesizes import A4, landscape  # noqa: E402
from reportlab.lib.styles import ParagraphStyle  # noqa: E402
from reportlab.lib.units import inch  # noqa: E402
from reportlab.platypus import (BaseDocTemplate, CondPageBreak, Frame, Image, KeepTogether, PageBreak,  # noqa: E402
                                PageTemplate, Paragraph, Spacer, Table, TableStyle)

from dsc.analysis import EW_LABEL, FUNNEL, Result, flagged_callers  # noqa: E402
from dsc.settings import CFG, TEAMS  # noqa: E402

NAVY_H, G1, G2, RULE = "#12253F", "#6B7280", "#9AA1AC", "#D5D9E0"
CUR, PREVB, GREEN, AMBER, RED = "#2E5FA3", "#AFC3DC", "#3E8E5A", "#D68910", "#C0392B"
CYCLE = ["#0F8C82", "#D2691E", "#7E57C2", "#C2185B", "#6E8B3D", "#00838F"]
TEAM_C = {t: c for t, c in zip(TEAMS, [CUR, "#0F8C82", "#D2691E", "#7E57C2"])}
IST = timezone(timedelta(hours=5, minutes=30))

PAGE = landscape(A4)
LM = RM = 0.5 * inch
TM, BM = 0.85 * inch, 0.45 * inch
CW = PAGE[0] - LM - RM

plt.rcParams.update({"font.family": "DejaVu Sans", "axes.spines.top": False, "axes.spines.right": False,
                     "axes.edgecolor": "#C9CED6", "axes.labelcolor": "#4B5563", "xtick.color": "#4B5563",
                     "ytick.color": "#4B5563", "font.size": 8})

S = {
    "h1": ParagraphStyle("h1", fontName="Helvetica-Bold", fontSize=13, textColor=colors.HexColor(NAVY_H), spaceAfter=4, spaceBefore=2),
    "h2": ParagraphStyle("h2", fontName="Helvetica-Bold", fontSize=10, textColor=colors.HexColor(NAVY_H), spaceAfter=3, spaceBefore=6),
    "p": ParagraphStyle("p", fontName="Helvetica", fontSize=8.4, leading=11, textColor=colors.HexColor("#1F2937")),
    "small": ParagraphStyle("small", fontName="Helvetica", fontSize=7.2, leading=9, textColor=colors.HexColor(G1)),
    "cell": ParagraphStyle("cell", fontName="Helvetica", fontSize=6.9, leading=8.2, alignment=TA_LEFT),
    "cellb": ParagraphStyle("cellb", fontName="Helvetica-Bold", fontSize=6.9, leading=8.2),
    "card_l": ParagraphStyle("cl", fontName="Helvetica", fontSize=7.5, textColor=colors.HexColor(G1), leading=9),
    "card_v": ParagraphStyle("cv", fontName="Helvetica-Bold", fontSize=14, textColor=colors.HexColor(NAVY_H), leading=17),
    "card_s": ParagraphStyle("cs", fontName="Helvetica", fontSize=7.2, textColor=colors.HexColor(G1), leading=9),
}


# ------------------------------------------------------------------ formatting
def rs(v) -> str:
    return "-" if v is None or pd.isna(v) else f"Rs {v:,.0f}"


def lakh(v) -> str:
    return "-" if v is None or pd.isna(v) else f"{v / 1e5:,.2f}L"


def pct(v) -> str:
    return "-" if v is None or pd.isna(v) else f"{v:.0f}%"


def f1(v, d=1) -> str:
    return "-" if v is None or pd.isna(v) else f"{v:,.{d}f}"


def pace_color(p) -> str:
    if p is None or pd.isna(p):
        return G1
    return GREEN if p >= 100 else AMBER if p >= CFG["mtd"]["min_pct"] else RED


def P(text, style="cell"):
    return Paragraph(str(text), S[style])


def fig_img(fig, w_in, h_in) -> Image:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=170, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return Image(buf, width=w_in * inch, height=h_in * inch)


def table(rows, widths, header_rows=1, zebra=True, font=6.9, extra=None, repeat=True) -> Table:
    t = Table(rows, colWidths=widths, repeatRows=header_rows if repeat else 0)
    st = [("FONT", (0, 0), (-1, -1), "Helvetica", font),
          ("FONT", (0, 0), (-1, header_rows - 1), "Helvetica-Bold", font),
          ("TEXTCOLOR", (0, 0), (-1, header_rows - 1), colors.white),
          ("BACKGROUND", (0, 0), (-1, header_rows - 1), colors.HexColor(NAVY_H)),
          ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
          ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor(RULE)),
          ("TOPPADDING", (0, 0), (-1, -1), 1.6), ("BOTTOMPADDING", (0, 0), (-1, -1), 1.6),
          ("LEFTPADDING", (0, 0), (-1, -1), 2.5), ("RIGHTPADDING", (0, 0), (-1, -1), 2.5)]
    if zebra:
        for i in range(header_rows, len(rows)):
            if (i - header_rows) % 2:
                st.append(("BACKGROUND", (0, i), (-1, i), colors.HexColor("#F4F6F9")))
    t.setStyle(TableStyle(st + (extra or [])))
    return t


# ------------------------------------------------------------------ charts
def short(t: str) -> str:
    return t.replace("Corporate law - ", "CL - ")


def chart_monthly(res: Result):
    mo = res.monthly
    fig, axes = plt.subplots(1, len(TEAMS), figsize=(10.2, 2.35), sharey=False)
    for ax, tm in zip(np.atleast_1d(axes), TEAMS):
        g = mo[mo["team"] == tm]
        x = np.arange(len(g))
        lab = [pd.Timestamp(m + "-01").strftime("%b") + (" (MTD)" if p else "") for m, p in zip(g["month"], g["partial"])]
        ax.bar(x - 0.2, g["prorated"] / 1e5, 0.4, color=PREVB, label="Target (MTD: pro-rated)")
        bars = ax.bar(x + 0.2, g["revenue"] / 1e5, 0.4, color=CUR, label="Revenue")
        for b, a in zip(bars, g["achv_pct"]):
            ax.text(b.get_x() + b.get_width() / 2, b.get_height(), pct(a), ha="center", va="bottom", fontsize=6.5,
                    color=pace_color(a), fontweight="bold")
        ax.set_xticks(x, lab, fontsize=7)
        ax.set_title(tm, fontsize=8.5, color=NAVY_H, loc="left", fontweight="bold")
        ax.set_ylabel("Rs lakh", fontsize=7)
    np.atleast_1d(axes)[0].legend(fontsize=6.5, frameon=False, loc="upper left")
    fig.suptitle("Monthly revenue vs target (label = achievement; current month vs pro-rated target)", fontsize=8.5,
                 x=0.01, ha="left", color=G1)
    fig.tight_layout()
    return fig_img(fig, 10.2, 2.35)


def chart_weekly(res: Result, metric: str, title: str, ylabel: str, run_rate=False, w=5.0, h=1.95):
    wt = res.weekly_team
    fig, ax = plt.subplots(figsize=(w, h))
    for tm in TEAMS:
        g = wt[wt["team"] == tm]
        lab = [f"{d:%d %b}" + ("" if c else "*") for d, c in zip(g["week"], g["complete"])]
        v = g[metric] / (1e5 if metric == "revenue" else 1)
        ax.plot(lab, v, marker="o", ms=3, lw=1.8, color=TEAM_C[tm], label=short(tm))
        if run_rate:
            ax.plot(lab, g["run_rate"] / 1e5, lw=1, ls="--", color=TEAM_C[tm], alpha=.6)
    ax.set_title(title, fontsize=8.5, color=NAVY_H, loc="left", fontweight="bold")
    ax.set_ylabel(ylabel, fontsize=7)
    ax.tick_params(labelsize=6.5)
    ax.legend(fontsize=6.3, frameon=False, ncol=3, loc="upper left")
    ax.grid(axis="y", color="#EEF0F3", lw=.6)
    fig.tight_layout()
    return fig_img(fig, w, h)


def _weeks(res: Result, tm: str) -> pd.DataFrame:
    return res.weekly_team[res.weekly_team["team"] == tm].reset_index(drop=True)


def _bar_labels(ax, bars, fmt, size=6.5):
    for b in bars:
        v = b.get_height()
        if v and not np.isnan(v):
            ax.text(b.get_x() + b.get_width() / 2, v, fmt(v), ha="center", va="bottom", fontsize=size, color="#1F2937")


def _simple_axes(ax, title):
    ax.set_title(title, fontsize=8, color=NAVY_H, loc="left", fontweight="bold")
    ax.spines["left"].set_visible(False)
    ax.set_yticks([])
    ax.tick_params(axis="x", labelsize=6.3, length=0)


def chart_week_revenue(res: Result, tm: str, w=3.4, h=2.0):
    g = _weeks(res, tm)
    lab = [f"{d:%d %b}" for d in g["week"]]
    cols = ["#C9CED6" if not c else (GREEN if r >= t else RED) for r, t, c in zip(g["revenue"], g["run_rate"], g["complete"])]
    fig, ax = plt.subplots(figsize=(w, h))
    bars = ax.bar(lab, g["revenue"] / 1e5, color=cols, width=.62)
    ax.plot(lab, g["run_rate"] / 1e5, color="#1F2937", ls="--", lw=1, marker="_", ms=10)
    _bar_labels(ax, bars, lambda v: f"{v:.1f}")
    _simple_axes(ax, "Revenue per week (Rs lakh) vs target - - -")
    top = np.nanmax([g["revenue"].max(), g["run_rate"].max(), 0])
    ax.set_ylim(0, top / 1e5 * 1.25 + .1)
    fig.tight_layout()
    return fig_img(fig, w, h)


def chart_week_count(res: Result, tm: str, col: str, title: str, fmt, color, w=3.4, h=1.75):
    g = _weeks(res, tm)
    lab = [f"{d:%d %b}" for d in g["week"]]
    fig, ax = plt.subplots(figsize=(w, h))
    bars = ax.bar(lab, g[col].fillna(0), color=[color if c else "#C9CED6" for c in g["complete"]], width=.62)
    _bar_labels(ax, bars, fmt)
    _simple_axes(ax, title)
    top = g[col].max()
    ax.set_ylim(0, (top if pd.notna(top) and top > 0 else 1) * 1.3)
    fig.tight_layout()
    return fig_img(fig, w, h)


def _change(g: pd.DataFrame, col: str):
    """Mean of the last 2 complete weeks vs the 2 before, or None."""
    c = g[g["complete"]]
    if len(c) < 4:
        return None
    a, b = c[col].iloc[-4:-2].mean(), c[col].iloc[-2:].mean()
    return (a, b, (b - a) / a * 100 if a else np.nan)


def week_takeaways(res: Result, tm: str) -> list[str]:
    g = _weeks(res, tm)
    c = g[g["complete"]]
    out = []
    if len(c):
        hit = int((c["revenue"] >= c["run_rate"]).sum())
        last = c.iloc[-1]
        out.append(f"<b>Revenue</b>: on target in <b>{hit} of {len(c)}</b> full weeks. Last week {lakh(last['revenue'])} vs target "
                   f"{lakh(last['run_rate'])} (<font color='{pace_color(last['revenue'] / last['run_rate'] * 100 if last['run_rate'] else np.nan)}'>"
                   f"<b>{pct(last['revenue'] / last['run_rate'] * 100 if last['run_rate'] else np.nan)}</b></font>).")
    for col, name, d in (("followups", "Follow-ups", 0), ("deep_per_day", "Counselling calls (15 min+) per caller/day", 1)):
        ch = _change(g, col)
        if ch:
            a, b, p_ = ch
            word = "up" if p_ > 5 else "down" if p_ < -5 else "flat"
            colr = GREEN if p_ > 5 else RED if p_ < -5 else G1
            out.append(f"<b>{name}</b>: <font color='{colr}'><b>{word} {abs(p_):.0f}%</b></font> - last 2 weeks "
                       f"{b:,.{d}f}/week vs {a:,.{d}f}/week the 2 weeks before." if col == "followups" else
                       f"<b>{name}</b>: <font color='{colr}'><b>{word} {abs(p_):.0f}%</b></font> - {b:.1f} vs {a:.1f} before.")
    return out


def chart_daily(res: Result, tm: str, w=5.0, h=2.3):
    g = res.daily[res.daily["team"] == tm]
    rr = g["run_rate"].iloc[0] if len(g) else 0
    fig, ax = plt.subplots(figsize=(w, h))
    lab = [f"{d.day}" for d in g["d"]]
    col = ["#C9CED6" if not wk else (GREEN if v >= rr else RED) for v, wk in zip(g["revenue"], g["working"])]
    bars = ax.bar(lab, g["revenue"] / 1e5, color=col)
    ax.axhline(rr / 1e5, color="#1F2937", ls="--", lw=1)
    ax.text(len(lab) - .5, rr / 1e5, f" daily target {rr / 1e5:.2f}L", va="bottom", ha="right", fontsize=6.5)
    _bar_labels(ax, bars, lambda v: f"{v:.1f}", 6)
    _simple_axes(ax, "Revenue each day this month (Rs lakh). Green = target met, red = missed, grey = week off")
    ax.set_ylim(0, np.nanmax([g["revenue"].max() if len(g) else 0, rr, 0]) / 1e5 * 1.3 + .1)
    fig.tight_layout()
    return fig_img(fig, w, h)


def chart_pacing(res: Result, tm: str, w=5.0, h=2.3):
    p = res.pacing[res.pacing["team"] == tm]
    months = sorted(p["month"].unique())
    fig, ax = plt.subplots(figsize=(w, h))
    prev = [m for m in months if m < res.month]
    if prev:
        g = p[p["month"] == prev[-1]]
        ax.plot(g["dom"], g["cum"] / 1e5, lw=1.4, color=PREVB, label=f"{pd.Timestamp(prev[-1] + '-01'):%B} (last month)")
    t = res.teams.set_index("team").loc[tm]
    if t["target"]:
        days = sorted({d.day for d in res.wd})
        cum = np.cumsum([1 if d in days else 0 for d in range(1, 32)])
        ax.plot(range(1, 32), t["target"] * cum / max(cum[-1], 1) / 1e5, color="#1F2937", lw=1, ls="--", label="where target needs us")
    g = p[p["month"] == res.month]
    ax.plot(g["dom"], g["cum"] / 1e5, lw=2.6, color=CUR, marker="o", ms=3, label=f"{pd.Timestamp(res.month + '-01'):%B} (now)", zorder=5)
    if len(g):
        ax.annotate(f"{g['cum'].iloc[-1] / 1e5:.1f}L", (g["dom"].iloc[-1], g["cum"].iloc[-1] / 1e5), textcoords="offset points",
                    xytext=(4, 4), fontsize=7, color=CUR, fontweight="bold")
    ax.set_xlim(1, 31)
    ax.set_xlabel("day of month", fontsize=7)
    ax.set_ylabel("Rs lakh, running total", fontsize=7)
    ax.tick_params(labelsize=6.5)
    ax.set_title("Month so far vs target and last month", fontsize=8.5, color=NAVY_H, loc="left", fontweight="bold")
    ax.legend(fontsize=6.5, frameon=False, loc="upper left")
    ax.grid(color="#EEF0F3", lw=.6)
    fig.tight_layout()
    return fig_img(fig, w, h)


# ------------------------------------------------------------------ page frame
def make_frame(res: Result, generated: str):
    def on_page(c, doc):
        c.saveState()
        c.setFont("Helvetica-Bold", 15)
        c.setFillColor(colors.HexColor(NAVY_H))
        c.drawString(LM, PAGE[1] - 0.42 * inch, getattr(doc, "page_title", "Daily Sales Check"))
        c.setFont("Helvetica", 8)
        c.setFillColor(colors.HexColor(G1))
        c.drawString(LM, PAGE[1] - 0.6 * inch,
                     f"Teams: {', '.join(TEAMS)} | MTD window 1-{res.day.day} {res.day:%b %Y} | previous working day "
                     f"{res.prev_wd:%a %d %b} | generated {generated} IST")
        c.setStrokeColor(colors.HexColor(RULE))
        c.setLineWidth(0.8)
        c.line(LM, PAGE[1] - 0.68 * inch, PAGE[0] - RM, PAGE[1] - 0.68 * inch)
        c.setFont("Helvetica", 7.3)
        c.setFillColor(colors.HexColor(G2))
        c.drawString(LM, 0.25 * inch, f"Daily Sales Check {res.day:%d %b %Y} | page {doc.page}")
        c.drawRightString(PAGE[0] - RM, 0.25 * inch, "Revenue = Fee paid (Revenue Analytics) | calls = Calling Analytics | "
                                                     "stages = LSQ | all times IST")
        c.restoreState()
    return on_page


class Title(Spacer):
    """Zero-size flowable that sets the running page title."""
    def __init__(self, text):
        super().__init__(0, 0)
        self.text = text

    def draw(self):
        self.canv._doctemplate.page_title = self.text


# ------------------------------------------------------------------ pages
def overview(res: Result, story):
    run = getattr(res, "run_date", None)
    story.append(Title(f"Daily Sales Check - {run:%a %d %b %Y} (data to {res.day:%a %d %b})" if run
                       else f"Daily Sales Check - data to {res.day:%a %d %b %Y}"))
    q = res.quality
    if res.stale:
        story.append(table([[P("<b>DATA NOT FRESH</b> - read every number below with care: " +
                               "; ".join(t for t, ok in q if not ok), "cell")]], [CW], header_rows=0, zebra=False,
                           extra=[("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FDECEA")),
                                  ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor(RED))]))
        story.append(Spacer(0, 4))
    story.append(P("Data: " + " | ".join(t for t, ok in q[:4]), "small"))
    story.append(Spacer(0, 5))
    # KPI cards
    cards = []
    for _, t in res.teams.iterrows():
        col = pace_color(t["achv_pct"])
        inner = [[P(f"<b>{t['team']}</b>", "card_l")],
                 [P(f"{rs(t['mtd'])}", "card_v")],
                 [P(f"<font color='{col}'><b>{pct(t['achv_pct'])}</b></font> of pro-rated target {rs(t['prorated'])} "
                    f"(month target {rs(t['target'])})", "card_s")],
                 [P(f"{res.prev_wd:%a %d %b}: <b>{rs(t['prev_wd_rev'])}</b> vs run-rate {rs(t['run_rate'])}/day "
                    f"(<font color='{pace_color(t['prev_wd_pct'])}'>{pct(t['prev_wd_pct'])}</font>)", "card_s")],
                 [P(f"Needed from now: <b>{rs(t['required_rr'])}</b> per working day ({len(res.remaining)} left) | "
                    f"enrolments {t['enrolments']}", "card_s")]]
        ct = Table(inner, colWidths=[CW / 3 - 12])
        ct.setStyle(TableStyle([("BOX", (0, 0), (-1, -1), 0.8, colors.HexColor(RULE)),
                                ("LINEABOVE", (0, 0), (-1, 0), 3, colors.HexColor(col)),
                                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FAFBFC")),
                                ("TOPPADDING", (0, 0), (-1, -1), 2), ("BOTTOMPADDING", (0, 0), (-1, -1), 2)]))
        cards.append(ct)
    story.append(Table([cards], colWidths=[CW / 3] * 3))
    story.append(Spacer(0, 6))

    # check matrix
    story.append(P("The seven checks at a glance", "h2"))
    names = {1: "1 Revenue data correct and fresh", 2: f"2 Run-rate on {res.prev_wd:%a %d %b}",
             3: f"3 Early warning off track {CFG['early_warning']['weeks_running']} weeks running",
             4: f"4 Below {CFG['mtd']['min_pct']}% of MTD target after the {CFG['mtd']['after_day']}th",
             5: f"5 High-intent leads not dialled > {CFG['leads']['untouched_hours']} h",
             6: f"6 Top {CFG['top_bottom']['n']} / bottom {CFG['top_bottom']['n']} callers",
             7: "7 Bootcamp collection"}
    rows = [["Check"] + TEAMS]
    styles = []
    for chk in range(1, 8):
        r = [P(f"<b>{names[chk]}</b>")]
        for j, tm in enumerate(TEAMS):
            fl = [f for f in res.flags if f.check == chk and f.team in (tm, "All")]
            if chk == 7:
                txt, col = "Parked (not in use)", G1
            elif chk == 6:
                top, bot = res.top_bottom.get(tm, (pd.DataFrame(), pd.DataFrame()))
                txt = ("Top: " + ", ".join(f"{x.caller} {pct(x.achv_pct)}" for x in top.itertuples()) + "<br/>Bottom: " +
                       ", ".join(f"{x.caller} {pct(x.achv_pct)}" for x in bot.itertuples())) if len(top) else "no ranked callers"
                col = "#1F2937"
            elif chk == 1:
                bad = [f for f in fl if f.level == "red"]
                txt, col = ("STALE - see top", RED) if bad else (("Name issues: see data check", AMBER) if fl else ("OK", GREEN))
            elif chk == 4 and res.day.day <= CFG["mtd"]["after_day"]:
                t = res.teams.set_index("team").loc[tm]
                txt, col = f"Applies after the {CFG['mtd']['after_day']}th (now {pct(t['achv_pct'])})", G1
            elif not fl:
                txt, col = "OK", GREEN
            elif chk == 3:
                team_off = any(f.who == "Team" for f in fl)
                ncall = len([f for f in fl if f.who != "Team"])
                txt = ("Team revenue below run-rate; " if team_off else "") + f"{ncall} caller(s): " + \
                      ", ".join(f.who for f in fl if f.who != "Team")
                col = RED if team_off else AMBER
            elif chk == 5:
                n = sum(int(f.what.split()[0]) for f in fl)
                txt, col = f"{n} lead(s) with {len(fl)} caller(s): " + ", ".join(
                    f"{f.who} ({f.what.split()[0]})" for f in sorted(fl, key=lambda f: -int(f.what.split()[0]))[:6]), AMBER
            else:
                txt, col = fl[0].what, RED if fl[0].level == "red" else AMBER
            r.append(P(f"<font color='{col}'>{txt}</font>"))
        rows.append(r)
    story.append(table(rows, [2.2 * inch] + [(CW - 2.2 * inch) / 3] * 3, font=7))
    story.append(Spacer(0, 6))
    story.append(P("In one line each: where, why, what to do today", "h2"))
    boxes = []
    for tm in TEAMS:
        lines = team_points(res, tm)
        boxes.append([P(f"<b>{tm}</b>", "p")] + [P(x, "p") for x in lines])
    story.append(Table([boxes], colWidths=[CW / 3] * 3,
                       style=[("VALIGN", (0, 0), (-1, -1), "TOP"), ("BOX", (0, 0), (0, 0), .6, colors.HexColor(RULE)),
                              ("BOX", (1, 0), (1, 0), .6, colors.HexColor(RULE)), ("BOX", (2, 0), (2, 0), .6, colors.HexColor(RULE)),
                              ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FAFBFC"))]))


def team_points(res: Result, tm: str) -> list[str]:
    """Three pinpoint lines per team: where it stands, the main reason (with names), what to do today."""
    t = res.teams.set_index("team").loc[tm]
    cal = res.callers[(res.callers["team"] == tm) & ~res.callers["lead"]]
    lab = {k: lbl for k, lbl, *_ in FUNNEL}
    out = [f"<b>Where:</b> <font color='{pace_color(t['achv_pct'])}'><b>{pct(t['achv_pct'])}</b></font> of target pace, "
           f"<b>{lakh(t['gap'])}</b> behind. Needs <b>{lakh(t['required_rr'])}</b> every working day from now."]
    gaps = cal[cal["primary_key"] != ""]
    if len(gaps):
        k = gaps["primary_key"].value_counts().index[0]
        who = gaps[gaps["primary_key"] == k]["caller"].tolist()
        out.append(f"<b>Main reason:</b> {lab[k].lower()} below the team's top 3 for {len(who)} caller(s): {', '.join(who)}.")
    L = res.leads[res.leads["team"] == tm] if res.leads is not None else pd.DataFrame()
    if len(L):
        top = L.groupby("caller").size().sort_values(ascending=False).head(3)
        out.append(f"<b>Do today:</b> dial the <b>{len(L)}</b> open high-intent leads not called in 24 h "
                   f"({', '.join(f'{c} {n}' for c, n in top.items())}...) - numbers in the leads Excel.")
    return out


def key_points(res: Result) -> str:
    out = []
    t = res.teams.sort_values("gap", ascending=False)
    for _, x in t.iterrows():
        cal = res.callers[(res.callers["team"] == x["team"]) & ~res.callers["lead"]]
        gaps = cal[cal["primary_key"] != ""]["primary_key"].value_counts()
        main = ""
        if len(gaps):
            lab = {k: lbl for k, lbl, *_ in FUNNEL}
            main = "; most common gap vs the team's top 3: " + ", ".join(f"<b>{lab[k]}</b> ({n} callers)" for k, n in gaps.head(2).items())
        fu = cal["followup_level"].value_counts()
        out.append(f"<b>{x['team']}</b>: {rs(x['mtd'])} = <b>{pct(x['achv_pct'])}</b> of pro-rated target, "
                   f"{rs(x['gap'])} behind pace; needs {rs(x['required_rr'])}/working day{main}. "
                   f"Follow-up levels: {fu.get('High', 0)} high, {fu.get('Medium', 0)} medium, {fu.get('Low', 0)} low.")
    n5 = len(res.leads) if res.leads is not None else 0
    if n5:
        out.append(f"<b>Lead hygiene</b>: {n5} high-intent leads (Roadmap Done / Follow Up For Closure, last "
                   f"{CFG['leads']['lookback_days']} days, not enrolled) have not been dialled for over "
                   f"{CFG['leads']['untouched_hours']} h - the leads Excel lists the numbers by caller.")
    return "<br/>".join(out)


def trends_page(res: Result, story):
    story.append(PageBreak())
    story.append(Title("Trends - what changed week by week"))
    story.append(P("Week by week, one column per team. Bars = full weeks (Mon-Sun); the grey bar is this week so far.", "small"))
    cols = []
    for tm in TEAMS:
        cell = [P(f"<b>{tm}</b>", "h2"), chart_week_revenue(res, tm),
                chart_week_count(res, tm, "followups", "Follow-ups set per week", lambda v: f"{v:.0f}", "#0F8C82"),
                chart_week_count(res, tm, "deep_per_day", "Counselling calls (15 min+) per caller per day",
                                 lambda v: f"{v:.1f}", "#7E57C2"),
                Spacer(0, 2)] + [P("&bull; " + t, "p") for t in week_takeaways(res, tm)]
        cols.append(cell)
    story.append(Table([cols], colWidths=[CW / 3] * 3, style=[("VALIGN", (0, 0), (-1, -1), "TOP")]))
    story.append(PageBreak())
    story.append(Title("Month by month"))
    story.append(chart_monthly(res))
    # monthly funnel table
    story.append(CondPageBreak(3.2 * inch))
    story.append(P("Monthly funnel by team (month's own team list; current month = MTD)", "h2"))
    mo = res.monthly
    rows = [["Team", "Month", "Revenue", "Target", "Achv", "Same days", "Enrol.", "Calls/day", "Answered", "3-min/day",
             "15-min+/day", "Follow-ups", "FU/day", "Enrol./100 FU"]]
    for _, x in mo.iterrows():
        rows.append([short(x["team"]), pd.Timestamp(x["month"] + "-01").strftime("%b %Y") + (" MTD" if x["partial"] else ""),
                     lakh(x["revenue"]), lakh(x["target"]), pct(x["achv_pct"]), lakh(x["same_window"]), x["enrolments"],
                     f1(x["calls_per_day"], 0), pct(x["connect_pct"]), f1(x["conv3_per_day"]), f1(x["deep_per_day"], 2),
                     x["followups"], f1(x["followups_per_day"]), f1(x["enrol_per_100fu"])])
    story.append(table(rows, [1.2 * inch, 0.8 * inch] + [(CW - 2.0 * inch) / 12] * 12))
    story.append(P(f"Same days = revenue on days 1-{res.day.day} of that month. Calling data starts 29 Jul 2026; "
                   "follow-ups from the LSQ stage report and the Team Uzair LSQ sheets.", "small"))


def checks_page(res: Result, story):
    story.append(PageBreak())
    story.append(Title("The checks in detail"))
    story.append(P("1. Is the revenue data correct?", "h2"))
    for t, ok in res.quality:
        story.append(P(f"<font color='{GREEN if ok else AMBER}'>{'OK' if ok else '!'}</font>  {t}", "p"))
    for n in res.notes:
        story.append(P(f"<font color='{AMBER}'>!</font>  {n}", "p"))
    story.append(P(f"2 and 4. Team run-rate and MTD target", "h2"))
    rows = [["Team", "Month target", "Working days", "Run-rate/day", f"{res.prev_wd:%a %d %b}", "% of run-rate",
             "MTD", "Pro-rated", "Achv", "Needed/day now"]]
    for _, t in res.teams.iterrows():
        rows.append([t["team"], rs(t["target"]), f"{len(res.elapsed)} of {len(res.wd)}", rs(t["run_rate"]), rs(t["prev_wd_rev"]),
                     P(f"<font color='{pace_color(t['prev_wd_pct'])}'><b>{pct(t['prev_wd_pct'])}</b></font>"),
                     rs(t["mtd"]), rs(t["prorated"]), P(f"<font color='{pace_color(t['achv_pct'])}'><b>{pct(t['achv_pct'])}</b></font>"),
                     rs(t["required_rr"])])
    story.append(table(rows, [1.5 * inch] + [(CW - 1.5 * inch) / 9] * 9))
    story.append(P(f"3. Early warning - last {CFG['early_warning']['weeks_running']} complete weeks", "h2"))
    wt = res.weekly_team
    ew = getattr(res, "ew_weeks", [])
    rows = [["Team"] + [f"Week of {w:%d %b}" for w in ew] + ["Off track?"]]
    for tm, (off, g) in getattr(res, "team_ew", {}).items():
        cells = [f"{rs(r.revenue)} vs run-rate {rs(r.run_rate)}" for r in g.itertuples()]
        rows.append([tm] + cells + [P(f"<font color='{RED if off else GREEN}'><b>{'Yes' if off else 'No'}</b></font>")])
    if len(rows) > 1:
        story.append(table(rows, [1.6 * inch] + [(CW - 2.4 * inch) / max(len(ew), 1)] * len(ew) + [0.8 * inch]))
    e = res.early
    if e is not None and len(e):
        story.append(Spacer(0, 3))
        rows = [["Team", "Caller", "Number off track", "Caller (week by week)", "Team median", "Below by"]]
        for r in e.sort_values(["team", "caller"]).itertuples():
            below = np.mean([(1 - v / b) * 100 for v, b in zip(r.values, r.benchmarks)])
            rows.append([short(r.team), r.caller, EW_LABEL[r.metric], " / ".join(f1(v) for v in r.values),
                         " / ".join(f1(b) for b in r.benchmarks), f"{below:.0f}%"])
        story.append(table(rows, [1.2 * inch, 1.4 * inch, 1.3 * inch, 1.5 * inch, 1.5 * inch, 0.8 * inch]))
    story.append(P(f"Caller off track = below {CFG['early_warning']['off_track_pct_of_benchmark']}% of the team median "
                   f"(callers, not team leaders) in each of the last {CFG['early_warning']['weeks_running']} complete weeks.",
                   "small"))
    story.append(CondPageBreak(2.2 * inch))
    story.append(P(f"6. Top {CFG['top_bottom']['n']} and bottom {CFG['top_bottom']['n']} callers (achievement of pro-rated target)", "h2"))
    rows = [["Team", "Top", "Bottom (and why)"]]
    for tm in TEAMS:
        top, bot = res.top_bottom.get(tm, (pd.DataFrame(), pd.DataFrame()))
        rows.append([tm, P("<br/>".join(f"<b>{x.caller}</b> {pct(x.achv_pct)} ({rs(x.mtd)})" for x in top.itertuples())),
                     P("<br/>".join(f"<b>{x.caller}</b> {pct(x.achv_pct)} ({rs(x.mtd)}) - {x.primary or '-'}" for x in bot.itertuples()))])
    story.append(table(rows, [1.5 * inch, 2.8 * inch, CW - 4.3 * inch]))


def team_pages(res: Result, tm: str, story):
    t = res.teams.set_index("team").loc[tm]
    cal = res.callers[res.callers["team"] == tm]
    story.append(PageBreak())
    story.append(Title(f"{tm} - where the team stands"))
    story.append(P(f"<b>MTD {rs(t['mtd'])}</b> | <font color='{pace_color(t['achv_pct'])}'><b>{pct(t['achv_pct'])}</b></font> of "
                   f"pro-rated {rs(t['prorated'])} | month target {rs(t['target'])} | {res.prev_wd:%a %d %b}: {rs(t['prev_wd_rev'])} "
                   f"vs run-rate {rs(t['run_rate'])} | needed {rs(t['required_rr'])}/working day | enrolments {t['enrolments']}", "p"))
    story.append(Spacer(0, 3))
    story.append(Table([[chart_daily(res, tm), chart_pacing(res, tm)]], colWidths=[CW / 2] * 2))
    wt = res.weekly_team[res.weekly_team["team"] == tm]
    rows = [["Week", "Revenue", "Run-rate", "vs RR", "Enrol.", "Calls/day", "Answered", "3-min/day", "15-min+/day",
             "Talk h/day", "Follow-ups", "FU/day", "Zip Hi+Mod"]]
    for r in wt.itertuples():
        vr = r.revenue / r.run_rate * 100 if r.run_rate else np.nan
        rows.append([f"{r.week:%d %b}" + ("" if r.complete else " (so far)"), rs(r.revenue), rs(r.run_rate),
                     P(f"<font color='{pace_color(vr)}'><b>{pct(vr)}</b></font>"), r.enrolments, f1(r.calls_per_day, 0),
                     pct(r.connect_pct), f1(r.conv3_per_day), f1(r.deep_per_day, 2), f1(r.talk_hrs_per_day),
                     r.followups, f1(r.followups_per_day),
                     "-" if not r.fu_zip_rated else f"{pct(r.fu_himod_pct)} of {r.fu_zip_rated}"])
    story.append(P("Weekly trend (Mon-Sun; per caller per active day; FU Zip High+Mod = follow-ups whose Zipteams "
                   "intent was High or Moderate, of those with a rated Zipteams note)", "h2"))
    story.append(table(rows, [1.0 * inch] + [(CW - 1.0 * inch) / 12] * 12))

    # callers
    story.append(PageBreak())
    story.append(Title(f"{tm} - callers: calling, follow-ups and revenue (MTD)"))
    hi = res.leads.groupby("caller").size() if res.leads is not None and len(res.leads) else pd.Series(dtype=int)
    has_zip = "zip_rated" in cal.columns and cal["zip_rated"].sum() > 0
    hdr = ["Caller", "Target", "MTD", "Achv", res.prev_wd.strftime("%d %b"), "Enr", "Days", "Calls /day", "Ans %", "3m",
           "15-20", "20+", "Talk h", "Avg /ans", "Long- est", "Break h/day", "Late", "FU", "FU /day", "FU level", "FU→ Enr",
           "HI >24h"] + (["FU Zip H/M/N/L"] if has_zip else []) + ["Why (first gap vs the team's top 3)"]
    rows = [hdr]
    for r in cal.itertuples():
        name = f"<b>{r.caller}</b>" + (" <font color='#6B7280'>(TL)</font>" if r.lead else "")
        lvl_c = {"High": GREEN, "Medium": AMBER, "Low": RED}.get(r.followup_level, G1)
        rows.append([P(name), lakh(r.target), lakh(r.mtd), P(f"<font color='{pace_color(r.achv_pct)}'><b>{pct(r.achv_pct)}</b></font>"),
                     lakh(r.prev_wd_rev) if r.prev_wd_rev else "-", r.enrolments, f"{r.present_days}/{len(res.elapsed)}", f1(r.calls_per_day, 0),
                     pct(r.connect_pct), r.calls_3m, r.calls_15_20, r.calls_20p, f1(r.talk_hrs, 1), f1(r.avg_talk_min, 1),
                     f1(r.longest_min, 0), f1(r.break_hrs_per_day, 1), r.late_days, r.followups, f1(r.followups_per_day),
                     P(f"<font color='{lvl_c}'><b>{r.followup_level}</b></font>"), pct(r.fu_conv_pct), int(hi.get(r.caller, 0))]
                    + ([P(f"<font color='{GREEN}'>{r.zip_high}</font>/{r.zip_moderate}/{r.zip_neutral}/"
                           f"<font color='{RED}'>{r.zip_low}</font>")] if has_zip else []) + [P(r.primary if not r.lead else "")])
    fixed = [1.15, .45, .45, .38, .4, .25, .28, .4, .33, .28, .3, .28, .37, .4, .42, .42, .28, .28, .3, .45, .4, .38] + ([.62] if has_zip else [])
    widths = [w * inch for w in fixed]
    widths.append(CW - sum(widths))
    hdr_cells = [P(f"<font color='white'><b>{h}</b></font>") for h in rows[0]]
    rows[0] = hdr_cells
    story.append(table(rows, widths, font=6.6))
    story.append(P("Target/MTD in Rs lakh. Days = working days with calls / working days so far. 3m = 3-min+ calls, 15-20 and 20+ = minutes. Talk h = sum of call "
                   "durations; Avg/ans and Longest in minutes. Late = days flagged Late Check-In. FU = leads moved to Follow Up For "
                   "Closure (LSQ). FU level vs team median per active day: High >= "
                   f"{CFG['followup_level']['high_pct']}%, Low < {CFG['followup_level']['low_pct']}%. FU→Enr = follow-up leads "
                   "this month that enrolled (BASE DATA, phone match). HI >24h = check 5 leads held (numbers in the leads Excel). "
                   "FU Zip H/M/N/L = this month's follow-ups by the Zipteams intent of the lead's call (High / Moderate / Neutral / "
                   "Low; follow-ups without a rated note not counted).", "small"))

    # why
    story.append(PageBreak())
    story.append(Title(f"{tm} - why revenue is not coming (flagged callers)"))
    fc = flagged_callers(res)
    fc = fc[fc["team"] == tm] if fc is not None and len(fc) else pd.DataFrame()
    top3 = cal[~cal["lead"]].sort_values("mtd", ascending=False).head(3)["caller"].tolist()
    story.append(P(f"Each flagged caller (bottom {CFG['top_bottom']['n']}, below {CFG['mtd']['min_pct']}% of pace, or early "
                   f"warning) is compared step by step with the median of the team's top 3 by MTD revenue "
                   f"(<b>{', '.join(top3)}</b>). The first step below {CFG['root_cause']['gap_pct']}% of the top 3 is the "
                   "primary reason: the steps after it usually fall because of it.", "small"))
    story.append(Spacer(0, 3))
    cards = [why_card(res, r) for r in fc.itertuples()]
    if not cards:
        story.append(P("No flagged callers.", "p"))
    for i in range(0, len(cards), 2):
        pair = cards[i:i + 2] + ([""] if len(cards[i:i + 2]) == 1 else [])
        story.append(KeepTogether([Table([pair], colWidths=[CW / 2] * 2, style=[("VALIGN", (0, 0), (-1, -1), "TOP")]),
                                   Spacer(0, 4)]))

    # leads: per-caller summary here; the numbers are in the leads Excel (Amit, 5 Nov 2026)
    story.append(CondPageBreak(2.6 * inch))
    story.append(P(f"High-intent leads not dialled for over {CFG['leads']['untouched_hours']} h (check 5)", "h2"))
    L = res.leads[res.leads["team"] == tm] if res.leads is not None else pd.DataFrame()
    ref = getattr(res, "lead_ref", None)
    if ref is not None:
        story.append(P(f"Latest stage in the last {CFG['leads']['lookback_days']} days is {' / '.join(CFG['leads']['stages'])}, "
                       f"still open in LSQ, not enrolled; no call to the number by anyone for over "
                       f"{CFG['leads']['untouched_hours']} h before {ref:%d %b %H:%M} IST. <b>Phone numbers, lead names and "
                       f"last dial times are in the Excel 'High-intent leads not dialled {res.day.isoformat()}'</b>, one sheet "
                       "per team.", "small"))
    Dr = res.leads_dropped[res.leads_dropped["team"] == tm] if getattr(res, "leads_dropped", None) is not None else pd.DataFrame()
    if len(Dr):
        mv = Dr["current_stage"].value_counts()
        story.append(P(f"Checked live in LSQ: <b>{len(Dr)}</b> more follow-up / roadmap lead(s) of this team are no longer open and "
                       "are left out: " + ", ".join(f"{k or 'blank'} {v}" for k, v in mv.items()) + ".", "small"))
    if not len(L):
        story.append(P("<font color='#3E8E5A'><b>None</b></font> - every high-intent lead was dialled within the window.", "p"))
        return
    g = L.assign(rm=L["stage"].str.startswith("Roadmap"), nd=L["last_call"].isna())
    summ = g.groupby("caller").agg(n=("phone", "size"), rm=("rm", "sum"), nd=("nd", "sum"),
                                   oldest=("hours", "max"), med=("hours", "median")).sort_values("n", ascending=False)
    rows = [["Caller", "Leads not dialled", "Roadmap Done", "Follow Up For Closure", "No dial at all (14 days)",
             "Longest wait (h)", "Median wait (h)"]]
    for c, x in summ.iterrows():
        rows.append([c, int(x.n), int(x.rm), int(x.n - x.rm), int(x.nd), f1(x.oldest, 0), f1(x.med, 0)])
    rows.append([P("<b>Team</b>"), int(summ["n"].sum()), int(summ["rm"].sum()), int(summ["n"].sum() - summ["rm"].sum()),
                 int(summ["nd"].sum()), f1(g["hours"].max(), 0), f1(g["hours"].median(), 0)])
    story.append(table(rows, [1.8 * inch] + [(CW - 1.8 * inch) / 6] * 6, font=7))


def why_card(res: Result, r) -> Table:
    head = P(f"<b>{r.caller}</b>  <font color='{pace_color(r.achv_pct)}'><b>{pct(r.achv_pct)}</b></font> of pace | MTD {rs(r.mtd)} "
             f"of {rs(r.prorated)} | follow-up level <b>{r.followup_level or '-'}</b>", "cell")
    gaps = {g["key"]: g for g in r.gaps}
    bench = eval(r.bench_json) if isinstance(r.bench_json, str) else {}  # noqa: S307 - our own repr of floats
    rows = [[head, "", "", ""], ["Funnel step", "Caller", "Top 3", "Gap"]]
    style = [("SPAN", (0, 0), (-1, 0)), ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EEF2F7")),
             ("FONT", (0, 1), (-1, 1), "Helvetica-Bold", 6.6), ("BACKGROUND", (0, 1), (-1, 1), colors.HexColor("#F4F6F9")),
             ("GRID", (0, 1), (-1, -1), .25, colors.HexColor(RULE)), ("BOX", (0, 0), (-1, -1), .8, colors.HexColor(RULE)),
             ("FONT", (0, 2), (-1, -1), "Helvetica", 6.6), ("TOPPADDING", (0, 0), (-1, -1), 1.2), ("BOTTOMPADDING", (0, 0), (-1, -1), 1.2)]
    for i, (key, label, unit, fmt, _) in enumerate(FUNNEL):
        v = getattr(r, key)
        b = bench.get(key)
        g = gaps.get(key)
        cv = "-" if v is None or pd.isna(v) else fmt.format(v)
        cb = "-" if b is None else fmt.format(b)
        rows.append([f"{label} ({unit})", cv, cb, f"-{g['short']:.0f}%" if g else ""])
        if g:
            col = RED if key == r.primary_key else AMBER
            style.append(("TEXTCOLOR", (0, len(rows) - 1), (-1, len(rows) - 1), colors.HexColor(col)))
            if key == r.primary_key:
                style.append(("FONT", (0, len(rows) - 1), (-1, len(rows) - 1), "Helvetica-Bold", 6.6))
    extra = []
    if r.primary:
        extra.append(f"<b>Primary reason</b>: {r.primary}.")
    if r.next_step:
        extra.append(f"<b>Next step</b>: {r.next_step}")
    if r.trend_note:
        extra.append(f"<b>Last 2 weeks vs the 2 before</b>: {r.trend_note}.")
    if r.late_days:
        extra.append(f"Late check-in on {r.late_days} day(s); breaks {f1(r.break_hrs_per_day)} h/day.")
    rows.append([P(" ".join(extra), "cell"), "", "", ""])
    style.append(("SPAN", (0, len(rows) - 1), (-1, len(rows) - 1)))
    w = CW / 2 - 8
    return Table(rows, colWidths=[w * .52, w * .16, w * .16, w * .16], style=style)


def definitions(res: Result, story):
    story.append(PageBreak())
    story.append(Title("How the numbers are made"))
    items = [
        ("Revenue", "Fee paid, every payment row, from the Revenue Analytics dashboard (Combined Revenue Sheet). New enrolment = "
                    "'New enrollment' above Rs 800. A caller's revenue is credited to their team in that month's MonthwiseTeamList; "
                    "Direct and leaver rows stay under the team written on the sheet."),
        ("Target", "MonthwiseTeamList (team_members_data_amit): Active rows with a Target. Team target = sum of its callers'. "
                   "Pro-rated target = target x working days elapsed / working days in the month (config/months/<month>.json)."),
        ("Run-rate", "Daily run-rate = monthly target / working days in the month. Needed per day = (target - MTD) / working days left."),
        ("Calling", "Calling Analytics agent_day (calls, answered, 3-min, 15-20, 20+ min, breaks, check-in issues) and calls "
                    "(talk time = sum of call durations, longest call). Days = days with at least one call."),
        ("Follow-ups", "Leads moved to 'Follow Up For Closure' in LSQ (stage report + Team Uzair LSQ live sheet and its monthly "
                       "copies), one per lead per caller per day. Follow-up level compares a caller's follow-ups per active day with "
                       "the team median. FU→Enr = this month's follow-up leads whose phone is in BASE DATA 'New enrollment'."),
        ("Zipteams", "Zipteams writes a 'Zipteams Notes' activity (237) on the lead in LSQ after each call, with the lead's intent "
                     "(High / Moderate / Neutral / Low). Each follow-up takes the intent of its lead's latest note within "
                     f"{CFG['zipteams']['match_days']} days of the follow-up (matched by Prospect ID). It shows whether a caller's "
                     "follow-ups are warm leads or weak ones. Zipteams sees one call only: an input, never the answer."),
        ("Current stage", "Before a lead is listed in check 5 its stage and owner are read live from LSQ (by Prospect ID, else "
                          "phone). Leads now in Not Interested, May buy later or any other stage are dropped and listed on the "
                          "'Dropped - stage changed' sheet of the leads Excel."),
        ("Check 5", f"High-intent = latest stage in {CFG['leads']['lookback_days']} days is {' / '.join(CFG['leads']['stages'])}, still "
                    "open in the 'Follow-up Status' sheet (not Actually Enrolled / Not Interested / ...), not in BASE DATA as a new "
                    "enrolment. Not dialled = no call to that number by anyone for more than "
                    f"{CFG['leads']['untouched_hours']} h before the latest call in the data."),
        ("Early warning", f"Last {CFG['early_warning']['weeks_running']} complete Mon-Sun weeks; a caller is off track on a number when "
                          f"it is below {CFG['early_warning']['off_track_pct_of_benchmark']}% of the team median in every one of "
                          "those weeks. Team leaders (TL / ATL / Manager / AD) are not flagged."),
        ("Why", f"Funnel order: attendance, dialling, connectivity, conversations (3-min+), counselling depth (15-min+), "
                f"follow-ups, closing (enrolments per 100 follow-ups), ticket size. Benchmark = median of the team's top 3 by "
                f"MTD revenue; the first step below {CFG['root_cause']['gap_pct']}% of it is the primary reason."),
        ("Settings", "Every threshold is in config/dsc.json; working days in config/months/<month>.json."),
    ]
    rows = [[P(f"<b>{k}</b>"), P(v)] for k, v in items]
    story.append(table([["Term", "Rule"]] + rows, [1.3 * inch, CW - 1.3 * inch], font=7.4))


def build(res: Result, path: str) -> str:
    gen = datetime.now(IST).strftime("%d %b %Y %H:%M")
    doc = BaseDocTemplate(path, pagesize=PAGE, leftMargin=LM, rightMargin=RM, topMargin=TM, bottomMargin=BM,
                          title=f"Daily Sales Check {res.day:%d %b %Y}", author="Daily Sales Check (automated)")
    doc.page_title = "Daily Sales Check"
    frame = Frame(LM, BM, CW, PAGE[1] - TM - BM, id="body", leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
    # the header is drawn when the page ends, so it carries the title set by the page's first flowable
    doc.addPageTemplates([PageTemplate(id="p", frames=[frame], onPageEnd=make_frame(res, gen))])
    story = []
    overview(res, story)
    trends_page(res, story)
    checks_page(res, story)
    for tm in TEAMS:
        team_pages(res, tm, story)
    definitions(res, story)
    doc.build(story)
    return path
