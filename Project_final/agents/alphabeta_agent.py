"""AlphaBetaAgent: Minimax có cắt tỉa Alpha-Beta cho Othello 8x8 (cấp 3 của đề).

THUẬT TOÁN
    Negamax với cửa sổ (alpha, beta). Hết ván / hết độ sâu thì chấm điểm bằng hàm lượng giá.
    Điểm luôn tính theo góc nhìn của NGƯỜI ĐANG ĐẾN LƯỢT tại nút đó (dương = tốt cho người đó).
    Pass: nếu người đến lượt không có nước đi mà đối thủ còn thì lượt chuyển sang đối thủ (KHÔNG tốn độ sâu),
    giống hệt engine. Cả hai đều hết nước = hết ván, điểm = ±(100000 + chênh lệch quân).

THAM SỐ (khai báo trong `params:` của configs/agents.yaml)
    depth          độ sâu tìm kiếm cố định (mặc định 4). Dùng khi time_budget=None.
    pruning        True = Alpha-Beta; False = Minimax thuần (cho ablation). Hai chế độ phải cho CÙNG nước đi
                   và cùng giá trị gốc, chỉ khác số nút và thời gian.
    move_ordering  True = duyệt nước theo bảng giá trị ô (góc trước, ô X/C sau) để cắt tỉa sớm hơn;
                   False = duyệt theo thứ tự ô (hàng trước, cột sau).
    eval           dict bật/tắt thành phần hàm lượng giá:
                     disc_diff    chênh lệch số quân (%)
                     mobility     chênh lệch số nước đi (%)
                     corners      số góc chiếm được
                     x_c_squares  phạt ô X / ô C khi góc kề còn trống (đối thủ chiếm thì cộng cho mình)
                     stability    quân ổn định dọc cạnh, tính từ góc đã chiếm (xấp xỉ, chỉ tính quân cạnh bám góc)
                   Khóa không ghi thì dùng mặc định: stability=False, các khóa còn lại True.
    weights        dict hệ số nhân cho từng thành phần (mặc định đều 1.0). Dùng để tune.
    max_depth      chỉ dùng khi có time_budget: chặn trên độ sâu lặp sâu (mặc định không chặn).

THỜI GIAN (API.md: agent tìm kiếm theo thời gian phải tôn trọng time_budget)
    time_budget=None  -> tìm đúng `depth` tầng.
    time_budget=giây  -> lặp sâu dần (1, 2, 3, ...) đến khi hết ~95% thời gian; trả nước của tầng sâu nhất hoàn tất.
                         Tầng 1 luôn hoàn tất để chắc chắn có nước đi. Tham số `depth` bị bỏ qua.

HIỆU NĂNG
    Bàn cờ được chuyển sang bitboard (2 số nguyên 64 bit) trong lúc tìm kiếm cho nhanh. Sinh nước đi và lật quân
    được test đối chiếu với othello/rules.py (tests/test_alphabeta_agent.py), nên kết quả khớp engine.

stats() -> {"nodes": số nút duyệt, "simulations": 0, "depth": độ sâu đạt được, "value": giá trị gốc theo góc nhìn mình}
search_tree() -> cây 3 tầng đầu cho panel cây của UI (xem docstring ui/tree.py); nút bị cắt tỉa đánh dấu "pruned".
"""

import time

from agents.base import Agent

# ---------------------------------------------------------------- bitboard
FULL = (1 << 64) - 1
NOT_A = 0xFEFEFEFEFEFEFEFE   # bỏ cột 0
NOT_H = 0x7F7F7F7F7F7F7F7F   # bỏ cột 7
# (số bit dịch, dịch trái?, mặt nạ chống tràn hàng). bit = row*8 + col, khớp action_to_index.
_DIRS = ((1, True, NOT_A), (1, False, NOT_H), (8, True, FULL), (8, False, FULL),
         (9, True, NOT_A), (9, False, NOT_H), (7, True, NOT_H), (7, False, NOT_A))

_pop = int.bit_count if hasattr(int, "bit_count") else (lambda x: bin(x).count("1"))


def _moves(me: int, opp: int) -> int:
    """Bitboard các ô `me` đi được."""
    empty = ~(me | opp) & FULL
    res = 0
    for n, left, mask in _DIRS:
        if left:
            t = ((me << n) & mask) & opp
            for _ in range(5):
                t |= ((t << n) & mask) & opp
            res |= ((t << n) & mask) & empty
        else:
            t = ((me >> n) & mask) & opp
            for _ in range(5):
                t |= ((t >> n) & mask) & opp
            res |= ((t >> n) & mask) & empty
    return res


