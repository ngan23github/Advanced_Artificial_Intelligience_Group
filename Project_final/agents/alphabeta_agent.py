"""AlphaBetaAgent (Cấp 3): Minimax với Cắt tỉa Alpha-Beta."""

import random
from agents.base import Agent
<<<<<<< HEAD
from eval.evaluation import evaluate_state, normalize_eval_config, normalize_weights, terminal_score
from othello.encoding import opponent
from utils.search_utils import SearchTimeout, depth_schedule, order_moves
=======
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
>>>>>>> 2e75aef339e541296e9a740ca54ae3a7ba63f59d


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
<<<<<<< HEAD
=======
    """Tác tử tìm kiếm Cấp 3: Minimax hỗ trợ Cắt tỉa Alpha-Beta.

    Cài đặt bằng bitboard (othello/bitboard.py): không clone `OthelloGame`, không dùng numpy trong vòng
    tìm kiếm => nhanh hơn bản cũ khoảng 15-20 lần với CÙNG hàm đánh giá, CÙNG thứ tự duyệt, CÙNG cách đếm `nodes`.

    Về pass: người đi tiếp được xác định THEO NGƯỜI THẬT SỰ ĐẾN LƯỢT (nếu đối thủ phải pass thì cùng một người đi
    tiếp và vẫn là nút max/min cũ). Bản cũ luôn đảo max/min sau mỗi nước nên sai khi có pass trong cây.
    """

>>>>>>> 2e75aef339e541296e9a740ca54ae3a7ba63f59d
    def __init__(
        self,
        depth: int = 4,
        pruning: bool = True,
        move_ordering: bool = True,
        eval: dict = None,
        weights: dict = None,
        max_depth: int = None,
        seed: int = None,
        name: str = "AlphaBetaAgent",
        **kwargs
    ):
        super().__init__()
        if depth < 1:
            raise ValueError("depth phải >= 1")
        self.depth = depth
        self.pruning = pruning
        self.move_ordering = move_ordering
        self.max_depth = max_depth
        self.eval_config = normalize_eval_config(eval)
        self.weights = normalize_weights(weights)
        self.name = name
        self.rng = random.Random(seed)
        self._nodes = 0
        self._deadline = None
        self._stats = {"nodes": 0, "simulations": 0, "depth": 0, "value": 0.0}
   

    def reset(self) -> None:
        self._nodes = 0

    def stats(self) -> dict:
        return dict(self._stats)


    # ---------- gốc cây ----------
    def select_action(self, game, time_budget: float = None):
        if game.is_terminal():
            return None
        black, white = board_to_bb(game.board)
        me, opp = (black, white) if game.current_player == BLACK else (white, black)
        root_moves = legal_mask(me, opp)
        if not root_moves:
            return None

        root = game.current_player
        order = order_moves(actions, self.move_ordering)
        self._nodes = 0
<<<<<<< HEAD

        if len(order) == 1:
            self._stats = {"nodes": 1, "simulations": 0, "depth": 0, "value": 0.0}

            return order[0]

        depths, deadline = depth_schedule(game, time_budget, self.depth, self.max_depth)
        best_action = order[0]
        value, reached = 0.0, 0
        rows = []

        for d in depths:
            self._deadline = deadline if d > 1 else None
            try:
                action, score, r = self._search_root(game, d, order, root)
            except SearchTimeout:
                break
            best_action, value, reached, rows = action, score, d, r
            order = [action] + [a for a in order if a != action]

        self._deadline = None
        self._stats = {"nodes": self._nodes, "simulations": 0, "depth": reached, "value": round(value, 2)}
        return best_action

    def _search_root(self, game, depth, order, root):
        alpha, beta = float("-inf"), float("inf")
        best_score = float("-inf")
        best_actions = []
        rows = []

        for action in order:
            child = game.clone()
            child.step(action)
            self._nodes += 1

            val = self._alphabeta(child, depth - 1, alpha, beta, root)
            exact = (not self.pruning) or val > alpha
            rows.append((action, val, exact))

            if val > best_score:
                best_score = val
                best_actions = [action]
            elif val == best_score:
                best_actions.append(action)

            if self.pruning:
                alpha = max(alpha, best_score)

        chosen_action = self.rng.choice(best_actions) if best_actions else order[0]
        return chosen_action, best_score, rows

    def _alphabeta(self, game, depth, alpha, beta, root):
        if self._deadline is not None and self._deadline.expired():
            raise SearchTimeout

        if game.is_terminal():
            return terminal_score(game.board, root)

        if depth == 0:
            return evaluate_state(game.board, root, self.eval_config, self.weights)
=======
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
>>>>>>> 2e75aef339e541296e9a740ca54ae3a7ba63f59d

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

<<<<<<< HEAD
        # Xử lý Pass lượt an toàn
        if not actions:
            cloned = game.clone()
            cloned.current_player = opponent(cloned.current_player)
            if not cloned.legal_actions():
                return terminal_score(cloned.board, root)
            return self._alphabeta(cloned, depth - 1, alpha, beta, root)

        actions = order_moves(actions, self.move_ordering)
        maximizing = game.current_player == root

        best = float("-inf") if maximizing else float("inf")
        for action in actions:
            child = game.clone()
            child.step(action)
            self._nodes += 1

            val = self._alphabeta(child, depth - 1, alpha, beta, root)
            if maximizing:
                best = max(best, val)
                if self.pruning:
                    alpha = max(alpha, val)
            else:
                best = min(best, val)
                if self.pruning:
                    beta = min(beta, val)

            if self.pruning and beta <= alpha:
                break

        return best

=======
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
>>>>>>> 2e75aef339e541296e9a740ca54ae3a7ba63f59d
