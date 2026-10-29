import random

import yaml
import os
from agents.base import Agent
from configs.constants import (  C_SQUARES,  CORNERS, DEFAULT_PRIORITIES, ENDGAME_ORDER, RULE_NAMES, X_SQUARES)
from othello.encoding import BLACK, EMPTY, opponent
from othello.rules import apply_move, count_discs, legal_moves

def rule_values(info: dict) -> dict:
    """Giá trị của từng luật cho 1 nước đi (càng lớn càng tốt)."""
    return {
        "win_now": info["outcome"],
        "take_corner": info["corner"],
        "avoid_x_square": -int(info["danger"] == 2),
        "avoid_c_square": -int(info["danger"] == 1),
        "maximize_mobility": info["mobility"],
        "maximize_discs": info["discs"],
    }


class HeuristicAgent(Agent):
    def __init__(self, seed=None, priorities=None, endgame_empties: int = 10, name: str = "Heuristic",config_file: str = "configs/agent_heuristic.yaml"):
            super().__init__()
            config = {}
            if config_file and os.path.exists(config_file):
                with open(config_file, "r", encoding="utf-8") as f:
                    config = yaml.safe_load(f) or {}
            self.name = config.get("name", name)
            self.endgame_empties = config.get("endgame_empties", endgame_empties)
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
        # nodes = số vị trí (sau nước thử) đã đánh giá cho nước vừa đi
        return {"nodes": self._nodes, "simulations": 0}

    def search_tree(self):
        """Cây 1 tầng cho UI: gốc -> các nước ứng viên, xếp từ tốt nhất đến tệ nhất."""
        return self._tree

    # ------------------------------------------------------------------
    @staticmethod
    def _danger(board, action) -> int:
        """0 = ô thường, 1 = ô C nguy hiểm, 2 = ô X nguy hiểm (góc kề còn trống)."""
        if action in X_SQUARES and board[X_SQUARES[action]] == EMPTY:
            return 2
        if action in C_SQUARES and board[C_SQUARES[action]] == EMPTY:
            return 1
        return 0

    def _score(self, board, me, action, endgame: bool) -> tuple:
        """(key, info). key: tuple so sánh từ trái sang phải, càng lớn càng tốt."""
        after = apply_move(board, me, action[0], action[1])
        self._nodes += 1
        opp = opponent(me)
        mine_moves = len(legal_moves(after, me))
        opp_moves = len(legal_moves(after, opp))
        black, white = count_discs(after)
        mine_discs, opp_discs = (black, white) if me == BLACK else (white, black)

        outcome = 0  # +1 thắng ngay, -1 thua ngay (nước này kết thúc ván), 0 chưa kết thúc / hòa
        if mine_moves == 0 and opp_moves == 0:
            outcome = (mine_discs > opp_discs) - (mine_discs < opp_discs)

        mobility = mine_moves - opp_moves
        corner = int(action in CORNERS)
        danger = self._danger(board, action)
        info = {"corner": corner, "danger": danger, "mobility": mobility, "discs": mine_discs, "outcome": outcome}

        vals = rule_values(info)
        order = self._endgame_order if endgame else self.priorities
        return tuple(vals[r] for r in order), info

    def select_action(self, game, time_budget=None):
        actions = game.legal_actions()
        if not actions:
            return None
        board, me = game.board, game.current_player  # chỉ đọc, không sửa game
        self._nodes = 0
        empties = int((board == EMPTY).sum())
        endgame = empties <= self.endgame_empties
        evals = [(*self._score(board, me, a, endgame), a) for a in actions]  # (key, info, action)
        best = max(k for k, _, _ in evals)
        chosen = self.rng.choice([a for k, _, a in evals if k == best])
        self._tree = self._build_tree(evals, chosen, endgame)
        return chosen

    @staticmethod
    def _build_tree(evals, chosen, endgame):
        children = []
        for _, info, a in sorted(evals, key=lambda e: e[0], reverse=True):
            if info["outcome"] > 0:
                caption = "win now"
            elif info["outcome"] < 0:
                caption = "loses"
            elif info["corner"]:
                caption = "corner"
            else:
                caption = f"mob {info['mobility']:+d}"
            children.append({
                "move": a,
                "value": info["mobility"],
                "caption": caption,
                "best": a == chosen,
                "text": (f"outcome={info['outcome']:+d}  corner={info['corner']}  "
                         f"X/C danger={info['danger']} (0 safe, 1 C, 2 X)  "
                         f"mobility={info['mobility']:+d}  discs={info['discs']}"),
                "children": [],
            })
        rule = ("endgame: win > corner > discs > mobility" if endgame
                else "win > corner > avoid X > avoid C > mobility > discs")
        return {"move": None, "label": "root", "caption": f"{len(evals)} moves",
                "text": "Priority: " + rule, "children": children}