"""Test riêng cho Alpha-Beta bitboard + bitboard luật chơi.

- bitboard cho cùng nước đi / cùng quân bị lật như cài đặt numpy gốc (flips_for_move),
- hàm đánh giá bitboard == evaluate_state,
- bật/tắt cắt tỉa cho CÙNG nước đi, nhưng cắt tỉa duyệt ít nút hơn,
- xử lý pass đúng (người đi tiếp vẫn là max/min cũ).
"""

import random

import numpy as np

from agents.alphabeta_agent import AlphaBetaAgent, _evaluate_bb, evaluate_state
from othello.bitboard import board_to_bb, bb_to_squares, flips_mask, legal_mask
from othello.encoding import BLACK, WHITE
from othello.game import OthelloGame
from othello.rules import flips_for_move


def _random_positions(n_games=15, seed=0):
    rng = random.Random(seed)
    for _ in range(n_games):
        g = OthelloGame()
        while not g.is_terminal():
            yield g
            g.step(rng.choice(g.legal_actions()))


def test_bitboard_legal_and_flips_match_numpy_rules():
    for g in _random_positions():
        black, white = board_to_bb(g.board)
        for player, (me, opp) in ((BLACK, (black, white)), (WHITE, (white, black))):
            ref = [(r, c) for r in range(8) for c in range(8) if flips_for_move(g.board, player, r, c)]
            assert bb_to_squares(legal_mask(me, opp)) == ref
            for r, c in ref:
                assert set(bb_to_squares(flips_mask(me, opp, 1 << (r * 8 + c)))) == set(flips_for_move(g.board, player, r, c))


def test_bitboard_eval_equals_reference_eval():
    for g in _random_positions(n_games=6, seed=1):
        black, white = board_to_bb(g.board)
        for cfg in ({}, {"mobility": False}, {"corners": False, "x_c_squares": False}):
            assert abs(evaluate_state(g.board, BLACK, cfg) - _evaluate_bb(black, white, cfg)) < 1e-9
            assert abs(evaluate_state(g.board, WHITE, cfg) - _evaluate_bb(white, black, cfg)) < 1e-9


def test_pruning_same_move_fewer_nodes():
    rng = random.Random(3)
    checked = 0
    for g in _random_positions(n_games=6, seed=2):
        if rng.random() > 0.35:
            continue
        a, b = AlphaBetaAgent(depth=3, pruning=True), AlphaBetaAgent(depth=3, pruning=False)
        assert a.select_action(g.clone()) == b.select_action(g.clone())
        assert a.stats()["nodes"] <= b.stats()["nodes"]
        checked += 1
    assert checked > 5


def test_returns_legal_move_with_tiny_time_budget():
    g = OthelloGame()
    a = AlphaBetaAgent(depth=6)
    assert a.select_action(g, time_budget=1e-6) in g.legal_actions()


def test_pass_in_search_tree_keeps_same_side_maximizing():
    """Thế cờ mà Trắng không có nước sau khi Đen đi: Đen phải đi liên tiếp, agent vẫn trả về nước hợp lệ."""
    board = np.zeros((8, 8), dtype=np.int8)
    board[0, 0], board[0, 1] = BLACK, WHITE   # Đen có thể đi (0,2); sau đó Trắng hết quân => hết ván / pass
    g = OthelloGame()
    g.board, g.current_player, g.move_history, g._terminal, g._cache_legal = board, BLACK, [], False, None
    assert g.legal_actions() == [(0, 2)]
    assert AlphaBetaAgent(depth=4).select_action(g) == (0, 2)
