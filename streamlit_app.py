"""Nuclear Diplomacy Simulation: moderator console for the classroom projector.

Run locally with:  streamlit run streamlit_app.py
"""
from __future__ import annotations

import base64
import math
import time
from fractions import Fraction
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

from boom import explosion_html
from game import (ATTACK_TABLE, COUNTRIES, MAX_MOVE, NAMES, RULES_BY_COUNTRY, SHORT, START_GPR,
                  START_NW, Game, attack_probability, band_label, display_ranks, replay_luck)

st.set_page_config(page_title="Nuclear Diplomacy Simulation", page_icon="☢️", layout="wide",
                   initial_sidebar_state="expanded")

HERE = Path(__file__).parent
REPO = "https://github.com/erfan-amini/nuclear-diplomacy-game"
COLORS = {"US": "#2a78d6", "IN": "#eb6834", "PK": "#1baf7a", "CN": "#eda100", "RU": "#e87ba4"}
SOURCE_COLORS = {"Starting GPR": "#c3c2b7", "Rules tripped": "#2a78d6",
                 "Ignored sanctions": "#eb6834", "Terrorist attacks": "#1baf7a"}


# ----------------------------------------------------------------------------- small helpers
@st.cache_data
def flag_uri(c: str) -> str:
    data = (HERE / "assets" / "flags" / f"flag_{c.lower()}.png").read_bytes()
    return "data:image/png;base64," + base64.b64encode(data).decode()


def flag(c: str, h: int = 28, cls: str = "fl") -> str:
    return f'<img class="{cls}" src="{flag_uri(c)}" style="height:{h}px" alt="{NAMES[c]} flag">'


def signed(m: int) -> str:
    return f"+{m}" if m > 0 else (f"−{abs(m)}" if m < 0 else "0")


def odds(p: Fraction) -> str:
    if p == 0:
        return "none"
    if p.numerator == 1:
        return f"1 in {p.denominator}"
    return f"{float(p) * 100:.0f}%"


def pct(x: float) -> str:
    if x == 0:
        return "0%"
    return f"{x * 100:.0f}%" if x >= 0.095 else f"{x * 100:.1f}%"


def plural(n: int, word: str) -> str:
    return f"{n} {word}{'' if n == 1 else 's'}"


def trefoil(size: int = 22, color: str = "currentColor") -> str:
    """Radiation symbol as inline SVG: a centre dot and three blades."""
    r1, r2, cx = 0.28, 1.0, 1.1
    paths = []
    for k in range(3):
        a0 = math.radians(90 + 120 * k - 30)
        a1 = math.radians(90 + 120 * k + 30)
        p = [(cx + r1 * math.cos(a0), cx + r1 * math.sin(a0)), (cx + r2 * math.cos(a0), cx + r2 * math.sin(a0)),
             (cx + r2 * math.cos(a1), cx + r2 * math.sin(a1)), (cx + r1 * math.cos(a1), cx + r1 * math.sin(a1))]
        paths.append(f"M{p[0][0]:.3f},{p[0][1]:.3f} L{p[1][0]:.3f},{p[1][1]:.3f} "
                     f"A{r2},{r2} 0 0 1 {p[2][0]:.3f},{p[2][1]:.3f} L{p[3][0]:.3f},{p[3][1]:.3f} "
                     f"A{r1},{r1} 0 0 0 {p[0][0]:.3f},{p[0][1]:.3f} Z")
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 2.2 2.2">'
           f'<g fill="{color}"><circle cx="1.1" cy="1.1" r="0.17"/>' + "".join(f'<path d="{d}"/>' for d in paths) + "</g></svg>")
    uri = "data:image/svg+xml;base64," + base64.b64encode(svg.encode()).decode()
    return f'<img src="{uri}" width="{size}" height="{size}" alt="" style="vertical-align:-0.15em">'


def meter(total: int, dark: bool = False) -> str:
    """The six attack-odds bands, with the current one lit."""
    cells = []
    for lo, hi, p in ATTACK_TABLE:
        on = total >= lo and (hi is None or total <= hi)
        cells.append(f'<div class="band{" on" if on else ""}"><span class="b-r">{band_label(lo, hi)}</span>'
                     f'<span class="b-o">{odds(p)}</span></div>')
    return f'<div class="meter{" dark" if dark else ""}">{"".join(cells)}</div>'


