"""AlphaBetaAgent (Cấp 3): Minimax với Cắt tỉa Alpha-Beta."""

import random
from agents.base import Agent
from eval.evaluation import evaluate_state, normalize_eval_config, normalize_weights, terminal_score
from othello.encoding import opponent
from utils.search_utils import SearchTimeout, depth_schedule, order_moves


class AlphaBetaAgent(Agent):
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


    def select_action(self, game, time_budget: float = None):
        actions = game.legal_actions()
        if not actions:
            return None

        root = game.current_player
        order = order_moves(actions, self.move_ordering)
        self._nodes = 0

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

        actions = game.legal_actions()

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

