"""Panel vẽ cây tìm kiếm (hiện bên phải cửa sổ game, bật/tắt bằng phím T).

======================================================================
AGENT MUỐN HIỆN CÂY: thêm 1 hàm (TÙY CHỌN, agent không có thì UI chỉ báo "no tree")
======================================================================
    def search_tree(self) -> dict | None:
        '''Cây của NƯỚC VỪA ĐI (gọi ngay sau select_action). Trả về node gốc.'''

Mỗi node là 1 dict, mọi khóa đều tùy chọn trừ "children":
    "move"     (row, col) nước dẫn tới node này; gốc để None
    "label"    chữ hiện trong ô (mặc định: tên ô như "d3", gốc là "root")
    "caption"  chữ nhỏ dòng 2 trong ô (mặc định tự ghép từ value / visits)
    "value"    điểm của node (Alpha-Beta: giá trị minimax, MCTS: Q)
    "visits"   số lần thăm (MCTS)
    "alpha", "beta"   cửa sổ alpha-beta tại node
    "pruned"   True nếu node bị cắt tỉa (vẽ mờ, không có con)
    "best"     True nếu node nằm trên đường đi tốt nhất (vẽ xanh)
    "text"     mô tả dài, hiện ở khung chi tiết khi rê chuột
    "children" list các node con, SẮP XẾP theo thứ tự muốn hiển thị (tốt nhất trước)

Chuỗi "move" từ gốc xuống phải là chuỗi nước hợp lệ từ vị trí lúc agent bắt đầu nghĩ
(engine tự xử lý pass), UI dùng nó để dựng lại bàn cờ khi rê chuột.
Cây to cũng không sao: UI chỉ vẽ phần đã mở (tối đa 10 con mỗi node, 3 tầng, có nút "+N more").

Thao tác: click = mở/đóng node, chuột phải = zoom vào node (chuột phải lần nữa ở gốc = quay lại),
lăn chuột = cuộn, rê chuột = xem chi tiết + bàn cờ sau nước đó.
"""

import pygame
import pygame.gfxdraw as gfx

from othello.encoding import BLACK, WHITE

TREE_W = 440
HEAD_H = 72
INFO_H = 150
ROW_H, BOX_W, BOX_H, PAD = 44, 84, 38, 12
MAX_DEPTH = 3   # số tầng dưới gốc được mở trong 1 lần nhìn
MAX_KIDS = 10   # số con tối đa hiện ban đầu của 1 node

C_BG = (24, 26, 31)
C_CARD = (42, 46, 55)
C_ACCENT = (46, 125, 90)
C_BTN = (58, 63, 74)
C_OFF = (36, 39, 46)
C_TEXT = (236, 238, 242)
C_DIM = (135, 142, 155)
C_WARN = (255, 196, 80)
NAME = {BLACK: "Black", WHITE: "White"}


def sq(action) -> str:
    return "abcdefgh"[action[1]] + str(action[0] + 1)


def fit(font, text: str, width: int) -> str:
    if font.size(text)[0] <= width:
        return text
    while len(text) > 1 and font.size(text + "..")[0] > width:
        text = text[:-1]
    return text + ".."


def wrap_text(font, text: str, width: int) -> list:
    lines, cur = [], ""
    for word in text.split():
        trial = (cur + " " + word).strip()
        if font.size(trial)[0] <= width or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines or [""]


def fmt_num(v) -> str:
    if isinstance(v, bool):
        return str(v)
    if isinstance(v, int):
        return f"{v:,}"
    if isinstance(v, float):
        return f"{v:+.2f}"
    return str(v)


def compact(n) -> str:
    n = int(n)
    return f"{n / 1000:.1f}k" if n >= 1000 else str(n)


def _disc(surf, color, center, r):
    gfx.filled_circle(surf, center[0], center[1], r, color)
    gfx.aacircle(surf, center[0], center[1], r, color)


def draw_empty_panel(scr, fonts, rect, note):
    scr.fill(C_BG, rect)
    pygame.draw.line(scr, C_CARD, (rect.x, 0), (rect.x, rect.h), 2)
    scr.blit(fonts.h.render("Search tree", True, C_TEXT), (rect.x + 14, 10))
    for i, ln in enumerate(wrap_text(fonts.body, note, rect.w - 40)):
        scr.blit(fonts.body.render(ln, True, C_DIM), (rect.x + 20, 90 + 26 * i))