# ----------------------------------------------------------------------------- style
st.html("""
<style>
:root {
  --ink:#18202C; --muted:#5E6878; --line:#DCE1E8; --panel:#F3F5F8; --slate:#1B2431; --slate2:#253042;
  --signal:#C00000; --amber:#F2B705; --amber-ink:#5A4300; --calm:#1E7B6B;
}
.block-container {padding-top:1.6rem; padding-bottom:3rem; max-width:1240px;}
section[data-testid="stSidebar"] {width:384px !important; min-width:384px !important;}
section[data-testid="stSidebar"] .block-container, section[data-testid="stSidebar"] [data-testid="stSidebarUserContent"] {padding-top:.4rem;}
[data-testid="stSidebarHeader"] {height:2.2rem; padding-bottom:0;}

/* header */
.hdr {display:flex; align-items:flex-end; justify-content:space-between; gap:1rem; flex-wrap:wrap; margin-bottom:.5rem;}
.brand {font-family:"Barlow Condensed",sans-serif; font-weight:700; font-size:2.5rem; line-height:1; color:var(--signal);
        display:flex; align-items:center; gap:.5rem;}
.rnd {text-align:right; color:var(--muted); font-size:1rem;}
.rnd b {color:var(--ink); font-family:"Barlow Condensed",sans-serif; font-size:1.45rem; font-weight:700;}
.pips {display:flex; gap:6px; justify-content:flex-end; margin-top:5px;}
.pip {width:22px; height:7px; border-radius:4px; background:#E3E7ED;}
.pip.done {background:#8C96A6;} .pip.now {background:var(--signal);}

/* stage strip */
.stages {display:flex; gap:0; margin:.2rem 0 1.1rem 0; border-radius:10px; overflow:hidden; border:1px solid var(--line); width:fit-content;}
.stg {padding:.42rem 1.1rem; font-weight:600; color:#8A93A3; background:#fff; border-right:1px solid var(--line); font-size:.98rem;}
.stg:last-child {border-right:none;}
.stg.done {color:var(--ink); background:var(--panel);}
.stg.now {color:#fff; background:var(--signal);}
h2.stage-title {font-family:"Barlow Condensed",sans-serif; font-weight:700; font-size:2rem; margin:.2rem 0 .1rem 0; color:var(--ink); padding:0;}
.lede {color:var(--muted); margin:0 0 .9rem 0; font-size:1.02rem;}

/* sidebar standings */
.sb {color:#E8EDF3; font-family:"Barlow",sans-serif;}
.sb-h {font-family:"Barlow Condensed",sans-serif; font-weight:700; font-size:1.75rem; letter-spacing:.01em; line-height:1;}
.sb-cap {color:#A9B4C4; font-size:.9rem; margin:.3rem 0 .7rem 0; line-height:1.3;}
.sb-cols {display:grid; grid-template-columns:24px 1fr 46px 60px; gap:6px; color:#8E9AAD; font-size:.82rem; padding:0 10px 4px 14px;}
.sb-cols span:nth-child(3), .sb-cols span:nth-child(4) {text-align:right;}
.sb-row {display:grid; grid-template-columns:24px 1fr 46px 60px; gap:6px; align-items:center; background:var(--slate2);
         border-radius:12px; padding:10px; margin-bottom:6px; border-left:4px solid transparent;}
.sb-row.lead {border-left-color:#E8EDF3;}
.sb-row.hit {border-left-color:#FF5A4F; background:#3A2430;}
.sb-rk {font-family:"Barlow Condensed",sans-serif; font-weight:700; font-size:1.45rem; color:#C9D2DE; text-align:center; white-space:nowrap;}
.sb-nm {display:flex; flex-direction:column; gap:3px; min-width:0;}
.sb-nm .top {display:flex; align-items:center; gap:7px; font-weight:600; font-size:1rem; white-space:nowrap; overflow:hidden;}
.sb-nm .fl {border-radius:3px; box-shadow:0 0 0 1px rgba(255,255,255,.18);}
.sb-num {text-align:right; font-family:"Barlow Condensed",sans-serif; font-weight:700; font-size:1.95rem; line-height:1;}
.sb-num .d {display:block; font-family:"Barlow",sans-serif; font-size:.78rem; font-weight:600; color:#8E9AAD; margin-top:2px;}
.sb-num .d.up {color:#FF8A80;} .sb-num .d.down {color:#7FD8B5;}
.sb-num.nw {color:#C9D2DE;}
.tag {display:inline-block; font-size:.74rem; font-weight:700; padding:1px 7px; border-radius:999px; margin-right:4px; white-space:nowrap;}
.tag.red {background:#FF5A4F; color:#fff;} .tag.amber {background:var(--amber); color:#2B2100;}
.tag.grey {background:#3B475B; color:#C9D2DE;} .tag.green {background:#2C6E5F; color:#DDF5EC;}
.sb-line {display:flex; justify-content:space-between; color:#8E9AAD; font-size:.78rem; margin:2px 4px 8px 4px;
          border-top:1px dashed #56637A; padding-top:5px;}
.sb-world {margin-top:14px; background:#141B26; border-radius:14px; padding:12px 12px 10px 12px;}
.sb-world .w {display:flex; align-items:baseline; gap:8px;}
.sb-world .w b {font-family:"Barlow Condensed",sans-serif; font-size:2.4rem; line-height:1;}
.sb-world .w span {color:#A9B4C4;}
.sb-world .o {margin:2px 0 8px 0; color:#E8EDF3;}
.sb-world .o b {color:#FF8A80; font-family:"Barlow Condensed",sans-serif; font-size:1.3rem;}

/* odds meter */
.meter {display:grid; grid-template-columns:repeat(6,1fr); gap:4px;}
.band {border-radius:8px; padding:5px 2px; text-align:center; background:#fff; border:1px solid var(--line); line-height:1.15;}
.band .b-r {display:block; font-size:.72rem; color:var(--muted);}
.band .b-o {display:block; font-size:.86rem; font-weight:700; color:#9AA3B2; white-space:nowrap;}
.band.on {background:var(--signal); border-color:var(--signal);}
.band.on .b-r, .band.on .b-o {color:#fff;}
.meter.dark .band {background:#212B3B; border-color:#2E3A4E;}
.meter.dark {gap:3px;} .meter.dark .band {padding:4px 0;}
.meter.dark .band .b-r {color:#8E9AAD; font-size:.68rem;} .meter.dark .band .b-o {color:#B6C0CF; font-size:.72rem; letter-spacing:-.01em;}
.meter.dark .band.on {background:var(--signal); border-color:var(--signal);}
.meter.dark .band.on .b-r, .meter.dark .band.on .b-o {color:#fff;}

/* decision rows */
[class*="st-key-drow_"] {background:var(--panel); border-radius:14px; padding:.55rem .9rem .55rem .9rem;}
.dname {display:flex; align-items:center; gap:10px;}
.dname .fl {border-radius:3px; box-shadow:0 0 0 1px rgba(0,0,0,.08);}
.dname b {font-size:1.15rem;} .dname .sub {display:block; color:var(--muted); font-size:.88rem; font-weight:400;}
.dres {font-family:"Barlow Condensed",sans-serif; font-size:1.6rem; font-weight:700; color:var(--ink); text-align:right;}
.dres .s {font-family:"Barlow",sans-serif; font-size:.86rem; font-weight:500; color:var(--muted); display:block;}
.req {display:inline-block; background:var(--amber); color:#2B2100; font-weight:700; font-size:.82rem; border-radius:999px; padding:1px 9px;}
button[data-variant="segmented_control"] {min-width:3.3rem;}
button[data-variant="segmented_control"] p {font-size:1.12rem; font-weight:700;}
.proj {display:flex; align-items:center; gap:1.2rem; flex-wrap:wrap; margin:.9rem 0 .7rem 0;}
.proj .t {font-size:1.05rem; color:var(--muted);} .proj .t b {font-family:"Barlow Condensed",sans-serif; font-size:1.7rem; color:var(--ink);}
.proj .meter {flex:1 1 420px; max-width:560px;}

/* attack hero */
.hero {background:var(--slate); color:#E8EDF3; border-radius:18px; padding:1.1rem 1.3rem; display:grid;
       grid-template-columns:minmax(150px,220px) 1fr; gap:1.3rem; align-items:center; margin-bottom:1rem;}
.hero .big {font-family:"Barlow Condensed",sans-serif; font-weight:700; font-size:4.6rem; line-height:.9;}
.hero .cap {color:#A9B4C4; font-size:1rem;}
.hero .oddsline {font-size:1.15rem; margin-bottom:.55rem;}
.hero .oddsline b {font-family:"Barlow Condensed",sans-serif; font-size:2.1rem; color:#FF8A80; margin-left:.35rem;}
.hero.drawing {background:#2A1418;}
.hero .ask {font-family:"Barlow Condensed",sans-serif; font-size:2.6rem; font-weight:700; color:#FFD9C7;}
.tgts-h {font-weight:600; margin:.2rem 0 .5rem 0; color:var(--ink); font-size:1.05rem;}
.tgts {display:flex; gap:.8rem; flex-wrap:wrap; margin-bottom:1rem;}
.tgt {flex:1 1 180px; border:2px solid var(--line); border-radius:14px; padding:.75rem .9rem; background:#fff;
      transition:transform .12s ease, background .12s ease;}
.tgt .fl {border-radius:3px; box-shadow:0 0 0 1px rgba(0,0,0,.08);}
.tgt .n {font-weight:700; font-size:1.15rem; margin:.35rem 0 .15rem 0;}
.tgt .o {font-family:"Barlow Condensed",sans-serif; font-weight:700; font-size:2rem; color:var(--signal); line-height:1;}
.tgt .s {color:var(--muted); font-size:.86rem;}
.tgt.lit {background:var(--signal); border-color:var(--signal); transform:scale(1.04);}
.tgt.lit .n, .tgt.lit .o, .tgt.lit .s {color:#fff;}
.tgt.dim {opacity:.45;}

/* result banners */
.result {border-radius:18px; padding:1rem 1.3rem; display:flex; align-items:center; gap:1.1rem; margin-bottom:1rem;}
.result.hit {background:linear-gradient(100deg,#7A0C0C 0%,#C00000 60%,#D9381E 100%); color:#fff;}
.result.calm {background:#E3F1EC; color:#0F4A3F;}
.result .h {font-family:"Barlow Condensed",sans-serif; font-weight:700; font-size:2.1rem; line-height:1.05;}
.result .s {font-size:1.02rem; opacity:.92; margin-top:.15rem;}
.result .fl {border-radius:4px; box-shadow:0 2px 8px rgba(0,0,0,.25);}

/* changes strip */
.chg {display:flex; gap:.5rem; flex-wrap:wrap; margin:.2rem 0 1rem 0;}
.chg .c {display:flex; align-items:center; gap:7px; padding:.35rem .7rem; border-radius:10px; background:var(--panel); font-weight:600;}
.chg .c .fl {border-radius:2px;}
.chg .c .v {font-family:"Barlow Condensed",sans-serif; font-size:1.35rem; font-weight:700; color:#8A93A3;}
.chg .c.up .v {color:var(--signal);}

/* sanctions */
.deciders {background:var(--panel); border-radius:14px; padding:.8rem 1rem;}
.deciders .t {color:var(--muted); font-size:.95rem; margin-bottom:.4rem;}
.deciders .d {display:flex; align-items:center; gap:8px; font-weight:600; font-size:1.08rem; margin:.3rem 0;}
.deciders .fl {border-radius:3px; box-shadow:0 0 0 1px rgba(0,0,0,.08);}
[class*="st-key-cand_"] {border:2px solid var(--line); border-radius:14px; padding:.7rem .9rem; background:#fff;}
[class*="st-key-cand_"][class*="_on"] {border-color:var(--amber); background:#FFF7DA;}
[class*="st-key-cand_"][class*="_no"] {background:var(--panel); border-style:dashed;}
.cname {display:flex; align-items:center; gap:9px; font-weight:700; font-size:1.15rem;}
.cname .fl {border-radius:3px; box-shadow:0 0 0 1px rgba(0,0,0,.08);}
.cnote {color:var(--muted); font-size:.9rem;}

/* manual attack tiles */
[class*="st-key-mpick_"] {border:2px solid var(--line); border-radius:12px; padding:.5rem .4rem .3rem .4rem; text-align:center;}
[class*="st-key-mpick_"][class*="_on"] {border-color:var(--signal); background:#FDEEEE;}
.mp-fl {display:flex; justify-content:center; height:34px; align-items:center;}
.mp-fl img {border-radius:3px; box-shadow:0 0 0 1px rgba(0,0,0,.08);}

/* chart titles and flag legends */
.ch-t {font-family:"Barlow Condensed",sans-serif; font-weight:700; font-size:1.35rem; color:var(--ink); margin:.6rem 0 .2rem 0;}
.ch-t span {font-family:"Barlow",sans-serif; font-weight:400; font-size:.95rem; color:var(--muted); margin-left:.4rem;}
.lgd {display:flex; flex-wrap:wrap; gap:.4rem 1rem; margin:.2rem 0 .4rem 0; font-size:.95rem; color:var(--ink);}
.lgd .li {display:flex; align-items:center; gap:6px;}
.lgd .sw {width:18px; height:4px; border-radius:2px; display:inline-block;}
.lgd .sw.sq {width:13px; height:13px; border-radius:3px;}
.lgd img {border-radius:2px; box-shadow:0 0 0 1px rgba(0,0,0,.08);}

/* horizontal bars with flags */
.hbars {display:flex; flex-direction:column; gap:8px; margin:.3rem 0 .6rem 0;}
.hb {display:grid; grid-template-columns:130px 1fr 54px; gap:10px; align-items:center;}
.hb-n {display:flex; align-items:center; gap:8px; font-weight:600;}
.hb-n img {border-radius:2px; box-shadow:0 0 0 1px rgba(0,0,0,.08);}
.hb-bar {display:flex; gap:2px; height:30px; background:var(--panel); border-radius:6px; overflow:hidden;}
.hb-bar .seg {display:flex; align-items:center; justify-content:center; color:#fff; font-weight:700; font-size:.9rem; height:100%;}
.hb-bar .seg:last-child {border-radius:0 6px 6px 0;}
.hb-v {font-family:"Barlow Condensed",sans-serif; font-weight:700; font-size:1.5rem; color:var(--ink);}
.tag-in {font-size:.8rem; font-weight:700; background:var(--slate); color:#fff; border-radius:999px; padding:2px 9px; white-space:nowrap;}
.luck .hb {grid-template-columns:130px 1fr 64px 170px;}

/* final */
.final {background:var(--slate); color:#E8EDF3; border-radius:18px; padding:1.4rem 1.5rem; display:flex; align-items:center; gap:1.3rem;}
.final .h {font-family:"Barlow Condensed",sans-serif; font-weight:700; font-size:2.6rem; line-height:1;}
.final .s {color:#A9B4C4; font-size:1.05rem; margin-top:.3rem;}
.final .fl {border-radius:5px;}

.small {color:var(--muted); font-size:.9rem;}
</style>
""")


