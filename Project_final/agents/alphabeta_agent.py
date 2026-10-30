"""AlphaBetaAgent (Cấp 3): Minimax với Cắt tỉa Alpha-Beta và Tái sử dụng Heuristic."""

import time
from agents.base import Agent
from configs.constants import CORNERS, X_SQUARES, C_SQUARES
from othello.bitboard import CORNER_MASK, bb_to_squares, board_to_bb, flips_mask, legal_mask
from othello.encoding import BLACK, EMPTY, opponent
from othello.rules import apply_move, count_discs, legal_moves


def evaluate_state(board, player: int, eval_config: dict = None) -> float:
    """Hàm đánh giá tĩnh (Heuristic Evaluation) cho trạng thái ở lá cây."""
    if eval_config is None:
        eval_config = {
            "disc_diff": True,
            "mobility": True,
            "corners": True,
            "x_c_squares": True,
        }

    opp = opponent(player)
    score = 0.0

    # 1. Chênh lệch số quân (disc_diff)
    if eval_config.get("disc_diff", True):
        p_coins = (board == player).sum()
        o_coins = (board == opp).sum()
        if p_coins + o_coins > 0:
            score += 10.0 * (p_coins - o_coins) / (p_coins + o_coins)

    # 2. Chiếm góc (corners)
    if eval_config.get("corners", True):
        p_corners = sum(1 for r, c in CORNERS if board[r, c] == player)
        o_corners = sum(1 for r, c in CORNERS if board[r, c] == opp)
        score += 100.0 * (p_corners - o_corners)

    # 3. Tránh ô X/C nguy hiểm (x_c_squares)
    if eval_config.get("x_c_squares", True):
        danger_penalty = 0
        for x_pos, corner_pos in X_SQUARES.items():
            if board[corner_pos] == EMPTY:
                if board[x_pos] == player:
                    danger_penalty -= 30
                elif board[x_pos] == opp:
                    danger_penalty += 30

        for c_pos, corner_pos in C_SQUARES.items():
            if board[corner_pos] == EMPTY:
                if board[c_pos] == player:
                    danger_penalty -= 15
                elif board[c_pos] == opp:
                    danger_penalty += 15
        score += danger_penalty

    # 4. Độ cơ động (mobility)
    if eval_config.get("mobility", True):
        p_moves = len(legal_moves(board, player))
        o_moves = len(legal_moves(board, opp))
        if p_moves + o_moves > 0:
            score += 20.0 * (p_moves - o_moves) / (p_moves + o_moves)

    return float(score)


# ---------------------------------------------------------------------------
# Phiên bản BITBOARD của evaluate_state (dùng trong tìm kiếm). Công thức, trọng số và THỨ TỰ cộng
# giống hệt evaluate_state ở trên nên cho cùng giá trị; chỉ khác là không tạo game/clone numpy.
# ---------------------------------------------------------------------------
def _sq_bit(pos) -> int:
    return 1 << (pos[0] * 8 + pos[1])


# (bit góc, bit ô X kề góc, mặt nạ các ô C kề góc)
_CORNER_GROUPS = tuple(
    (_sq_bit(corner),
     _sq_bit(x_pos),
     sum(_sq_bit(c_pos) for c_pos, c_corner in C_SQUARES.items() if c_corner == corner))
    for x_pos, corner in X_SQUARES.items()
)
_ROOT_CORNER_BITS = tuple(sorted(_sq_bit(c) for c in CORNERS))


def _evaluate_bb(me: int, opp: int, cfg: dict) -> float:
    """Đánh giá theo góc nhìn `me` (người gốc của cây tìm kiếm). cfg: dict {tên_thành_phần: bool}."""
    score = 0.0
    if cfg.get("disc_diff", True):
        p_coins, o_coins = me.bit_count(), opp.bit_count()
        if p_coins + o_coins > 0:
            score += 10.0 * (p_coins - o_coins) / (p_coins + o_coins)
    if cfg.get("corners", True):
        score += 100.0 * ((me & CORNER_MASK).bit_count() - (opp & CORNER_MASK).bit_count())
    if cfg.get("x_c_squares", True):
        danger = 0
        occupied = me | opp
        for corner_bit, x_bit, c_mask in _CORNER_GROUPS:
            if not occupied & corner_bit:
                if me & x_bit:
                    danger -= 30
                elif opp & x_bit:
                    danger += 30
                danger -= 15 * (me & c_mask).bit_count()
                danger += 15 * (opp & c_mask).bit_count()
        score += danger
    if cfg.get("mobility", True):
        p_moves = legal_mask(me, opp).bit_count()
        o_moves = legal_mask(opp, me).bit_count()
        if p_moves + o_moves > 0:
            score += 20.0 * (p_moves - o_moves) / (p_moves + o_moves)
    return float(score)


def _ordered_squares(moves: int, ordering: bool) -> list:
    """Danh sách bit nước đi (mỗi phần tử là 1 << index). Ordering: góc trước, còn lại giữ thứ tự (row, col)."""
    out = []
    if ordering:
        corner_moves = moves & CORNER_MASK
        while corner_moves:
            low = corner_moves & -corner_moves
            out.append(low)
            corner_moves ^= low
        moves &= ~CORNER_MASK
    while moves:
        low = moves & -moves
        out.append(low)
        moves ^= low
    return out