class Rec:
    """Một ô đang hiện trên màn hình (node thật hoặc ô '+N more')."""

    __slots__ = ("node", "depth", "path", "kids", "y", "more_of", "more_n")

    def __init__(self, node, depth, path, more_of=None, more_n=0):
        self.node, self.depth, self.path = node, depth, path
        self.more_of, self.more_n = more_of, more_n
        self.kids, self.y = [], 0.0


class TreeView:
    def __init__(self, root: dict, root_game, chosen, title: str):
        self.root_game = root_game  # vị trí lúc agent bắt đầu nghĩ
        self.chosen = tuple(chosen)
        self.title = title
        self.stack = [(root, [])]   # (node đang là gốc khung nhìn, đường nước từ gốc thật)
        self.flags = {}             # id(node) -> {"open", "all", "mover"}; không sửa dữ liệu của agent
        self.scroll = 0
        self._center = True  # lần vẽ đầu / sau khi zoom: cuộn để gốc nằm giữa khung
        self.recs, self.nrows = [], 0
        self._rects, self._vp, self.hover = [], pygame.Rect(0, 0, 0, 0), None
        self._auto_open(root)

    # ---------- trạng thái ----------
    def _f(self, node) -> dict:
        return self.flags.setdefault(id(node), {})

    def _is_best(self, rec) -> bool:
        n = rec.node
        return bool(n.get("best")) or (len(rec.path) == 1 and n.get("move") == self.chosen)

    def _auto_open(self, root):
        n, path = root, []
        for _ in range(MAX_DEPTH):
            self._f(n)["open"] = True
            nxt = None
            for c in n.get("children") or []:
                p = path + ([c["move"]] if c.get("move") is not None else [])
                if c.get("best") or (len(p) == 1 and c.get("move") == self.chosen):
                    nxt, path = c, p
                    break
            if nxt is None:
                break
            n = nxt

    def scroll_by(self, dy):
        self.scroll += dy

    # ---------- layout (ngang: gốc bên trái, mỗi lá 1 hàng) ----------
    def _layout(self):
        root, path = self.stack[-1]
        self.recs, self.nrows = [], 0

        def build(node, depth, p):
            rec = Rec(node, depth, p)
            f = self._f(node)
            if f.get("open") and depth < MAX_DEPTH:
                ch = node.get("children") or []
                shown = ch if f.get("all") else ch[:MAX_KIDS]
                for c in shown:
                    cp = p + ([c["move"]] if c.get("move") is not None else [])
                    rec.kids.append(build(c, depth + 1, cp))
                if len(ch) > len(shown):
                    m = Rec(None, depth + 1, p, more_of=node, more_n=len(ch) - len(shown))
                    m.y = float(self.nrows)
                    self.nrows += 1
                    self.recs.append(m)
                    rec.kids.append(m)
            if rec.kids:
                rec.y = (rec.kids[0].y + rec.kids[-1].y) / 2
            else:
                rec.y = float(self.nrows)
                self.nrows += 1
            self.recs.append(rec)
            return rec

        build(root, 0, path)

    # ---------- dựng lại bàn cờ từ đường nước ----------
    def _mover(self, rec):
        f = self._f(rec.node)
        if "mover" not in f:
            f["mover"] = None
            if rec.node.get("move") is not None:
                try:
                    g = self.root_game.clone()
                    for m in rec.path[:-1]:
                        g.step(m)
                    f["mover"] = g.current_player
                except Exception:  # noqa: BLE001
                    pass
        return f["mover"]

    def _board_at(self, rec):
        try:
            g = self.root_game.clone()
            for m in rec.path:
                g.step(m)
            return g.board
        except Exception:  # noqa: BLE001
            return None

    # ---------- vẽ ----------
    def draw_panel(self, scr, fonts, rect, mouse):
        x0 = rect.x
        scr.fill(C_BG, rect)
        pygame.draw.line(scr, C_CARD, (x0, 0), (x0, rect.h), 2)
        scr.blit(fonts.h.render("Search tree", True, C_TEXT), (x0 + 14, 10))
        _, path = self.stack[-1]
        line = self.title if len(self.stack) == 1 else \
            self.title + "  |  " + " > ".join(["root"] + [sq(m) for m in path])
        scr.blit(fonts.small.render(fit(fonts.small, line, rect.w - 28), True, C_DIM), (x0 + 14, 38))
        hint = "click: open/close   right-click: focus/back   wheel: scroll"
        scr.blit(fonts.small.render(fit(fonts.small, hint, rect.w - 28), True, C_DIM), (x0 + 14, 54))

        vp = pygame.Rect(x0, HEAD_H, rect.w, rect.h - HEAD_H - INFO_H)
        self._vp = vp
        self._layout()
        if self._center:
            self._center = False
            self.scroll = PAD + self.recs[-1].y * ROW_H + ROW_H / 2 - vp.h / 2
        self.scroll = max(0, min(self.scroll, self.nrows * ROW_H + 2 * PAD - vp.h))
        gap = (rect.w - 2 * PAD - BOX_W) / MAX_DEPTH

        def box(rec):
            x = vp.x + PAD + rec.depth * gap
            cy = vp.y + PAD + rec.y * ROW_H + ROW_H / 2 - self.scroll
            return pygame.Rect(int(x), int(cy - BOX_H / 2), BOX_W, BOX_H)

        rects = [(box(r), r) for r in self.recs]
        rmap = {id(r): rc for rc, r in rects}
        old_clip = scr.get_clip()
        scr.set_clip(vp)
        for rc, r in rects:
            for k in r.kids:
                kc = rmap[id(k)]
                best = k.node is not None and self._is_best(k)
                mx = (rc.right + kc.left) // 2
                pts = [(rc.right, rc.centery), (mx, rc.centery), (mx, kc.centery), (kc.left, kc.centery)]
                pygame.draw.lines(scr, C_ACCENT if best else C_BTN, False, pts, 3 if best else 2)
        hover = None
        for rc, r in rects:
            is_hover = vp.collidepoint(mouse) and rc.collidepoint(mouse)
            if is_hover and r.node is not None:
                hover = r
            self._draw_box(scr, fonts, rc, r, is_hover)
        scr.set_clip(old_clip)
        self.hover, self._rects = hover, rects
        self._draw_info(scr, fonts, pygame.Rect(x0, rect.h - INFO_H, rect.w, INFO_H))

    def _draw_box(self, scr, fonts, rc, rec, hover):
        if rec.node is None:
            pygame.draw.rect(scr, C_OFF, rc, border_radius=8)
            pygame.draw.rect(scr, C_WHITE if hover else C_DIM, rc, width=1, border_radius=8)
            t = fonts.small.render(f"+{rec.more_n} more", True, C_DIM)
            scr.blit(t, t.get_rect(center=rc.center))
            return
        n = rec.node
        pruned = bool(n.get("pruned"))
        best = rec.depth > 0 and self._is_best(rec)
        bg = C_BTN if rec.depth == 0 else (C_ACCENT if best else (C_OFF if pruned else C_CARD))
        pygame.draw.rect(scr, bg, rc, border_radius=8)
        pygame.draw.rect(scr, C_WHITE if hover else C_BTN, rc, width=2 if hover else 1, border_radius=8)
        label = n.get("label") or (sq(n["move"]) if n.get("move") is not None else "root")
        if pruned:
            caption = "cut"
        elif n.get("caption"):
            caption = str(n["caption"])
        else:
            parts = []
            if n.get("value") is not None:
                parts.append(fmt_num(n["value"]))
            if n.get("visits") is not None:
                parts.append("n=" + compact(n["visits"]))
            caption = " ".join(parts)
        col = C_DIM if pruned else C_TEXT
        scr.blit(fonts.sb.render(fit(fonts.sb, str(label), BOX_W - 36), True, col), (rc.x + 22, rc.y + 3))
        scr.blit(fonts.small.render(fit(fonts.small, caption, BOX_W - 26), True, C_DIM if not best else C_TEXT),
                 (rc.x + 22, rc.y + 20))
        mover = self._mover(rec)
        if mover is not None:
            _disc(scr, (22, 22, 24) if mover == BLACK else (246, 246, 244), (rc.x + 11, rc.centery), 5)
            gfx.aacircle(scr, rc.x + 11, rc.centery, 5, C_DIM)
        if n.get("children") and rec.depth < MAX_DEPTH:  # dấu +/- mở rộng
            cx, cy = rc.right - 10, rc.y + 10
            pygame.draw.line(scr, C_TEXT, (cx - 4, cy), (cx + 4, cy), 2)
            if not self._f(n).get("open"):
                pygame.draw.line(scr, C_TEXT, (cx, cy - 4), (cx, cy + 4), 2)

    def _info_lines(self, rec):
        n = rec.node
        if rec.depth == 0 and not rec.path:
            head = "Root position"
        else:
            m = self._mover(rec)
            lab = n.get("label") or (sq(n["move"]) if n.get("move") is not None else "?")
            head = f"{NAME[m]} plays {lab}" if m else f"Move {lab}"
        lines = [(head, "bold")]
        kv = [f"{k} {fmt_num(n[k])}" for k in ("value", "visits", "alpha", "beta") if n.get(k) is not None]
        if kv:
            lines.append(("   ".join(kv), "small"))
        if n.get("pruned"):
            lines.append(("Pruned: this branch was cut off.", "small"))
        if n.get("text"):
            lines.append((str(n["text"]), "small"))
        kids = len(n.get("children") or [])
        if kids:
            lines.append((f"{kids} child nodes", "small"))
        return lines

    def _draw_info(self, scr, fonts, rect):
        pygame.draw.line(scr, C_CARD, (rect.x, rect.y), (rect.right, rect.y), 2)
        rec = self.hover
        if rec is None:
            for i, ln in enumerate(wrap_text(fonts.small, "Hover a node to see its details and the "
                                             "board after that move.", rect.w - 28)):
                scr.blit(fonts.small.render(ln, True, C_DIM), (rect.x + 14, rect.y + 12 + 18 * i))
            return
        text_w = rect.w - 28 - 132
        y = rect.y + 10
        for s, kind in self._info_lines(rec):
            font = fonts.bold if kind == "bold" else fonts.small
            for ln in wrap_text(font, s, text_w):
                if y > rect.bottom - 18:
                    break
                scr.blit(font.render(ln, True, C_TEXT if kind == "bold" else C_DIM), (rect.x + 14, y))
                y += 24 if kind == "bold" else 18
        board = self._board_at(rec)
        if board is not None:
            cs = 15
            bx, by = rect.right - 12 - 8 * cs, rect.y + 12
            pygame.draw.rect(scr, (38, 128, 78), (bx, by, 8 * cs, 8 * cs))
            for i in range(9):
                pygame.draw.line(scr, (22, 80, 48), (bx + i * cs, by), (bx + i * cs, by + 8 * cs))
                pygame.draw.line(scr, (22, 80, 48), (bx, by + i * cs), (bx + 8 * cs, by + i * cs))
            for r in range(8):
                for c in range(8):
                    v = int(board[r, c])
                    if v:
                        _disc(scr, (22, 22, 24) if v == BLACK else (246, 246, 244),
                              (bx + c * cs + cs // 2, by + r * cs + cs // 2), cs // 2 - 1)
            mv = rec.node.get("move")
            if mv is not None:
                _disc(scr, (235, 80, 70), (bx + mv[1] * cs + cs // 2, by + mv[0] * cs + cs // 2), 3)

    # ---------- chuột ----------
    def click(self, pos, button) -> bool:
        if not self._vp.collidepoint(pos):
            return False
        for rc, r in reversed(self._rects):
            if not rc.collidepoint(pos):
                continue
            if r.node is None:                       # ô "+N more"
                self._f(r.more_of)["all"] = True
                return True
            n = r.node
            if button == 1 and n.get("children") and r.depth < MAX_DEPTH:
                f = self._f(n)
                f["open"] = not f.get("open")
            elif button == 3:
                if r.depth == 0 and len(self.stack) > 1:
                    self.stack.pop()
                    self.scroll, self._center = 0, True
                elif r.depth > 0 and n.get("children"):
                    self.stack.append((n, r.path))
                    self._f(n)["open"] = True
                    self.scroll, self._center = 0, True
            return True
        if button == 3 and len(self.stack) > 1:      # chuột phải ra chỗ trống = quay lại
            self.stack.pop()
            self.scroll, self._center = 0, True
            return True
        return False


C_WHITE = (246, 246, 244)