# ----------------------------------------------------------------------------- state
def get_game() -> Game:
    if "game" not in st.session_state:
        g = None
        token = st.query_params.get("g")
        if token:
            try:
                g = Game.from_token(token)
                st.session_state.restored = True
            except Exception:
                g = None
        st.session_state.game = g or Game()
    return st.session_state.game


def save_and_rerun(g: Game):
    st.query_params["g"] = g.to_token()
    st.rerun()


game = get_game()
prefs = st.session_state.setdefault("prefs", {"secret": False, "suspense": True, "boom": True})
if st.session_state.pop("restored", False):
    st.toast("Game restored from the link in the address bar.")

phase = game.phase
r = game.current if game.rounds else None
done = game.completed_rounds


def mark_boom(victim):
    if victim and prefs["boom"]:
        st.session_state.boom = (game.seed, game.current.number)


# ----------------------------------------------------------------------------- sidebar: standings
def standings():
    """What the standings panel shows in each phase."""
    tags = {c: [] for c in COUNTRIES}
    hit = None
    if phase == "over":
        last = done[-1]
        nw, gpr, order, d_gpr, d_nw = game.nw, game.gpr, last.order_after, last.delta, last.moves
        cap = f"Final standings after {plural(len(done), 'round')}. Lower GPR means more power."
        hit = last.attack["victim"]
        world = sum(game.nw.values())
    elif phase == "decide":
        prev = done[-1] if done else None
        nw, gpr, order = game.nw, game.gpr, r.order_start
        d_gpr = prev.delta if prev else None
        d_nw = prev.moves if prev else None
        cap = ("Opening table. Lower GPR means more power." if not prev else
               f"Start of round {r.number}. Small numbers show what changed in round {prev.number}.")
        for c in r.sanctioned:
            tags[c].append((f"Sanctioned: must play {signed(r.required[c])}", "amber"))
        world = sum(nw.values())
    elif phase == "attack":
        nw, gpr, order, d_gpr, d_nw = r.nw_after, r.gpr_start, r.order_start, None, r.moves
        cap = f"Round {r.number}: weapons after the decisions. GPR updates after the attack stage."
        for c in r.sanctioned:
            ok = r.moves[c] == r.required[c]
            tags[c].append(("Obeyed the sanction" if ok else "Ignored the sanction", "green" if ok else "amber"))
        world = r.total
    else:  # sanctions
        nw, gpr, order, d_gpr, d_nw = r.nw_after, r.gpr_after, r.order_after, r.delta, r.moves
        cap = f"After round {r.number}. Small numbers show this round's changes."
        hit = r.attack["victim"]
        for c in r.sanctioned:
            if r.sanction_pts[c]:
                tags[c].append(("Ignored sanction +2", "amber"))
        world = r.total
    if hit:
        tags[hit].insert(0, ("Attacked +4", "red"))
    for c in COUNTRIES:
        if nw[c] == 0:
            tags[c].append(("0 weapons", "grey"))
    return nw, gpr, order, d_gpr, d_nw, tags, cap, world, hit