def _flips(me: int, opp: int, move: int) -> int:
    """Bitboard các quân bị lật khi `me` đặt vào ô `move` (1 bit)."""
    f = 0
    for n, left, mask in _DIRS:
        line = 0
        x = ((move << n) & mask) if left else ((move >> n) & mask)
        while x & opp:
            line |= x
            x = ((x << n) & mask) if left else ((x >> n) & mask)
        if x & me:
            f |= line
    return f


def _to_bits(board, player):
    me = opp = 0
    for i, v in enumerate(board.ravel().tolist()):
        if v == player:
            me |= 1 << i
        elif v == -player:
            opp |= 1 << i
    return me, opp


def _bits_of(x):
    while x:
        b = x & -x
        yield b.bit_length() - 1
        x ^= b


# ---------------------------------------------------------------- hàm lượng giá
WIN = 100000
INF = 10 ** 9
CORNER_BITS = (0, 7, 56, 63)
CORNER_MASK = sum(1 << i for i in CORNER_BITS)
# với mỗi góc: (bit góc, bit ô X, [bit ô C], [2 đường cạnh xuất phát từ góc])
_CORNER_INFO = (
    (1 << 0, 1 << 9, (1 << 1, 1 << 8), ((1, 2, 3, 4, 5, 6, 7), (8, 16, 24, 32, 40, 48, 56))),
    (1 << 7, 1 << 14, (1 << 6, 1 << 15), ((6, 5, 4, 3, 2, 1, 0), (15, 23, 31, 39, 47, 55, 63))),
    (1 << 56, 1 << 49, (1 << 48, 1 << 57), ((57, 58, 59, 60, 61, 62, 63), (48, 40, 32, 24, 16, 8, 0))),
    (1 << 63, 1 << 54, (1 << 55, 1 << 62), ((62, 61, 60, 59, 58, 57, 56), (55, 47, 39, 31, 23, 15, 7))),
)
EVAL_KEYS = ("disc_diff", "mobility", "corners", "x_c_squares", "stability")
DEFAULT_EVAL = {"disc_diff": True, "mobility": True, "corners": True, "x_c_squares": True, "stability": False}
DEFAULT_WEIGHTS = {k: 1.0 for k in EVAL_KEYS}

# bảng giá trị ô chỉ để SẮP XẾP nước đi (không dùng trong hàm lượng giá)
_POS = [
    [100, -20, 10, 5, 5, 10, -20, 100],
    [-20, -50, -2, -2, -2, -2, -50, -20],
    [10, -2, 1, 1, 1, 1, -2, 10],
    [5, -2, 1, 0, 0, 1, -2, 5],
    [5, -2, 1, 0, 0, 1, -2, 5],
    [10, -2, 1, 1, 1, 1, -2, 10],
    [-20, -50, -2, -2, -2, -2, -50, -20],
    [100, -20, 10, 5, 5, 10, -20, 100],
]
_POS_FLAT = [v for row in _POS for v in row]


def _terminal(me: int, opp: int) -> float:
    d = _pop(me) - _pop(opp)
    return (WIN + d) if d > 0 else ((-WIN + d) if d < 0 else 0)


def _fmt(v: float) -> str:
    if v >= WIN / 2:
        return "win"
    if v <= -WIN / 2:
        return "loss"
    return f"{v:+.0f}"


class _Timeout(Exception):
    pass


TREE_PLY = 3   # số tầng đầu được ghi vào cây cho UI