class AlphaBetaAgent(Agent):
    """Tác tử tìm kiếm Cấp 3: Minimax hỗ trợ Cắt tỉa Alpha-Beta.

    Cài đặt bằng bitboard (othello/bitboard.py): không clone `OthelloGame`, không dùng numpy trong vòng
    tìm kiếm => nhanh hơn bản cũ khoảng 15-20 lần với CÙNG hàm đánh giá, CÙNG thứ tự duyệt, CÙNG cách đếm `nodes`.

    Về pass: người đi tiếp được xác định THEO NGƯỜI THẬT SỰ ĐẾN LƯỢT (nếu đối thủ phải pass thì cùng một người đi
    tiếp và vẫn là nút max/min cũ). Bản cũ luôn đảo max/min sau mỗi nước nên sai khi có pass trong cây.
    """

    def __init__(
        self,
        depth: int = 4,
        pruning: bool = True,
        move_ordering: bool = True,
        eval: dict = None,
        seed: int = None,
        name: str = "AlphaBetaAgent",
        **kwargs
    ):
        super().__init__()
        self.depth = depth
        self.pruning = pruning
        self.move_ordering = move_ordering
        self.eval_config = eval or {}
        self.name = name
        self._nodes = 0

    def reset(self) -> None:
        self._nodes = 0

    def stats(self) -> dict:
        """Trả về số nút đã duyệt phục vụ giải đấu và báo cáo."""
        return {"nodes": self._nodes, "simulations": 0}

    # ---------- gốc cây ----------
    def select_action(self, game, time_budget: float = None):
        if game.is_terminal():
            return None
        black, white = board_to_bb(game.board)
        me, opp = (black, white) if game.current_player == BLACK else (white, black)
        root_moves = legal_mask(me, opp)
        if not root_moves:
            return None

        self._nodes = 0
        self._cfg = self.eval_config
        self._deadline = (time.time() + time_budget) if time_budget else None

        best_score = float("-inf")
        best_bit = None
        alpha = float("-inf")
        beta = float("inf")

        for bit in _ordered_squares(root_moves, self.move_ordering):
            if best_bit is not None and self._deadline is not None and time.time() >= self._deadline:
                break
            if best_bit is None:
                best_bit = bit  # luôn có nước hợp lệ để trả về (giống bản cũ: actions[0])
            self._nodes += 1
            val = self._child_value(me, opp, bit, self.depth - 1, alpha, beta, True)
            if val > best_score:
                best_score = val
                best_bit = bit
            if self.pruning:
                alpha = max(alpha, best_score)

        return divmod(best_bit.bit_length() - 1, 8)

    # ---------- đệ quy ----------
    def _child_value(self, me, opp, bit, depth, alpha, beta, mover_is_root):
        """Đi nước `bit` cho bên `me` (đang đến lượt), rồi đánh giá nút con.

        `mover_is_root`: bên `me` có phải người gốc (root) không.
        """
        flips = flips_mask(me, opp, bit)
        me2 = me | bit | flips
        opp2 = opp & ~flips
        # người đi tiếp: đối thủ nếu họ có nước, nếu không thì chính `me` đi tiếp (pass), nếu không ai đi được => hết ván
        nxt_moves = legal_mask(opp2, me2)
        if nxt_moves:
            return self._node(opp2, me2, nxt_moves, depth, alpha, beta, not mover_is_root)
        own_moves = legal_mask(me2, opp2)
        if own_moves:
            return self._node(me2, opp2, own_moves, depth, alpha, beta, mover_is_root)
        return self._leaf(me2, opp2, mover_is_root)

    def _leaf(self, me, opp, me_is_root):
        """Đánh giá theo góc nhìn người gốc."""
        if me_is_root:
            return _evaluate_bb(me, opp, self._cfg)
        return _evaluate_bb(opp, me, self._cfg)

    def _node(self, me, opp, moves, depth, alpha, beta, maximizing):
        """Nút có `me` đến lượt, `moves` là mặt nạ nước đi của `me`. maximizing = `me` là người gốc."""
        if depth == 0 or (self._deadline is not None and time.time() >= self._deadline):
            return self._leaf(me, opp, maximizing)

        ordered = _ordered_squares(moves, self.move_ordering)
        if maximizing:
            best = float("-inf")
            for bit in ordered:
                self._nodes += 1
                v = self._child_value(me, opp, bit, depth - 1, alpha, beta, True)
                if v > best:
                    best = v
                if self.pruning:
                    if best > alpha:
                        alpha = best
                    if beta <= alpha:
                        break
            return best
        best = float("inf")
        for bit in ordered:
            self._nodes += 1
            v = self._child_value(me, opp, bit, depth - 1, alpha, beta, False)
            if v < best:
                best = v
            if self.pruning:
                if best < beta:
                    beta = best
                if beta <= alpha:
                    break
        return best