def standings_html() -> str:
    nw, gpr, order, d_gpr, d_nw, tags, cap, world, hit = standings()
    ranks = display_ranks(gpr, order)
    rows = []
    for i, c in enumerate(order):
        cls = "sb-row" + (" lead" if i == 0 else "") + (" hit" if c == hit else "")
        dg = ""
        if d_gpr is not None:
            v = d_gpr[c]
            dg = f'<span class="d{" up" if v > 0 else ""}">+{v}</span>'
        dn = ""
        if d_nw is not None:
            v = d_nw[c]
            dn = f'<span class="d{" up" if v > 0 else (" down" if v < 0 else "")}">{signed(v) if v else "held"}</span>'
        tag_html = "".join(f'<span class="tag {k}">{t}</span>' for t, k in tags[c])
        rows.append(f'<div class="{cls}"><div class="sb-rk">{ranks[c]}</div>'
                    f'<div class="sb-nm"><div class="top">{flag(c, 18)}{NAMES[c]}</div>'
                    f'{"<div>" + tag_html + "</div>" if tag_html else ""}</div>'
                    f'<div class="sb-num">{gpr[c]}{dg}</div><div class="sb-num nw">{nw[c]}{dn}</div></div>')
        if i == 2:
            rows.append('<div class="sb-line"><span>&uarr; attack targets</span><span>can be sanctioned &darr;</span></div>')
    p = attack_probability(world)
    return (f'<div class="sb"><div class="sb-h">Standings</div><div class="sb-cap">{cap}</div>'
            f'<div class="sb-cols"><span></span><span></span><span>GPR</span><span>Weapons</span></div>'
            f'{"".join(rows)}'
            f'<div class="sb-world"><div class="w"><b>{world}</b><span>weapons in the world</span></div>'
            f'<div class="o">Chance of a terrorist attack: <b>{odds(p)}</b></div>{meter(world, dark=True)}</div></div>')


with st.sidebar:
    st.html(standings_html())


# ----------------------------------------------------------------------------- header
def header_html() -> str:
    n_done = len(done)
    if phase == "over":
        rtxt = f"<b>Game over</b> after {plural(n_done, 'round')}"
    elif r.number > game.planned:
        rtxt = f"<b>Round {r.number}</b> (extra round)"
    else:
        rtxt = f"<b>Round {r.number}</b> of {game.planned}"
    if game.label:
        rtxt = f"{game.label} &nbsp;&middot;&nbsp; " + rtxt
    total = max(game.planned, n_done + (0 if phase == "over" else 1))
    pips = []
    for i in range(1, total + 1):
        cls = "done" if i <= n_done else ("now" if phase != "over" and i == r.number else "")
        pips.append(f'<span class="pip {cls}"></span>')
    return (f'<div class="hdr"><div class="brand">{trefoil(34, "#C00000")}Nuclear Diplomacy</div>'
            f'<div class="rnd">{rtxt}<div class="pips">{"".join(pips)}</div></div></div>')


st.html(header_html())
st.session_state.setdefault("view", "Game")
view = st.segmented_control("View", ["Game", "History", "Debrief", "Settings"],
                            key="view", label_visibility="collapsed") or "Game"


def stages_html(ph: str) -> str:
    names = [("decide", "1  Decisions"), ("attack", "2  Attack"), ("sanctions", "3  Sanctions")]
    idx = {"decide": 0, "attack": 1, "sanctions": 2}[ph]
    out = []
    for i, (_, n) in enumerate(names):
        out.append(f'<div class="stg {"now" if i == idx else ("done" if i < idx else "")}">{n}</div>')
    return '<div class="stages">' + "".join(out) + "</div>"


