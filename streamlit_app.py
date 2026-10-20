"""Nuclear Diplomacy Simulation: moderator console for the classroom projector.

Run locally with:  streamlit run streamlit_app.py
"""
from __future__ import annotations

import base64
import time
from fractions import Fraction
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

from game import (ATTACK_TABLE, COUNTRIES, attack_probability, MAX_MOVE, NAMES, RULES_BY_COUNTRY, SHORT, START_GPR,
                  START_NW, Game, RuleError, band_label, display_ranks, replay_luck)

st.set_page_config(page_title="Nuclear Diplomacy Simulation", page_icon="☢️", layout="wide")

HERE = Path(__file__).parent
COLORS = {"US": "#2a78d6", "IN": "#eb6834", "PK": "#1baf7a", "CN": "#eda100", "RU": "#e87ba4"}
SOURCE_COLORS = {"Starting GPR": "#c3c2b7", "Rules tripped": "#2a78d6",
                 "Ignored sanctions": "#eb6834", "Terrorist attacks": "#1baf7a"}


@st.cache_data
def flag_uri(c: str) -> str:
    data = (HERE / "assets" / "flags" / f"flag_{c.lower()}.png").read_bytes()
    return "data:image/png;base64," + base64.b64encode(data).decode()


def flag(c: str, h: int = 28) -> str:
    return f'<img src="{flag_uri(c)}" style="height:{h}px;border:1px solid #ddd;border-radius:3px;vertical-align:middle">'


def signed(m: int) -> str:
    return f"+{m}" if m > 0 else (f"−{abs(m)}" if m < 0 else "0")


def odds(p: Fraction) -> str:
    if p == 0:
        return "no chance"
    if p.numerator == 1:
        return f"1 in {p.denominator}"
    return f"{float(p) * 100:.0f}%"


def pct(x: float) -> str:
    if x == 0:
        return "0%"
    return f"{x * 100:.0f}%" if x >= 0.095 else f"{x * 100:.1f}%"


