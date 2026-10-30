"""OthelloGame: quản lý trạng thái ván cờ, lượt đi, pass, kết thúc, kết quả.

API (khớp yêu cầu đề bài; xem thêm API.md):
    reset()            -> đưa game về vị trí đầu, trả về chính game
    legal_actions()    -> list[(row, col)] của người đang đến lượt ([] nếu hết ván)
    step(action)       -> thực hiện nước đi (sửa game tại chỗ), trả về chính game
    is_terminal()      -> bool
    result(player=None)-> +1 / 0 / -1 theo góc nhìn `player` (mặc định: BLACK)
    render()           -> str bàn cờ dạng text
    clone()            -> bản sao ĐỘC LẬP (dùng cho Alpha-Beta, MCTS)

Quy tắc pass (engine tự xử lý, agent không thấy):
    Sau mỗi nước đi, nếu người kế tiếp không có nước hợp lệ thì lượt quay lại
    người vừa đi. Nếu cả hai đều không đi được thì ván kết thúc.
"""

import numpy as np

from othello.encoding import BLACK, WHITE, initial_board, opponent
from othello.rules import apply_move, count_discs, legal_moves


class IllegalMoveError(ValueError):
    """Ném ra khi step() nhận nước đi không hợp lệ."""


class OthelloGame:
    def __init__(self):
        self.reset()

    # ---------- khởi tạo ----------
    def reset(self):
        self.board = initial_board()
        self.current_player = BLACK
        self.move_history = []  # list[(player, (row, col))]
        self._terminal = False
        self._cache_legal = None
        return self

    # ---------- truy vấn ----------
    def legal_actions(self) -> list:
        if self._terminal:
            return []
        if self._cache_legal is None:
            self._cache_legal = legal_moves(self.board, self.current_player)
        return list(self._cache_legal)

    def is_terminal(self) -> bool:
        return self._terminal

    def score(self) -> tuple:
        """(quân đen, quân trắng) hiện tại."""
        return count_discs(self.board)

    def result(self, player: int = BLACK) -> int:
        """Kết quả theo góc nhìn `player`: +1 thắng, 0 hòa, -1 thua.

        Chỉ gọi khi ván đã kết thúc. Thắng thua theo số quân.
        """
        if not self._terminal:
            raise RuntimeError("Ván chưa kết thúc, chưa có result().")
        black, white = self.score()
        diff = black - white
        winner_sign = (diff > 0) - (diff < 0)  # +1 đen thắng, -1 trắng thắng, 0 hòa
        return winner_sign * player

    # ---------- biến đổi trạng thái ----------
    def step(self, action):
        if self._terminal:
            raise IllegalMoveError("Ván đã kết thúc.")
        action = tuple(action)
        if action not in self.legal_actions():
            raise IllegalMoveError(
                f"Nước đi {action} không hợp lệ cho người chơi {self.current_player}."
            )
        mover = self.current_player
        self.board = apply_move(self.board, mover, action[0], action[1])
        self.move_history.append((mover, action))
        self._advance_turn(mover)
        return self

    def _advance_turn(self, last_mover: int):
        """Chuyển lượt, tự xử lý pass và kết thúc ván.

        Nước đi hợp lệ của người đến lượt đã được tính ngay ở đây để quyết định pass,
        nên lưu luôn vào `_cache_legal` (trước đây bị bỏ đi rồi `legal_actions()` tính lại lần nữa).
        """
        nxt = opponent(last_mover)
        moves = legal_moves(self.board, nxt)
        if moves:
            self.current_player = nxt
            self._cache_legal = moves
            return
        moves = legal_moves(self.board, last_mover)
        if moves:
            self.current_player = last_mover  # đối thủ phải pass
            self._cache_legal = moves
        else:
            self._terminal = True  # không ai đi được
            self._cache_legal = None

    def clone(self) -> "OthelloGame":
        g = OthelloGame.__new__(OthelloGame)
        g.board = self.board.copy()
        g.current_player = self.current_player
        g.move_history = list(self.move_history)
        g._terminal = self._terminal
        g._cache_legal = None if self._cache_legal is None else list(self._cache_legal)
        return g

    # ---------- hiển thị ----------
    def render(self) -> str:
        sym = {BLACK: "X", WHITE: "O", 0: "."}
        lines = ["  " + " ".join(str(c) for c in range(8))]
        for r in range(8):
            lines.append(str(r) + " " + " ".join(sym[int(v)] for v in self.board[r]))
        b, w = self.score()
        turn = "Hết ván" if self._terminal else ("Đen (X)" if self.current_player == BLACK else "Trắng (O)")
        lines.append(f"Đen X: {b}  Trắng O: {w}  Lượt: {turn}")
        return "\n".join(lines)