# ----------------------------------------------------------------------------- game: decisions
def stage_decide():
    st.html(stages_html("decide"))
    st.html(f'<h2 class="stage-title">Round {r.number}: the decision slips</h2>'
            f'<p class="lede">Wait until all five slips are in, then enter them. Nothing counts until you lock them in.</p>')
    chosen = {}
    for c in COUNTRIES:
        with st.container(key=f"drow_{c}"):
            a, b, d = st.columns([2.2, 4.1, 0.8], vertical_alignment="center")
            with a:
                req = (f'<span class="req">Sanctioned: must play {signed(r.required[c])}</span>'
                       if c in r.sanctioned else f'<span class="sub">{plural(game.nw[c], "weapon")}, moves up to {MAX_MOVE[c]}</span>')
                st.html(f'<div class="dname">{flag(c, 30)}<div><b>{NAMES[c]}</b>{req}</div></div>')
            with b:
                chosen[c] = st.segmented_control(
                    f"{NAMES[c]} move", game.legal_moves(c), format_func=signed,
                    key=f"mv_{game.seed}_{r.number}_{c}", label_visibility="collapsed")
            with d:
                if chosen[c] is None:
                    st.html('<div class="dres"><span class="s">waiting</span></div>')
                else:
                    after = game.nw[c] + chosen[c]
                    st.html(f'<div class="dres">{after}<span class="s">{"weapon" if after == 1 else "weapons"}</span></div>')
    missing = [SHORT[c] for c in COUNTRIES if chosen[c] is None]
    total = sum(game.nw[c] + (chosen[c] or 0) for c in COUNTRIES)
    label = "With these moves" if not missing else "So far"
    st.html(f'<div class="proj"><div class="t">{label}: <b>{total}</b> weapons in the world, '
            f'attack chance <b>{odds(attack_probability(total))}</b></div>{meter(total)}</div>')
    if missing:
        st.button("Lock in decisions", type="primary", disabled=True, icon=":material/lock:")
        st.caption("Still waiting for: " + ", ".join(missing))
    elif st.button("Lock in decisions", type="primary", icon=":material/lock:"):
        game.submit_moves(chosen)
        save_and_rerun(game)


# ----------------------------------------------------------------------------- game: attack
def hero_html(rd, asking: str | None = None) -> str:
    if asking:
        return (f'<div class="hero drawing"><div><div class="big">{rd.total}</div><div class="cap">weapons in the world</div></div>'
                f'<div><div class="ask">{asking}</div></div></div>')
    return (f'<div class="hero"><div><div class="big">{rd.total}</div><div class="cap">weapons in the world</div></div>'
            f'<div><div class="oddsline">Chance of a nuclear terrorist attack this round<b>{odds(rd.p_attack)}</b></div>'
            f'{meter(rd.total, dark=True)}</div></div>')


def targets_html(rd, lit: str | None = None) -> str:
    tiles = []
    for c in [c for c in rd.order_start if rd.shares[c] > 0]:
        cls = "tgt" + (" lit" if c == lit else (" dim" if lit else ""))
        tiles.append(f'<div class="{cls}">{flag(c, 30)}<div class="n">{NAMES[c]}</div>'
                     f'<div class="o">{odds(rd.shares[c])}</div>'
                     f'<div class="s">if there is an attack. Overall: {odds(rd.p_attack * rd.shares[c])} this round.</div></div>')
    head = ("If there is an attack, it hits one of the three most powerful countries" if len(tiles) == 3 else
            "If there is an attack, it hits one of these countries (tied GPRs share their chances)")
    return f'<div class="tgts-h">{head}</div><div class="tgts">{"".join(tiles)}</div>'


def stage_attack():
    st.html(stages_html("attack"))
    st.html(f'<h2 class="stage-title">Round {r.number}: the attack</h2>'
            '<p class="lede">More weapons in the world means a higher chance of a nuclear terrorist attack.</p>')
    slot = st.empty()
    slot.html(hero_html(r) + targets_html(r))
    if st.button("Run the attack draw", type="primary", icon=":material/casino:"):
        game.draw_attack()
        rd = game.current
        victim = rd.attack["victim"]
        if prefs["suspense"]:
            for i in range(6):
                slot.html(hero_html(rd, "Is there an attack" + "." * (i % 4)) + targets_html(rd))
                time.sleep(0.33)
            if victim:
                slot.html(hero_html(rd, "Yes. Who is hit?") + targets_html(rd))
                time.sleep(0.7)
                seq = [c for c in rd.order_start if rd.shares[c] > 0]
                spins = seq * 4
                while spins[-1] != victim:
                    spins.append(seq[(seq.index(spins[-1]) + 1) % len(seq)])
                for k, c in enumerate(spins):
                    slot.html(hero_html(rd, "Yes. Who is hit?") + targets_html(rd, lit=c))
                    time.sleep(0.1 + 0.025 * k)
                time.sleep(0.5)
            else:
                slot.html(hero_html(rd, "No attack this round.") + targets_html(rd))
                time.sleep(1.0)
        mark_boom(victim)
        save_and_rerun(game)

    with st.expander("Moderator: call the attack yourself"):
        st.caption("The teacher guide lets the moderator call or skip an attack, for example after rolling dice in the room. "
                   "Pick an outcome, then apply it.")
        pk = f"manual_{game.seed}_{r.number}"
        pick = st.session_state.get(pk, "none")
        opts = ["none"] + list(r.order_start)
        cols = st.columns(len(opts))
        for col, c in zip(cols, opts):
            with col:
                with st.container(key=f"mpick_{c}_{'on' if pick == c else 'off'}"):
                    st.html(f'<div class="mp-fl">{flag(c, 30) if c != "none" else trefoil(30, "#9AA3B2")}</div>')
                    if st.button(NAMES[c] if c != "none" else "No attack", key=f"mp_{game.seed}_{r.number}_{c}", width="stretch"):
                        st.session_state[pk] = c
                        st.rerun()
        label = "Apply: no attack" if pick == "none" else f"Apply: attack on {NAMES[pick]}"
        if st.button(label, type="primary", icon=":material/check:"):
            victim = None if pick == "none" else pick
            game.set_attack(victim)
            mark_boom(victim)
            save_and_rerun(game)


