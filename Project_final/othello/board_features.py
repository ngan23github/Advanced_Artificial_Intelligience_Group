"""Đặc trưng của bàn cờ: các hàm THUẦN (chỉ đọc board, không sửa), dùng chung cho Heuristic, Alpha-Beta, MCTS...

Tách riêng để mỗi thứ chỉ định nghĩa MỘT lần ("ô nguy hiểm", "số góc", "độ cơ động"...). Trước đây heuristic_agent
và evaluate_state mỗi nơi tự viết lại logic ô X/C; sửa một nơi là lệch nơi kia.
Mọi hàm nhận `player` và trả về cặp (của player, của đối thủ) hoặc một số theo góc nhìn player.
"""

from configs.constants import C_SQUARES, CORNERS, DANGER_C, DANGER_X, X_SQUARES, XC_PENALTY
from othello.encoding import EMPTY, opponent
from othello.rules import legal_moves


def square_danger(board, pos) -> int:
    """Mức nguy hiểm của ô `pos`: DANGER_X (2) nếu là ô X, DANGER_C (1) nếu là ô C, 0 nếu thường.
    Chỉ nguy hiểm khi GÓC KỀ NÓ CÒN TRỐNG; góc đã có quân thì ô này coi như thường."""
    if pos in X_SQUARES and board[X_SQUARES[pos]] == EMPTY:
        return DANGER_X
    if pos in C_SQUARES and board[C_SQUARES[pos]] == EMPTY:
        return DANGER_C
    return 0


def disc_counts(board, player):
    """(số quân của player, số quân của đối thủ)."""
    return int((board == player).sum()), int((board == opponent(player)).sum())


def corner_counts(board, player):
    """(số góc của player, số góc của đối thủ)."""
    opp = opponent(player)
    mine = sum(1 for r, c in CORNERS if board[r, c] == player)
    theirs = sum(1 for r, c in CORNERS if board[r, c] == opp)
    return mine, theirs


def mobility_counts(board, player):
    """(số nước đi của player, số nước đi của đối thủ) nếu mỗi bên đến lượt."""
    return len(legal_moves(board, player)), len(legal_moves(board, opponent(player)))


def x_c_balance(board, player, penalty=XC_PENALTY) -> float:
    """Điểm ô nguy hiểm: quân của player đứng trên ô X/C nguy hiểm bị trừ, của đối thủ thì được cộng."""
    total = 0.0
    for pos in (*X_SQUARES, *C_SQUARES):
        level = square_danger(board, pos)
        if not level:
            continue
        if board[pos] == player:
            total -= penalty[level]
        elif board[pos] == opponent(player):
            total += penalty[level]
    return total