class AlphaBetaAgent(Agent):
    def __init__(self, depth: int = 4, pruning: bool = True, move_ordering: bool = True, eval=None,
                 weights=None, max_depth=None, name: str = "AlphaBeta"):
        super().__init__()
        if depth < 1:
            raise ValueError("depth phải >= 1")
        ev = dict(DEFAULT_EVAL)
        for k, v in (eval or {}).items():
            if k not in EVAL_KEYS:
                raise ValueError(f"eval: khóa không biết '{k}'. Hợp lệ: {list(EVAL_KEYS)}")
            ev[k] = bool(v)
        w = dict(DEFAULT_WEIGHTS)
        for k, v in (weights or {}).items():
            if k not in EVAL_KEYS:
                raise ValueError(f"weights: khóa không biết '{k}'. Hợp lệ: {list(EVAL_KEYS)}")
            w[k] = float(v)
        self.name = name
        self.depth, self.pruning, self.move_ordering = depth, bool(pruning), bool(move_ordering)
        self.eval_flags, self.weights, self.max_depth = ev, w, max_depth
        self._nodes, self._deadline = 0, None
        self._stats = {"nodes": 0, "simulations": 0, "depth": 0, "value": 0.0}
        self._tree = None

    def reset(self) -> None:
        self._nodes = 0

    def stats(self) -> dict:
        return dict(self._stats)

    def search_tree(self):
        return self._tree

    # ---------------------------------------------------------------- lượng giá
    def _eval(self, me: int, opp: int) -> float:
        """Điểm của thế cờ theo góc nhìn `me` (người đến lượt)."""
        mm, om = _pop(_moves(me, opp)), _pop(_moves(opp, me))
        if mm == 0 and om == 0:
            return _terminal(me, opp)
        f, w, s = self.eval_flags, self.weights, 0.0
        if f["disc_diff"]:
            m, o = _pop(me), _pop(opp)
            s += w["disc_diff"] * 100.0 * (m - o) / (m + o)
        if f["mobility"] and mm + om:
            s += w["mobility"] * 100.0 * (mm - om) / (mm + om)
        if f["corners"]:
            s += w["corners"] * 25.0 * (_pop(me & CORNER_MASK) - _pop(opp & CORNER_MASK))
        if f["x_c_squares"]:
            occ = me | opp
            t = 0.0
            for corner, x, cs, _ in _CORNER_INFO:
                if occ & corner:
                    continue            # góc đã có quân thì ô X/C không còn nguy hiểm
                if me & x:
                    t -= 12.5
                elif opp & x:
                    t += 12.5
                for c in cs:
                    if me & c:
                        t -= 6.25
                    elif opp & c:
                        t += 6.25
            s += w["x_c_squares"] * t
        if f["stability"]:
            s += w["stability"] * 5.0 * (self._stable(me) - self._stable(opp))
        return s

    @staticmethod
    def _stable(x: int) -> int:
        """Số quân ổn định (xấp xỉ): góc + quân liền nhau dọc 2 cạnh xuất phát từ góc đó."""
        n = 0
        for corner, _, _, edges in _CORNER_INFO:
            if not x & corner:
                continue
            n += 1
            for line in edges:
                for i in line:
                    if x >> i & 1:
                        n += 1
                    else:
                        break
        return n

    def evaluate_board(self, board, player) -> float:
        """Tiện cho test/phân tích: điểm của board (numpy) theo góc nhìn `player`."""
        me, opp = _to_bits(board, player)
        return self._eval(me, opp)

    # ---------------------------------------------------------------- tìm kiếm
    def _order(self, mv: int) -> list:
        idxs = list(_bits_of(mv))   # tăng dần theo chỉ số ô
        if self.move_ordering:
            idxs.sort(key=lambda i: (-_POS_FLAT[i], i))
        return idxs

    def _search(self, me, opp, depth, alpha, beta, maxi, ply, rec):
        """Negamax. maxi = True nếu `me` là người chơi gốc. rec = dict nút (để ghi cây) hoặc None."""
        self._nodes += 1
        if self._deadline is not None and (self._nodes & 1023) == 0 and time.perf_counter() > self._deadline:
            raise _Timeout
        if depth == 0:
            return self._eval(me, opp)
        mv = _moves(me, opp)
        if not mv:
            if not _moves(opp, me):
                return _terminal(me, opp)
            return -self._search(opp, me, depth, -beta, -alpha, not maxi, ply, rec)   # pass, không tốn độ sâu
        order = self._order(mv)
        record = rec is not None and ply < TREE_PLY
        best = -INF
        for k, idx in enumerate(order):
            bit = 1 << idx
            fl = _flips(me, opp, bit)
            nme, nopp = me | bit | fl, opp & ~fl
            child = None
            if record:
                child = {"move": divmod(idx, 8), "children": []}
                rec["children"].append(child)
            a_c, b_c = (-beta, -alpha) if self.pruning else (-INF, INF)
            r = self._search(nopp, nme, depth - 1, a_c, b_c, not maxi, ply + 1, child)
            self._annotate(child, r, a_c, b_c, not maxi)
            score = -r
            if score > best:
                best = score
                if record:
                    rec["_best"] = child
            if self.pruning:
                if score > alpha:
                    alpha = score
                if alpha >= beta:      # cắt tỉa: các nước còn lại không cần xét
                    if record:
                        for j in order[k + 1:]:
                            rec["children"].append({"move": divmod(j, 8), "pruned": True, "children": []})
                    break
        return best

    @staticmethod
    def _annotate(rec, r, a, b, maxi):
        """Ghi giá trị (theo góc nhìn người chơi gốc) và loại cận (chính xác / <= / >=) vào nút của cây."""
        if rec is None:
            return
        kind = "le" if r <= a else ("ge" if r >= b else "eq")   # trong hệ quy chiếu của nút
        v = r if maxi else -r
        if not maxi and kind != "eq":
            kind = "ge" if kind == "le" else "le"                # đổi dấu thì đổi chiều cận
        rec["value"] = round(v, 1)
        rec["caption"] = _fmt(v) if kind == "eq" else ("<=" if kind == "le" else ">=") + _fmt(v)
        if abs(a) < INF / 2:
            rec["alpha"], rec["beta"] = round(a, 1), round(b, 1)
        note = {"eq": "exact value", "le": "upper bound (true value <= shown)", "ge": "lower bound (true value >= shown)"}[kind]
        rec["text"] = note + "; value is from the root player's view"

    def _search_root(self, me, opp, depth, order, first):
        if first is not None:
            order = [first] + [i for i in order if i != first]
        root = {"move": None, "label": "root", "children": []}
        alpha, beta = -INF, INF
        best, best_idx, best_child = -INF, None, None
        for idx in order:
            bit = 1 << idx
            fl = _flips(me, opp, bit)
            nme, nopp = me | bit | fl, opp & ~fl
            child = {"move": divmod(idx, 8), "children": []}
            root["children"].append(child)
            a_c, b_c = (-beta, -alpha) if self.pruning else (-INF, INF)
            r = self._search(nopp, nme, depth - 1, a_c, b_c, False, 1, child)
            self._annotate(child, r, a_c, b_c, False)
            score = -r
            if score > best:               # nghiêm ngặt: chọn nước đầu tiên đạt max -> tất định
                best, best_idx, best_child = score, idx, child
            if self.pruning and score > alpha:
                alpha = score
        root["_best"] = best_child
        return best_idx, best, root

    @staticmethod
    def _finish_tree(root, depth, value):
        n = root
        while n.get("_best") is not None:        # đánh dấu đường đi tốt nhất
            n = n["_best"]
            n["best"] = True
        stack = [root]
        while stack:                              # dọn khóa tạm
            x = stack.pop()
            x.pop("_best", None)
            stack.extend(x["children"])
        root["value"] = round(value, 1)
        root["caption"] = f"depth {depth}"
        root["text"] = f"Search depth {depth}; best value {_fmt(value)} for the side to move"
        return root

    def select_action(self, game, time_budget=None):
        board, player = game.board, game.current_player   # chỉ đọc
        me, opp = _to_bits(board, player)
        order = self._order(_moves(me, opp))
        self._nodes = 0
        if len(order) == 1:                                  # nước duy nhất: khỏi tìm kiếm
            idx = order[0]
            self._stats = {"nodes": 1, "simulations": 0, "depth": 0, "value": 0.0}
            self._tree = {"move": None, "label": "root", "caption": "forced", "text": "Only one legal move.",
                          "children": [{"move": divmod(idx, 8), "best": True, "caption": "forced", "children": []}]}
            return divmod(idx, 8)

        empties = 64 - _pop(me | opp)
        if time_budget is None:
            depths, limit = [self.depth], None
        else:
            cap = min(empties, self.max_depth or empties)
            depths, limit = range(1, cap + 1), time.perf_counter() + 0.95 * time_budget
        best_idx = tree = None
        value, reached, prev = 0.0, 0, None
        for d in depths:
            self._deadline = limit if d > 1 else None        # tầng 1 luôn hoàn tất
            try:
                idx, score, root = self._search_root(me, opp, d, order, prev)
            except _Timeout:
                break
            best_idx, value, reached, prev = idx, score, d, idx
            tree = self._finish_tree(root, d, score)
        self._deadline = None
        self._stats = {"nodes": self._nodes, "simulations": 0, "depth": reached, "value": round(value, 2)}
        self._tree = tree
        return divmod(best_idx, 8)