# ----------------------------------------------------------------------------- game: sanctions
def result_html(rd) -> str:
    a = rd.attack
    if a["victim"]:
        how = "Drawn by the app." if a["by"] == "draw" else "Called by the moderator."
        return (f'<div class="result hit">{trefoil(44, "#FFFFFF")}<div><div class="h">Nuclear terrorist attack on '
                f'{"the " if a["victim"] == "US" else ""}{NAMES[a["victim"]]}</div>'
                f'<div class="s">{NAMES[a["victim"]]} GPR +4. The chance was {odds(rd.p_attack)}. {how}</div></div>'
                f'<div style="margin-left:auto">{flag(a["victim"], 54)}</div></div>')
    how = "" if a["by"] == "draw" else " (moderator's call)"
    return (f'<div class="result calm"><div><div class="h">No attack this round{how}</div>'
            f'<div class="s">The chance was {odds(rd.p_attack)} with {rd.total} weapons in the world.</div></div></div>')


def changes_html(rd) -> str:
    chips = []
    for c in rd.order_after:
        v = rd.delta[c]
        chips.append(f'<div class="c{" up" if v else ""}">{flag(c, 16)}{SHORT[c]}<span class="v">'
                     f'{"+" + str(v) if v else "+0"}</span></div>')
    return '<div class="chg">' + "".join(chips) + "</div>"


def breakdown(rd):
    """Moderator-only table: why each GPR moved."""
    rows = []
    for c in rd.order_after:
        parts = [f"+1 {text}" for _, text in rd.hits[c]]
        if rd.sanction_pts[c]:
            parts.append(f"+2 ignored the sanction (had to play {signed(rd.required[c])}, played {signed(rd.moves[c])})")
        if rd.attack_pts[c]:
            parts.append("+4 terrorist attack")
        rows.append({"Country": NAMES[c], "Change": f"+{rd.delta[c]}", "Why": "; ".join(parts) or "nothing tripped"})
    st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")


def go_to(v):
    st.session_state.view = v


def end_game():
    game.end()
    st.query_params["g"] = game.to_token()
    st.session_state.view = "Debrief"


def stage_sanctions():
    st.html(stages_html("sanctions"))
    st.html(result_html(r))
    boom = st.session_state.pop("boom", None)
    if boom == (game.seed, r.number) and r.attack["victim"]:
        v = r.attack["victim"]
        st.html(explosion_html(NAMES[v], flag_uri(v), "GPR +4"), unsafe_allow_javascript=True)

    st.html('<div class="tgts-h">GPR changes this round</div>' + changes_html(r))
    if prefs["secret"]:
        with st.expander("Why each GPR changed (reveals the secret rules)", expanded=True):
            breakdown(r)

    deciders, candidates, note = game.sanction_groups()
    st.html(f'<h2 class="stage-title">Round {r.number}: sanctions</h2>'
            '<p class="lede">The three most powerful countries decide together. They may sanction one, both, or neither '
            'of the two weakest. A sanctioned country must cut by its maximum next round, or take +2.</p>')
    left, right = st.columns([1, 2.2], gap="medium")
    with left:
        st.html('<div class="deciders"><div class="t">Deciding together</div>'
                + "".join(f'<div class="d">{flag(c, 22)}{NAMES[c]}</div>' for c in deciders) + "</div>")
        if note:
            st.caption(note)
    picks = []
    with right:
        cols = st.columns(len(candidates))
        for col, c in zip(cols, candidates):
            ok, why = game.can_be_sanctioned(c)
            ck = f"sx_{game.seed}_{r.number}_{c}"
            state = "no" if not ok else ("on" if st.session_state.get(ck) else "off")
            with col:
                with st.container(key=f"cand_{c}_{state}"):
                    st.html(f'<div class="cname">{flag(c, 26)}{NAMES[c]}</div>')
                    if ok:
                        if st.checkbox("Sanction", key=ck):
                            picks.append(c)
                        need = -min(MAX_MOVE[c], r.nw_after[c])
                        st.html(f'<div class="cnote">Next round it must play {signed(need)}, or take +2.</div>')
                    else:
                        st.checkbox("Sanction", key=ck, value=False, disabled=True)
                        st.html(f'<div class="cnote">{NAMES[c]} {why}.</div>')
    st.write("")
    b1, b2, b3 = st.columns([1.6, 1, 2])
    with b1:
        label = "Impose sanctions" + (" on " + " and ".join(SHORT[c] for c in picks) if picks else "")
        if st.button(label, type="primary", disabled=not picks, icon=":material/gavel:", width="stretch"):
            game.impose_sanctions(picks)
            save_and_rerun(game)
    with b2:
        if st.button("No sanctions", width="stretch"):
            game.impose_sanctions([])
            save_and_rerun(game)
    if r.number >= game.planned:
        st.info(f"That was round {r.number} of {game.planned}. End the game now, or choose sanctions to play another round.",
                icon=":material/flag:")
        st.button("End the game and open the debrief", on_click=end_game, icon=":material/flag:")


def stage_over():
    best = min(game.gpr.values())
    winners = [c for c in COUNTRIES if game.gpr[c] == best]
    names = " and ".join(NAMES[c] for c in winners)
    flags = "".join(flag(c, 56) for c in winners)
    st.html(f'<div class="final">{flags}<div><div class="h">Lowest GPR: {names}</div>'
            f'<div class="s">GPR {best} after {plural(len(done), "round")}. The Debrief shows where every point came from, '
            f'and how much of it was luck.</div></div></div>')
    st.write("")
    st.button("Open the debrief", type="primary", on_click=go_to, args=("Debrief",), icon=":material/insights:")


# ----------------------------------------------------------------------------- history
def flag_legend() -> str:
    return '<div class="lgd">' + "".join(
        f'<span class="li"><span class="sw" style="background:{COLORS[c]}"></span>{flag(c, 15)}{SHORT[c]}</span>'
        for c in COUNTRIES) + "</div>"


def by_country_table(values, start) -> pd.DataFrame:
    rows = []
    for c in sorted(COUNTRIES, key=lambda x: game.gpr[x]):
        row = {"Flag": flag_uri(c), "Country": NAMES[c]}
        if start is not None:
            row["Start"] = start[c]
        for rd in done:
            row[f"Round {rd.number}"] = values(rd, c)
        rows.append(row)
    return pd.DataFrame(rows)


