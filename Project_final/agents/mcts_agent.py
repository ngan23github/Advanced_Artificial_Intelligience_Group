"""MCTSAgent (Cấp 4): Monte Carlo Tree Search với UCT.

Bốn bước mỗi lần mô phỏng: chọn (UCT) -> mở rộng 1 nút -> mô phỏng ngẫu nhiên đến hết ván -> lan truyền kết quả.

Chi tiết quan trọng với Othello:
- Pass do engine xử lý nên MỘT người có thể đi liên tiếp 2 lần. Vì vậy mỗi nút lưu `mover` (người vừa đặt quân
  để tới nút đó) thay vì giả định lượt đổi đều; phần thưởng lan truyền theo `mover` của từng nút.
- Phần thưởng nằm trong [0, 1]: thắng 1, hòa 0.5, thua 0 (theo góc nhìn người đi của nút đó).
- Khi chọn nước cuối cùng lấy nút con được thăm NHIỀU NHẤT (ổn định hơn lấy tỉ lệ thắng cao nhất).

Tham số (khớp configs/agents.yaml):
    simulations       số mô phỏng tối đa cho mỗi nước đi.
    exploration_c     hằng số UCT (mặc định sqrt(2) ~ 1.414).
    rollout_policy    "random" (đi ngẫu nhiên) | "heuristic" (ưu tiên góc, tránh ô X/C, còn lại ngẫu nhiên).
Có time_budget: dừng ở lúc nào đến trước, đủ `simulations` hoặc hết 95% thời gian.
"""

import math
import random
import warnings

from agents.base import Agent
from configs.constants import C_SQUARES, CORNERS, X_SQUARES
from othello.encoding import opponent
from othello.rules import apply_move, count_discs, legal_moves
from utils.search_utils import Deadline

ROLLOUT_POLICIES = ("random", "heuristic")


class _Node:
    __slots__ = ("parent", "action", "mover", "game", "untried", "children", "visits", "value")

    def __init__(self, game, parent=None, action=None, mover=None, rng=None):
        self.parent = parent
        self.action = action          # nước đi dẫn tới nút này (None ở gốc)
        self.mover = mover            # người vừa đi nước đó (None ở gốc)
        self.game = game              # trạng thái tại nút (đã clone, độc lập)
        self.untried = game.legal_actions()   # [] nếu ván đã kết thúc
        if rng is not None:
            rng.shuffle(self.untried)
        self.children = []
        self.visits = 0
        self.value = 0.0              # tổng phần thưởng theo góc nhìn của `mover`


