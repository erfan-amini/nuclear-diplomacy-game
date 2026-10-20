"""Game engine for the Nuclear Diplomacy Simulation (K=1 Project, Columbia University).

The game is stored as a short log of events. Every number on screen is rebuilt by
replaying that log, so undo means "drop the last event" and a page refresh can
restore the game from the log kept in the URL.

Rules follow the K=1 Project teacher guide, the general student instructions and the
five country sheets. Choices the instructor made where the sources are silent:
- a country with 0 weapons cannot be sanctioned (it can still be attacked);
- a GPR tie across the sanction line (ranks 3 and 4) is broken at random;
- tied countries share their attack-victim chances equally.
"""
from __future__ import annotations

import base64
import json
import random
import zlib
from dataclasses import dataclass, field
from fractions import Fraction

# ----------------------------------------------------------------------------- setup
COUNTRIES = ["CN", "IN", "PK", "RU", "US"]
NAMES = {"CN": "China", "IN": "India", "PK": "Pakistan", "RU": "Russia", "US": "United States"}
SHORT = {"CN": "China", "IN": "India", "PK": "Pakistan", "RU": "Russia", "US": "U.S."}
MAX_MOVE = {"CN": 1, "IN": 1, "PK": 1, "RU": 2, "US": 3}
START_NW = {"CN": 3, "IN": 1, "PK": 1, "RU": 5, "US": 10}
START_GPR = {"CN": 2, "IN": 5, "PK": 6, "RU": 3, "US": 1}

ATTACK_POINTS = 4
SANCTION_POINTS = 2
SLOT_CHANCE = [Fraction(1, 2), Fraction(1, 3), Fraction(1, 6), Fraction(0), Fraction(0)]

# Attack probability by total NW count: (lowest total, highest total, probability)
ATTACK_TABLE = [
    (0, 0, Fraction(0)),
    (1, 5, Fraction(1, 32)),
    (6, 11, Fraction(1, 16)),
    (12, 18, Fraction(1, 8)),
    (19, 27, Fraction(1, 4)),
    (28, None, Fraction(1, 2)),
]


def attack_probability(total: int) -> Fraction:
    for lo, hi, p in ATTACK_TABLE:
        if total >= lo and (hi is None or total <= hi):
            return p
    raise ValueError(f"bad total {total}")


def band_label(lo: int, hi: int | None) -> str:
    if hi is None:
        return f"{lo}+"
    return str(lo) if lo == hi else f"{lo}-{hi}"


# ----------------------------------------------------------------------------- secret rules
# Each rule: (id, country, text shown at the debrief, test(nw_after, moves) -> bool)
def _up(moves, c):
    return moves[c] > 0


RULES = [
    ("CN1", "CN", "India has more weapons than Pakistan", lambda n, m: n["IN"] > n["PK"]),
    ("CN2", "CN", "India has as many weapons as China, or more", lambda n, m: n["IN"] >= n["CN"]),
    ("CN3", "CN", "The U.S. built and China did not", lambda n, m: _up(m, "US") and not _up(m, "CN")),
    ("CN4", "CN", "Russia built and China did not", lambda n, m: _up(m, "RU") and not _up(m, "CN")),

    ("IN1", "IN", "China built", lambda n, m: _up(m, "CN")),
    ("IN2", "IN", "Pakistan has more weapons than India", lambda n, m: n["PK"] > n["IN"]),
    ("IN3", "IN", "Pakistan and China together have more weapons than Russia", lambda n, m: n["PK"] + n["CN"] > n["RU"]),

    ("PK1", "PK", "India has more weapons than Pakistan", lambda n, m: n["IN"] > n["PK"]),
    ("PK2", "PK", "Pakistan has as many weapons as China, or more", lambda n, m: n["PK"] >= n["CN"]),
    ("PK3", "PK", "India has more weapons than China", lambda n, m: n["IN"] > n["CN"]),

    ("RU1", "RU", "Pakistan has more weapons than India", lambda n, m: n["PK"] > n["IN"]),
    ("RU2", "RU", "China, India or Pakistan has more weapons than Russia",
     lambda n, m: any(n[x] > n["RU"] for x in ("CN", "IN", "PK"))),
    ("RU3", "RU", "The U.S. built and Russia did not", lambda n, m: _up(m, "US") and not _up(m, "RU")),
    ("RU4", "RU", "China built and Russia did not", lambda n, m: _up(m, "CN") and not _up(m, "RU")),

    ("US1", "US", "Pakistan has more than 2 weapons", lambda n, m: n["PK"] > 2),
    ("US2", "US", "Another country has more weapons than the U.S.",
     lambda n, m: any(n[x] > n["US"] for x in ("CN", "IN", "PK", "RU"))),
    ("US3", "US", "Russia built and the U.S. did not", lambda n, m: _up(m, "RU") and not _up(m, "US")),
    ("US4", "US", "China built and the U.S. did not", lambda n, m: _up(m, "CN") and not _up(m, "US")),
]
RULES_BY_COUNTRY = {c: [r for r in RULES if r[1] == c] for c in COUNTRIES}