# ----------------------------------------------------------------------------- style
st.markdown("""
<style>
.block-container {padding-top: 2.2rem; padding-bottom: 3rem; max-width: 1500px;}
h1, h2, h3 {letter-spacing: -0.01em;}
.nd-title {display:flex; align-items:baseline; gap:.8rem; flex-wrap:wrap; margin-bottom:.2rem;}
.nd-title .t {font-size:2.1rem; font-weight:800; color:#C00000;}
.nd-title .s {font-size:1.05rem; color:#666;}
.steps {display:flex; gap:.5rem; margin:.4rem 0 1.1rem 0; flex-wrap:wrap;}
.step {padding:.35rem .9rem; border-radius:999px; background:#F1EFEB; color:#777; font-weight:600; font-size:.95rem;}
.step.on {background:#C00000; color:#fff;}
.step.done {background:#E8E4DD; color:#444;}
.board {display:flex; gap:.8rem; flex-wrap:wrap; margin-bottom:.9rem;}
.cty {flex:1 1 170px; min-width:170px; background:#fff; border:1px solid #E4E1DB; border-radius:14px;
      padding:.8rem .9rem .7rem .9rem; position:relative; box-shadow:0 1px 3px rgba(0,0,0,.05);}
.cty.attacked {border:2px solid #C00000; background:#FFF6F6;}
.cty .rank {position:absolute; top:.55rem; right:.7rem; font-weight:800; font-size:1.05rem; color:#999;}
.cty .rank.r1 {color:#C00000;}
.cty .nm {font-weight:700; font-size:1.15rem; margin:.35rem 0 .45rem 0; color:#222;}
.cty .row {display:flex; justify-content:space-between; align-items:baseline; margin:.1rem 0;}
.cty .lbl {color:#777; font-size:.85rem; text-transform:uppercase; letter-spacing:.05em;}
.cty .big {font-size:2rem; font-weight:800; color:#222; line-height:1.1;}
.cty .chg {font-size:.95rem; font-weight:700; margin-left:.35rem;}
.chg.up {color:#C00000;} .chg.down {color:#2E7D32;} .chg.flat {color:#999;}
.chips {display:flex; gap:.3rem; flex-wrap:wrap; margin-top:.45rem; min-height:1.4rem;}
.chip {font-size:.78rem; font-weight:700; padding:.12rem .5rem; border-radius:999px; background:#EEE; color:#444;}
.chip.red {background:#C00000; color:#fff;} .chip.amber {background:#FFE7A8; color:#6B4E00;}
.chip.grey {background:#ECEAE6; color:#555;} .chip.blue {background:#DCEBFB; color:#1C4E8A;}
.world {display:flex; gap:1.2rem; align-items:center; flex-wrap:wrap; background:#F7F5F1; border-radius:14px;
        padding:.8rem 1rem; margin-bottom:1rem;}
.world .tot {font-size:1.05rem; color:#444;} .world .tot b {font-size:2rem; color:#222;}
.bands {display:flex; gap:.3rem; flex-wrap:wrap;}
.band {text-align:center; padding:.3rem .55rem; border-radius:8px; background:#fff; border:1px solid #E4E1DB; min-width:68px;}
.band .r {font-size:.78rem; color:#777;} .band .o {font-size:.95rem; font-weight:700; color:#999;}
.band.on {background:#C00000; border-color:#C00000;} .band.on .r, .band.on .o {color:#fff;}
.banner {border-radius:14px; padding:1rem 1.2rem; margin:.3rem 0 1rem 0; font-size:1.5rem; font-weight:800;}
.banner.hit {background:#C00000; color:#fff;} .banner.calm {background:#E9F4EA; color:#1E5E22;}
.banner .sub {font-size:1rem; font-weight:500; opacity:.92; margin-top:.2rem;}
.drum {font-size:2.4rem; font-weight:800; text-align:center; padding:1.6rem 0; color:#C00000;}
.drum.dim {color:#999;}
.who {font-size:1.05rem; margin:.2rem 0 .6rem 0;}
.small {color:#666; font-size:.9rem;}
.req {color:#8A5A00; font-weight:700; font-size:.9rem;}
button[data-variant="segmented_control"] {min-width:3.4rem;}
button[data-variant="segmented_control"] p {font-size:1.1rem; font-weight:700;}
</style>
""", unsafe_allow_html=True)


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
if st.session_state.pop("restored", False):
    st.toast("Game restored from the link in the address bar.")


# ----------------------------------------------------------------------------- sidebar
EVENT_TEXT = {"moves": "the decisions", "attack": "the attack stage", "sanctions": "the sanctions", "end": "End game"}

with st.sidebar:
    st.markdown("### Moderator")
    label = st.text_input("Class or section", value=game.label, placeholder="e.g. Section 22")
    planned = st.number_input("Rounds planned", min_value=1, max_value=12, value=game.planned, step=1)
    if label != game.label or planned != game.planned:
        game.label, game.planned = label, int(planned)
        st.query_params["g"] = game.to_token()

    secret = st.toggle("Show why each GPR changed", value=False,
                       help="Reveals the secret country rules. Leave it off while the room can see the screen.")
    suspense = st.toggle("Suspense on the attack draw", value=True)

    st.divider()
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

    if game.completed_rounds and not game.over:
        with st.popover("End the game", icon=":material/flag:", width="stretch"):
            st.write("End now and open the debrief? An unfinished round is dropped.")
            if st.button("Yes, end the game", type="primary"):
                game.end()
                save_and_rerun(game)

    with st.popover("New game", icon=":material/restart_alt:", width="stretch"):
        st.write("Start over from the opening table? This game will be cleared.")
        if st.button("Yes, start a new game", type="primary"):
            st.session_state.game = Game(label=game.label, planned=game.planned)
            save_and_rerun(st.session_state.game)

    st.caption("The address bar keeps the whole game. A refresh, or the same link "
               "opened later, brings it back.")

    with st.expander("Rules for everyone"):
        st.markdown(
            "**Moves per round.** U.S. up to 3 weapons up or down, Russia up to 2, "
            "China, India and Pakistan 1. Nobody goes below 0.\n\n"
            "**GPR.** Lower means more powerful. It never goes down. "
            "+1 for each rule on your sheet that is tripped, +4 for a terrorist attack, "
            "+2 for ignoring a sanction.\n\n"
            "**Attack.** More weapons in the world, higher odds. If there is an attack, "
            "it hits one of the three lowest GPRs: 1 in 2, 1 in 3, 1 in 6. Ties are broken by chance.\n\n"
            "**Sanctions.** The three lowest GPRs may sanction one or both of the two highest. "
            "A sanctioned country must cut by its maximum next round or take +2. "
            "**A country with 0 weapons cannot be sanctioned.**")


