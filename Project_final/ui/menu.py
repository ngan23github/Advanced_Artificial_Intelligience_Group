"""Màn hình menu: chọn chế độ, bên cầm quân, agent (lấy từ configs/agents.yaml qua registry) và thời gian mỗi nước."""

import pygame

from agents.registry import list_presets
from othello.encoding import BLACK, WHITE, opponent
from ui.config import (C_ACCENT, C_BG, C_BG_TOP, C_BORDER, C_CARD, C_DIM, C_DISC_B,
                       C_DISC_W, C_ERR, C_GOLD, C_TEXT, MODES, TIMES, WIN_H, WIN_W)
from ui.draw_utils import disc
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
        full = 740
        x0 = (WIN_W - full) // 2
        gap = 16
        bw2 = (full - gap) // 2

        # 1. Chọn chế độ chơi
        labels.append(("GAME MODE", (x0, 128)))
        for i, (name, key) in enumerate(MODES):
            sub_txt = "Challenge an AI agent" if key == "hva" else "Watch two AI agents battle"
            btns.append(Button((x0 + i * (bw2 + gap), 154, bw2, 56), name,
                               lambda k=key: setattr(self, "mode", k), selected=self.mode == key, sub=sub_txt))

        # 2. Chọn màu quân & Agent
        if self.mode == "hva":
            labels.append(("YOUR SIDE", (x0, 232)))
            for i, (name, side) in enumerate([("Black  (Moves First)", BLACK), ("White  (Moves Second)", WHITE)]):
                btns.append(Button((x0 + i * (bw2 + gap), 258, bw2, 48), name,
                                   lambda s=side: setattr(self, "human_side", s), selected=self.human_side == side))
            labels.append(("AI OPPONENT", (x0, 328)))
            selectors.append((self.sel_opponent, (x0, 354, full, 66)))
        else:
            labels.append(("BLACK AGENT  (MOVES FIRST)", (x0, 232)))
            selectors.append((self.sel_black, (x0, 258, full, 64)))
            labels.append(("WHITE AGENT  (MOVES SECOND)", (x0, 338)))
            selectors.append((self.sel_white, (x0, 364, full, 64)))

        for sel, rect in selectors:
            btns += sel.buttons(rect)

        # 3. Ngân sách thời gian mỗi nước
        labels.append(("TIME BUDGET PER MOVE", (x0, 444)))
        tw = (full - 4 * 12) // len(TIMES)
        for i, (name, _) in enumerate(TIMES):
            btns.append(Button((x0 + i * (tw + 12), 470, tw, 44), name,
                               lambda i=i: setattr(self, "time_idx", i), selected=self.time_idx == i))

        # 4. Nút Start Game nổi bật ở giữa dưới
        btns.append(Button((x0, 540, full, 52), "START MATCH   (ENTER)", self.start,
                           enabled=self.can_start(), primary=True))
        return btns, labels, selectors

    def draw(self, screen, fonts, mouse):
        screen.fill(C_BG)
        # Dải trang trí trên đầu màn hình
        pygame.draw.rect(screen, C_BG_TOP, (0, 0, WIN_W, 96))
        pygame.draw.line(screen, C_BORDER, (0, 96), (WIN_W, 96), 1)

        # Khung thẻ lớn chính giữa chứa cài đặt trận đấu
        card_rect = pygame.Rect((WIN_W - 804) // 2, 110, 804, 502)
        pygame.draw.rect(screen, (8, 11, 16), card_rect.move(0, 4), border_radius=16)
        pygame.draw.rect(screen, C_CARD, card_rect, border_radius=16)
        pygame.draw.rect(screen, C_BORDER, card_rect, width=1, border_radius=16)

        # Logo 2 quân cờ Đen/Trắng + Tiêu đề
        cx = (WIN_W - 804) // 2 + 22
        disc(screen, C_DISC_B, (cx, 48), 20)
        disc(screen, C_DISC_W, (cx + 26, 48), 20)
        title = fonts.title.render("OTHELLO", True, C_TEXT)
        screen.blit(title, title.get_rect(midleft=(cx + 60, 48)))

        btns, labels, selectors = self.layout()
        for text, pos in labels:
            lbl = fonts.small.render(text, True, C_GOLD)
            screen.blit(lbl, pos)
        for sel, rect in selectors:
            sel.draw(screen, fonts, rect)
        for b in btns:
            b.draw(screen, fonts, mouse)

        sub = self.error or ("Ready to launch match  ·  Press Enter or click Start Match" if self.can_start()
                             else "Selected agent is unavailable (check missing checkpoint message above).")
        status_surf = fonts.small.render(sub, True, C_ERR if self.error else C_DIM)
        screen.blit(status_surf, status_surf.get_rect(center=(WIN_W // 2, WIN_H - 15)))
        return btns