def rule_hits(nw_after: dict, moves: dict) -> dict:
    """Rules that fire this round, per country: {c: [(rule_id, text), ...]}. Each is +1."""
    hits = {c: [] for c in COUNTRIES}
    for rid, c, text, test in RULES:
        if test(nw_after, moves):
            hits[c].append((rid, text))
    return hits


# ----------------------------------------------------------------------------- ranking helpers
def tiebreak_keys(seed: int, state_index: int) -> dict:
    """A fixed random order used only to separate countries with equal GPR."""
    rng = random.Random(f"{seed}:{state_index}")
    return {c: rng.random() for c in COUNTRIES}


def ranking(gpr: dict, keys: dict) -> list:
    """Most powerful first: lowest GPR, ties separated by the random keys."""
    return sorted(COUNTRIES, key=lambda c: (gpr[c], keys[c]))


def display_ranks(gpr: dict, order: list) -> dict:
    """Rank labels for the table; tied countries share a rank, e.g. '2='."""
    labels = {}
    for i, c in enumerate(order):
        first = next(j for j, x in enumerate(order) if gpr[x] == gpr[c])
        tied = sum(1 for x in COUNTRIES if gpr[x] == gpr[c]) > 1
        labels[c] = f"{first + 1}{'=' if tied else ''}"
    return labels


def hit_shares(gpr: dict) -> dict:
    """Chance of being the victim IF there is an attack.

    1/2, 1/3, 1/6 for the three lowest GPRs. Countries tied on GPR share their
    slots equally, which is what re-rolling the die for ties does on average.
    """
    order = sorted(COUNTRIES, key=lambda c: gpr[c])
    shares = {}
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and gpr[order[j + 1]] == gpr[order[i]]:
            j += 1
        group = order[i:j + 1]
        pooled = sum(SLOT_CHANCE[i:j + 1], Fraction(0))
        for c in group:
            shares[c] = pooled / len(group)
        i = j + 1
    return shares


# ----------------------------------------------------------------------------- records
@dataclass
class Round:
    number: int
    nw_start: dict
    gpr_start: dict
    order_start: list                      # ranking used for the attack stage
    sanctioned: list                       # countries under sanction during this round
    moves: dict | None = None
    nw_after: dict | None = None
    total: int | None = None
    p_attack: Fraction | None = None
    shares: dict | None = None             # chance of being hit if there is an attack
    attack: dict | None = None             # {"victim": c or None, "by": "draw"|"moderator", "u": .., "v": ..}
    hits: dict | None = None               # rule hits per country
    sanction_pts: dict | None = None       # +2 for ignoring a sanction
    attack_pts: dict | None = None
    delta: dict | None = None
    gpr_after: dict | None = None
    order_after: list | None = None        # ranking used for the sanction stage
    imposed: list | None = None            # sanctions imposed at the end of this round

    @property
    def required(self) -> dict:
        """Move each sanctioned country must make: cut by the most it can."""
        return {c: -min(MAX_MOVE[c], self.nw_start[c]) for c in self.sanctioned}


def _join(items: list) -> str:
    return items[0] if len(items) == 1 else ", ".join(items[:-1]) + " and " + items[-1]


class RuleError(ValueError):
    pass


