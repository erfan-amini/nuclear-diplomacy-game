"""Nuclear Diplomacy Simulation: moderator console for the classroom projector.

Run locally with:  streamlit run streamlit_app.py
Every game screen is laid out to fit a laptop or projector screen without scrolling.
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
BLANK = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="


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
    if p.denominator <= 100:
        return f"{p.numerator} in {p.denominator}"
    return f"{float(p) * 100:.0f}%"


def pct(x: float) -> str:
    if x == 0:
        return "0%"
    return f"{x * 100:.0f}%" if x >= 0.095 else f"{x * 100:.1f}%"


def plural(n: int, word: str) -> str:
    return f"{n} {word}{'' if n == 1 else 's'}"


@st.cache_data
def trefoil(size: int = 22, color: str = "#C00000") -> str:
    """Radiation symbol, drawn as an SVG and embedded as an image."""
    r1, r2, cx = 0.28, 1.0, 1.1
    paths = []
    for k in range(3):
        a0, a1 = math.radians(90 + 120 * k - 30), math.radians(90 + 120 * k + 30)
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
  --signal:#C00000; --amber:#F2B705; --calm:#1E7B6B;
}
header[data-testid="stHeader"] {background:transparent; height:2.4rem;}
.block-container {padding-top:.9rem !important; padding-bottom:1rem !important; max-width:1320px;}
[data-testid="stMain"] [data-testid="stVerticalBlock"] {gap:.6rem;}
section[data-testid="stSidebar"] {width:384px !important; min-width:384px !important;}
[data-testid="stSidebarHeader"] {height:2rem; padding-bottom:0;}
[data-testid="stSidebarUserContent"] {padding-top:0 !important; padding-bottom:.5rem !important;}

/* header row */
.brand {font-family:"Barlow Condensed",sans-serif; font-weight:700; font-size:2rem; line-height:1; color:var(--signal);
        display:flex; align-items:center; gap:.45rem; white-space:nowrap;}
.toprow {display:flex; align-items:center; justify-content:flex-start; gap:1.6rem; padding-right:22rem; min-height:2.6rem;}
.rnd {text-align:left; color:var(--muted); font-size:.98rem; line-height:1.15; padding-left:1.2rem; border-left:2px solid var(--line);}
.rnd b {color:var(--ink); font-family:"Barlow Condensed",sans-serif; font-size:1.4rem; font-weight:700;}
.pips {display:flex; gap:5px; justify-content:flex-start; margin-top:4px;}
.pip {width:20px; height:6px; border-radius:3px; background:#E3E7ED;}
.pip.done {background:#8C96A6;} .pip.now {background:var(--signal);}

/* stage line */
.stline {display:flex; justify-content:flex-end;}
.stages {display:flex; border-radius:10px; overflow:hidden; border:1px solid var(--line); flex:0 0 auto;}
.stg {padding:.36rem 1rem; font-weight:600; color:#8A93A3; background:#fff; border-right:1px solid var(--line); font-size:.95rem;}
.stg:last-child {border-right:none;}
.stg.done {color:var(--ink); background:var(--panel);}
.stg.now {color:#fff; background:var(--signal);}
.lede {color:var(--muted); font-size:1rem; margin:0;}
h2.vt {font-family:"Barlow Condensed",sans-serif; font-weight:700; font-size:1.7rem; margin:0; padding:0; color:var(--ink);}

/* sidebar standings */
.sb {color:#E8EDF3; font-family:"Barlow",sans-serif;}
.sb-h {display:flex; align-items:baseline; justify-content:space-between; gap:8px;}
.sb-h b {font-family:"Barlow Condensed",sans-serif; font-weight:700; font-size:1.6rem; line-height:1;}
.sb-h span {color:#A9B4C4; font-size:.85rem; text-align:right;}
.sb-sub {color:#8E9AAD; font-size:.8rem; margin-top:2px;}
.sb-cols {display:grid; grid-template-columns:22px 1fr 54px 66px; gap:6px; color:#8E9AAD; font-size:.78rem; padding:6px 10px 3px 12px;}
.sb-cols span:nth-child(3), .sb-cols span:nth-child(4) {text-align:right;}
.sb-row {display:grid; grid-template-columns:22px 1fr 54px 66px; gap:6px; align-items:center; background:var(--slate2);
         border-radius:11px; padding:7px 10px; margin-bottom:5px; border-left:4px solid transparent;}
.sb-row.lead {border-left-color:#E8EDF3;}
.sb-row.hit {border-left-color:#FF5A4F; background:#3A2430;}
.sb-rk {font-family:"Barlow Condensed",sans-serif; font-weight:700; font-size:1.3rem; color:#C9D2DE; text-align:center; white-space:nowrap;}
.sb-nm {display:flex; flex-direction:column; gap:2px; min-width:0;}
.sb-nm .top {display:flex; align-items:center; gap:7px; font-weight:600; font-size:.98rem; white-space:nowrap; overflow:hidden;}
.sb-nm .fl {border-radius:2px; box-shadow:0 0 0 1px rgba(255,255,255,.18);}
.sb-num {display:flex; align-items:baseline; justify-content:flex-end; gap:4px; font-family:"Barlow Condensed",sans-serif;
         font-weight:700; font-size:1.75rem; line-height:1;}
.sb-num .d {font-family:"Barlow",sans-serif; font-size:.74rem; font-weight:600; color:#8E9AAD; min-width:18px; text-align:left;}
.sb-num .d.up {color:#FF8A80;} .sb-num .d.down {color:#7FD8B5;}
.sb-num.nw {color:#C9D2DE;}
.tag {display:inline-block; font-size:.72rem; font-weight:700; padding:0 7px; border-radius:999px; margin-right:4px; white-space:nowrap;}
.tag.red {background:#FF5A4F; color:#fff;} .tag.amber {background:var(--amber); color:#2B2100;}
.tag.grey {background:#3B475B; color:#C9D2DE;} .tag.green {background:#2C6E5F; color:#DDF5EC;}
.sb-line {display:flex; justify-content:space-between; color:#8E9AAD; font-size:.74rem; margin:1px 4px 6px 4px;
          border-top:1px dashed #56637A; padding-top:3px;}
.sb-world {margin-top:10px; background:#141B26; border-radius:13px; padding:10px 11px 9px 11px;}
.sb-world .w {display:flex; align-items:baseline; gap:7px; flex-wrap:wrap;}
.sb-world .w b {font-family:"Barlow Condensed",sans-serif; font-size:2rem; line-height:1;}
.sb-world .w span {color:#A9B4C4; font-size:.92rem;}
.sb-world .w i {font-style:normal; margin-left:auto; color:#E8EDF3; font-size:.92rem;}
.sb-world .w i b {color:#FF8A80; font-size:1.25rem;}

/* odds meter */
.meter {display:grid; grid-template-columns:repeat(6,1fr); gap:4px; margin-top:6px;}
.band {border-radius:7px; padding:3px 1px; text-align:center; background:#fff; border:1px solid var(--line); line-height:1.12;}
.band .b-r {display:block; font-size:.7rem; color:var(--muted);}
.band .b-o {display:block; font-size:.82rem; font-weight:700; color:#9AA3B2; white-space:nowrap;}
.band.on {background:var(--signal); border-color:var(--signal);}
.band.on .b-r, .band.on .b-o {color:#fff;}
.meter.dark {gap:3px;}
.meter.dark .band {background:#212B3B; border-color:#2E3A4E;}
.meter.dark .band .b-r {color:#8E9AAD; font-size:.66rem;} .meter.dark .band .b-o {color:#B6C0CF; font-size:.7rem;}
.meter.dark .band.on {background:var(--signal); border-color:var(--signal);}
.meter.dark .band.on .b-r, .meter.dark .band.on .b-o {color:#fff;}

/* decision rows */
[class*="st-key-drow_"] {background:var(--panel); border-radius:12px; padding:.28rem .8rem;}
[class*="st-key-drow_"] [data-testid="stVerticalBlock"] {gap:0;}
.dname {display:flex; align-items:center; gap:10px;}
.dname .fl {border-radius:3px; box-shadow:0 0 0 1px rgba(0,0,0,.08);}
.dname b {font-size:1.08rem;} .dname .sub {display:block; color:var(--muted); font-size:.84rem; font-weight:400; line-height:1.15;}
.dres {font-family:"Barlow Condensed",sans-serif; font-size:1.5rem; font-weight:700; color:var(--ink); text-align:right; line-height:1;}
.dres .s {font-family:"Barlow",sans-serif; font-size:.8rem; font-weight:500; color:var(--muted); display:block;}
.req {display:inline-block; background:var(--amber); color:#2B2100; font-weight:700; font-size:.8rem; border-radius:999px; padding:0 8px;}
button[data-variant="segmented_control"] {min-width:3.2rem;}
button[data-variant="segmented_control"] p {font-size:1.08rem; font-weight:700;}
.proj {font-size:1rem; color:var(--muted);} .proj b {font-family:"Barlow Condensed",sans-serif; font-size:1.55rem; color:var(--ink);}

/* attack */
.hero {background:var(--slate); color:#E8EDF3; border-radius:16px; padding:.8rem 1.2rem; display:grid;
       grid-template-columns:minmax(150px,210px) 1fr; gap:1.2rem; align-items:center;}
.hero .big {font-family:"Barlow Condensed",sans-serif; font-weight:700; font-size:3.6rem; line-height:.9;}
.hero .cap {color:#A9B4C4; font-size:.95rem;}
.hero .oddsline {font-size:1.08rem;}
.hero .oddsline b {font-family:"Barlow Condensed",sans-serif; font-size:1.9rem; color:#FF8A80; margin-left:.35rem;}
.strip {display:grid; grid-template-columns:190px 1fr; gap:14px; align-items:center; margin-top:.75rem;}
.st-l {font-weight:700; color:var(--ink); line-height:1.2; font-size:1rem;}
.st-l span {display:block; font-weight:400; color:var(--muted); font-size:.86rem;}
.st-bar {position:relative; display:flex; gap:3px; height:54px;}
.sg {display:flex; align-items:center; justify-content:center; gap:8px; border-radius:10px; font-weight:700; font-size:1rem;
     color:var(--ink); background:#E9EDF2; overflow:hidden; white-space:nowrap; min-width:0; transition:background .2s ease;}
.sg .o {font-family:"Barlow Condensed",sans-serif; font-size:1.35rem;}
.sg .fl {border-radius:2px; box-shadow:0 0 0 1px rgba(0,0,0,.1);}
.sg.atk {background:#F6D5D5; color:#7A0C0C;}
.sg.calm {background:#DDEFE9; color:#0F4A3F;}
.sg.t0 {background:#E3E8F0;} .sg.t1 {background:#EBEEF3;} .sg.t2 {background:#F2F4F7;}
.sg.lit {background:var(--signal) !important; color:#fff !important;}
.sg.lit.calm {background:var(--calm) !important;}
.sg.dim {opacity:.45;}
.ptr {position:absolute; top:-12px; bottom:-6px; width:0; z-index:3;}
.ptr::before {content:""; position:absolute; left:-9px; top:0; border-left:9px solid transparent; border-right:9px solid transparent;
              border-top:12px solid var(--ink);}
.ptr::after {content:""; position:absolute; left:-1.5px; top:10px; bottom:0; width:3px; background:var(--ink); border-radius:2px;}
[class*="st-key-mpick_"] {border:2px solid var(--line); border-radius:12px; padding:.45rem .35rem .25rem .35rem; text-align:center;}
[class*="st-key-mpick_"][class*="_on"] {border-color:var(--signal); background:#FDEEEE;}
[class*="st-key-mpick_"] [data-testid="stVerticalBlock"] {gap:.3rem;}
.mp-fl {display:flex; justify-content:center; height:30px; align-items:center;}
.mp-fl img {border-radius:3px; box-shadow:0 0 0 1px rgba(0,0,0,.08);}

/* result and changes */
.result {border-radius:16px; padding:.7rem 1.2rem; display:flex; align-items:center; gap:1rem;}
.result.hit {background:linear-gradient(100deg,#7A0C0C 0%,#C00000 60%,#D9381E 100%); color:#fff;}
.result.calm {background:#E3F1EC; color:#0F4A3F;}
.result .h {font-family:"Barlow Condensed",sans-serif; font-weight:700; font-size:1.85rem; line-height:1.05;}
.result .s {font-size:.98rem; opacity:.92;}
.result .fl {border-radius:4px; box-shadow:0 2px 8px rgba(0,0,0,.25);}
.chg {display:flex; gap:.45rem; flex-wrap:wrap; align-items:center;}
.chg .l {color:var(--muted); font-size:.95rem; margin-right:.2rem;}
.chg .c {display:flex; align-items:center; gap:5px; padding:.18rem .5rem; border-radius:9px; background:var(--panel); font-weight:600; font-size:.95rem;}
.chg .c .fl {border-radius:2px;}
.chg .c .v {font-family:"Barlow Condensed",sans-serif; font-size:1.2rem; font-weight:700; color:#8A93A3;}
.chg .c.up .v {color:var(--signal);}

/* sanctions */
.sanc-h {font-weight:700; color:var(--ink); font-size:1.05rem;}
.sanc-h span {font-weight:400; color:var(--muted); font-size:.92rem;}
.deciders {background:var(--panel); border-radius:12px; padding:.6rem .9rem; height:100%;}
.deciders .t {color:var(--muted); font-size:.9rem; margin-bottom:.25rem;}
.deciders .d {display:flex; align-items:center; gap:8px; font-weight:600; font-size:1.02rem; margin:.22rem 0;}
.deciders .fl {border-radius:3px; box-shadow:0 0 0 1px rgba(0,0,0,.08);}
[class*="st-key-cand_"] {border:2px solid var(--line); border-radius:12px; padding:.55rem .8rem; background:#fff;}
[class*="st-key-cand_"][class*="_on"] {border-color:var(--amber); background:#FFF7DA;}
[class*="st-key-cand_"][class*="_no"] {background:var(--panel); border-style:dashed;}
[class*="st-key-cand_"] [data-testid="stVerticalBlock"] {gap:.35rem;}
.cname {display:flex; align-items:center; gap:9px; font-weight:700; font-size:1.1rem;}
.cname .fl {border-radius:3px; box-shadow:0 0 0 1px rgba(0,0,0,.08);}
.cnote {color:var(--muted); font-size:.86rem; line-height:1.25;}
.endnote {color:var(--muted); font-size:.88rem; line-height:1.25;}

/* final */
.final {background:var(--slate); color:#E8EDF3; border-radius:16px; padding:1.2rem 1.4rem; display:flex; align-items:center; gap:1.2rem;}
.final .h {font-family:"Barlow Condensed",sans-serif; font-weight:700; font-size:2.4rem; line-height:1;}
.final .s {color:#A9B4C4; font-size:1.02rem; margin-top:.3rem;}
.final .fl {border-radius:5px;}

/* charts, legends, bars */
.ch-t {font-family:"Barlow Condensed",sans-serif; font-weight:700; font-size:1.25rem; color:var(--ink);}
.ch-t span {font-family:"Barlow",sans-serif; font-weight:400; font-size:.9rem; color:var(--muted); margin-left:.3rem;}
.lgd {display:flex; flex-wrap:wrap; gap:.25rem .9rem; font-size:.9rem; color:var(--ink);}
.lgd .li {display:flex; align-items:center; gap:5px;}
.lgd .sw {width:16px; height:4px; border-radius:2px; display:inline-block;}
.lgd .sw.sq {width:12px; height:12px; border-radius:3px;}
.lgd img {border-radius:2px; box-shadow:0 0 0 1px rgba(0,0,0,.08);}
.hbars {display:flex; flex-direction:column; gap:8px;}
.hb {display:grid; grid-template-columns:130px 1fr 54px; gap:10px; align-items:center;}
.luck .hb {grid-template-columns:130px 1fr 64px 170px;}
.hb-n {display:flex; align-items:center; gap:8px; font-weight:600;}
.hb-n img {border-radius:2px; box-shadow:0 0 0 1px rgba(0,0,0,.08);}
.hb-bar {display:flex; gap:2px; height:30px; background:var(--panel); border-radius:6px; overflow:hidden;}
.hb-bar .seg {display:flex; align-items:center; justify-content:center; font-weight:700; font-size:.9rem; height:100%;}
.hb-v {font-family:"Barlow Condensed",sans-serif; font-weight:700; font-size:1.45rem; color:var(--ink);}
.tag-in {font-size:.8rem; font-weight:700; background:var(--slate); color:#fff; border-radius:999px; padding:2px 9px; white-space:nowrap;}
.rules .cname {font-size:1rem; margin-bottom:.2rem;}
.rules .r {color:var(--muted); font-size:.86rem; margin:.3rem 0; line-height:1.25;}
.rules .r b {color:var(--ink);} .rules .r .k {font-weight:600;}
.small {color:var(--muted); font-size:.88rem;}
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
        cap = f"final, after {plural(len(done), 'round')}"
        hit = last.attack["victim"]
        world = sum(game.nw.values())
    elif phase == "decide":
        prev = done[-1] if done else None
        nw, gpr, order = game.nw, game.gpr, r.order_start
        d_gpr = prev.delta if prev else None
        d_nw = prev.moves if prev else None
        cap = "opening table" if not prev else f"start of round {r.number}"
        for c in r.sanctioned:
            tags[c].append((f"Sanctioned: must play {signed(r.required[c])}", "amber"))
        world = sum(nw.values())
    elif phase == "attack":
        nw, gpr, order, d_gpr, d_nw = r.nw_after, r.gpr_start, r.order_start, None, r.moves
        cap = f"round {r.number}: new weapons"
        for c in r.sanctioned:
            ok = r.moves[c] == r.required[c]
            tags[c].append(("Obeyed the sanction" if ok else "Ignored the sanction", "green" if ok else "amber"))
        world = r.total
    else:  # sanctions
        nw, gpr, order, d_gpr, d_nw = r.nw_after, r.gpr_after, r.order_after, r.delta, r.moves
        cap = f"after round {r.number}"
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
        dg = dn = '<span class="d"></span>'
        if d_gpr is not None:
            v = d_gpr[c]
            dg = f'<span class="d{" up" if v > 0 else ""}">+{v}</span>'
        if d_nw is not None:
            v = d_nw[c]
            dn = f'<span class="d{" up" if v > 0 else (" down" if v < 0 else "")}">{signed(v)}</span>'
        tag_html = "".join(f'<span class="tag {k}">{t}</span>' for t, k in tags[c])
        rows.append(f'<div class="{cls}"><div class="sb-rk">{ranks[c]}</div>'
                    f'<div class="sb-nm"><div class="top">{flag(c, 17)}{NAMES[c]}</div>'
                    f'{"<div>" + tag_html + "</div>" if tag_html else ""}</div>'
                    f'<div class="sb-num">{gpr[c]}{dg}</div><div class="sb-num nw">{nw[c]}{dn}</div></div>')
        if i == 2:
            rows.append('<div class="sb-line"><span>&uarr; attack targets</span><span>can be sanctioned &darr;</span></div>')
    p = attack_probability(world)
    return (f'<div class="sb"><div class="sb-h"><b>Standings</b><span>{cap}</span></div>'
            f'<div class="sb-sub">Lower GPR means more power.</div>'
            f'<div class="sb-cols"><span></span><span></span><span>GPR</span><span>Weapons</span></div>'
            f'{"".join(rows)}'
            f'<div class="sb-world"><div class="w"><b>{world}</b><span>weapons in the world</span>'
            f'<i>attack chance <b>{odds(p)}</b></i></div>{meter(world, dark=True)}</div></div>')


with st.sidebar:
    st.html(standings_html())


# ----------------------------------------------------------------------------- header row
def round_html() -> str:
    n_done = len(done)
    if phase == "over":
        rtxt = f"<b>Game over</b> after {plural(n_done, 'round')}"
    elif r.number > game.planned:
        rtxt = f"<b>Round {r.number}</b> (extra)"
    else:
        rtxt = f"<b>Round {r.number}</b> of {game.planned}"
    if game.label:
        rtxt = f"{game.label} &nbsp;&middot;&nbsp; " + rtxt
    total = max(game.planned, n_done + (0 if phase == "over" else 1))
    pips = "".join(f'<span class="pip {"done" if i <= n_done else ("now" if phase != "over" and i == r.number else "")}"></span>'
                   for i in range(1, total + 1))
    return f'<div class="rnd">{rtxt}<div class="pips">{pips}</div></div>'


st.session_state.setdefault("view", "Game")
st.html(f'<div class="toprow"><div class="brand">{trefoil(30)}Nuclear Diplomacy</div>{round_html()}</div>')
nav, stg = st.columns([1.15, 1], vertical_alignment="center")
with nav:
    view = st.segmented_control("View", ["Game", "History", "Debrief", "Settings"],
                                key="view", label_visibility="collapsed") or "Game"
with stg:
    if view == "Game" and phase != "over":
        names = ["1  Decisions", "2  Attack", "3  Sanctions"]
        idx = {"decide": 0, "attack": 1, "sanctions": 2}[phase]
        steps = "".join(f'<div class="stg {"now" if i == idx else ("done" if i < idx else "")}">{n}</div>'
                        for i, n in enumerate(names))
        st.html(f'<div class="stline"><div class="stages">{steps}</div></div>')


def stage_line(ph: str, lede: str):
    """Kept for call sites; the stage strip now sits in the header row."""
    return None


# ----------------------------------------------------------------------------- game: decisions
def stage_decide():
    stage_line("decide", "Collect all five slips, enter each move, then lock them in.")
    chosen = {}
    for c in COUNTRIES:
        with st.container(key=f"drow_{c}"):
            a, b, d = st.columns([2.3, 4.2, 0.9], vertical_alignment="center")
            with a:
                sub = (f'<span class="req">Sanctioned: must play {signed(r.required[c])}</span>'
                       if c in r.sanctioned else f'<span class="sub">{plural(game.nw[c], "weapon")}, moves up to {MAX_MOVE[c]}</span>')
                st.html(f'<div class="dname">{flag(c, 26)}<div><b>{NAMES[c]}</b>{sub}</div></div>')
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
    left, right = st.columns([3.1, 1.2], vertical_alignment="center")
    with left:
        st.html(f'<div class="proj">{"With these moves" if not missing else "So far"}: <b>{total}</b> weapons in the world, '
                f'attack chance <b>{odds(attack_probability(total))}</b></div>{meter(total)}')
    with right:
        if missing:
            st.button("Lock in decisions", type="primary", disabled=True, icon=":material/lock:", width="stretch")
            st.caption("Waiting for: " + ", ".join(missing))
        elif st.button("Lock in decisions", type="primary", icon=":material/lock:", width="stretch"):
            game.submit_moves(chosen)
            save_and_rerun(game)


# ----------------------------------------------------------------------------- game: attack
def hero_html(rd) -> str:
    return (f'<div class="hero"><div><div class="big">{rd.total}</div><div class="cap">weapons in the world</div></div>'
            f'<div><div class="oddsline">Chance of a nuclear terrorist attack this round<b>{odds(rd.p_attack)}</b></div>'
            f'{meter(rd.total, dark=True)}</div></div>')


def pointer_html(x: float, anim: bool) -> str:
    """A needle over a strip. When animated it sweeps, slows down and stops at x (0 to 1)."""
    pos = max(0.6, min(99.4, x * 100))
    if not anim:
        return f'<div class="ptr" style="left:{pos:.2f}%"></div>'
    name = f"nd{int(time.time() * 1000) % 10**9}"
    back = max(4.0, min(96.0, pos + (14 if pos < 70 else -14)))
    return (f'<style>@keyframes {name}{{0%{{left:1%}}32%{{left:98%}}58%{{left:6%}}82%{{left:{back:.1f}%}}'
            f'100%{{left:{pos:.2f}%}}}}</style>'
            f'<div class="ptr" style="left:{pos:.2f}%;animation:{name} 2s cubic-bezier(.25,.8,.3,1) both"></div>')


def strip_attack(rd, u: float | None = None, anim: bool = False, lit: str | None = None) -> str:
    p = float(rd.p_attack)
    segs = []
    if p > 0:
        segs.append(("atk", p, f'Attack <span class="o">{odds(rd.p_attack)}</span>', "atk"))
    segs.append(("none", 1 - p, f'No attack <span class="o">{odds(1 - rd.p_attack) if p else "certain"}</span>', "calm"))
    body = "".join(f'<div class="sg {cls}{" lit" if lit == k else (" dim" if lit else "")}" style="width:{w * 100:.3f}%">'
                   f'{lab if w >= 0.12 else ""}</div>' for k, w, lab, cls in segs)
    ptr = pointer_html(u, anim) if u is not None else ""
    return (f'<div class="strip"><div class="st-l">Step 1: is there an attack?<span>the needle lands at random</span></div>'
            f'<div class="st-bar">{body}{ptr}</div></div>')


def strip_victim(rd, v: float | None = None, anim: bool = False, lit: str | None = None) -> str:
    targets = [c for c in rd.order_start if rd.shares[c] > 0]
    body = []
    for i, c in enumerate(targets):
        w = float(rd.shares[c])
        lab = (f'{flag(c, 20)}{SHORT[c]} <span class="o">{odds(rd.shares[c])}</span>' if w >= 0.26 else
               f'{flag(c, 18)}<span class="o">{odds(rd.shares[c])}</span>' if w >= 0.1 else f'{flag(c, 14)}')
        cls = f"t{min(i, 2)}" + (" lit" if lit == c else (" dim" if lit else ""))
        body.append(f'<div class="sg {cls}" style="width:{w * 100:.3f}%">{lab}</div>')
    ptr = pointer_html(v, anim) if v is not None else ""
    head = ("Step 2: if yes, who is hit?" if len(targets) == 3 else "Step 2: if yes, who is hit?")
    sub = "more power, bigger slice" if len(targets) == 3 else "tied countries share their slices"
    return (f'<div class="strip"><div class="st-l">{head}<span>{sub}</span></div>'
            f'<div class="st-bar">{"".join(body)}{ptr}</div></div>')


def stage_attack():
    stage_line("attack", "More weapons in the world means a higher chance of a nuclear terrorist attack.")
    st.html(hero_html(r))
    slot = st.empty()
    slot.html(strip_attack(r) + strip_victim(r))
    b1, b2, _ = st.columns([1.5, 1.4, 1.6])
    with b1:
        run = st.button("Run the attack draw", type="primary", icon=":material/casino:", width="stretch")
    with b2:
        with st.popover("Call it yourself", icon=":material/gavel:", width="stretch"):
            manual_picker()
    if run:
        game.draw_attack()
        rd = game.current
        a = rd.attack
        victim = a["victim"]
        if prefs["suspense"]:
            slot.html(strip_attack(rd, a["u"], anim=True) + strip_victim(rd))
            time.sleep(2.3)
            slot.html(strip_attack(rd, a["u"], lit="atk" if victim else "none") + strip_victim(rd))
            time.sleep(0.6)
            if victim:
                slot.html(strip_attack(rd, a["u"], lit="atk") + strip_victim(rd, a["v"], anim=True))
                time.sleep(2.3)
                slot.html(strip_attack(rd, a["u"], lit="atk") + strip_victim(rd, a["v"], lit=victim))
                time.sleep(0.8)
        mark_boom(victim)
        save_and_rerun(game)


def manual_picker():
    st.caption("The teacher guide lets the moderator call or skip an attack, for example after rolling dice in the room. "
               "Pick an outcome, then apply it.")
    pk = f"manual_{game.seed}_{r.number}"
    pick = st.session_state.get(pk, "none")
    opts = ["none"] + list(r.order_start)
    for row in (opts[:3], opts[3:]):
        cols = st.columns(3)
        for col, c in zip(cols, row):
            with col:
                with st.container(key=f"mpick_{c}_{'on' if pick == c else 'off'}"):
                    st.html(f'<div class="mp-fl">{flag(c, 26) if c != "none" else trefoil(26, "#9AA3B2")}</div>')
                    st.button(SHORT[c] if c != "none" else "No attack", key=f"mp_{game.seed}_{r.number}_{c}", width="stretch",
                              on_click=st.session_state.__setitem__, args=(pk, c))
    label = "Apply: no attack" if pick == "none" else f"Apply: attack on {NAMES[pick]}"
    if st.button(label, type="primary", icon=":material/check:", width="stretch"):
        victim = None if pick == "none" else pick
        game.set_attack(victim)
        mark_boom(victim)
        save_and_rerun(game)


# ----------------------------------------------------------------------------- game: sanctions
def result_html(rd) -> str:
    a = rd.attack
    if a["victim"]:
        how = "drawn by the app" if a["by"] == "draw" else "called by the moderator"
        return (f'<div class="result hit">{trefoil(40, "#FFFFFF")}<div><div class="h">Nuclear terrorist attack on '
                f'{"the " if a["victim"] == "US" else ""}{NAMES[a["victim"]]}</div>'
                f'<div class="s">GPR +4. The chance of an attack was {odds(rd.p_attack)}, {how}.</div></div>'
                f'<div style="margin-left:auto">{flag(a["victim"], 46)}</div></div>')
    how = "" if a["by"] == "draw" else " (moderator's call)"
    return (f'<div class="result calm"><div><div class="h">No attack this round{how}</div>'
            f'<div class="s">The chance was {odds(rd.p_attack)} with {rd.total} weapons in the world.</div></div></div>')


def changes_html(rd) -> str:
    chips = "".join(f'<div class="c{" up" if rd.delta[c] else ""}">{flag(c, 15)}{SHORT[c]}<span class="v">+{rd.delta[c]}</span></div>'
                    for c in rd.order_after)
    return f'<div class="chg"><span class="l">GPR changes</span>{chips}</div>'


def breakdown(rd):
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
    stage_line("sanctions", "The three most powerful countries may sanction one, both, or neither of the two weakest.")
    st.html(result_html(r))
    boom = st.session_state.pop("boom", None)
    if boom == (game.seed, r.number) and r.attack["victim"]:
        v = r.attack["victim"]
        st.html(explosion_html(NAMES[v], flag_uri(v), "GPR +4"), unsafe_allow_javascript=True)
    if prefs["secret"]:
        c1, c2 = st.columns([5, 1.4], vertical_alignment="center")
        with c1:
            st.html(changes_html(r))
        with c2:
            with st.popover("Why? (secret rules)", width="stretch"):
                breakdown(r)
    else:
        st.html(changes_html(r))

    deciders, candidates, note = game.sanction_groups()
    st.html('<div class="sanc-h">Sanctions <span>Must cut by the maximum next round, or take +2. '
            '0 weapons: cannot be sanctioned.</span></div>')
    cols = st.columns([1.15] + [1] * len(candidates) + [1.25])
    with cols[0]:
        st.html('<div class="deciders"><div class="t">Deciding together</div>'
                + "".join(f'<div class="d">{flag(c, 20)}{SHORT[c]}</div>' for c in deciders) + "</div>")
        if note:
            st.caption(note)
    picks = []
    for col, c in zip(cols[1:-1], candidates):
        ok, why = game.can_be_sanctioned(c)
        ck = f"sx_{game.seed}_{r.number}_{c}"
        state = "no" if not ok else ("on" if st.session_state.get(ck) else "off")
        with col:
            with st.container(key=f"cand_{c}_{state}"):
                st.html(f'<div class="cname">{flag(c, 24)}{NAMES[c]}</div>')
                if ok:
                    if st.checkbox("Sanction", key=ck):
                        picks.append(c)
                    need = -min(MAX_MOVE[c], r.nw_after[c])
                    st.html(f'<div class="cnote">Next round it must play {signed(need)}, or take +2.</div>')
                else:
                    st.checkbox("Sanction", key=ck, value=False, disabled=True)
                    st.html(f'<div class="cnote">{NAMES[c]} {why}.</div>')
    with cols[-1]:
        label = "Impose sanctions" + (" on " + " and ".join(SHORT[c] for c in picks) if picks else "")
        if st.button(label, type="primary", disabled=not picks, icon=":material/gavel:", width="stretch"):
            game.impose_sanctions(picks)
            save_and_rerun(game)
        if st.button("No sanctions", width="stretch"):
            game.impose_sanctions([])
            save_and_rerun(game)
        if r.number >= game.planned:
            st.html(f'<div class="endnote">That was round {r.number} of {game.planned}. '
                    f'Sanctions start another round.</div>')
            st.button("End the game", on_click=end_game, icon=":material/flag:", width="stretch")


def stage_over():
    best = min(game.gpr.values())
    winners = [c for c in COUNTRIES if game.gpr[c] == best]
    names = " and ".join(NAMES[c] for c in winners)
    flags = "".join(flag(c, 52) for c in winners)
    st.html(f'<div class="final">{flags}<div><div class="h">Lowest GPR: {names}</div>'
            f'<div class="s">GPR {best} after {plural(len(done), "round")}. The Debrief shows where every point came from, '
            f'and how much of it was luck.</div></div></div>')
    st.button("Open the debrief", type="primary", on_click=go_to, args=("Debrief",), icon=":material/insights:")


# ----------------------------------------------------------------------------- history
FLAGCOL = {"Flag": st.column_config.ImageColumn("", width="small"),
           "Hit": st.column_config.ImageColumn("", width="small")}


def flag_legend() -> str:
    return '<div class="lgd">' + "".join(
        f'<span class="li"><span class="sw" style="background:{COLORS[c]}"></span>{flag(c, 14)}{SHORT[c]}</span>'
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
        rows.append({"Round": rd.number, "Weapons": rd.total, "Chance": odds(rd.p_attack), "Hit": flag_uri(v) if v else BLANK,
                     "Attack": (SHORT[v] if v else "none") + (" (mod.)" if rd.attack["by"] == "moderator" else ""),
                     "Under sanction": ", ".join(SHORT[c] for c in rd.sanctioned),
                     "Sanctioned next": ", ".join(SHORT[c] for c in (rd.imposed or []))})
    return pd.DataFrame(rows)


def style_chart(ch):
    return (ch.configure(font="Barlow").configure_view(strokeWidth=0)
            .configure_axis(labelFontSize=12, titleFontSize=12, domainColor="#BBBBBB", tickColor="#BBBBBB",
                            labelColor="#5E6878", titleColor="#5E6878"))


def line_chart(series: dict, ytitle: str, height: int):
    rows = [{"Round": rnd, "Country": SHORT[c], "v": v} for c in COUNTRIES for rnd, v in series[c]]
    long = pd.DataFrame(rows)
    order = [rnd for rnd, _ in series[COUNTRIES[0]]]
    dom = [SHORT[c] for c in COUNTRIES]
    base = alt.Chart(long).encode(
        x=alt.X("Round:N", sort=order, title=None, axis=alt.Axis(labelAngle=0, grid=False)),
        y=alt.Y("v:Q", title=ytitle, axis=alt.Axis(tickMinStep=1, gridColor="#EEF0F3")),
        color=alt.Color("Country:N", scale=alt.Scale(domain=dom, range=[COLORS[c] for c in COUNTRIES]), legend=None),
        tooltip=["Country", "Round", alt.Tooltip("v:Q", title=ytitle)])
    return style_chart((base.mark_line(strokeWidth=3) + base.mark_point(size=70, filled=True)).properties(height=height))


def csv_log() -> str:
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
    return pd.DataFrame(log).to_csv(index=False)


def view_history():
    if not done:
        st.info("No rounds played yet. The history fills in after the first attack stage.")
        return
    st.session_state.setdefault("hist_view", "Charts")
    part = st.segmented_control("History part", ["Charts", "Round by round", "Exact numbers"], key="hist_view",
                                label_visibility="collapsed") or "Charts"
    if part == "Charts":
        gpr_series = {c: [("Start", START_GPR[c])] + [(str(rd.number), rd.gpr_after[c]) for rd in done] for c in COUNTRIES}
        nw_series = {c: [("Start", START_NW[c])] + [(str(rd.number), rd.nw_after[c]) for rd in done] for c in COUNTRIES}
        st.html(flag_legend())
        c1, c2 = st.columns(2, gap="large")
        with c1:
            st.html('<div class="ch-t">GPR after each round <span>(lower is more powerful)</span></div>')
            st.altair_chart(line_chart(gpr_series, "GPR", 290), width="stretch")
        with c2:
            st.html('<div class="ch-t">Weapons after each round</div>')
            st.altair_chart(line_chart(nw_series, "Weapons", 290), width="stretch")
    elif part == "Round by round":
        st.dataframe(rounds_table(), hide_index=True, width="stretch", height=36 + 35 * len(done) + 2, column_config=FLAGCOL)
        name = f"nuclear_diplomacy_{(game.label or 'game').replace(' ', '_')}.csv"
        st.download_button("Download the activity log (CSV)", csv_log(), file_name=name, mime="text/csv",
                           icon=":material/download:")
    else:
        h = 34 + 30 * 5 + 2
        st.html('<div class="ch-t">Moves</div>')
        st.dataframe(by_country_table(lambda rd, c: signed(rd.moves[c]), None), hide_index=True, width="stretch",
                     height=h, column_config=FLAGCOL, row_height=30)
        c3, c4 = st.columns(2, gap="large")
        with c3:
            st.html('<div class="ch-t">GPR</div>')
            st.dataframe(by_country_table(lambda rd, c: rd.gpr_after[c], START_GPR), hide_index=True, width="stretch",
                         height=h, column_config=FLAGCOL, row_height=30)
        with c4:
            st.html('<div class="ch-t">Weapons</div>')
            st.dataframe(by_country_table(lambda rd, c: rd.nw_after[c], START_NW), hide_index=True, width="stretch",
                         height=h, column_config=FLAGCOL, row_height=30)


# ----------------------------------------------------------------------------- debrief
def view_debrief():
    if not done:
        st.info("Play at least one round first.")
        return
    if not game.over and not prefs["secret"]:
        st.info("The debrief shows each country's secret rules, so it opens after you end the game. "
                "To preview it, turn on “Show why each GPR changed” in Settings.")
        return
    st.session_state.setdefault("deb_view", "Where the points came from")
    part = st.segmented_control("Part", ["Where the points came from", "How much was luck?", "The secret rules",
                                         "Questions for the room"], key="deb_view", label_visibility="collapsed") \
        or "Where the points came from"

    if part == "Where the points came from":
        order = sorted(COUNTRIES, key=lambda c: game.gpr[c])
        top = max(game.gpr.values())
        legend = "".join(f'<span class="li"><span class="sw sq" style="background:{col}"></span>{name}</span>'
                         for name, col in SOURCE_COLORS.items())
        rows = []
        for c in order:
            parts = [("Starting GPR", START_GPR[c]), ("Rules tripped", sum(len(rd.hits[c]) for rd in done)),
                     ("Ignored sanctions", sum(rd.sanction_pts[c] for rd in done)),
                     ("Terrorist attacks", sum(rd.attack_pts[c] for rd in done))]
            segs = "".join(f'<span class="seg" title="{name}: {v}" style="width:{100 * v / top:.2f}%;'
                           f'background:{SOURCE_COLORS[name]};color:{"#2B2B2B" if name == "Starting GPR" else "#FFFFFF"}">'
                           f'{v if v and 100 * v / top > 6 else ""}</span>' for name, v in parts if v)
            rows.append(f'<div class="hb"><div class="hb-n">{flag(c, 18)}{SHORT[c]}</div><div class="hb-bar">{segs}</div>'
                        f'<div class="hb-v">{game.gpr[c]}</div></div>')
        st.html(f'<div class="lgd">{legend}</div><div class="hbars" style="margin-top:.5rem">{"".join(rows)}</div>')
        st.caption("Grey is where each country started. Blue is what the choices around the table cost. "
                   "Orange is ignored sanctions. Green is the terrorist attacks: bad luck.")

    elif part == "How much was luck?":
        st.html('<p class="lede">Keep every decision and sanction from this game, and draw the terrorist attacks again. '
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
                            f'<span class="seg" title="{pct(w[c])} of replays" style="width:{max(w[c] * 100, 0.4):.2f}%;'
                            f'background:{COLORS[c]}"></span></div><div class="hb-v">{pct(w[c])}</div>{mark}</div>')
            st.html(f'<div class="hbars luck">{"".join(rows)}</div>')

    elif part == "The secret rules":
        cols = st.columns(5)
        n = len(done)
        for col, c in zip(cols, sorted(COUNTRIES, key=lambda x: game.gpr[x])):
            with col:
                items = [f'<div class="rules"><div class="cname">{flag(c, 20)}{NAMES[c]}</div>']
                for rid, _, text, _ in RULES_BY_COUNTRY[c]:
                    k = sum(1 for rd in done if any(h[0] == rid for h in rd.hits[c]))
                    items.append(f'<div class="r"><b>+1</b> {text}<br><span class="k" style="color:{"#C00000" if k else "#98A1AF"}">'
                                 f'fired in {k} of {n} {"round" if n == 1 else "rounds"}</span></div>')
                st.html("".join(items) + "</div>")

    else:
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
    left, mid, right = st.columns(3, gap="large")
    with left:
        st.html('<h2 class="vt">This class</h2>')
        label = st.text_input("Class or section", value=game.label, placeholder="e.g. Section 22")
        planned = st.number_input("Rounds planned", min_value=1, max_value=12, value=game.planned, step=1)
        if label != game.label or planned != game.planned:
            game.label, game.planned = label, int(planned)
            st.query_params["g"] = game.to_token()
            st.rerun()
    with mid:
        st.html('<h2 class="vt">During play</h2>')
        st.toggle("Show why each GPR changed", value=prefs["secret"], key="w_secret",
                  on_change=set_pref, args=("secret", "w_secret"),
                  help="Reveals the secret country rules. Leave it off while the room can see the screen.")
        st.toggle("Suspense before the attack result", value=prefs["suspense"], key="w_suspense",
                  on_change=set_pref, args=("suspense", "w_suspense"))
        st.toggle("Explosion when a country is attacked", value=prefs["boom"], key="w_boom",
                  on_change=set_pref, args=("boom", "w_boom"))
    with right:
        st.html('<h2 class="vt">Game</h2>')
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

    with st.expander("Rules for everyone"):
      st.markdown(
        "- **Moves.** Each round the U.S. can go up or down by up to 3 weapons, Russia by 2, "
        "China, India and Pakistan by 1. Nobody goes below 0.\n"
        "- **GPR.** Lower means more powerful. It never goes down: +1 for each rule on your sheet that is tripped, "
        "+4 for a terrorist attack, +2 for ignoring a sanction.\n"
        "- **Attack.** More weapons in the world, higher odds. An attack hits one of the three lowest GPRs: "
        "1 in 2 for the most powerful, 1 in 3 for the second, 1 in 6 for the third. Ties share their chances.\n"
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