# ----------------------------------------------------------------------------- header
r = game.current if game.rounds else None
phase = game.phase
title_round = (f"Round {r.number} of {game.planned}" if phase != "over"
               else f"Final, after {len(game.completed_rounds)} rounds")
section = f" &middot; {game.label}" if game.label else ""
st.markdown(f'<div class="nd-title"><span class="t">Nuclear Diplomacy</span>'
            f'<span class="s">{title_round}{section}</span></div>', unsafe_allow_html=True)

view = st.segmented_control("View", ["Game", "History", "Debrief"], default="Game",
                            key="view", label_visibility="collapsed") or "Game"


# ----------------------------------------------------------------------------- pieces
def steps_html(phase: str) -> str:
    names = [("decide", "1  Decisions"), ("attack", "2  Attack"), ("sanctions", "3  Sanctions")]
    idx = {"decide": 0, "attack": 1, "sanctions": 2}.get(phase, 3)
    out = []
    for i, (_, n) in enumerate(names):
        cls = "on" if i == idx else ("done" if i < idx else "")
        out.append(f'<span class="step {cls}">{n}</span>')
    return '<div class="steps">' + "".join(out) + "</div>"


def board_html(nw, gpr, order, d_gpr=None, d_nw=None, chips=None, hit=None) -> str:
    ranks = display_ranks(gpr, order)
    cards = []
    for c in order:
        rk = ranks[c]
        cls = "cty attacked" if chips and any("Attacked" in t for t, _ in chips.get(c, [])) else "cty"
        g_chg = ""
        if d_gpr is not None:
            v = d_gpr[c]
            g_chg = f'<span class="chg {"up" if v > 0 else "flat"}">{"+" + str(v) if v > 0 else "+0"}</span>'
        n_chg = ""
        if d_nw is not None:
            v = d_nw[c]
            n_chg = f'<span class="chg {"up" if v > 0 else ("down" if v < 0 else "flat")}">{signed(v)}</span>'
        chip_html = "".join(f'<span class="chip {k}">{t}</span>' for t, k in (chips or {}).get(c, []))
        hit_html = ""
        if hit is not None and hit[c] > 0:
            hit_html = f'<div class="small">Chance of being hit: <b>{odds(hit[c])}</b></div>'
        cards.append(f"""
<div class="{cls}">
  <div class="rank {'r1' if rk.startswith('1') else ''}">#{rk}</div>
  {flag(c, 30)}
  <div class="nm">{NAMES[c]}</div>
  <div class="row"><span class="lbl">GPR</span><span><span class="big">{gpr[c]}</span>{g_chg}</span></div>
  <div class="row"><span class="lbl">Weapons</span><span><span class="big">{nw[c]}</span>{n_chg}</span></div>
  {hit_html}
  <div class="chips">{chip_html}</div>
</div>""")
    return '<div class="board">' + "".join(cards) + "</div>"


def world_html(total: int, label: str) -> str:
    bands = []
    for lo, hi, p in ATTACK_TABLE:
        on = total >= lo and (hi is None or total <= hi)
        bands.append(f'<div class="band {"on" if on else ""}"><div class="r">{band_label(lo, hi)}</div>'
                     f'<div class="o">{"none" if p == 0 else odds(p)}</div></div>')
    p = attack_probability(total)
    return (f'<div class="world"><div class="tot">{label}<br><b>{total}</b> weapons &nbsp;&middot;&nbsp; '
            f'chance of an attack: <b style="color:#C00000">{odds(p)}</b></div>'
            f'<div class="bands">{"".join(bands)}</div></div>')


