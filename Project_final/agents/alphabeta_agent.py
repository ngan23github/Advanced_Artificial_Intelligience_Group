"""AlphaBetaAgent (Cấp 3): Minimax với Cắt tỉa Alpha-Beta và Tái sử dụng Heuristic."""

import time
from agents.base import Agent
from configs.constants import CORNERS, X_SQUARES, C_SQUARES
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


class AlphaBetaAgent(Agent):
    """Tác tử tìm kiếm Cấp 3: Minimax hỗ trợ Cắt tỉa Alpha-Beta."""

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

    def select_action(self, game, time_budget: float = None):
        actions = game.legal_actions()
        if not actions:
            return None

        self._nodes = 0
        me = game.current_player
        best_score = float("-inf")
        best_action = actions[0]

        alpha = float("-inf")
        beta = float("inf")

        # Đặt thời gian hết giờ nếu có time_budget
        start_time = time.time()

        # Sắp xếp nước đi ưu tiên ô góc trước nếu bật move_ordering
        if self.move_ordering:
            actions = sorted(actions, key=lambda a: a in CORNERS, reverse=True)

        for action in actions:
            # Kiểm tra ngân sách thời gian
            if time_budget and (time.time() - start_time) >= time_budget:
                break

            cloned = game.clone()
            cloned.step(action)
            self._nodes += 1

            # Gọi Minimax/Alpha-Beta đệ quy cho đối thủ ở tầng kế tiếp
            val = self._alphabeta(
                cloned,
                depth=self.depth - 1,
                alpha=alpha,
                beta=beta,
                maximizing_player=False,
                root_player=me,
                start_time=start_time,
                time_budget=time_budget,
            )

            if val > best_score:
                best_score = val
                best_action = action

            if self.pruning:
                alpha = max(alpha, best_score)

        return best_action

    def _alphabeta(
        self,
        game,
        depth: int,
        alpha: float,
        beta: float,
        maximizing_player: bool,
        root_player: int,
        start_time: float,
        time_budget: float,
    ) -> float:
        # Kiểm tra điều kiện dừng: hết độ sâu, hết ván, hoặc hết time_budget
        if depth == 0 or game.is_terminal() or (time_budget and (time.time() - start_time) >= time_budget):
            return evaluate_state(game.board, root_player, self.eval_config)

        actions = game.legal_actions()

        # Xử lý trường hợp Pass lượt (không có nước hợp lệ nhưng chưa hết ván)
        if not actions:
            cloned = game.clone()
            cloned._advance_turn(cloned.current_player)
            return self._alphabeta(
                cloned, depth - 1, alpha, beta, not maximizing_player, root_player, start_time, time_budget
            )

        if self.move_ordering:
            actions = sorted(actions, key=lambda a: a in CORNERS, reverse=True)

        if maximizing_player:
            max_eval = float("-inf")
            for action in actions:
                cloned = game.clone()
                cloned.step(action)
                self._nodes += 1

                eval_val = self._alphabeta(
                    cloned, depth - 1, alpha, beta, False, root_player, start_time, time_budget
                )
                max_eval = max(max_eval, eval_val)

                if self.pruning:
                    alpha = max(alpha, eval_val)
                    if beta <= alpha:
                        break  # Cắt tỉa Beta
            return max_eval
        else:
            min_eval = float("inf")
            for action in actions:
                cloned = game.clone()
                cloned.step(action)
                self._nodes += 1

                eval_val = self._alphabeta(
                    cloned, depth - 1, alpha, beta, True, root_player, start_time, time_budget
                )
                min_eval = min(min_eval, eval_val)

                if self.pruning:
                    beta = min(beta, eval_val)
                    if beta <= alpha:
                        break  # Cắt tỉa Alpha
            return min_eval