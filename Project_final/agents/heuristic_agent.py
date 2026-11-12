"""HeuristicAgent: Tác tử Cấp 2 chọn nước đi theo luật ưu tiên cố định (chỉ nhìn 1 nước)."""

import os
import random
import yaml

from agents.base import Agent
from configs.constants import (
    C_SQUARES,
    CORNERS,
    DEFAULT_PRIORITIES,
    ENDGAME_ORDER,
    RULE_NAMES,
    X_SQUARES,
)
from othello.encoding import BLACK, EMPTY, opponent
from othello.rules import apply_move, count_discs, legal_moves


def rule_values(info: dict) -> dict:
    """Giá trị của từng luật cho 1 nước đi (càng lớn càng tốt)."""
    return {
        "win_now": info["outcome"],
        "take_corner": info["corner"],
        "deny_corner": -info["opp_corner_moves"],   # càng ít góc đối thủ lấy được càng tốt
        "avoid_x_square": -int(info["danger"] == 2),
        "avoid_c_square": -int(info["danger"] == 1),
        "maximize_mobility": info["mobility"],
        "maximize_discs": info["discs"],
    }


class HeuristicAgent(Agent):
    def __init__(
        self,
        seed=None,
        priorities=None,
        endgame_empties: int = None,
        name: str = None,
        config_file: str = "configs/agents_heuristic.yaml",
        **kwargs
    ):
        super().__init__()

        # Đọc cấu hình từ YAML nếu tồn tại
        config = {}
        if config_file:
            cfg_path = config_file
            if not os.path.isabs(cfg_path) and not os.path.exists(cfg_path):
                repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                cfg_path = os.path.join(repo_root, config_file)
            if os.path.exists(cfg_path):
                with open(cfg_path, "r", encoding="utf-8") as f:
                    config = yaml.safe_load(f) or {}

        # Thứ tự ưu tiên: THAM SỐ TRUYỀN VÀO > YAML > mặc định (trước đây YAML đè tham số truyền vào)
        self.name = name if name is not None else config.get("name", "Heuristic")
        self.endgame_empties = (
            endgame_empties if endgame_empties is not None else config.get("endgame_empties", 10)
        )

        if priorities is None:
            priorities = config.get("priorities", DEFAULT_PRIORITIES)

        pr = list(priorities)
        unknown = [r for r in pr if r not in RULE_NAMES]
        if unknown:
            raise ValueError(f"Luật không biết: {unknown}. Hợp lệ: {list(RULE_NAMES)}")
        if len(set(pr)) != len(pr):
            raise ValueError(f"priorities có luật bị trùng: {pr}")

        self.priorities = pr
        self._endgame_order = [r for r in ENDGAME_ORDER if r in pr]
        self.rng = random.Random(seed)
        self._nodes = 0
        self._tree = None

    def reset(self) -> None:
        self._nodes = 0

    def stats(self) -> dict:
        return {"nodes": self._nodes, "simulations": 0}

    def search_tree(self):
        return self._tree

    @staticmethod
    def _danger(board, action) -> int:
        if action in X_SQUARES and board[X_SQUARES[action]] == EMPTY:
            return 2
        if action in C_SQUARES and board[C_SQUARES[action]] == EMPTY:
            return 1
        return 0

    def _score(self, board, me, action, endgame: bool) -> tuple:
        after = apply_move(board, me, action[0], action[1])
        self._nodes += 1
        opp = opponent(me)
        mine_list = legal_moves(after, me)
        opp_list = legal_moves(after, opp)
        mine_moves, opp_moves = len(mine_list), len(opp_list)
        black, white = count_discs(after)
        mine_discs, opp_discs = (black, white) if me == BLACK else (white, black)

        outcome = 0
        if mine_moves == 0 and opp_moves == 0:
            outcome = (mine_discs > opp_discs) - (mine_discs < opp_discs)

        mobility = mine_moves - opp_moves
        corner = int(action in CORNERS)
        danger = self._danger(board, action)
        # số góc mà đối thủ có thể lấy ngay ở lượt kế tiếp (sau nước đi này)
        opp_corner_moves = sum(1 for m in opp_list if m in CORNERS)
        info = {
            "corner": corner,
            "danger": danger,
            "mobility": mobility,
            "discs": mine_discs,
            "outcome": outcome,
            "opp_corner_moves": opp_corner_moves,
        }

        vals = rule_values(info)
        order = self._endgame_order if endgame else self.priorities
        return tuple(vals[r] for r in order), info

    def select_action(self, game, time_budget=None):
        actions = game.legal_actions()
        if not actions:
            return None
        board, me = game.board, game.current_player
        self._nodes = 0
        empties = int((board == EMPTY).sum())
        endgame = empties <= self.endgame_empties
        evals = [(*self._score(board, me, a, endgame), a) for a in actions]
        best = max(k for k, _, _ in evals)
        chosen = self.rng.choice([a for k, _, a in evals if k == best])
        order = self._endgame_order if endgame else self.priorities
        self._tree = self._build_tree(evals, chosen, endgame, order)
        return chosen

    @staticmethod
    def _build_tree(evals, chosen, endgame, order):
        children = []
        for _, info, a in sorted(evals, key=lambda e: e[0], reverse=True):
            if info["outcome"] > 0:
                caption = "win now"
            elif info["outcome"] < 0:
                caption = "loses"
            elif info["corner"]:
                caption = "corner"
            elif info["opp_corner_moves"]:
                caption = f"gives corner x{info['opp_corner_moves']}"
            else:
                caption = f"mob {info['mobility']:+d}"
            children.append({
                "move": a,
                "value": info["mobility"],
                "caption": caption,
                "best": a == chosen,
                "text": (f"outcome={info['outcome']:+d}  corner={info['corner']}  "
                         f"opp_corner_moves={info['opp_corner_moves']}  "
                         f"X/C danger={info['danger']} (0 safe, 1 C, 2 X)  "
                         f"mobility={info['mobility']:+d}  discs={info['discs']}"),
                "children": [],
            })
        rule = ("endgame: " if endgame else "") + " > ".join(order)
        return {"move": None, "label": "root", "caption": f"{len(evals)} moves",
                "text": "Priority: " + rule, "children": children}