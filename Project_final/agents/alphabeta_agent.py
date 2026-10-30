"""AlphaBetaAgent (Cấp 3): Minimax với Cắt tỉa Alpha-Beta và Tái sử dụng Heuristic."""

import random
import time
from agents.base import Agent
from configs.constants import C_SQUARES, CORNERS, X_SQUARES
from othello.encoding import BLACK, EMPTY, opponent
from othello.rules import legal_moves
from eval.evaluation import evaluate_state

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
        self.rng = random.Random(seed)
        self._nodes = 0
        self._tree = None

    def reset(self) -> None:
        self._nodes = 0

    def stats(self) -> dict:
        """Trả về số nút đã duyệt phục vụ giải đấu và báo cáo."""
        return {"nodes": self._nodes, "simulations": 0}

    def search_tree(self):
        return self._tree

    def select_action(self, game, time_budget: float = None):
        actions = game.legal_actions()
        if not actions:
            return None

        self._nodes = 0
        me = game.current_player
        start_time = time.time()

        # Sắp xếp nước đi ưu tiên ô góc trước nếu bật move_ordering
        if self.move_ordering:
            actions = sorted(actions, key=lambda a: a in CORNERS, reverse=True)

        best_score = float("-inf")
        best_actions = []
        alpha = float("-inf")
        beta = float("inf")

        for action in actions:
            if time_budget and (time.time() - start_time) >= time_budget:
                break

            cloned = game.clone()
            cloned.step(action)
            self._nodes += 1

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
                best_actions = [action]
            elif val == best_score:
                best_actions.append(action)

            if self.pruning:
                alpha = max(alpha, best_score)

        chosen = self.rng.choice(best_actions) if best_actions else actions[0]
        return chosen

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
        # Điều kiện dừng: Hết độ sâu, hết ván hoặc hết ngân sách thời gian
        if depth == 0 or game.is_terminal() or (time_budget and (time.time() - start_time) >= time_budget):
            return evaluate_state(game.board, root_player, self.eval_config)

        actions = game.legal_actions()

        # Xử lý trường hợp Pass lượt an toàn (không gọi phương thức ẩn)
        if not actions:
            cloned = game.clone()
            cloned.current_player = opponent(cloned.current_player)
            # Nếu đối thủ cũng không đi được thì game kết thúc
            if not cloned.legal_actions():
                return evaluate_state(cloned.board, root_player, self.eval_config)
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