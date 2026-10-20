import random
from fractions import Fraction

import pytest

from game import (COUNTRIES, Game, RuleError, attack_probability, hit_shares, replay_luck,
                  START_GPR)


def moves(**kw):
    d = {c: 0 for c in COUNTRIES}
    d.update(kw)
    return d


def test_attack_table_edges():
    assert attack_probability(0) == 0
    assert attack_probability(1) == Fraction(1, 32)
    assert attack_probability(5) == Fraction(1, 32)
    assert attack_probability(6) == Fraction(1, 16)
    assert attack_probability(11) == Fraction(1, 16)
    assert attack_probability(12) == Fraction(1, 8)
    assert attack_probability(18) == Fraction(1, 8)
    assert attack_probability(19) == Fraction(1, 4)
    assert attack_probability(20) == Fraction(1, 4)
    assert attack_probability(27) == Fraction(1, 4)
    assert attack_probability(28) == Fraction(1, 2)
    assert attack_probability(60) == Fraction(1, 2)


def test_sample_game_from_teacher_guide():
    """The three-round sample game in the K=1 teacher guide, number for number."""
    g = Game(seed=1)
    # Round 1: China holds, everyone else +1. No attack. India sanctioned.
    g.submit_moves(moves(IN=1, PK=1, RU=1, US=1))
    assert g.current.total == 24 and g.current.p_attack == Fraction(1, 4)
    g.set_attack(None)
    assert g.gpr == {"US": 1, "RU": 3, "CN": 4, "IN": 5, "PK": 6}
    assert g.nw == {"US": 11, "RU": 6, "CN": 3, "IN": 2, "PK": 2}
    g.impose_sanctions(["IN"])
    assert g.current.sanctioned == ["IN"] and g.current.required == {"IN": -1}
    # Round 2: CN +1, IN +1, PK +1, RU -1, US -3. U.S. attacked. No sanctions.
    g.submit_moves(moves(CN=1, IN=1, PK=1, RU=-1, US=-3))
    g.set_attack("US")
    r = g.completed_rounds[-1]
    assert r.sanction_pts["IN"] == 2                     # India built while sanctioned
    assert r.delta["IN"] == 4 and r.delta["US"] == 6
    assert g.gpr == {"RU": 4, "CN": 4, "PK": 6, "US": 7, "IN": 9}
    assert g.nw == {"RU": 5, "CN": 4, "PK": 3, "US": 8, "IN": 3}
    g.impose_sanctions([])
    # Round 3: everyone holds. Russia attacked.
    g.submit_moves(moves())
    g.set_attack("RU")
    assert g.gpr == {"CN": 4, "PK": 6, "US": 8, "RU": 8, "IN": 10}


def test_everyone_holding_at_the_start_trips_no_rule():
    g = Game(seed=2)
    g.submit_moves(moves())
    g.set_attack(None)
    assert g.gpr == START_GPR


def test_legal_moves_respect_max_and_zero():
    g = Game(seed=3)
    assert g.legal_moves("US") == [-3, -2, -1, 0, 1, 2, 3]
    assert g.legal_moves("RU") == [-2, -1, 0, 1, 2]
    assert g.legal_moves("IN") == [-1, 0, 1]
    g.submit_moves(moves(IN=-1))
    g.set_attack(None)
    g.impose_sanctions([])
    assert g.legal_moves("IN") == [0, 1]                 # cannot go below zero
    with pytest.raises(RuleError):
        g.submit_moves(moves(IN=-1))


def test_country_with_zero_weapons_cannot_be_sanctioned():
    g = Game(seed=4)
    g.submit_moves(moves(PK=-1))                         # Pakistan goes to 0
    g.set_attack(None)
    deciders, candidates, _ = g.sanction_groups()
    assert set(candidates) == {"IN", "PK"}
    assert g.can_be_sanctioned("PK")[0] is False
    assert g.can_be_sanctioned("IN")[0] is True
    with pytest.raises(RuleError):
        g.impose_sanctions(["PK"])
    g.impose_sanctions(["IN"])
    assert g.current.sanctioned == ["IN"]


def test_only_bottom_two_can_be_sanctioned():
    g = Game(seed=5)
    g.submit_moves(moves())
    g.set_attack(None)
    with pytest.raises(RuleError):
        g.impose_sanctions(["US"])


