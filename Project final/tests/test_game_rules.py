import numpy as np
import pytest

from othello.encoding import BLACK, EMPTY, WHITE, initial_board
from othello.game import IllegalMoveError, OthelloGame
from othello.rules import apply_move, flips_for_move, legal_moves


def make_game(rows, player):
    """Tạo game từ 8 chuỗi ký hiệu: X=đen, O=trắng, .=trống."""
    m = {"X": BLACK, "O": WHITE, ".": EMPTY}
    g = OthelloGame()
    g.board = np.array([[m[ch] for ch in row] for row in rows], dtype=np.int8)
    g.current_player = player
    g._terminal = False
    g._cache_legal = None
    # dùng cùng logic kết thúc/pass của engine để dựng trạng thái nhất quán
    if not legal_moves(g.board, player):
        g._advance_turn(-player)
    return g


def test_initial_position():
    g = OthelloGame()
    assert g.score() == (2, 2)
    assert g.current_player == BLACK
    assert g.board[3, 3] == WHITE and g.board[4, 4] == WHITE
    assert g.board[3, 4] == BLACK and g.board[4, 3] == BLACK


def test_initial_legal_moves_black():
    g = OthelloGame()
    assert sorted(g.legal_actions()) == [(2, 3), (3, 2), (4, 5), (5, 4)]


def test_step_flips_and_switches_player():
    g = OthelloGame()
    g.step((2, 3))  # đen đặt (2,3) kẹp (3,3)
    assert g.board[2, 3] == BLACK and g.board[3, 3] == BLACK
    assert g.score() == (4, 1)
    assert g.current_player == WHITE


def test_illegal_move_rejected_and_state_unchanged():
    g = OthelloGame()
    before = g.board.copy()
    for bad in [(0, 0), (3, 3), (7, 7)]:
        with pytest.raises(IllegalMoveError):
            g.step(bad)
    assert np.array_equal(g.board, before)
    assert g.current_player == BLACK


def test_apply_move_does_not_mutate_input():
    b = initial_board()
    before = b.copy()
    nb = apply_move(b, BLACK, 2, 3)
    assert np.array_equal(b, before)
    assert not np.array_equal(nb, before)


def test_flips_multiple_directions():
    # Bàn dựng tay (hàng 3: ". . . O O X", cột 3: O ở hàng 3-4, X ở hàng 5):
    #   (3,2): hướng phải kẹp (3,3),(3,4) tới X ở (3,5)
    #   (2,3): hướng xuống kẹp (3,3),(4,3) tới X ở (5,3)
    g = make_game(
        [
            "........",
            "........",
            "........",
            "...OOX..",
            "...O....",
            "...X....",
            "........",
            "........",
        ],
        BLACK,
    )
    assert set(flips_for_move(g.board, BLACK, 3, 2)) == {(3, 3), (3, 4)}
    assert set(flips_for_move(g.board, BLACK, 2, 3)) == {(3, 3), (4, 3)}
    # ô xa, không kẹp được gì thì không hợp lệ
    assert flips_for_move(g.board, BLACK, 0, 0) == []
    # sau khi đi (3,2) thì engine lật đúng 2 quân
    g.step((3, 2))
    assert (g.board[3, 2:6] == BLACK).all()


def test_clone_is_independent():
    g = OthelloGame()
    c = g.clone()
    c.step(c.legal_actions()[0])
    assert g.score() == (2, 2)
    assert len(g.move_history) == 0
    assert len(c.move_history) == 1


def test_game_ends_when_nobody_can_move():
    # Sau nước đi, cả hai bên đều không còn nước hợp lệ -> ván kết thúc.
    g = make_game(
        [
            "XO......",
            "........",
            "........",
            "........",
            "........",
            "........",
            "........",
            "........",
        ],
        BLACK,
    )
    # Đen đặt (0,2) lật (0,1) -> chỉ còn quân đen -> trắng hết quân, không ai đi được.
    g.step((0, 2))
    assert g.is_terminal()
    assert g.result(BLACK) == 1
    assert g.result(WHITE) == -1


def test_white_must_pass_black_continues():
    g = make_game(
        [
            "OXXXXXXX",
            "........",
            "........",
            "........",
            "........",
            "........",
            "........",
            "XO......",
        ],
        WHITE,
    )
    # Trắng có nước hợp lệ?  (0,0)=O đã có; hàng 7: X O . ... trắng đặt không kẹp được ai.
    # Trắng không đi được, đen có thể đi (7,2) kẹp (7,1). Engine phải chuyển lượt cho đen.
    assert g.current_player == BLACK
    assert (7, 2) in g.legal_actions()


def test_terminal_draw():
    g = OthelloGame()
    g.board = np.zeros((8, 8), dtype=np.int8)
    g.board[:4, :] = BLACK
    g.board[4:, :] = WHITE
    g._terminal = True
    assert g.result(BLACK) == 0 and g.result(WHITE) == 0


def test_result_before_end_raises():
    with pytest.raises(RuntimeError):
        OthelloGame().result()


def test_no_actions_after_terminal():
    g = OthelloGame()
    g._terminal = True
    assert g.legal_actions() == []
    with pytest.raises(IllegalMoveError):
        g.step((2, 3))
