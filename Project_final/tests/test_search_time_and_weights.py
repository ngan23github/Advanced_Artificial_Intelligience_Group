"""Test bổ sung cho agent tìm kiếm: lặp sâu theo giờ (Alpha-Beta), trọng số hàm đánh giá, MCTS (giờ, seed, pass)."""

import random
import time

import numpy as np
import pytest

from agents.alphabeta_agent import AlphaBetaAgent
from agents.mcts_agent import MCTSAgent
from othello.encoding import BLACK
from othello.game import OthelloGame


def _position(ply, seed):
    rng, g = random.Random(seed), OthelloGame()
    for _ in range(ply):
        if g.is_terminal():
            break
        g.step(rng.choice(g.legal_actions()))
    return g


def test_alphabeta_rejects_unknown_params_and_weight_keys():
    with pytest.raises(TypeError):
        AlphaBetaAgent(depht=3)                 # gõ sai tên tham số không được im lặng bỏ qua
    with pytest.raises(ValueError):
        AlphaBetaAgent(weights={"mobilty": 1})


def test_alphabeta_time_budget_reaches_depth_and_matches_fixed_depth():
    """Lặp sâu: nước trả về phải đúng bằng nước của tìm kiếm cố định ở độ sâu hoàn chỉnh đã đạt (không dùng tầng dở dang)."""
    for seed in range(4):
        g = _position(14, seed)
        timed = AlphaBetaAgent(depth=1)
        move = timed.select_action(g.clone(), time_budget=0.15)
        reached = timed.stats()["depth"]
        assert reached >= 3
        assert move == AlphaBetaAgent(depth=reached).select_action(g.clone())


def test_alphabeta_tiny_budget_still_legal_and_depth_one_complete():
    g = _position(10, 5)
    a = AlphaBetaAgent()
    assert a.select_action(g, time_budget=1e-9) in g.legal_actions()
    assert a.stats()["depth"] >= 1


def test_alphabeta_solves_endgame_exactly_with_time_budget():
    """Còn ít ô trống: lặp sâu đi hết số ô trống -> nước thắng tuyệt đối, và khớp Minimax thuần đủ sâu."""
    g = _position(50, 11)
    if g.is_terminal():
        g = _position(48, 11)
    empties = int((g.board == 0).sum())
    a = AlphaBetaAgent()
    move = a.select_action(g.clone(), time_budget=5.0)
    assert a.stats()["depth"] == empties
    assert move == AlphaBetaAgent(depth=empties, pruning=False).select_action(g.clone())


def test_alphabeta_weights_change_behaviour():
    """Trọng số phải thật sự đi vào hàm đánh giá (trước đây bị bỏ qua)."""
    changed = 0
    for seed in range(12):
        g = _position(16, seed)
        base = AlphaBetaAgent(depth=2).select_action(g.clone())
        odd = AlphaBetaAgent(depth=2, weights={"disc_diff": 1000.0, "mobility": 0.0, "corners": 0.0,
                                               "x_c_squares": 0.0}).select_action(g.clone())
        changed += base != odd
    assert changed >= 1


def test_mcts_respects_time_budget_and_reports_simulations():
    g = _position(12, 0)
    m = MCTSAgent(seed=0, simulations=10_000_000)
    t0 = time.perf_counter()
    move = m.select_action(g, time_budget=0.2)
    assert time.perf_counter() - t0 < 0.5
    assert move in g.legal_actions()
    assert m.stats()["simulations"] > 10


def test_mcts_reproducible_with_seed_and_exact_simulations():
    g = _position(12, 1)
    a, b = MCTSAgent(simulations=200, seed=7), MCTSAgent(simulations=200, seed=7)
    assert a.select_action(g.clone()) == b.select_action(g.clone())
    assert a.stats()["simulations"] == 200


def test_mcts_takes_forced_win_in_pass_position():
    """Đen chỉ còn 1 nước (0,2) rồi ván kết thúc: MCTS phải trả đúng nước đó (xử lý pass/hết ván trong cây)."""
    board = np.zeros((8, 8), dtype=np.int8)
    board[0, 0], board[0, 1] = BLACK, -BLACK
    g = OthelloGame()
    g.board, g.current_player, g.move_history, g._terminal, g._cache_legal = board, BLACK, [], False, None
    assert MCTSAgent(simulations=30, seed=0).select_action(g) == (0, 2)
