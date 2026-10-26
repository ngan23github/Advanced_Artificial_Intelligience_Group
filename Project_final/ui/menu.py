"""Màn hình menu: chọn chế độ, bên cầm quân, agent (lấy từ configs/agents.yaml qua registry) và thời gian mỗi nước."""

from agents.registry import list_presets
from othello.encoding import BLACK, WHITE, opponent
from ui.config import (C_BG, C_DIM, C_ERR, C_TEXT, MODES, TIMES, WIN_H, WIN_W)
from ui.widgets import Button, Selector


class Menu:
    def __init__(self, on_start, agents_config=None):
        self.on_start = on_start
        self.presets = list_presets(agents_config)            # mọi mục trong agents.yaml, kèm trạng thái dùng được
        usable = [i for i, p in enumerate(self.presets) if p.available]
        first = usable[0] if usable else 0
        second = usable[1] if len(usable) > 1 else first
        self.mode = "hva"
        self.human_side = BLACK
        self.sel_opponent = Selector(self.presets, first)
        self.sel_black = Selector(self.presets, first)
        self.sel_white = Selector(self.presets, second)
        self.time_idx = 0
        self.error = ""

    # ---------- logic ----------
    def _selected(self):
        """Các Selector đang dùng theo chế độ hiện tại."""
        return [self.sel_opponent] if self.mode == "hva" else [self.sel_black, self.sel_white]

    def can_start(self):
        return all(s.current.available for s in self._selected())

    def start(self):
        """Gọi on_start với cấu hình ván: tên preset (None = người) cho Đen/Trắng và ngân sách thời gian."""
        cfg = {"time": TIMES[self.time_idx][1], "black": None, "white": None}
        if self.mode == "hva":
            agent_side = opponent(self.human_side)
            cfg["black" if agent_side == BLACK else "white"] = self.sel_opponent.current.name
        else:
            cfg["black"], cfg["white"] = self.sel_black.current.name, self.sel_white.current.name
        self.on_start(cfg)

    # ---------- bố cục và vẽ ----------
    def layout(self):
        """Trả về (buttons, labels, selectors[(selector, rect)]) cho trạng thái hiện tại."""
        btns, labels, selectors = [], [], []
        bw, gap = 260, 16
        x0 = (WIN_W - (3 * bw + 2 * gap)) // 2
        full = 3 * bw + 2 * gap                      # bề rộng vùng nội dung
        labels.append(("Game mode", (x0, 112)))
        for i, (name, key) in enumerate(MODES):
            btns.append(Button((x0 + i * (bw + gap), 138, bw, 54), name,
                               lambda k=key: setattr(self, "mode", k), selected=self.mode == key))
        if self.mode == "hva":
            labels.append(("You play as", (x0, 216)))
            for i, (name, side) in enumerate([("Black (moves first)", BLACK), ("White", WHITE)]):
                btns.append(Button((x0 + i * 236, 242, 220, 46), name,
                                   lambda s=side: setattr(self, "human_side", s), selected=self.human_side == side))
            labels.append(("Opponent agent", (x0, 312)))
            selectors.append((self.sel_opponent, (x0, 338, full, 70)))
        else:
            labels.append(("Black agent", (x0, 216)))
            selectors.append((self.sel_black, (x0, 242, full, 70)))
            labels.append(("White agent", (x0, 336)))
            selectors.append((self.sel_white, (x0, 362, full, 70)))
        for sel, rect in selectors:
            btns += sel.buttons(rect)

        labels.append(("Time per move", (x0, 456)))
        for i, (name, _) in enumerate(TIMES):
            btns.append(Button((x0 + i * 124, 482, 112, 40), name,
                               lambda i=i: setattr(self, "time_idx", i), selected=self.time_idx == i))
        btns.append(Button((WIN_W - 300, WIN_H - 50, 280, 40), "Start game", self.start, enabled=self.can_start()))
        return btns, labels, selectors

    def draw(self, screen, fonts, mouse):
        screen.fill(C_BG)
        screen.blit(fonts.title.render("OTHELLO", True, C_TEXT), (60, 28))
        sub = self.error or ("Pick a mode and agents, then start." if self.can_start()
                             else "Selected agent is not available (see message under its name).")
        screen.blit(fonts.body.render(sub, True, C_ERR if self.error else C_DIM), (60, WIN_H - 40))
        btns, labels, selectors = self.layout()
        for text, pos in labels:
            screen.blit(fonts.h.render(text, True, C_TEXT), pos)
        for sel, rect in selectors:
            sel.draw(screen, fonts, rect)
        for b in btns:
            b.draw(screen, fonts, mouse)
        return btns