def attack_banner(rd) -> str:
    a = rd.attack
    if a["victim"]:
        how = "drawn by the app" if a["by"] == "draw" else "called by the moderator"
        return (f'<div class="banner hit">&#9762; Nuclear terrorist attack on {NAMES[a["victim"]]}'
                f'<div class="sub">{NAMES[a["victim"]]} GPR +4. Odds this round were {odds(rd.p_attack)}; {how}.</div></div>')
    how = "" if a["by"] == "draw" else " (moderator's call)"
    return (f'<div class="banner calm">No attack this round{how}.'
            f'<div class="sub">Odds were {odds(rd.p_attack)} with {rd.total} weapons in the world.</div></div>')


def breakdown(rd):
    """Moderator-only table: why each GPR moved."""
    rows = []
    for c in COUNTRIES:
        parts = [f"+1 {text}" for _, text in rd.hits[c]]
        if rd.sanction_pts[c]:
            parts.append(f"+2 ignored the sanction (had to play {signed(rd.required[c])}, played {signed(rd.moves[c])})")
        if rd.attack_pts[c]:
            parts.append("+4 terrorist attack")
        rows.append({"Country": NAMES[c], "Change": f"+{rd.delta[c]}", "Why": "; ".join(parts) or "nothing tripped"})
    st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")


