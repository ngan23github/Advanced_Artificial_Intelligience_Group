"""Perft: đếm số nút lá ở độ sâu d từ vị trí đầu, so với dãy chuẩn Othello 8x8.

Dãy chuẩn: 4, 12, 56, 244, 1396, 8200, 55092, 390216, ...
(Các giá trị đầu không bị ảnh hưởng bởi pass nên khớp với engine tự xử lý pass.)
"""

import pytest

from othello.game import OthelloGame

EXPECTED = {1: 4, 2: 12, 3: 56, 4: 244, 5: 1396, 6: 8200}
EXPECTED_SLOW = {7: 55092}


def perft(game: OthelloGame, depth: int) -> int:
    if depth == 0 or game.is_terminal():
        return 1
    total = 0
    for a in game.legal_actions():
        child = game.clone()
        child.step(a)
        total += perft(child, depth - 1)
    return total


@pytest.mark.parametrize("depth,expected", sorted(EXPECTED.items()))
def test_perft(depth, expected):
    assert perft(OthelloGame(), depth) == expected


@pytest.mark.slow
def test_perft_depth7():
    assert perft(OthelloGame(), 7) == EXPECTED_SLOW[7]