def rounds_table() -> pd.DataFrame:
    rows = []
    for rd in done:
        v = rd.attack["victim"]
        rows.append({"Round": rd.number, "World total": rd.total, "Attack chance": odds(rd.p_attack),
                     "Hit": flag_uri(v) if v else BLANK,
                     "Attack": (NAMES[v] if v else "none") + (" (moderator)" if rd.attack["by"] == "moderator" else ""),
                     "Under sanction": ", ".join(SHORT[c] for c in rd.sanctioned),
                     "Sanctioned next": ", ".join(SHORT[c] for c in (rd.imposed or []))})
    return pd.DataFrame(rows)


BLANK = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="
FLAGCOL = {"Flag": st.column_config.ImageColumn("", width="small"),
           "Hit": st.column_config.ImageColumn("", width="small")}


def style_chart(ch):
    return (ch.configure(font="Barlow").configure_view(strokeWidth=0)
            .configure_axis(labelFontSize=13, titleFontSize=13, domainColor="#BBBBBB", tickColor="#BBBBBB",
                            labelColor="#5E6878", titleColor="#5E6878"))


def line_chart(series: dict, ytitle: str):
    rows = []
    for c in COUNTRIES:
        for rnd, v in series[c]:
            rows.append({"Round": rnd, "Country": SHORT[c], "v": v})
    long = pd.DataFrame(rows)
    order = [rnd for rnd, _ in series[COUNTRIES[0]]]
    dom = [SHORT[c] for c in COUNTRIES]
    base = alt.Chart(long).encode(
        x=alt.X("Round:N", sort=order, title="Round", axis=alt.Axis(labelAngle=0, grid=False)),
        y=alt.Y("v:Q", title=ytitle, axis=alt.Axis(tickMinStep=1, gridColor="#EEF0F3")),
        color=alt.Color("Country:N", scale=alt.Scale(domain=dom, range=[COLORS[c] for c in COUNTRIES]), legend=None),
        tooltip=["Country", "Round", alt.Tooltip("v:Q", title=ytitle)])
    return style_chart((base.mark_line(strokeWidth=3) + base.mark_point(size=80, filled=True)).properties(height=300))


def view_history():
    if not done:
        st.info("No rounds played yet. The history fills in after the first attack stage.")
        return
    st.html('<h2 class="stage-title">Round by round</h2>')
    st.dataframe(rounds_table(), hide_index=True, width="stretch", column_config=FLAGCOL)
    gpr_series = {c: [("Start", START_GPR[c])] + [(str(rd.number), rd.gpr_after[c]) for rd in done] for c in COUNTRIES}
    nw_series = {c: [("Start", START_NW[c])] + [(str(rd.number), rd.nw_after[c]) for rd in done] for c in COUNTRIES}
    c1, c2 = st.columns(2, gap="large")
    with c1:
        st.html('<div class="ch-t">GPR after each round <span>(lower is more powerful)</span></div>' + flag_legend())
        st.altair_chart(line_chart(gpr_series, "GPR"), width="stretch")
    with c2:
        st.html('<div class="ch-t">Weapons after each round</div>' + flag_legend())
        st.altair_chart(line_chart(nw_series, "Weapons"), width="stretch")
    st.html('<div class="ch-t">Moves</div>')
    st.dataframe(by_country_table(lambda rd, c: signed(rd.moves[c]), None), hide_index=True, width="stretch", column_config=FLAGCOL)
    c3, c4 = st.columns(2, gap="large")
    with c3:
        st.html('<div class="ch-t">GPR</div>')
        st.dataframe(by_country_table(lambda rd, c: rd.gpr_after[c], START_GPR), hide_index=True, width="stretch", column_config=FLAGCOL)
    with c4:
        st.html('<div class="ch-t">Weapons</div>')
        st.dataframe(by_country_table(lambda rd, c: rd.nw_after[c], START_NW), hide_index=True, width="stretch", column_config=FLAGCOL)

    log = []
    for rd in done:
        row = {"Round": rd.number, "World total": rd.total, "Attack chance": odds(rd.p_attack),
               "Attack": NAMES[rd.attack["victim"]] if rd.attack["victim"] else "none",
               "Called by": "app draw" if rd.attack["by"] == "draw" else "moderator",
               "Under sanction": ", ".join(SHORT[c] for c in rd.sanctioned),
               "Sanctioned next": ", ".join(SHORT[c] for c in (rd.imposed or []))}
        for c in COUNTRIES:
            row[f"{SHORT[c]} move"] = rd.moves[c]
            row[f"{SHORT[c]} weapons"] = rd.nw_after[c]
            row[f"{SHORT[c]} GPR"] = rd.gpr_after[c]
            row[f"{SHORT[c]} GPR change"] = rd.delta[c]
        log.append(row)
    name = f"nuclear_diplomacy_{(game.label or 'game').replace(' ', '_')}.csv"
    st.download_button("Download the activity log (CSV)", pd.DataFrame(log).to_csv(index=False), file_name=name,
                       mime="text/csv", icon=":material/download:")