# ----------------------------------------------------------------------------- views
def view_game():
    if phase == "over":
        last = game.completed_rounds[-1]
        board_chips = {c: [] for c in COUNTRIES}
        st.markdown(board_html(game.nw, game.gpr, last.order_after, chips=board_chips), unsafe_allow_html=True)
        best = min(game.gpr.values())
        top = [NAMES[c] for c in COUNTRIES if game.gpr[c] == best]
        st.markdown(f'<div class="banner calm">Lowest GPR: {" and ".join(top)} ({best})'
                    f'<div class="sub">Open the Debrief view for where the points came from, '
                    f'and how much was luck.</div></div>', unsafe_allow_html=True)
        return

    st.markdown(steps_html(phase), unsafe_allow_html=True)

    # ---------------------------------------------------------------- 1. decisions
    if phase == "decide":
        chips = {c: [] for c in COUNTRIES}
        for c in r.sanctioned:
            chips[c].append((f"Sanctioned: must play {signed(r.required[c])}", "amber"))
        for c in COUNTRIES:
            if game.nw[c] == 0:
                chips[c].append(("0 weapons", "grey"))
        st.markdown(board_html(game.nw, game.gpr, r.order_start, chips=chips), unsafe_allow_html=True)

        st.markdown(f"#### Round {r.number}: enter the five decision slips")
        st.caption("Wait until every slip is in. Nothing is final until you lock it in.")
        chosen = {}
        for c in COUNTRIES:
            a, b, d = st.columns([1.5, 3.2, 2.3], vertical_alignment="center")
            with a:
                st.markdown(f'{flag(c, 24)} &nbsp;<b style="font-size:1.1rem">{NAMES[c]}</b>',
                            unsafe_allow_html=True)
            with b:
                chosen[c] = st.segmented_control(
                    f"{NAMES[c]} move", game.legal_moves(c), format_func=signed,
                    key=f"mv_{game.seed}_{r.number}_{c}", label_visibility="collapsed")
            with d:
                note = ""
                if c in r.sanctioned:
                    note = f'<div class="req">Sanctioned: must play {signed(r.required[c])}</div>'
                if chosen[c] is not None:
                    st.markdown(f'{note}<div class="small">{game.nw[c]} &rarr; <b>{game.nw[c] + chosen[c]}</b> weapon{"" if game.nw[c] + chosen[c] == 1 else "s"}</div>',
                                unsafe_allow_html=True)
                else:
                    st.markdown(f'{note}<div class="small">{game.nw[c]} weapon{"" if game.nw[c] == 1 else "s"} now, moves up to {MAX_MOVE[c]}</div>',
                                unsafe_allow_html=True)
        missing = [SHORT[c] for c in COUNTRIES if chosen[c] is None]
        st.write("")
        if missing:
            st.button("Lock in decisions", type="primary", disabled=True, icon=":material/lock:")
            st.caption("Still waiting for: " + ", ".join(missing))
        else:
            total = sum(game.nw[c] + chosen[c] for c in COUNTRIES)
            st.caption(f"With these moves the world will hold {total} weapons: "
                       f"chance of an attack {odds(attack_probability(total))}.")
            if st.button("Lock in decisions", type="primary", icon=":material/lock:"):
                game.submit_moves(chosen)
                save_and_rerun(game)

    # ---------------------------------------------------------------- 2. attack
    elif phase == "attack":
        d_nw = r.moves
        hit = {c: r.p_attack * r.shares[c] for c in COUNTRIES}
        chips = {c: [] for c in COUNTRIES}
        for c in r.sanctioned:
            ok = r.moves[c] == r.required[c]
            chips[c].append(("Obeyed the sanction" if ok else "Ignored the sanction", "blue" if ok else "amber"))
        st.markdown(board_html(r.nw_after, r.gpr_start, r.order_start, d_nw=d_nw, chips=chips, hit=hit),
                    unsafe_allow_html=True)
        st.markdown(world_html(r.total, "The world now holds"), unsafe_allow_html=True)
        targets = [c for c in r.order_start if r.shares[c] > 0]
        who = " &nbsp;&middot;&nbsp; ".join(f"{flag(c, 18)} {SHORT[c]} <b>{odds(r.shares[c])}</b>" for c in targets)
        st.markdown(f'<div class="who">If there is an attack, it hits one of the three most powerful: {who}</div>',
                    unsafe_allow_html=True)

        stage = st.empty()
        if stage.button("Run the attack draw", type="primary", icon=":material/casino:"):
            game.draw_attack()
            rd = game.current
            if suspense:
                victim = rd.attack["victim"]
                for i in range(7):
                    stage.markdown(f'<div class="drum dim">Is there an attack{"." * (i % 4)}</div>',
                                   unsafe_allow_html=True)
                    time.sleep(0.32)
                if victim:
                    seq = [c for c in rd.order_start if rd.shares[c] > 0]
                    spins = seq * 4
                    while spins[-1] != victim:
                        spins.append(seq[(seq.index(spins[-1]) + 1) % len(seq)])
                    for k, c in enumerate(spins):
                        stage.markdown(f'<div class="drum">&#9762; {NAMES[c]}</div>', unsafe_allow_html=True)
                        time.sleep(0.12 + 0.03 * k)
                    time.sleep(0.6)
            save_and_rerun(game)

        with st.expander("Moderator: call the attack yourself"):
            st.caption("The teacher guide lets the moderator call or skip an attack. Use it if the draw "
                       "should not decide, or if you rolled dice in the room.")
            pick = st.radio("Outcome", ["No attack"] + [NAMES[c] for c in r.order_start], horizontal=True,
                            key=f"manual_{game.seed}_{r.number}")
            if st.button("Apply this outcome"):
                victim = None if pick == "No attack" else next(c for c in COUNTRIES if NAMES[c] == pick)
                game.set_attack(victim)
                save_and_rerun(game)

    # ---------------------------------------------------------------- 3. sanctions
    elif phase == "sanctions":
        chips = {c: [] for c in COUNTRIES}
        if r.attack["victim"]:
            chips[r.attack["victim"]].append(("Attacked +4", "red"))
        for c in r.sanctioned:
            if r.sanction_pts[c]:
                chips[c].append(("Ignored sanction +2", "amber"))
            else:
                chips[c].append(("Obeyed the sanction", "blue"))
        for c in COUNTRIES:
            if r.nw_after[c] == 0:
                chips[c].append(("0 weapons", "grey"))
        st.markdown(attack_banner(r), unsafe_allow_html=True)
        st.markdown(board_html(r.nw_after, r.gpr_after, r.order_after, d_gpr=r.delta, d_nw=r.moves, chips=chips),
                    unsafe_allow_html=True)
        if secret:
            st.markdown("##### Why each GPR changed (secret rules)")
            breakdown(r)

        deciders, candidates, note = game.sanction_groups()
        st.markdown("#### Sanctions")
        dec = " ".join(f"{flag(c, 20)} {SHORT[c]}" for c in deciders)
        st.markdown(f'<div class="who">The three most powerful decide together: {dec}</div>', unsafe_allow_html=True)
        if note:
            st.caption(note)
        st.write("They may sanction one, both, or neither of these two:")
        picks = []
        cols = st.columns(len(candidates) + 2)
        for col, c in zip(cols, candidates):
            ok, why = game.can_be_sanctioned(c)
            with col:
                st.markdown(f"{flag(c, 22)} &nbsp;**{NAMES[c]}**", unsafe_allow_html=True)
                if st.checkbox("Sanction", key=f"sx_{game.seed}_{r.number}_{c}", disabled=not ok):
                    picks.append(c)
                if ok:
                    st.markdown(f'<div class="small">Next round it must play {signed(-min(MAX_MOVE[c], r.nw_after[c]))}, '
                                f'or take +2</div>', unsafe_allow_html=True)
                else:
                    st.markdown(f'<div class="small">{NAMES[c]} {why}.</div>', unsafe_allow_html=True)
        b1, b2, _ = st.columns([1.2, 1, 3])
        with b1:
            if st.button(f"Impose sanctions{' on ' + ' and '.join(SHORT[c] for c in picks) if picks else ''}",
                         type="primary", disabled=not picks, icon=":material/gavel:"):
                game.impose_sanctions(picks)
                save_and_rerun(game)
        with b2:
            if st.button("No sanctions"):
                game.impose_sanctions([])
                save_and_rerun(game)
        if r.number >= game.planned:
            st.info(f"That was round {r.number} of {game.planned}. End the game from the sidebar, "
                    f"or choose sanctions to play another round.", icon=":material/flag:")


