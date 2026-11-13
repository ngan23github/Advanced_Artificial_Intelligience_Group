"""AlphaBetaAgent (Cấp 3): Minimax với cắt tỉa Alpha-Beta chạy trên bitboard.

Hai chế độ (khớp configs/agents*.yaml):
- Không có time_budget: tìm đúng `depth` tầng (cố định, tất định).
- Có time_budget: LẶP SÂU 1, 2, 3, ... đến khi hết giờ (hoặc hết ô trống, tức đã giải xong ván). Tầng đang dở khi
  hết giờ bị BỎ HẲN, trả nước của tầng hoàn chỉnh gần nhất -> nước đi luôn là kết quả của một lần tìm kiếm đầy đủ.
  Tham số `depth` bị bỏ qua; `max_depth` (tùy chọn) chặn độ sâu tối đa.

Pass: sau một nước đi người kế tiếp có thể vẫn là người cũ, nên max/min được xác định bằng "nút này của ai"
(mover_is_root), KHÔNG đảo dấu theo độ sâu.

Nút kết thúc ván được chấm bằng terminal score (thắng luôn > mọi điểm heuristic), không dùng hàm đánh giá tĩnh.

Tham số:
    depth, pruning, move_ordering, max_depth
    eval     bật/tắt thành phần: {disc_diff, mobility, corners, x_c_squares}  (stability chưa cài đặt)
    weights  hệ số từng thành phần (dùng để tune), mặc định configs.constants.EVAL_SCALES
Agent tất định (không dùng RNG): `seed` được nhận cho đúng API nhưng không ảnh hưởng.
"""

from agents.base import Agent
from eval.evaluation import (_evaluate_bb, _terminal_bb, evaluate_state,  # noqa: F401  (evaluate_state: test dùng)
                             normalize_eval_config, normalize_weights)
from othello.bitboard import CORNER_MASK, board_to_bb, flips_mask, legal_mask
from othello.encoding import BLACK
from utils.search_utils import SearchTimeout, depth_schedule

_CHECK_EVERY = 128    # kiểm tra đồng hồ mỗi 128 nút (gọi đồng hồ mỗi nút khá tốn)


def _ordered_squares(moves: int, ordering: bool) -> list:
    """Danh sách bit nước đi (mỗi phần tử là 1 << index). Ordering: góc trước, còn lại giữ thứ tự."""
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
    """Tác tử tìm kiếm Cấp 3: Minimax hỗ trợ cắt tỉa Alpha-Beta trên bitboard."""

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
        if kwargs:
            raise TypeError(f"AlphaBetaAgent: tham số không biết: {sorted(kwargs)}")
        if depth < 1:
            raise ValueError("depth phải >= 1")
        self.depth = int(depth)
        self.pruning = pruning
        self.move_ordering = move_ordering
        self.max_depth = max_depth
        self.eval_config = normalize_eval_config(eval)
        self.weights = normalize_weights(weights)
        self.name = name
        self._nodes = 0
        self._reached = 0

    def reset(self) -> None:
        self._nodes = 0
        self._reached = 0

    def stats(self) -> dict:
        # depth = độ sâu hoàn chỉnh đạt được ở nước vừa đi (với lặp sâu theo giờ)
        return {"nodes": self._nodes, "simulations": 0, "depth": self._reached}

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
        self._reached = 0
        self._tick = 0
        self._timed = False
        depths, self._deadline = depth_schedule(game, time_budget, self.depth, self.max_depth)

        best_bit = None
        for d in depths:
            # tầng 1 luôn chạy xong để chắc chắn có nước hợp lệ; từ tầng 2 mới chịu hạn giờ
            self._timed = self._deadline is not None and d > 1
            try:
                best_bit = self._root_search(me, opp, root_moves, d, best_bit)
            except SearchTimeout:
                break
            self._reached = d
        return divmod(best_bit.bit_length() - 1, 8)

    def _root_search(self, me, opp, root_moves, depth, pv_bit):
        ordered = _ordered_squares(root_moves, self.move_ordering)
        if self.move_ordering and pv_bit in ordered:      # nước tốt nhất của tầng trước đi trước -> cắt tỉa nhiều hơn
            ordered.remove(pv_bit)
            ordered.insert(0, pv_bit)
        best_score, best_bit = float("-inf"), ordered[0]
        alpha, beta = float("-inf"), float("inf")
        for bit in ordered:
            self._nodes += 1
            val = self._child_value(me, opp, bit, depth - 1, alpha, beta, True)
            if val > best_score:
                best_score, best_bit = val, bit
            if self.pruning:
                alpha = max(alpha, best_score)
        return best_bit

    # ---------- đệ quy ----------
    def _child_value(self, me, opp, bit, depth, alpha, beta, mover_is_root):
        flips = flips_mask(me, opp, bit)
        me2 = me | bit | flips
        opp2 = opp & ~flips

        nxt_moves = legal_mask(opp2, me2)
        if nxt_moves:
            return self._node(opp2, me2, nxt_moves, depth, alpha, beta, not mover_is_root)
        own_moves = legal_mask(me2, opp2)
        if own_moves:                                      # đối thủ phải pass: cùng một người đi tiếp
            return self._node(me2, opp2, own_moves, depth, alpha, beta, mover_is_root)
        # cả hai hết nước: ván kết thúc
        return _terminal_bb(me2, opp2) if mover_is_root else _terminal_bb(opp2, me2)

    def _leaf(self, me, opp, me_is_root):
        if me_is_root:
            return _evaluate_bb(me, opp, self.eval_config, self.weights)
        return _evaluate_bb(opp, me, self.eval_config, self.weights)

    def _node(self, me, opp, moves, depth, alpha, beta, maximizing):
        if self._timed:
            self._tick += 1
            if not (self._tick % _CHECK_EVERY) and self._deadline.expired():
                raise SearchTimeout
        if depth == 0:
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