# ----------------------------------------------------------------------------- debrief
def view_debrief():
    if not done:
        st.info("Play at least one round first.")
        return
    if not game.over and not prefs["secret"]:
        st.info("The debrief shows each country's secret rules, so it opens after you end the game. "
                "To preview it, turn on “Show why each GPR changed” in Settings.")
        return

    st.html('<h2 class="stage-title">Where each country\'s GPR points came from</h2>')
    order = sorted(COUNTRIES, key=lambda c: game.gpr[c])
    top = max(game.gpr.values())
    legend = "".join(f'<span class="li"><span class="sw sq" style="background:{col}"></span>{name}</span>'
                     for name, col in SOURCE_COLORS.items())
    rows = []
    for c in order:
        parts = [("Starting GPR", START_GPR[c]), ("Rules tripped", sum(len(rd.hits[c]) for rd in done)),
                 ("Ignored sanctions", sum(rd.sanction_pts[c] for rd in done)),
                 ("Terrorist attacks", sum(rd.attack_pts[c] for rd in done))]
        segs = "".join(f'<span class="seg" title="{name}: {v}" style="width:{100 * v / top:.2f}%;background:{SOURCE_COLORS[name]};'
                       f'color:{"#2B2B2B" if name == "Starting GPR" else "#FFFFFF"}">'
                       f'{v if v and 100 * v / top > 6 else ""}</span>' for name, v in parts if v)
        rows.append(f'<div class="hb"><div class="hb-n">{flag(c, 18)}{SHORT[c]}</div><div class="hb-bar">{segs}</div>'
                    f'<div class="hb-v">{game.gpr[c]}</div></div>')
    st.html(f'<div class="lgd">{legend}</div><div class="hbars">{"".join(rows)}</div>')
    st.caption("Grey is where each country started. Blue is what the choices around the table cost. "
               "Orange is ignored sanctions. Green is the terrorist attacks: bad luck.")

    st.html('<h2 class="stage-title">How much was luck?</h2>'
            '<p class="lede">Keep every decision and sanction from this game, and draw the terrorist attacks again. '
            'How often would each country finish with the lowest GPR?</p>')
    if st.button("Replay this game 5,000 times", icon=":material/replay:"):
        st.session_state.luck = (game.to_token(), replay_luck(game, runs=5000, seed=7))
    luck = st.session_state.get("luck")
    if luck and luck[0] == game.to_token():
        w = luck[1]
        best = min(game.gpr.values())
        rows = []
        for c in sorted(COUNTRIES, key=lambda x: -w[x]):
            mark = '<span class="tag-in">finished first in class</span>' if game.gpr[c] == best else "<span></span>"
            rows.append(f'<div class="hb"><div class="hb-n">{flag(c, 18)}{SHORT[c]}</div><div class="hb-bar">'
                        f'<span class="seg" title="{pct(w[c])} of replays" style="width:{max(w[c] * 100, 0.4):.2f}%;background:{COLORS[c]}"></span></div>'
                        f'<div class="hb-v">{pct(w[c])}</div>{mark}</div>')
        st.html(f'<div class="hbars luck">{"".join(rows)}</div>')

    st.html('<h2 class="stage-title">The secret rules, and how often each one fired</h2>')
    cols = st.columns(5)
    n = len(done)
    for col, c in zip(cols, sorted(COUNTRIES, key=lambda x: game.gpr[x])):
        with col:
            items = [f'<div class="cname">{flag(c, 22)}{NAMES[c]}</div>']
            for rid, _, text, _ in RULES_BY_COUNTRY[c]:
                k = sum(1 for rd in done if any(h[0] == rid for h in rd.hits[c]))
                items.append(f'<div class="small" style="margin:.45rem 0"><b>+1</b> {text}<br>'
                             f'<span style="color:{"#C00000" if k else "#98A1AF"};font-weight:600">'
                             f'fired in {k} of {n} {"round" if n == 1 else "rounds"}</span></div>')
            st.html("".join(items))

    st.html('<h2 class="stage-title">Questions for the room</h2>')
    st.markdown(
        "- Did the GPR rules make sense? Which one would you change?\n"
        "- The attack falls on the most powerful. Is that how it works? How would you choose the target?\n"
        "- Where is this game like real nuclear diplomacy, and where is it not?\n"
        "- Did anyone disarm because it was right, or only because of the attack odds?")


# ----------------------------------------------------------------------------- settings
EVENT_TEXT = {"moves": "the decisions", "attack": "the attack stage", "sanctions": "the sanctions"}


def new_game():
    g = Game(label=game.label, planned=game.planned)
    st.session_state.game = g
    st.query_params["g"] = g.to_token()
    st.session_state.view = "Game"


def set_pref(name, key):
    prefs[name] = st.session_state[key]


def view_settings():
    st.html('<h2 class="stage-title">Settings</h2>')
    left, right = st.columns(2, gap="large")
    with left:
        st.subheader("This class")
        label = st.text_input("Class or section", value=game.label, placeholder="e.g. Section 22")
        planned = st.number_input("Rounds planned", min_value=1, max_value=12, value=game.planned, step=1)
        if label != game.label or planned != game.planned:
            game.label, game.planned = label, int(planned)
            st.query_params["g"] = game.to_token()
            st.rerun()

        st.subheader("During play")
        st.toggle("Show why each GPR changed", value=prefs["secret"], key="w_secret",
                  on_change=set_pref, args=("secret", "w_secret"),
                  help="Reveals the secret country rules. Leave it off while the room can see the screen.")
        st.toggle("Suspense before the attack result", value=prefs["suspense"], key="w_suspense",
                  on_change=set_pref, args=("suspense", "w_suspense"))
        st.toggle("Explosion when a country is attacked", value=prefs["boom"], key="w_boom",
                  on_change=set_pref, args=("boom", "w_boom"))

    with right:
        st.subheader("Game")
        if game.events:
            last = game.events[-1]
            rnd = game.rounds[-1].number if game.rounds else 1
            if last["t"] in ("moves", "attack"):
                what = f"round {rnd}: {EVENT_TEXT[last['t']]}"
            elif last["t"] == "sanctions":
                what = f"round {rnd - 1}: {EVENT_TEXT['sanctions']}"
            else:
                what = "the end of the game"
            if st.button(f"Undo {what}", icon=":material/undo:", width="stretch"):
                game.undo()
                save_and_rerun(game)
        else:
            st.button("Undo", icon=":material/undo:", disabled=True, width="stretch")

        if done and not game.over:
            with st.popover("End the game", icon=":material/flag:", width="stretch"):
                st.write("End now and open the debrief? A round that has not reached its attack stage is dropped.")
                st.button("Yes, end the game", type="primary", on_click=end_game)

        with st.popover("New game", icon=":material/restart_alt:", width="stretch"):
            st.write("Start over from the opening table? This game will be cleared.")
            st.button("Yes, start a new game", type="primary", on_click=new_game)
        st.caption("The address bar keeps the whole game. A refresh, or the same link opened later, brings it back.")

        st.subheader("Rules for everyone")
        st.markdown(
            "- **Moves.** Each round the U.S. can go up or down by up to 3 weapons, Russia by 2, "
            "China, India and Pakistan by 1. Nobody goes below 0.\n"
            "- **GPR.** Lower means more powerful. It never goes down: +1 for each rule on your sheet that is tripped, "
            "+4 for a terrorist attack, +2 for ignoring a sanction.\n"
            "- **Attack.** More weapons in the world, higher odds. An attack hits one of the three lowest GPRs: "
            "1 in 2, 1 in 3 or 1 in 6. Ties are broken by chance.\n"
            "- **Sanctions.** The three lowest GPRs may sanction one or both of the two highest. A sanctioned country "
            "must cut by its maximum next round, or take +2. **A country with 0 weapons cannot be sanctioned.**")
        st.caption(f"Game design and country briefs: the K=1 Project, Columbia University. Code: {REPO}")


# ----------------------------------------------------------------------------- route
if view == "Game":
    if phase == "over":
        stage_over()
    elif phase == "decide":
        stage_decide()
    elif phase == "attack":
        stage_attack()
    else:
        stage_sanctions()
elif view == "History":
    view_history()
elif view == "Debrief":
    view_debrief()
else:
    view_settings()