def history_frames():
    rounds = game.completed_rounds
    moves_rows, nw_rows, gpr_rows = [], [], []
    nw_rows.append({"Round": "Start", **{SHORT[c]: START_NW[c] for c in COUNTRIES}, "World total": sum(START_NW.values())})
    gpr_rows.append({"Round": "Start", **{SHORT[c]: START_GPR[c] for c in COUNTRIES}})
    for rd in rounds:
        a = rd.attack
        attack = "none" if not a["victim"] else SHORT[a["victim"]]
        if a["by"] == "moderator":
            attack += " (moderator)"
        moves_rows.append({"Round": str(rd.number), **{SHORT[c]: signed(rd.moves[c]) for c in COUNTRIES},
                           "World total": rd.total, "Odds": odds(rd.p_attack), "Attack": attack,
                           "Under sanction": ", ".join(SHORT[c] for c in rd.sanctioned) or "",
                           "Sanctioned next": ", ".join(SHORT[c] for c in (rd.imposed or [])) or ""})
        nw_rows.append({"Round": str(rd.number), **{SHORT[c]: rd.nw_after[c] for c in COUNTRIES}, "World total": rd.total})
        gpr_rows.append({"Round": str(rd.number), **{SHORT[c]: rd.gpr_after[c] for c in COUNTRIES}})
    return pd.DataFrame(moves_rows), pd.DataFrame(nw_rows), pd.DataFrame(gpr_rows)


