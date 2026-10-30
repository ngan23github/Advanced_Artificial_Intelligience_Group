"""AlphaBetaAgent (Cấp 3): Minimax với Cắt tỉa Alpha-Beta chạy trên Bitboard."""

import time
from agents.base import Agent
from configs.constants import CORNERS
from eval.evaluation import _evaluate_bb
from othello.bitboard import CORNER_MASK, board_to_bb, flips_mask, legal_mask
from othello.encoding import BLACK


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
    """Tác tử tìm kiếm Cấp 3: Minimax hỗ trợ Cắt tỉa Alpha-Beta trên Bitboard."""

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
                best_bit = bit
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
        flips = flips_mask(me, opp, bit)
        me2 = me | bit | flips
        opp2 = opp & ~flips

        nxt_moves = legal_mask(opp2, me2)
        if nxt_moves:
            return self._node(opp2, me2, nxt_moves, depth, alpha, beta, not mover_is_root)
        own_moves = legal_mask(me2, opp2)
        if own_moves:
            return self._node(me2, opp2, own_moves, depth, alpha, beta, mover_is_root)
        return self._leaf(me2, opp2, mover_is_root)

    def _leaf(self, me, opp, me_is_root):
        if me_is_root:
            return _evaluate_bb(me, opp, self._cfg)
        return _evaluate_bb(opp, me, self._cfg)

    def _node(self, me, opp, moves, depth, alpha, beta, maximizing):
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