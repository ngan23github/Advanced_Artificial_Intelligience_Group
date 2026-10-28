"""HeuristicAgent: chọn nước đi theo luật ưu tiên cố định (không tìm kiếm).

THỨ TỰ ƯU TIÊN (so sánh từ trên xuống; luật trên thắng tuyệt đối luật dưới,
luật dưới chỉ dùng để phân xử khi các luật trên hòa):

    1. Chiếm góc            Nước đi vào góc luôn được chọn trước mọi thứ khác.
    2. Tránh ô X            Ô chéo sát góc: (1,1) (1,6) (6,1) (6,6).
    3. Tránh ô C            Ô cạnh sát góc: (0,1) (1,0) (0,6) (1,7) (6,0) (7,1) (6,7) (7,6).
    4. Nhiều nước đi        Mobility = (số nước của mình) - (số nước của đối thủ) sau khi đi.
    5. Nhiều quân           Số quân của mình sau khi đi.
    6. Hòa hết              Chọn ngẫu nhiên (RNG riêng theo seed).

CÁC TRƯỜNG HỢP XUNG ĐỘT / QUY ƯỚC:
    a) Có nước vào góc nhưng nó làm giảm mobility -> VẪN chiếm góc (luật 1 > luật 4).
    b) Toàn bộ nước hợp lệ đều là ô X/C -> chọn cái "ít tệ nhất": ô thường > ô C > ô X
       (X tệ hơn C vì dễ cho đối thủ chiếm góc hơn). Hòa thì xét luật 4, 5.
    c) Ô X/C chỉ bị coi là nguy hiểm khi GÓC KỀ NÓ CÒN TRỐNG. Nếu góc đó đã có quân
       (của ai cũng được) thì ô này được coi là ô thường.
    d) Luật 4 thắng luật 5: thà ít quân hơn nhưng nhiều nước đi hơn (đầu/giữa ván,
       ăn nhiều quân thường là xấu).
    e) Ngoại lệ cuối ván: khi số ô trống <= endgame_empties, đổi sang
       (góc, số quân, mobility) và bỏ luật X/C, vì lúc này chỉ còn số quân quyết định
       thắng thua. Đặt endgame_empties=0 để tắt ngoại lệ này.
    f) Nước đi làm ván kết thúc ngay: so số quân cuối, thắng được điểm tuyệt đối cao nhất
       ở luật 4, thua thấp nhất.
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
WIN_SCORE = 1000  # mobility "vô cực" cho nước kết thúc ván


class HeuristicAgent(Agent):
    def __init__(self, seed=None, endgame_empties: int = 10, name: str = "Heuristic"):
        super().__init__()
        self.name = name
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

        if mine_moves == 0 and opp_moves == 0:  # ván kết thúc ngay sau nước này
            diff = mine_discs - opp_discs
            mobility = WIN_SCORE if diff > 0 else (-WIN_SCORE if diff < 0 else 0)
        else:
            mobility = mine_moves - opp_moves

        corner = int(action in CORNERS)
        danger = self._danger(board, action)
        info = {"corner": corner, "danger": danger, "mobility": mobility, "discs": mine_discs}
        if endgame:
            return (corner, mine_discs, mobility), info
        return (corner, -danger, mobility, mine_discs), info

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
            children.append({
                "move": a,
                "value": info["mobility"],
                "caption": "corner" if info["corner"] else f"mob {info['mobility']:+d}",
                "best": a == chosen,
                "text": (f"corner={info['corner']}  X/C danger={info['danger']} (0 safe, 1 C, 2 X)  "
                         f"mobility={info['mobility']:+d}  discs={info['discs']}"),
                "children": [],
            })
        rule = ("endgame: corner > discs > mobility" if endgame
                else "corner > avoid X > avoid C > mobility > discs")
        return {"move": None, "label": "root", "caption": f"{len(evals)} moves",
                "text": "Priority: " + rule, "children": children}