def line_chart(df: pd.DataFrame, title: str, ytitle: str):
    long = df.melt(id_vars="Round", value_vars=[SHORT[c] for c in COUNTRIES], var_name="Country", value_name="v")
    order = list(df["Round"])
    dom = [SHORT[c] for c in COUNTRIES]
    rng = [COLORS[c] for c in COUNTRIES]
    base = alt.Chart(long).encode(
        x=alt.X("Round:N", sort=order, title="Round", axis=alt.Axis(labelAngle=0, grid=False)),
        y=alt.Y("v:Q", title=ytitle, axis=alt.Axis(tickMinStep=1, gridColor="#EEEEEE")),
        color=alt.Color("Country:N", scale=alt.Scale(domain=dom, range=rng),
                        legend=alt.Legend(orient="top", title=None, labelFontSize=14, symbolStrokeWidth=3)),
        tooltip=["Country", "Round", alt.Tooltip("v:Q", title=ytitle)])
    chart = (base.mark_line(strokeWidth=3) + base.mark_point(size=80, filled=True)).properties(
        title=title, height=320)
    return chart.configure_view(strokeWidth=0).configure_axis(labelFontSize=13, titleFontSize=13,
                                                             domainColor="#BBBBBB", tickColor="#BBBBBB")


def view_history():
    if not game.completed_rounds:
        st.info("No rounds played yet.")
        return
    moves_df, nw_df, gpr_df = history_frames()
    st.markdown("#### Decisions, attacks and sanctions")
    st.dataframe(moves_df, hide_index=True, width="stretch")
    c1, c2 = st.columns(2)
    with c1:
        st.altair_chart(line_chart(gpr_df, "GPR after each round (lower is more powerful)", "GPR"), width="stretch")
        st.dataframe(gpr_df, hide_index=True, width="stretch")
    with c2:
        st.altair_chart(line_chart(nw_df, "Weapons after each round", "Weapons"), width="stretch")
        st.dataframe(nw_df, hide_index=True, width="stretch")

    log = moves_df.merge(nw_df.drop(columns=["World total"]).rename(columns={SHORT[c]: f"{SHORT[c]} weapons" for c in COUNTRIES}),
                         on="Round", how="left")
    log = log.merge(gpr_df.rename(columns={SHORT[c]: f"{SHORT[c]} GPR" for c in COUNTRIES}), on="Round", how="left")
    name = f"nuclear_diplomacy_{(game.label or 'game').replace(' ', '_')}.csv"
    st.download_button("Download the activity log (CSV)", log.to_csv(index=False), file_name=name,
                       mime="text/csv", icon=":material/download:")


