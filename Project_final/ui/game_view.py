"""Màn hình chơi: vẽ bàn cờ, quân, nước hợp lệ, thẻ điểm từng bên, trạng thái và nút điều khiển."""

import pygame
import pygame.gfxdraw as gfx

from othello.encoding import BLACK, WHITE
from ui.config import (BOARD_PX, BOARD_W, C_ACCENT, C_BOARD, C_BOARD_ALT, C_CARD, C_DIM, C_DISC_B, C_DISC_W, C_GRID,
                       C_LAST, C_PANEL, C_TEXT, C_WARN, CELL, MARGIN, N, NAME, PANEL_W, WIN_H)
from ui.draw_utils import disc
from ui.widgets import Button


class GameView:
    def __init__(self, screen, fonts):
        self.screen, self.fonts = screen, fonts
        self.board_bg = self._make_board_bg()    # nền bàn cờ vẽ sẵn một lần (lưới + nhãn a-h, 1-8)

    def _make_board_bg(self):
        s = pygame.Surface((BOARD_W, BOARD_W))
        s.fill(C_PANEL)
        pygame.draw.rect(s, C_BOARD, (MARGIN, MARGIN, BOARD_PX, BOARD_PX))
        for r in range(N):
            for c in range(N):
                if (r + c) % 2:
                    pygame.draw.rect(s, C_BOARD_ALT, (MARGIN + c * CELL, MARGIN + r * CELL, CELL, CELL))
        for i in range(N + 1):
            p = MARGIN + i * CELL
            pygame.draw.line(s, C_GRID, (p, MARGIN), (p, MARGIN + BOARD_PX), 2)
            pygame.draw.line(s, C_GRID, (MARGIN, p), (MARGIN + BOARD_PX, p), 2)
        for i in range(N):
            c = MARGIN + i * CELL + CELL // 2
            for ch, pos in (("abcdefgh"[i], (c, MARGIN // 2)), ("abcdefgh"[i], (c, BOARD_W - MARGIN // 2)),
                            (str(i + 1), (MARGIN // 2, c)), (str(i + 1), (BOARD_W - MARGIN // 2, c))):
                t = self.fonts.small.render(ch, True, C_DIM)
                s.blit(t, t.get_rect(center=pos))
        return s

    # ---------- các phần của màn hình ----------
    def buttons(self, match, on_menu):
        x0, w = BOARD_W + 20, PANEL_W - 40
        btns = []
        if not match.has_human:
            btns.append(Button((x0, WIN_H - 124, w, 36), "Resume (Space)" if match.paused else "Pause (Space)",
                               lambda: setattr(match, "paused", not match.paused)))
        bw = (w - 20) // 3
        for i, (name, fn) in enumerate([("New", match.new_game), ("Undo", match.undo), ("Menu", on_menu)]):
            btns.append(Button((x0 + i * (bw + 10), WIN_H - 76, bw, 40), name, fn))
        return btns

    def _draw_board(self, match):
        g, scr = match.game, self.screen
        scr.blit(self.board_bg, (0, 0))
        center = lambda r, c: (MARGIN + c * CELL + CELL // 2, MARGIN + r * CELL + CELL // 2)
        for r in range(N):
            for c in range(N):
                v = int(g.board[r, c])
                if v:
                    cx, cy = center(r, c)
                    disc(scr, (0, 0, 0, 80), (cx + 2, cy + 3), CELL // 2 - 8)          # bóng
                    disc(scr, C_DISC_B if v == BLACK else C_DISC_W, (cx, cy), CELL // 2 - 8)
        if not g.is_terminal() and match.agents[g.current_player] is None:               # gợi ý nước hợp lệ cho người
            for r, c in g.legal_actions():
                disc(scr, (0, 0, 0, 90), center(r, c), 8)
        if match.last_move is not None:
            disc(scr, C_LAST, center(*match.last_move), 6)

    def _card(self, match, y, player):
        g, scr = match.game, self.screen
        x = BOARD_W + 14
        rect = pygame.Rect(x, y, PANEL_W - 28, 118)
        pygame.draw.rect(scr, C_CARD, rect, border_radius=10)
        if g.current_player == player and not g.is_terminal():
            pygame.draw.rect(scr, C_ACCENT, rect, width=3, border_radius=10)
        disc(scr, C_DISC_B if player == BLACK else C_DISC_W, (x + 26, y + 26), 11)
        gfx.aacircle(scr, x + 26, y + 26, 11, C_DIM)
        scr.blit(self.fonts.bold.render(f"{NAME[player]} · {match.labels[player]}", True, C_TEXT), (x + 48, y + 14))
        b, w = g.score()
        scr.blit(self.fonts.big.render(str(b if player == BLACK else w), True, C_TEXT), (x + 16, y + 38))
        l1, l2 = match.info[player]
        scr.blit(self.fonts.small.render(l1, True, C_DIM), (x + 16, y + 86))
        scr.blit(self.fonts.small.render(l2, True, C_DIM), (x + 16, y + 100))

    @staticmethod
    def _status(match):
        g = match.game
        if g.is_terminal():
            res = g.result(BLACK)
            return ("Draw" if res == 0 else f"{NAME[BLACK if res > 0 else WHITE]} wins"), C_WARN
        if match.paused:
            return "Paused", C_DIM
        if match.thinking:
            return f"{NAME[g.current_player]} is thinking...", C_DIM
        if match.agents[g.current_player] is None:
            return f"{NAME[g.current_player]}: your move", C_TEXT
        return "", C_TEXT

    def _draw_panel(self, match, status, color):
        g, scr = match.game, self.screen
        x0 = BOARD_W + 20
        scr.fill(C_PANEL, (BOARD_W, 0, PANEL_W, WIN_H))
        scr.blit(self.fonts.h.render("OTHELLO", True, C_TEXT), (x0, 18))
        self._card(match, 52, BLACK)
        self._card(match, 182, WHITE)
        scr.blit(self.fonts.h.render(status, True, color), (x0, 318))
        if match.msg:
            scr.blit(self.fonts.small.render(match.msg, True, C_WARN), (x0, 350))
        scr.blit(self.fonts.small.render(f"Moves played: {len(g.move_history)}", True, C_DIM), (x0, 374))
        keys = "N new  U undo  M menu" + ("" if match.has_human else "  Space pause")
        scr.blit(self.fonts.small.render(keys, True, C_DIM), (x0, WIN_H - 22))

    def _draw_end_overlay(self, match, status):
        scr = self.screen
        b, w = match.game.score()
        ov = pygame.Surface((BOARD_PX, 150), pygame.SRCALPHA)
        ov.fill((0, 0, 0, 170))
        scr.blit(ov, (MARGIN, MARGIN + BOARD_PX // 2 - 75))
        t = self.fonts.title.render(status, True, C_WARN)
        scr.blit(t, t.get_rect(center=(MARGIN + BOARD_PX // 2, MARGIN + BOARD_PX // 2 - 22)))
        t = self.fonts.h.render(f"Black {b}  -  {w} White", True, C_TEXT)
        scr.blit(t, t.get_rect(center=(MARGIN + BOARD_PX // 2, MARGIN + BOARD_PX // 2 + 28)))

    def draw(self, match, mouse, on_menu):
        """Vẽ cả màn hình chơi; trả về danh sách nút để App xử lý click."""
        self._draw_board(match)
        status, color = self._status(match)
        self._draw_panel(match, status, color)
        if match.game.is_terminal():
            self._draw_end_overlay(match, status)
        btns = self.buttons(match, on_menu)
        for b in btns:
            b.draw(self.screen, self.fonts, mouse)
        return btns
