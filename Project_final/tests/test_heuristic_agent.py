"""Test HeuristicAgent: tính đúng đắn của từng luật ưu tiên và cờ ablation.

Chạy: pytest tests/test_heuristic_agent.py
Các vị trí tình huống được dựng bằng chữ: X = Đen, O = Trắng, . = trống (Đen đi).
"""

import random

import numpy as np
import pytest

from agents.heuristic_agent import CORNERS, DEFAULT_PRIORITIES, HeuristicAgent
from othello.encoding import BLACK
from othello.game import OthelloGame

SYM = {"X": 1, "O": -1, ".": 0}
NO_WIN = [r for r in DEFAULT_PRIORITIES if r != "win_now"]   # tắt luật thắng ngay


def game_from_rows(rows, player=BLACK) -> OthelloGame:
    g = OthelloGame()
    g.board = np.array([[SYM[c] for c in row] for row in rows], dtype=np.int8)
    g.current_player = player
    g._terminal, g._cache_legal = False, None
    return g


def random_positions(n, seed=0, max_plies=58):
    """n vị trí chưa kết thúc, sinh bằng chơi ngẫu nhiên (tất định theo seed)."""
    rng, out = random.Random(seed), []
    while len(out) < n:
        g = OthelloGame()
        for _ in range(rng.randint(0, max_plies)):
            if g.is_terminal():
                break
            g.step(rng.choice(g.legal_actions()))
        if not g.is_terminal():
            out.append(g)
    return out


# Vị trí dựng sẵn: nước thắng ngay (2,1) ĐỐI LẬP với nước vào góc (0,0)
WIN_VS_CORNER = [
    ".X.XXXXX",
    "XOXXXX.X",
    "X.XXXXXX",
    "XXXXXXXX",
    "XOXXXXXX",
    "XOXXXXXX",
    "XXXXXXXX",
    "XXXXXXXX",
]
# Nước thắng ngay (6,6) là ô X, đối lập với nước thường (5,7)
WIN_VS_X = [
    "XXXXXXXX",
    "XXXXXXXX",
    "X.XXXXXX",
    "XXXXXXXX",
    "XXXXXXXX",
    "XXXXXXO.",
    "XXOXXX.X",
    "XXXXXXX.",
]


def test_returns_legal_action_and_does_not_mutate_game():
    agent = HeuristicAgent(seed=0)
    for g in random_positions(40, seed=1):
        board, player, hist = g.board.copy(), g.current_player, list(g.move_history)
        action = agent.select_action(g)
        assert action in g.legal_actions()
        assert (g.board == board).all() and g.current_player == player and g.move_history == hist


def test_same_seed_same_moves():
    positions = random_positions(30, seed=2)
    a, b = HeuristicAgent(seed=5), HeuristicAgent(seed=5)
    assert [a.select_action(g) for g in positions] == [b.select_action(g) for g in positions]


def test_win_now_beats_corner():
    g = game_from_rows(WIN_VS_CORNER)
    assert {(2, 1), (0, 0)} <= set(g.legal_actions())
    assert HeuristicAgent(seed=0).select_action(g) == (2, 1)                       # luật 0 > luật 1
    assert HeuristicAgent(seed=0, priorities=NO_WIN).select_action(g) == (0, 0)    # tắt luật 0 -> chiếm góc


def test_win_now_beats_x_square_penalty():
    g = game_from_rows(WIN_VS_X)
    assert {(6, 6), (5, 7)} <= set(g.legal_actions())
    assert HeuristicAgent(seed=0, endgame_empties=0).select_action(g) == (6, 6)
    # tắt luật thắng ngay: ô X bị tránh, chọn nước thường
    assert HeuristicAgent(seed=0, endgame_empties=0, priorities=NO_WIN).select_action(g) == (5, 7)


def test_corner_is_taken_whenever_available():
    agent = HeuristicAgent(seed=0, endgame_empties=0, priorities=NO_WIN)
    seen = 0
    for g in random_positions(300, seed=3):
        corners = [a for a in g.legal_actions() if a in CORNERS]
        if corners:
            seen += 1
            assert agent.select_action(g) in corners
    assert seen >= 5   # đảm bảo test không rỗng


def test_avoids_x_and_c_when_no_corner_available():
    agent = HeuristicAgent(seed=0, endgame_empties=0, priorities=NO_WIN)
    seen_bad = 0
    for g in random_positions(300, seed=4):
        acts = g.legal_actions()
        if any(a in CORNERS for a in acts):
            continue
        danger = {a: HeuristicAgent._danger(g.board, a) for a in acts}
        if max(danger.values()) > 0:
            seen_bad += 1
        assert danger[agent.select_action(g)] == min(danger.values())
    assert seen_bad >= 5


def test_endgame_mode_maximises_discs():
    agent = HeuristicAgent(seed=0, endgame_empties=64, priorities=NO_WIN)   # luôn ở chế độ cuối ván
    for g in random_positions(60, seed=6):
        acts = g.legal_actions()
        if any(a in CORNERS for a in acts):
            continue
        counts = {}
        for a in acts:
            after = g.clone().step(a).board
            counts[a] = int((after == g.current_player).sum())
        assert counts[agent.select_action(g)] == max(counts.values())


def test_all_rules_off_still_legal_and_varied():
    g = OthelloGame()
    picks = {HeuristicAgent(seed=s, priorities=[]).select_action(g) for s in range(30)}
    assert picks <= set(g.legal_actions()) and len(picks) > 1


def test_stats_and_tree():
    agent = HeuristicAgent(seed=0)
    g = random_positions(1, seed=7)[0]
    action = agent.select_action(g)
    n = len(g.legal_actions())
    assert agent.stats()["nodes"] == n
    tree = agent.search_tree()
    assert len(tree["children"]) == n
    best = [c for c in tree["children"] if c["best"]]
    assert len(best) == 1 and best[0]["move"] == action


@pytest.mark.parametrize("kw", [{}, {"priorities": ["maximize_discs"]}, {"endgame_empties": 0}])
def test_full_game_runs_to_the_end(kw):
    a, b = HeuristicAgent(seed=1, **kw), HeuristicAgent(seed=2)
    g = OthelloGame()
    agents = {1: a, -1: b}
    while not g.is_terminal():
        g.step(agents[g.current_player].select_action(g.clone()))
    assert g.is_terminal()


def test_priorities_from_yaml_style_list_and_validation():
    # đúng như khai báo trong configs/agents.yaml: list (cũng nhận tuple), tên sai/trùng bị từ chối
    HeuristicAgent(priorities=("take_corner", "avoid_x_square", "maximize_discs"))
    with pytest.raises(ValueError):
        HeuristicAgent(priorities=["take_corner", "no_such_rule"])
    with pytest.raises(ValueError):
        HeuristicAgent(priorities=["take_corner", "take_corner"])


def test_discs_only_ablation_maximises_discs():
    agent = HeuristicAgent(seed=0, endgame_empties=0, priorities=["maximize_discs"])
    for g in random_positions(60, seed=8):
        counts = {a: int((g.clone().step(a).board == g.current_player).sum()) for a in g.legal_actions()}
        assert counts[agent.select_action(g)] == max(counts.values())


def test_priority_order_matters():
    default = HeuristicAgent(seed=0, endgame_empties=0, priorities=NO_WIN)
    mob_first = HeuristicAgent(seed=0, endgame_empties=0,
                               priorities=["maximize_mobility", "take_corner", "avoid_x_square", "avoid_c_square"])
    diff = sum(default.select_action(g) != mob_first.select_action(g) for g in random_positions(200, seed=9))
    assert diff > 0
