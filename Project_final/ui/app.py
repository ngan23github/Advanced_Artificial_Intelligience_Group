"""Giao diện Pygame cho Othello: Menu -> Game. Chạy: `python -m ui.app` (từ thư mục gốc repo).

File này chỉ giữ vòng lặp chính và điều phối giữa các màn hình. Phần còn lại tách ra:
    ui/config.py      hằng số (kích thước, màu, danh sách chế độ/thời gian)
    ui/draw_utils.py  font, hàm vẽ quân
    ui/widgets.py     Button, Selector
    ui/menu.py        màn hình menu (agent lấy từ configs/agents.yaml qua agents/registry.py)
    ui/match.py       một ván đang chơi (logic + thread AI, không phụ thuộc pygame)
    ui/game_view.py   màn hình chơi (bàn cờ, thẻ điểm, nút)
"""

import pygame

from ui.config import WIN_H, WIN_W
from ui.draw_utils import Fonts
from ui.game_view import GameView
from ui.match import Match
from ui.menu import Menu


class App:
    def __init__(self, seed=None, agents_config=None):
        self.seed = seed
        self.agents_config = agents_config
        self.state = "menu"
        self.match = None
        self.menu = Menu(self.start_match, agents_config)
        self.running = True

    # ---------- chuyển màn hình ----------
    def start_match(self, cfg):
        try:
            self.match = Match(cfg["black"], cfg["white"], cfg["time"], self.seed, self.agents_config)
        except Exception as e:  # noqa: BLE001 - thiếu checkpoint, agent lỗi... -> báo trên menu thay vì văng lỗi
            self.menu.error = f"Could not create agent: {e}"[:80]
            return
        self.menu.error = ""
        self.state = "game"

    def to_menu(self):
        if self.match:
            self.match.gen += 1       # bỏ kết quả của thread AI đang chạy dở
        self.match, self.state = None, "menu"

    def init_graphics(self):
        pygame.init()
        pygame.display.set_caption("Othello")
        self.screen = pygame.display.set_mode((WIN_W, WIN_H))
        self.fonts = Fonts()
        self.game_view = GameView(self.screen, self.fonts)

    # ---------- vòng lặp ----------
    def frame(self, events, mouse):
        """Xử lý event + vẽ đúng 1 frame (tách ra để test được)."""
        if self.state == "menu":
            btns = self.menu.draw(self.screen, self.fonts, mouse)
        else:
            self.match.update()
            btns = self.game_view.draw(self.match, mouse, self.to_menu)
        for e in events:
            if e.type == pygame.QUIT:
                self.running = False
            elif e.type == pygame.KEYDOWN:
                self.on_key(e.key)
            elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                hit = next((b for b in btns if b.enabled and b.rect.collidepoint(e.pos)), None)
                if hit:
                    hit.action()
                    break
                if self.state == "game":
                    self.match.click(e.pos)

    def on_key(self, key):
        if self.state == "menu":
            if key == pygame.K_ESCAPE:
                self.running = False
            elif key == pygame.K_RETURN and self.menu.can_start():
                self.menu.start()
            return
        m = self.match
        if key in (pygame.K_ESCAPE, pygame.K_m):
            self.to_menu()
        elif key == pygame.K_n:
            m.new_game()
        elif key == pygame.K_u:
            m.undo()
        elif key == pygame.K_SPACE and not m.has_human:
            m.paused = not m.paused

    def run(self):
        self.init_graphics()
        clock = pygame.time.Clock()
        while self.running:
            self.frame(pygame.event.get(), pygame.mouse.get_pos())
            pygame.display.flip()
            clock.tick(60)
        pygame.quit()


def run_gui(seed=None):
    App(seed).run()


if __name__ == "__main__":
    run_gui()