@dataclass
class Game:
    seed: int = field(default_factory=lambda: random.SystemRandom().randrange(10**9))
    label: str = ""
    planned: int = 5
    events: list = field(default_factory=list)

    # ------------------------------------------------------------------ replay
    def __post_init__(self):
        self._replay()

    def _replay(self):
        self.nw = dict(START_NW)
        self.gpr = dict(START_GPR)
        self.rounds: list[Round] = []
        self.over = False
        self._open_round(sanctioned=[])
        for ev in self.events:
            self._apply(ev)

    def _open_round(self, sanctioned):
        n = len(self.rounds) + 1
        keys = tiebreak_keys(self.seed, n - 1)
        self.rounds.append(Round(number=n, nw_start=dict(self.nw), gpr_start=dict(self.gpr),
                                 order_start=ranking(self.gpr, keys), sanctioned=list(sanctioned)))

    @property
    def current(self) -> Round:
        return self.rounds[-1]

    @property
    def phase(self) -> str:
        if self.over:
            return "over"
        r = self.current
        if r.moves is None:
            return "decide"
        if r.attack is None:
            return "attack"
        return "sanctions"

    @property
    def completed_rounds(self) -> list:
        return [r for r in self.rounds if r.gpr_after is not None]

    # ------------------------------------------------------------------ queries
    def legal_moves(self, c: str) -> list:
        lo = -min(MAX_MOVE[c], self.nw[c])
        return list(range(lo, MAX_MOVE[c] + 1))

    def sanction_groups(self):
        """(deciders, candidates, note). Only valid in the sanctions phase."""
        r = self.current
        order = r.order_after
        deciders, candidates = order[:3], order[3:]
        note = None
        g = r.gpr_after
        if g[order[2]] == g[order[3]]:
            tied = [c for c in order if g[c] == g[order[2]]]
            inside = [c for c in tied if c in deciders]
            note = (f"{_join([SHORT[c] for c in tied])} are tied on GPR {g[order[2]]}. "
                    f"A random tie-break put {_join([SHORT[c] for c in inside])} in the top three.")
        return deciders, candidates, note

    def can_be_sanctioned(self, c: str) -> tuple[bool, str]:
        deciders, candidates, _ = self.sanction_groups()
        if c not in candidates:
            return False, "not one of the two weakest countries"
        if self.current.nw_after[c] == 0:
            return False, "has 0 weapons, so it cannot be sanctioned"
        return True, ""

    # ------------------------------------------------------------------ actions
    def submit_moves(self, moves: dict):
        self._push({"t": "moves", "m": [moves[c] for c in COUNTRIES]})

    def draw_attack(self, rng: random.Random | None = None):
        """Let the app decide: one draw for 'attack or not', one for the victim."""
        rng = rng or random.SystemRandom()
        r = self.current
        if self.phase != "attack":
            raise RuleError("not in the attack stage")
        u = rng.random()
        victim = None
        v = None
        if u < float(r.p_attack):
            v = rng.random()
            acc = 0.0
            for c in r.order_start:                       # walk the ranking; tied countries share slots
                acc += float(r.shares[c])
                if v < acc:
                    victim = c
                    break
            if victim is None:                            # float edge case
                victim = max(COUNTRIES, key=lambda c: r.shares[c])
        self._push({"t": "attack", "victim": victim, "by": "draw", "u": round(u, 6),
                    "v": None if v is None else round(v, 6)})

    def set_attack(self, victim: str | None):
        """The moderator calls the attack (the teacher guide allows this)."""
        self._push({"t": "attack", "victim": victim, "by": "moderator"})

    def impose_sanctions(self, targets: list):
        self._push({"t": "sanctions", "s": sorted(targets)})

    def end(self):
        self._push({"t": "end"})

    def undo(self):
        if not self.events:
            return
        self.events.pop()
        self._replay()

    def _push(self, ev: dict):
        self._apply(ev)              # raises before the event is stored if it breaks a rule
        self.events.append(ev)

    # ------------------------------------------------------------------ the rules
    def _apply(self, ev: dict):
        if self.over:
            raise RuleError("the game is over")
        t = ev["t"]
        r = self.current
        if t == "end":
            if not self.completed_rounds:
                raise RuleError("play at least one round first")
            self.over = True
            if r.attack is None:                      # drop a round that has not reached the GPR update
                self.rounds.pop()
            return

        if t == "moves":
            if self.phase != "decide":
                raise RuleError("decisions are already in for this round")
            if len(ev["m"]) != len(COUNTRIES) or any(not float(m).is_integer() for m in ev["m"]):
                raise RuleError("each country needs one whole-number move")
            moves = dict(zip(COUNTRIES, (int(m) for m in ev["m"])))
            for c in COUNTRIES:
                if moves[c] not in self.legal_moves(c):
                    raise RuleError(f"{NAMES[c]} cannot move {moves[c]:+d}")
            r.moves = moves
            r.nw_after = {c: self.nw[c] + moves[c] for c in COUNTRIES}
            r.total = sum(r.nw_after.values())
            r.p_attack = attack_probability(r.total)
            r.shares = hit_shares(r.gpr_start)
            return

        if t == "attack":
            if self.phase != "attack":
                raise RuleError("not in the attack stage")
            victim = ev.get("victim")
            if victim is not None and victim not in COUNTRIES:
                raise RuleError(f"unknown country {victim}")
            r.attack = dict(ev)
            # GPR update
            r.hits = rule_hits(r.nw_after, r.moves)
            r.sanction_pts = {c: (SANCTION_POINTS if c in r.sanctioned and r.moves[c] != r.required[c] else 0)
                              for c in COUNTRIES}
            r.attack_pts = {c: (ATTACK_POINTS if c == victim else 0) for c in COUNTRIES}
            r.delta = {c: len(r.hits[c]) + r.sanction_pts[c] + r.attack_pts[c] for c in COUNTRIES}
            self.nw = dict(r.nw_after)
            self.gpr = {c: self.gpr[c] + r.delta[c] for c in COUNTRIES}
            r.gpr_after = dict(self.gpr)
            r.order_after = ranking(self.gpr, tiebreak_keys(self.seed, r.number))
            return

        if t == "sanctions":
            if self.phase != "sanctions":
                raise RuleError("not in the sanctions stage")
            targets = list(ev["s"])
            if len(set(targets)) != len(targets):
                raise RuleError("a country is listed twice")
            for c in targets:
                if c not in COUNTRIES:
                    raise RuleError(f"unknown country {c}")
                ok, why = self.can_be_sanctioned(c)
                if not ok:
                    raise RuleError(f"{NAMES[c]} cannot be sanctioned: {why}")
            r.imposed = sorted(targets)
            self._open_round(sanctioned=r.imposed)
            return

        raise RuleError(f"unknown event {t}")

    # ------------------------------------------------------------------ save / restore
    def to_dict(self) -> dict:
        return {"v": 1, "seed": self.seed, "label": self.label, "planned": self.planned, "ev": self.events}

    @classmethod
    def from_dict(cls, d: dict) -> "Game":
        return cls(seed=int(d["seed"]), label=d.get("label", ""), planned=int(d.get("planned", 5)),
                   events=list(d.get("ev", [])))

    def to_token(self) -> str:
        raw = json.dumps(self.to_dict(), separators=(",", ":")).encode()
        return base64.urlsafe_b64encode(zlib.compress(raw, 9)).decode().rstrip("=")

    @classmethod
    def from_token(cls, token: str) -> "Game":
        pad = "=" * (-len(token) % 4)
        return cls.from_dict(json.loads(zlib.decompress(base64.urlsafe_b64decode(token + pad))))


