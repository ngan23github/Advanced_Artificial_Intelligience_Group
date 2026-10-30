"""Luật Othello thuần (hàm không có trạng thái): tìm nước hợp lệ và lật quân.

Các hàm ở đây KHÔNG sửa board đầu vào (trừ khi ghi rõ), để thuật toán tìm kiếm
không vô tình làm hỏng trạng thái đang dùng. `game.py` mới là nơi giữ trạng thái.
"""

import numpy as np

from othello.bitboard import bb_to_squares, board_to_bb, flips_mask, legal_mask
from othello.encoding import BOARD_SIZE, DIRECTIONS, EMPTY, opponent


def _in_bounds(r: int, c: int) -> bool:
    return 0 <= r < BOARD_SIZE and 0 <= c < BOARD_SIZE


def flips_for_move(board: np.ndarray, player: int, row: int, col: int) -> list:
    """Danh sách các ô sẽ bị lật nếu `player` đặt quân tại (row, col).

    Trả về list rỗng nếu nước đi không hợp lệ (ô đã có quân hoặc không kẹp được gì).
    """
    if not _in_bounds(row, col) or board[row, col] != EMPTY:
        return []
    enemy = opponent(player)
    flips = []
    for dr, dc in DIRECTIONS:
        r, c = row + dr, col + dc
        line = []
        # đi dọc theo hướng này qua các quân đối thủ liên tiếp
        while _in_bounds(r, c) and board[r, c] == enemy:
            line.append((r, c))
            r += dr
            c += dc
        # chỉ hợp lệ nếu có ít nhất 1 quân đối thủ và kết thúc bằng quân của mình
        if line and _in_bounds(r, c) and board[r, c] == player:
            flips.extend(line)
    return flips


def is_legal_move(board: np.ndarray, player: int, row: int, col: int) -> bool:
    return len(flips_for_move(board, player, row, col)) > 0


def legal_moves(board: np.ndarray, player: int) -> list:
    """Tất cả nước hợp lệ của `player`, sắp theo (row, col) để kết quả tất định.

    Dùng bitboard (othello/bitboard.py) thay cho vòng lặp 64 ô x 8 hướng: nhanh hơn ~25 lần,
    cùng kết quả và cùng thứ tự với bản cũ (test_game_rules + perft kiểm tra).
    """
    black, white = board_to_bb(board)
    me, opp = (black, white) if player == 1 else (white, black)
    return bb_to_squares(legal_mask(me, opp))


def apply_move(board: np.ndarray, player: int, row: int, col: int) -> np.ndarray:
    """Trả về board MỚI sau khi `player` đặt quân tại (row, col).

    Raise ValueError nếu nước đi không hợp lệ.
    """
    if not _in_bounds(row, col) or board[row, col] != EMPTY:
        raise ValueError(f"Nước đi bất hợp lệ: {(row, col)} cho người chơi {player}")
    black, white = board_to_bb(board)
    me, opp = (black, white) if player == 1 else (white, black)
    flips = flips_mask(me, opp, 1 << (row * BOARD_SIZE + col))
    if not flips:
        raise ValueError(f"Nước đi bất hợp lệ: {(row, col)} cho người chơi {player}")
    new_board = board.copy()
    new_board[row, col] = player
    for r, c in bb_to_squares(flips):
        new_board[r, c] = player
    return new_board


def count_discs(board: np.ndarray) -> tuple:
    """(số quân đen, số quân trắng)."""
    return int((board == 1).sum()), int((board == -1).sum())