def view_debrief():
    rounds = game.completed_rounds
    if not rounds:
        st.info("Play at least one round first.")
        return
    if not game.over and not secret:
        st.info("The debrief shows each country's secret rules. It opens after End game, "
                "or turn on “Show why each GPR changed” in the sidebar to preview it.")
        return

    st.markdown("#### Where each country's GPR points came from")
    rows = []
    for c in COUNTRIES:
        rows += [{"Country": SHORT[c], "Source": "Starting GPR", "Points": START_GPR[c]},
                 {"Country": SHORT[c], "Source": "Rules tripped", "Points": sum(len(rd.hits[c]) for rd in rounds)},
                 {"Country": SHORT[c], "Source": "Ignored sanctions", "Points": sum(rd.sanction_pts[c] for rd in rounds)},
                 {"Country": SHORT[c], "Source": "Terrorist attacks", "Points": sum(rd.attack_pts[c] for rd in rounds)}]
    src = pd.DataFrame(rows)
    order = sorted(COUNTRIES, key=lambda c: game.gpr[c])
    src_order = list(SOURCE_COLORS)
    src["o"] = src["Source"].map({s: i for i, s in enumerate(src_order)})
    bars = alt.Chart(src[src.Points > 0]).mark_bar(height=34, stroke="white", strokeWidth=2).encode(
        y=alt.Y("Country:N", sort=[SHORT[c] for c in order], title=None),
        x=alt.X("sum(Points):Q", title="GPR (lower is more powerful)", axis=alt.Axis(tickMinStep=1, gridColor="#EEEEEE")),
        color=alt.Color("Source:N", scale=alt.Scale(domain=src_order, range=list(SOURCE_COLORS.values())),
                        legend=alt.Legend(orient="top", title=None, labelFontSize=14)),
        order=alt.Order("o:Q"),
        tooltip=["Country", "Source", "Points"])
    totals = pd.DataFrame({"Country": [SHORT[c] for c in COUNTRIES], "GPR": [game.gpr[c] for c in COUNTRIES]})
    labels = alt.Chart(totals).mark_text(align="left", dx=6, fontSize=15, fontWeight="bold", color="#222").encode(
        y=alt.Y("Country:N", sort=[SHORT[c] for c in order]), x="GPR:Q", text="GPR:Q")
    st.altair_chart((bars + labels).properties(height=60 * 5).configure_view(strokeWidth=0)
                    .configure_axis(labelFontSize=14, titleFontSize=13, domainColor="#BBBBBB"), width="stretch")
    st.caption("Grey is where each country started. Blue is what the choices around the table cost. "
               "Orange is ignored sanctions. Green is bad luck.")

    st.markdown("#### How much was luck?")
    st.write("Keep every decision and sanction from this game, and draw the terrorist attacks again. "
             "How often would each country finish with the lowest GPR?")
    if st.button("Replay this game 5,000 times", icon=":material/replay:"):
        st.session_state.luck = (game.to_token(), replay_luck(game, runs=5000, seed=7))
    luck = st.session_state.get("luck")
    if luck and luck[0] == game.to_token():
        w = luck[1]
        df = pd.DataFrame({"Country": [SHORT[c] for c in COUNTRIES], "Share": [w[c] for c in COUNTRIES],
                           "c": COUNTRIES})
        df["Label"] = df["Share"].map(pct)
        actual = min(game.gpr.values())
        df["Label"] = [lab + ("   (finished first in class)" if game.gpr[c] == actual else "")
                       for lab, c in zip(df["Label"], df["c"])]
        sort = list(df.sort_values("Share", ascending=False)["Country"])
        y = alt.Y("Country:N", sort=sort, title=None)
        ch = alt.Chart(df).mark_bar(cornerRadiusEnd=4, height=30).encode(
            y=y,
            x=alt.X("Share:Q", title="Share of replays finishing first", scale=alt.Scale(domain=[0, 1]),
                    axis=alt.Axis(format="%", gridColor="#EEEEEE")),
            color=alt.Color("Country:N", scale=alt.Scale(domain=[SHORT[c] for c in COUNTRIES],
                                                         range=[COLORS[c] for c in COUNTRIES]), legend=None),
            tooltip=["Country", alt.Tooltip("Share:Q", format=".1%")])
        txt = alt.Chart(df).mark_text(align="left", dx=6, fontSize=14, fontWeight="bold", color="#222").encode(
            y=y, x="Share:Q", text="Label:N")
        st.altair_chart((ch + txt).properties(height=260).configure_view(strokeWidth=0)
                        .configure_axis(labelFontSize=14, titleFontSize=13, domainColor="#BBBBBB"), width="stretch")

    st.markdown("#### The secret rules, and how often each one fired")
    cols = st.columns(5)
    n = len(rounds)
    for col, c in zip(cols, sorted(COUNTRIES, key=lambda x: game.gpr[x])):
        with col:
            st.markdown(f"{flag(c, 22)} &nbsp;**{NAMES[c]}**", unsafe_allow_html=True)
            for rid, _, text, _ in RULES_BY_COUNTRY[c]:
                k = sum(1 for rd in rounds if any(h[0] == rid for h in rd.hits[c]))
                st.markdown(f'<div class="small" style="margin:.25rem 0"><b>+1</b> {text}<br>'
                            f'<span style="color:{"#C00000" if k else "#999"}">fired in {k} of {n} rounds</span></div>',
                            unsafe_allow_html=True)

    st.markdown("#### Questions for the room")
    st.markdown(
        "- Did the GPR rules make sense? Which one would you change?\n"
        "- The attack falls on the most powerful. Is that how it works? How would you choose the target?\n"
        "- Where is this game like real nuclear diplomacy, and where is it not?\n"
        "- Did anyone disarm because it was right, or only because of the attack odds?")


if view == "Game":
    view_game()
elif view == "History":
    view_history()
else:
    view_debrief()
