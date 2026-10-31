"""MCTSAgent (Cấp 4): Monte Carlo Tree Search với UCT, cài bằng bitboard để chạy nhanh.

Bốn bước mỗi lần mô phỏng:
    1. Selection      đi xuống theo UCT khi nút đã mở rộng hết và chưa kết thúc.
    2. Expansion      thêm 1 nút con từ 1 nước chưa thử.
    3. Simulation     đi ngẫu nhiên (rollout) đến hết ván.
    4. Backpropagation lan truyền kết quả ngược lên gốc.

Điểm quan trọng với Othello:
- PASS: engine bỏ lượt khi người kế tiếp không có nước đi, nên một người có thể đi liên tiếp 2 lần. Cây xử lý
  giống hệt engine (xem `_next_player`): lượt KHÔNG đổi đều.
- Vì vậy mỗi nút lưu `mover` (người vừa đặt quân để tới nút đó) và phần thưởng được lan truyền THEO NGƯỜI CHƠI
  TẠI TỪNG NÚT: nút nào có mover == người ở gốc thì cộng r, ngược lại cộng 1 - r.
- Phần thưởng trong [0, 1]: thắng 1, hòa 0.5, thua 0. Nước cuối cùng = nút con được thăm NHIỀU NHẤT.

Tham số (khớp configs/agents.yaml):
    simulations      số mô phỏng mỗi nước đi.
    exploration_c    hằng số UCT (mặc định ~ sqrt(2)).
    rollout_policy   "random" | "heuristic" (ưu tiên góc, tránh ô X/C, còn lại ngẫu nhiên).
time_budget: nếu được truyền thì DỪNG THEO GIỜ (95% ngân sách, bỏ qua `simulations`); không truyền thì chạy đúng
`simulations` lần. Số mô phỏng thực tế luôn ghi vào stats()["simulations"].

Bitboard: dùng othello/bitboard.py (bit = row * 8 + col); kết quả khớp rules.py (đã kiểm thử).
"""

import math
import random
import warnings

from agents.base import Agent
from configs.constants import C_SQUARES, X_SQUARES
from othello.bitboard import CORNER_MASK, board_to_bb, flips_mask, legal_mask, popcount
from othello.encoding import BLACK, BOARD_SIZE, WHITE
from utils.search_utils import Deadline

ROLLOUT_POLICIES = ("random", "heuristic")

# ---------------------------------------------------------------- bitboard
# Dùng chung othello/bitboard.py của nhóm (bit i = ô (row, col), i = row * 8 + col).
_legal_bits = legal_mask
_to_bits = board_to_bb
_CORNER_BITS = CORNER_MASK


def _bit(pos) -> int:
    return 1 << (pos[0] * BOARD_SIZE + pos[1])


_XC_BITS = sum(_bit(p) for p in (*X_SQUARES, *C_SQUARES))


def _bits(x: int) -> list:
    """Danh sách bit đơn lẻ của x."""
    out = []
    while x:
        b = x & -x
        out.append(b)
        x ^= b
    return out


def _play(p: int, o: int, move: int):
    """Trả về (p', o') sau khi p đặt `move`."""
    f = flips_mask(p, o, move)
    return p | move | f, o & ~f


class _Node:
    __slots__ = ("parent", "action", "mover", "black", "white", "player", "untried", "children", "visits", "value")

    def __init__(self, black, white, player, parent=None, action=None, mover=None):
        self.parent = parent
        self.action = action        # (row, col) dẫn tới nút này (None ở gốc)
        self.mover = mover          # người vừa đi nước đó (None ở gốc)
        self.black = black
        self.white = white
        self.player = player        # người sẽ đi tại nút này (None nếu ván kết thúc)
        self.untried = []           # các bit nước đi chưa thử
        self.children = []
        self.visits = 0
        self.value = 0.0            # tổng phần thưởng theo góc nhìn của `mover`


