"""Hằng số và quy ước mã hóa cho Othello 8x8.

Cả nhóm dùng chung file này; KHÔNG tự định nghĩa lại hằng số ở nơi khác.

Quy ước:
- Board: numpy array int8 shape (8, 8).
- Ô: EMPTY=0, BLACK=1, WHITE=-1.
- Người chơi: BLACK (=1) đi trước.
- Action: tuple (row, col), mỗi số từ 0..7. KHÔNG dùng (x, y).
- Pass: engine tự xử lý, agent không bao giờ nhận/trả về action pass.
- Result: góc nhìn của một người chơi cụ thể: +1 thắng, 0 hòa, -1 thua.
"""

import numpy as np

BOARD_SIZE = 8

EMPTY = 0
BLACK = 1
WHITE = -1

# 8 hướng (d_row, d_col)
DIRECTIONS = (
    (-1, -1), (-1, 0), (-1, 1),
    (0, -1),           (0, 1),
    (1, -1),  (1, 0),  (1, 1),
)

Action = tuple  # (row, col)


def opponent(player: int) -> int:
    """Trả về người chơi đối thủ."""
    return -player


def initial_board() -> np.ndarray:
    """Bàn cờ ban đầu: 4 quân ở giữa xếp chéo.

    Chuẩn: d5 và e4 là đen, d4 và e5 là trắng.
    Với (row, col) 0-index: (3,4) và (4,3) đen; (3,3) và (4,4) trắng.
    """
    board = np.zeros((BOARD_SIZE, BOARD_SIZE), dtype=np.int8)
    mid = BOARD_SIZE // 2
    board[mid - 1, mid - 1] = WHITE
    board[mid, mid] = WHITE
    board[mid - 1, mid] = BLACK
    board[mid, mid - 1] = BLACK
    return board


def action_to_index(action: Action) -> int:
    """(row, col) -> 0..63. Dùng cho NN (policy head có 64 đầu ra)."""
    return action[0] * BOARD_SIZE + action[1]


def index_to_action(index: int) -> Action:
    """0..63 -> (row, col)."""
    return divmod(int(index), BOARD_SIZE)


def encode_planes(board: np.ndarray, player: int) -> np.ndarray:
    """Mã hóa cho NN theo góc nhìn của `player`: shape (2, 8, 8) float32.

    Plane 0: quân của người đang đi. Plane 1: quân của đối thủ.
    (Người 3 có thể mở rộng thêm plane nước hợp lệ nếu cần.)
    """
    return np.stack([board == player, board == -player]).astype(np.float32)