def test_sanction_compliance_is_the_full_cut():
    g = Game(seed=6)
    g.submit_moves(moves()); g.set_attack("US"); g.impose_sanctions([])     # U.S. GPR 1 -> 5
    g.submit_moves(moves()); g.set_attack("US")                             # U.S. GPR 5 -> 9, last place
    deciders, candidates, _ = g.sanction_groups()
    assert set(candidates) == {"PK", "US"}
    g.impose_sanctions(["US"])
    assert g.current.required == {"US": -3}
    g.submit_moves(moves(US=-2))                         # a partial cut is not enough
    g.set_attack(None)
    assert g.completed_rounds[-1].sanction_pts["US"] == 2


def test_required_cut_shrinks_when_stock_is_small():
    g = Game(seed=8)
    g.submit_moves(moves(RU=-2)); g.set_attack("RU"); g.impose_sanctions([])   # Russia 5 -> 3 weapons
    g.submit_moves(moves(RU=-2)); g.set_attack("RU")                           # Russia 3 -> 1 weapon
    assert g.nw["RU"] == 1
    deciders, candidates, _ = g.sanction_groups()
    assert "RU" in candidates
    g.impose_sanctions(["RU"])
    assert g.current.required == {"RU": -1}              # cutting its last weapon is full compliance
    g.submit_moves(moves(RU=-1)); g.set_attack(None)
    assert g.completed_rounds[-1].sanction_pts["RU"] == 0


def test_hit_shares_without_ties():
    s = hit_shares({"US": 1, "CN": 2, "RU": 3, "IN": 5, "PK": 6})
    assert s == {"US": Fraction(1, 2), "CN": Fraction(1, 3), "RU": Fraction(1, 6), "IN": 0, "PK": 0}


def test_hit_shares_with_ties_sum_to_one():
    s = hit_shares({"US": 4, "CN": 4, "RU": 6, "IN": 6, "PK": 9})
    assert s["US"] == s["CN"] == Fraction(5, 12)
    assert s["RU"] == s["IN"] == Fraction(1, 12)
    assert s["PK"] == 0
    assert sum(s.values()) == 1


def test_draw_frequencies_match_the_rules():
    counts = {c: 0 for c in COUNTRIES}
    counts[None] = 0
    rng = random.Random(42)
    n = 40000
    for _ in range(n):
        g = Game(seed=9)
        g.submit_moves(moves())                          # total 20 -> 1/4
        g.draw_attack(rng)
        counts[g.completed_rounds[-1].attack["victim"]] += 1
    assert abs(counts[None] / n - 0.75) < 0.01
    assert abs(counts["US"] / n - 0.125) < 0.01          # 1/4 x 1/2
    assert abs(counts["CN"] / n - 1 / 12) < 0.01         # 1/4 x 1/3
    assert abs(counts["RU"] / n - 1 / 24) < 0.01         # 1/4 x 1/6
    assert counts["IN"] == counts["PK"] == 0


def test_undo_and_token_round_trip():
    g = Game(seed=10, label="Section 22", planned=4)
    g.submit_moves(moves(US=1))
    g.set_attack(None)
    g.impose_sanctions(["PK"])
    token = g.to_token()
    h = Game.from_token(token)
    assert h.gpr == g.gpr and h.phase == "decide" and h.current.sanctioned == ["PK"] and h.label == "Section 22"
    h.undo()
    assert h.phase == "sanctions"
    h.undo(); h.undo()
    assert h.phase == "decide" and h.gpr == START_GPR and h.current.number == 1


def test_end_game_drops_unfinished_round():
    g = Game(seed=11)
    with pytest.raises(RuleError):
        g.end()
    g.submit_moves(moves()); g.set_attack(None); g.impose_sanctions([])
    g.submit_moves(moves(US=1))
    g.end()
    assert g.over and len(g.rounds) == 1 and g.nw["US"] == 10


def test_luck_replay_is_a_distribution():
    g = Game(seed=12)
    for _ in range(4):
        g.submit_moves(moves()); g.set_attack(None); g.impose_sanctions([])
    g.end()
    w = replay_luck(g, runs=2000)
    assert abs(sum(w.values()) - 1) < 1e-9
    assert w["US"] > w["PK"]                             # U.S. starts first, so no attacks keeps it first