# ----------------------------------------------------------------------------- luck check
def replay_luck(game: Game, runs: int = 5000, seed: int = 0) -> dict:
    """Replay the class's own choices with fresh attack draws.

    Rule points and sanction points depend only on the moves, so they are fixed.
    Only the attacks change; each run picks victims from the GPR ranking as it
    stands in that run. Returns the share of runs each country finishes with the
    lowest GPR (ties split).
    """
    rounds = game.completed_rounds
    rng = random.Random(seed)
    wins = {c: 0.0 for c in COUNTRIES}
    for _ in range(runs):
        g = dict(START_GPR)
        for r in rounds:
            base = {c: len(r.hits[c]) + r.sanction_pts[c] for c in COUNTRIES}
            victim = None
            if rng.random() < float(r.p_attack):
                shares = hit_shares(g)
                v, acc = rng.random(), 0.0
                for c in sorted(COUNTRIES, key=lambda x: (g[x], rng.random())):
                    acc += float(shares[c])
                    if v < acc:
                        victim = c
                        break
            for c in COUNTRIES:
                g[c] += base[c] + (ATTACK_POINTS if c == victim else 0)
        best = min(g.values())
        winners = [c for c in COUNTRIES if g[c] == best]
        for c in winners:
            wins[c] += 1 / len(winners)
    return {c: wins[c] / runs for c in COUNTRIES}