class MCTSAgent(Agent):
    def __init__(
        self,
        simulations: int = 1000,
        exploration_c: float = 1.414,
        rollout_policy: str = "random",
        seed: int = None,
        name: str = "MCTS",
        tree_depth: int = 2,
        tree_branch: int = 5,
        **kwargs
    ):
        super().__init__()
        if kwargs:
            warnings.warn(f"MCTSAgent: bỏ qua tham số không biết: {sorted(kwargs)}", stacklevel=2)
        if simulations < 1:
            raise ValueError("simulations phải >= 1")
        if exploration_c < 0:
            raise ValueError("exploration_c phải >= 0")
        if rollout_policy not in ROLLOUT_POLICIES:
            raise ValueError(f"rollout_policy không biết: '{rollout_policy}'. Hợp lệ: {list(ROLLOUT_POLICIES)}")
        self.simulations = int(simulations)
        self.c = float(exploration_c)
        self.rollout_policy = rollout_policy
        self.name = name
        self.tree_depth = tree_depth      # độ sâu cây trả về cho UI (search_tree)
        self.tree_branch = tree_branch    # số nút con nhiều lượt thăm nhất giữ lại ở mỗi tầng
        self.rng = random.Random(seed)
        self._stats = {"nodes": 0, "simulations": 0, "depth": 0, "value": 0.0}
        self._tree = None

    # ---------- API chung của Agent ----------
    def reset(self) -> None:
        self._stats = {"nodes": 0, "simulations": 0, "depth": 0, "value": 0.0}
        self._tree = None

    def stats(self) -> dict:
        return dict(self._stats)

    def search_tree(self):
        return self._tree

    def select_action(self, game, time_budget: float = None):
        actions = game.legal_actions()
        if not actions:
            return None
        if len(actions) == 1:
            self._stats = {"nodes": 1, "simulations": 0, "depth": 0, "value": 0.0}
            self._tree = None
            return actions[0]

        root_player = game.current_player
        root = _Node(game.clone(), rng=self.rng)
        deadline = Deadline(time_budget) if time_budget is not None else None
        nodes, max_depth, sims = 1, 0, 0

        while sims < self.simulations:
            if deadline is not None and sims > 0 and deadline.expired():
                break

            # 1) CHỌN: đi xuống theo UCT khi nút đã mở rộng hết và chưa kết thúc
            node, depth = root, 0
            while not node.untried and node.children:
                node = self._uct_child(node)
                depth += 1

            # 2) MỞ RỘNG: thêm 1 nút con từ 1 nước chưa thử
            if node.untried:
                action = node.untried.pop()
                mover = node.game.current_player
                child_game = node.game.clone()
                child_game.step(action)
                child = _Node(child_game, parent=node, action=action, mover=mover, rng=self.rng)
                node.children.append(child)
                node = child
                depth += 1
                nodes += 1

            # 3) MÔ PHỎNG: đi (gần) ngẫu nhiên đến hết ván, kết quả theo góc nhìn người đi ở gốc
            reward_root = self._rollout(node.game.board, node.game.current_player, root_player)

            # 4) LAN TRUYỀN: mỗi nút nhận phần thưởng theo góc nhìn `mover` của nó
            while node is not None:
                node.visits += 1
                if node.mover is not None:
                    node.value += reward_root if node.mover == root_player else 1.0 - reward_root
                node = node.parent

            sims += 1
            max_depth = max(max_depth, depth)

        best = max(root.children, key=lambda ch: ch.visits)
        top = [ch for ch in root.children if ch.visits == best.visits]
        chosen = self.rng.choice(top)

        self._stats = {
            "nodes": nodes,
            "simulations": sims,
            "depth": max_depth,
            "value": round(chosen.value / chosen.visits, 3),   # tỉ lệ thắng ước lượng của nước được chọn
        }
        self._tree = self._export_tree(root, chosen.action, sims)
        return chosen.action

    # ---------- các bước nội bộ ----------
    def _uct_child(self, node):
        log_n = math.log(node.visits)
        c = self.c
        # q/n: tỉ lệ thắng theo góc nhìn người chọn tại `node` (= mover của nút con)
        return max(node.children, key=lambda ch: ch.value / ch.visits + c * math.sqrt(log_n / ch.visits))

    def _pick(self, moves):
        if self.rollout_policy == "heuristic":
            corners = [a for a in moves if a in CORNERS]
            if corners:
                moves = corners
            else:
                safe = [a for a in moves if a not in X_SQUARES and a not in C_SQUARES]
                if safe:
                    moves = safe
        return moves[self.rng.randrange(len(moves))]

    def _rollout(self, board, player, root_player) -> float:
        """Đi đến hết ván (cùng luật pass với engine); trả về 1 / 0.5 / 0 theo góc nhìn root_player."""
        while True:
            moves = legal_moves(board, player)
            if not moves:
                player = opponent(player)          # pass
                moves = legal_moves(board, player)
                if not moves:
                    break                          # không ai đi được -> hết ván
            action = self._pick(moves)
            board = apply_move(board, player, action[0], action[1])
            player = opponent(player)
        black, white = count_discs(board)
        diff = (black - white) * root_player
        return 1.0 if diff > 0 else (0.0 if diff < 0 else 0.5)

    # ---------- xuất cây cho UI (cùng định dạng với HeuristicAgent.search_tree) ----------
    def _export_tree(self, root, chosen_action, sims):
        def build(node, depth, is_root):
            kids = sorted(node.children, key=lambda ch: ch.visits, reverse=True)[: self.tree_branch]
            if depth >= self.tree_depth:
                kids = []
            rate = 0.0 if is_root else node.value / max(node.visits, 1)
            return {
                "move": node.action,
                "label": "root" if is_root else None,
                "value": round(rate, 3),
                "caption": f"{sims} sims" if is_root else f"{node.visits}v {rate:.0%}",
                "best": (not is_root) and depth == 1 and node.action == chosen_action,
                "text": (f"MCTS: {sims} mô phỏng, c={self.c}, rollout={self.rollout_policy}" if is_root else
                         f"visits={node.visits}  win-rate={rate:.1%} (góc nhìn người vừa đi)"),
                "children": [build(ch, depth + 1, False) for ch in kids],
            }
        return build(root, 0, True)
