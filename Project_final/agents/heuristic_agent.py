"""HeuristicAgent: chọn nước đi theo luật ưu tiên cố định (không tìm kiếm sâu, chỉ nhìn 1 nước).

CÁC LUẬT (tên dùng trong `priorities` ở configs/agents.yaml), thứ tự MẶC ĐỊNH từ trên xuống;
luật trên thắng tuyệt đối luật dưới, luật dưới chỉ phân xử khi các luật trên hòa:

    win_now            Thắng ngay: nước kết thúc ván mà mình nhiều quân hơn -> chọn; nước kết thúc ván mà mình thua -> tránh.
    take_corner        Chiếm góc (kiểm soát vị trí: góc không bao giờ bị lật).
    avoid_x_square     Tránh ô X, ô chéo sát góc: (1,1) (1,6) (6,1) (6,6).
    avoid_c_square     Tránh ô C, ô cạnh sát góc: (0,1) (1,0) (0,6) (1,7) (6,0) (7,1) (6,7) (7,6).
    maximize_mobility  Chặn đối thủ: mobility = (số nước của mình) - (số nước của đối thủ) sau khi đi.
    maximize_discs     Nhiều quân của mình sau khi đi.
    (hết luật)         Còn hòa thì chọn ngẫu nhiên (RNG riêng theo seed).

THAM SỐ (khai báo trong `params:` của configs/agents.yaml):
    priorities         list tên luật theo thứ tự ưu tiên giảm dần. Bỏ luật khỏi list = tắt luật đó (ablation);
                       đổi thứ tự = đổi ưu tiên (tune). Tên sai / trùng -> ValueError. List rỗng = chọn ngẫu nhiên.
    endgame_empties    xem trường hợp (f) dưới đây.

CÁC TRƯỜNG HỢP XUNG ĐỘT / QUY ƯỚC (với thứ tự mặc định):
    a) Có nước vào góc nhưng làm giảm mobility -> VẪN chiếm góc (take_corner > maximize_mobility).
    b) Vừa có nước thắng ngay vừa có nước vào góc -> chọn nước thắng ngay (win_now > take_corner).
    c) Toàn bộ nước hợp lệ đều là ô X/C -> chọn cái "ít tệ nhất": ô thường > ô C > ô X
       (X tệ hơn C vì dễ cho đối thủ chiếm góc hơn). Hòa thì xét luật tiếp theo.
    d) Ô X/C chỉ bị coi là nguy hiểm khi GÓC KỀ NÓ CÒN TRỐNG. Góc đó đã có quân (của ai cũng được)
       thì ô này được coi là ô thường.
    e) maximize_mobility > maximize_discs: thà ít quân hơn nhưng nhiều nước đi hơn (đầu/giữa ván,
       ăn nhiều quân thường là xấu).
    f) Ngoại lệ cuối ván: khi số ô trống <= endgame_empties (mặc định 10), thứ tự đổi thành
       win_now, take_corner, maximize_discs, maximize_mobility (chỉ giữ luật có trong `priorities`) và bỏ luật X/C,
       vì lúc này chỉ còn số quân quyết định thắng thua. endgame_empties=0 để tắt ngoại lệ này.
"""

import random

from agents.base import Agent
from othello.encoding import BLACK, EMPTY, opponent
from othello.rules import apply_move, count_discs, legal_moves

CORNERS = frozenset({(0, 0), (0, 7), (7, 0), (7, 7)})
# ô X / ô C  ->  góc kề nó
X_SQUARES = {(1, 1): (0, 0), (1, 6): (0, 7), (6, 1): (7, 0), (6, 6): (7, 7)}
C_SQUARES = {
    (0, 1): (0, 0), (1, 0): (0, 0),
    (0, 6): (0, 7), (1, 7): (0, 7),
    (6, 0): (7, 0), (7, 1): (7, 0),
    (6, 7): (7, 7), (7, 6): (7, 7),
}


RULE_NAMES = ("win_now", "take_corner", "avoid_x_square", "avoid_c_square", "maximize_mobility", "maximize_discs")
DEFAULT_PRIORITIES = list(RULE_NAMES)
ENDGAME_ORDER = ("win_now", "take_corner", "maximize_discs", "maximize_mobility")


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
    def __init__(self, seed=None, priorities=None, endgame_empties: int = 10, name: str = "Heuristic"):
        super().__init__()
        pr = list(DEFAULT_PRIORITIES if priorities is None else priorities)
        unknown = [r for r in pr if r not in RULE_NAMES]
        if unknown:
            raise ValueError(f"Luật không biết: {unknown}. Hợp lệ: {list(RULE_NAMES)}")
        if len(set(pr)) != len(pr):
            raise ValueError(f"priorities có luật bị trùng: {pr}")
        self.name = name
        self.priorities = pr
        self._endgame_order = [r for r in ENDGAME_ORDER if r in pr]
        self.endgame_empties = endgame_empties
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