def _next_player(black: int, white: int, last_mover: int):
    """Luật pass giống OthelloGame._advance_turn. Trả về người đi tiếp, hoặc None nếu hết ván."""
    nxt = -last_mover
    if nxt == BLACK:
        if _legal_bits(black, white):
            return BLACK
        if _legal_bits(white, black):
            return WHITE
    else:
        if _legal_bits(white, black):
            return WHITE
        if _legal_bits(black, white):
            return BLACK
    return None


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
        self.tree_depth = tree_depth      # độ sâu cây xuất cho UI (search_tree)
        self.tree_branch = tree_branch    # số nút con nhiều lượt thăm nhất giữ lại mỗi tầng
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
        black, white = _to_bits(game.board)
        root = _Node(black, white, root_player)
        self._init_untried(root)

        deadline = Deadline(time_budget) if time_budget is not None else None
        limit = None if deadline is not None else self.simulations   # có giờ -> dừng theo giờ
        nodes, max_depth, sims = 1, 0, 0

        while True:
            if deadline is not None:
                if sims > 0 and deadline.expired():
                    break
            elif sims >= limit:
                break

            # 1) SELECTION
            node, depth = root, 0
            while not node.untried and node.children:
                node = self._uct_child(node)
                depth += 1

            # 2) EXPANSION
            if node.untried:
                move = node.untried.pop()
                mover = node.player
                if mover == BLACK:
                    p, o = _play(node.black, node.white, move)
                    nb, nw = p, o
                else:
                    p, o = _play(node.white, node.black, move)
                    nb, nw = o, p
                child = _Node(nb, nw, _next_player(nb, nw, mover), parent=node,
                              action=divmod(move.bit_length() - 1, BOARD_SIZE), mover=mover)
                self._init_untried(child)
                node.children.append(child)
                node = child
                depth += 1
                nodes += 1

            # 3) SIMULATION (kết quả theo góc nhìn người đi ở gốc)
            reward_root = self._rollout(node.black, node.white, node.player, root_player)

            # 4) BACKPROPAGATION: theo `mover` của từng nút
            while node is not None:
                node.visits += 1
                if node.mover is not None:
                    node.value += reward_root if node.mover == root_player else 1.0 - reward_root
                node = node.parent

            sims += 1
            if depth > max_depth:
                max_depth = depth

        best_visits = max(ch.visits for ch in root.children)
        chosen = self.rng.choice([ch for ch in root.children if ch.visits == best_visits])

        self._stats = {
            "nodes": nodes,
            "simulations": sims,
            "depth": max_depth,
            "value": round(chosen.value / chosen.visits, 3),   # tỉ lệ thắng ước lượng của nước được chọn
        }
        self._tree = self._export_tree(root, chosen.action, sims)
        return chosen.action

    # ---------- các bước nội bộ ----------
    def _init_untried(self, node):
        if node.player is None:
            node.untried = []
            return
        p, o = (node.black, node.white) if node.player == BLACK else (node.white, node.black)
        node.untried = _bits(_legal_bits(p, o))
        self.rng.shuffle(node.untried)

    def _uct_child(self, node):
        log_n = math.log(node.visits)
        c = self.c
        # value/visits: tỉ lệ thắng của người chọn tại `node` (chính là mover của nút con)
        return max(node.children, key=lambda ch: ch.value / ch.visits + c * math.sqrt(log_n / ch.visits))

    def _pick(self, mv: int) -> int:
        if self.rollout_policy == "heuristic":
            corners = mv & _CORNER_BITS
            if corners:
                mv = corners
            else:
                safe = mv & ~_XC_BITS
                if safe:
                    mv = safe
        bits = _bits(mv)
        return bits[self.rng.randrange(len(bits))]

    def _rollout(self, black: int, white: int, player, root_player) -> float:
        """Đi đến hết ván, luật pass như engine. Trả về 1 / 0.5 / 0 theo góc nhìn root_player."""
        if player is None:
            cur, p, o = BLACK, black, white     # ván đã kết thúc: chỉ cần đếm quân
        else:
            cur = player
            p, o = (black, white) if cur == BLACK else (white, black)
        while True:
            mv = _legal_bits(p, o)
            if not mv:
                if not _legal_bits(o, p):
                    break                        # không ai đi được -> hết ván
                p, o, cur = o, p, -cur           # pass
                continue
            p, o = _play(p, o, self._pick(mv))
            p, o, cur = o, p, -cur
        mine_black = popcount(p) if cur == BLACK else popcount(o)
        mine_white = popcount(o) if cur == BLACK else popcount(p)
        diff = (mine_black - mine_white) * root_player
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