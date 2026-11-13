"""Màn hình chơi: vẽ bàn cờ nỉ & khung gỗ, quân 3D, gợi ý nước hợp lệ + hiệu ứng hover, thanh tỷ lệ quân, thẻ điểm và nút điều khiển."""

import time
import pygame
import pygame.gfxdraw as gfx

from othello.encoding import BLACK, WHITE
from ui.config import (BOARD_PX, BOARD_W, C_ACCENT, C_ACCENT_GLOW, C_BG, C_BOARD, C_BOARD_ALT,
                       C_BORDER, C_CARD, C_CARD_HI, C_DIM, C_DISC_B, C_DISC_W, C_GOLD, C_GRID,
                       C_LAST, C_PANEL, C_TEXT, C_WARN, C_WOOD, C_WOOD_BORDER, CELL, FLIP_TIME,
                       FLIP_WAVE, MARGIN, N, NAME, PANEL_W, PLACE_TIME, WIN_H)
from ui.draw_utils import disc, draw_flipping_disc, draw_placed_disc, load_move_sound
from ui.widgets import Button


class GameView:
    def __init__(self, screen, fonts):
        self.screen, self.fonts = screen, fonts
        self.board_bg = self._make_board_bg()    # nền bàn cờ vẽ sẵn một lần (khung gỗ + lưới + hoshi + nhãn a-h, 1-8)
        self.move_sound = load_move_sound()      # âm thanh đặt cờ (ui/assets/chess_sound.mp3)
        self._sound_tag = None                   # đánh dấu nước đi đã phát âm thanh

    def _make_board_bg(self):
        s = pygame.Surface((BOARD_W, BOARD_W))
        s.fill(C_BG)

        # Khung viền bàn cờ kiểu gỗ tối sang trọng
        frame_rect = pygame.Rect(6, 6, BOARD_W - 12, BOARD_W - 12)
        pygame.draw.rect(s, C_WOOD, frame_rect, border_radius=14)
        pygame.draw.rect(s, C_WOOD_BORDER, frame_rect, width=2, border_radius=14)

        # Viền chỉ vàng/ngọc quanh mặt nỉ bàn cờ
        inner_bezel = pygame.Rect(MARGIN - 3, MARGIN - 3, BOARD_PX + 6, BOARD_PX + 6)
        pygame.draw.rect(s, C_WOOD_BORDER, inner_bezel, width=2, border_radius=4)

        # Mặt bàn cờ nỉ xanh lục bảo
        pygame.draw.rect(s, C_BOARD, (MARGIN, MARGIN, BOARD_PX, BOARD_PX))
        for r in range(N):
            for c in range(N):
                if (r + c) % 2:
                    pygame.draw.rect(s, C_BOARD_ALT, (MARGIN + c * CELL, MARGIN + r * CELL, CELL, CELL))

        # Đường kẻ lưới
        for i in range(N + 1):
            p = MARGIN + i * CELL
            pygame.draw.line(s, C_GRID, (p, MARGIN), (p, MARGIN + BOARD_PX), 2)
            pygame.draw.line(s, C_GRID, (MARGIN, p), (MARGIN + BOARD_PX, p), 2)

        # 4 chấm sao chuẩn bàn cờ Othello (Hoshi dots tại giao điểm C3, G3, C7, G7)
        for hr, hc in ((2, 2), (2, 6), (6, 2), (6, 6)):
            hx, hy = MARGIN + hc * CELL, MARGIN + hr * CELL
            gfx.filled_circle(s, hx, hy, 4, C_GRID)
            gfx.aacircle(s, hx, hy, 4, C_GRID)

        # Nhãn tọa độ a-h, 1-8
        for i in range(N):
            c = MARGIN + i * CELL + CELL // 2
            for ch, pos in (("ABCDEFGH"[i], (c, MARGIN // 2 + 2)),
                            ("ABCDEFGH"[i], (c, BOARD_W - MARGIN // 2 - 2)),
                            (str(i + 1), (MARGIN // 2 + 2, c)),
                            (str(i + 1), (BOARD_W - MARGIN // 2 - 2, c))):
                t = self.fonts.small.render(ch, True, (185, 175, 155))
                s.blit(t, t.get_rect(center=pos))
        return s

    # ---------- các phần của màn hình ----------
    def buttons(self, match, on_menu):
        x0, w = BOARD_W + 18, PANEL_W - 36
        btns = []
        if not match.has_human:
            btns.append(Button((x0, WIN_H - 120, w, 38),
                               "Resume (Space)" if match.paused else "Pause (Space)",
                               lambda: setattr(match, "paused", not match.paused),
                               selected=match.paused))
        bw = (w - 20) // 3
        for i, (name, fn) in enumerate([("New (N)", match.new_game), ("Undo (U)", match.undo), ("Menu (M)", on_menu)]):
            btns.append(Button((x0 + i * (bw + 10), WIN_H - 72, bw, 40), name, fn))
        return btns

    def _draw_board(self, match, mouse=(0, 0)):
        g, scr = match.game, self.screen
        scr.blit(self.board_bg, (0, 0))
        center = lambda r, c: (MARGIN + c * CELL + CELL // 2, MARGIN + r * CELL + CELL // 2)
        rad = CELL // 2 - 7
        move_time = getattr(match, "move_time", 0.0)
        elapsed = time.time() - move_time
        tag = (id(match), len(g.move_history), match.last_move)
        if tag != self._sound_tag:
            self._sound_tag = tag
            if move_time > 0.0 and self.move_sound is not None:
                self.move_sound.play()

        # Tô sáng nhẹ ô vừa đi
        if match.last_move is not None:
            lr, lc = match.last_move
            hl = pygame.Surface((CELL - 2, CELL - 2), pygame.SRCALPHA)
            hl.fill((255, 230, 120, 32))
            scr.blit(hl, (MARGIN + lc * CELL + 1, MARGIN + lr * CELL + 1))

        flip_delays = {}
        if match.last_move is not None:
            r0, c0 = match.last_move
            for fr, fc in getattr(match, "last_flips", ()):
                dist = max(abs(fr - r0), abs(fc - c0))
                flip_delays[(fr, fc)] = 0.08 + (dist - 1) * FLIP_WAVE

        for r in range(N):
            for c in range(N):
                v = int(g.board[r, c])
                if not v:
                    continue
                cx, cy = center(r, c)
                new_col = C_DISC_B if v == BLACK else C_DISC_W
                old_col = C_DISC_W if v == BLACK else C_DISC_B
                if (r, c) == match.last_move and 0.0 <= elapsed < PLACE_TIME:
                    draw_placed_disc(scr, new_col, C_ACCENT_GLOW, (cx, cy), rad, elapsed / PLACE_TIME)
                elif (r, c) in flip_delays and 0.0 <= elapsed < flip_delays[(r, c)] + FLIP_TIME:
                    delay = flip_delays[(r, c)]
                    if elapsed <= delay:
                        disc(scr, (0, 0, 0, 90), (cx + 2, cy + 3), rad)
                        disc(scr, old_col, (cx, cy), rad)
                    else:
                        draw_flipping_disc(scr, old_col, new_color=new_col, center=(cx, cy),
                                           r=rad, progress=(elapsed - delay) / FLIP_TIME)
                else:
                    disc(scr, (0, 0, 0, 90), (cx + 2, cy + 3), rad)
                    disc(scr, new_col, (cx, cy), rad)

        # Gợi ý nước hợp lệ cho người chơi + xem trước quân mờ khi rê chuột vào ô hợp lệ
        if not g.is_terminal() and match.agents[g.current_player] is None:
            mx, my = mouse
            hover_cell = None
            if MARGIN <= mx < MARGIN + BOARD_PX and MARGIN <= my < MARGIN + BOARD_PX:
                hover_cell = ((my - MARGIN) // CELL, (mx - MARGIN) // CELL)
            ghost_col = (20, 22, 28, 120) if g.current_player == BLACK else (245, 248, 252, 130)
            for r, c in g.legal_actions():
                cx, cy = center(r, c)
                if hover_cell == (r, c):
                    disc(scr, ghost_col, (cx, cy), rad - 2)
                    gfx.aacircle(scr, cx, cy, rad - 2, C_ACCENT_GLOW)
                else:
                    disc(scr, (10, 45, 26, 130), (cx, cy), 9)
                    disc(scr, (140, 245, 190, 195), (cx, cy), 5)

        if match.last_move is not None:
            lx, ly = center(*match.last_move)
            if 0.0 <= elapsed < PLACE_TIME:
                p = elapsed / PLACE_TIME
                ly -= int(round(10 * (1.0 - p) ** 2))
            disc(scr, C_LAST, (lx, ly), 5)

    def _draw_dominance_bar(self, match, x, y, w):
        """Thanh tiến trình trực quan so sánh tỷ lệ quân Đen vs Trắng."""
        scr = self.screen
        b, wh = match.game.score()
        total = max(1, b + wh)
        b_w = int(round(w * (b / total)))

        bar_rect = pygame.Rect(x, y, w, 12)
        pygame.draw.rect(scr, C_DISC_W, bar_rect, border_radius=6)
        if b_w > 0:
            pygame.draw.rect(scr, (28, 34, 44), (x, y, max(8, b_w), 12), border_radius=6)
        pygame.draw.rect(scr, C_BORDER, bar_rect, width=1, border_radius=6)

    def _card(self, match, y, player):
        g, scr = match.game, self.screen
        x = BOARD_W + 18
        w = PANEL_W - 36
        active = (g.current_player == player and not g.is_terminal())
        rect = pygame.Rect(x, y, w, 122)

        pygame.draw.rect(scr, (8, 11, 16), rect.move(0, 3), border_radius=12)
        pygame.draw.rect(scr, C_CARD_HI if active else C_CARD, rect, border_radius=12)
        pygame.draw.rect(scr, C_ACCENT_GLOW if active else C_BORDER, rect, width=2 if active else 1, border_radius=12)

        disc(scr, C_DISC_B if player == BLACK else C_DISC_W, (x + 26, y + 26), 14)
        title_str = f"{NAME[player]}  ·  {match.labels[player]}"
        scr.blit(self.fonts.bold.render(title_str[:26], True, C_TEXT), (x + 50, y + 15))

        if active:
            badge = self.fonts.small.render("TURN", True, (10, 25, 18))
            br = badge.get_rect(topright=(rect.right - 14, y + 14))
            pygame.draw.rect(scr, C_ACCENT_GLOW, br.inflate(12, 4), border_radius=6)
            scr.blit(badge, br)

        b, wh = g.score()
        score_val = b if player == BLACK else wh
        scr.blit(self.fonts.big.render(str(score_val), True, C_TEXT), (x + 18, y + 44))
        scr.blit(self.fonts.small.render("discs", True, C_DIM), (x + 68, y + 60))

        l1, l2 = match.info[player]
        if l1:
            scr.blit(self.fonts.small.render(f"Last: {l1}", True, C_ACCENT_GLOW if active else C_TEXT), (x + 18, y + 86))
        else:
            scr.blit(self.fonts.small.render("Waiting for first move...", True, C_DIM), (x + 18, y + 86))
        if l2:
            scr.blit(self.fonts.small.render(l2[:38], True, C_DIM), (x + 18, y + 103))

    @staticmethod
    def _status(match):
        g = match.game
        if g.is_terminal():
            res = g.result(BLACK)
            return ("Draw Match" if res == 0 else f"{NAME[BLACK if res > 0 else WHITE]} Wins!"), C_GOLD
        if match.paused:
            return "Match Paused", C_WARN
        if match.thinking:
            return f"{NAME[g.current_player]} AI is thinking...", C_ACCENT_GLOW
        if match.agents[g.current_player] is None:
            return f"{NAME[g.current_player]}'s Turn — Click a highlighted square", C_TEXT
        return "AI Match in progress", C_DIM

    def _draw_panel(self, match, status, color):
        g, scr = match.game, self.screen
        x0 = BOARD_W + 18
        w = PANEL_W - 36
        scr.fill(C_PANEL, (BOARD_W, 0, PANEL_W, WIN_H))
        pygame.draw.line(scr, C_BORDER, (BOARD_W, 0), (BOARD_W, WIN_H), 1)

        scr.blit(self.fonts.h.render("OTHELLO  ARENA", True, C_TEXT), (x0, 16))
        budget_txt = "Default cfg" if match.time_budget is None else f"{match.time_budget}s / move"
        b_surf = self.fonts.small.render(budget_txt, True, C_GOLD)
        scr.blit(b_surf, (BOARD_W + PANEL_W - 18 - b_surf.get_width(), 20))

        self._draw_dominance_bar(match, x0, 48, w)
        self._card(match, 72, BLACK)
        self._card(match, 206, WHITE)

        # Hộp trạng thái ván đấu
        st_box = pygame.Rect(x0, 342, w, 108)
        pygame.draw.rect(scr, C_CARD, st_box, border_radius=12)
        pygame.draw.rect(scr, C_BORDER, st_box, width=1, border_radius=12)
        scr.blit(self.fonts.bold.render(status[:34], True, color), (x0 + 14, 354))

        empties = 64 - sum(g.score())
        legal_cnt = len(g.legal_actions()) if not g.is_terminal() else 0
        scr.blit(self.fonts.small.render(
            f"Ply: {len(g.move_history)}   ·   Empty: {empties}   ·   Legal moves: {legal_cnt}",
            True, C_DIM), (x0 + 14, 384))

        if match.msg:
            scr.blit(self.fonts.small.render(match.msg[:38], True, C_WARN), (x0 + 14, 412))
        elif match.last_move is not None:
            r, c = match.last_move
            coord = "abcdefgh"[c] + str(r + 1)
            scr.blit(self.fonts.small.render(
                f"Last stone at {coord.upper()} (flipped {len(getattr(match, 'last_flips', ()))} discs)",
                True, C_DIM), (x0 + 14, 412))

        keys = "Shortcuts:  [N] New   [U] Undo   [M/Esc] Menu" + ("" if match.has_human else "   [Space] Pause")
        scr.blit(self.fonts.small.render(keys, True, C_DIM), (x0, WIN_H - 22))

    def _draw_end_overlay(self, match, status):
        scr = self.screen
        b, w = match.game.score()
        cx, cy = MARGIN + BOARD_PX // 2, MARGIN + BOARD_PX // 2

        ov = pygame.Surface((BOARD_PX, BOARD_PX), pygame.SRCALPHA)
        ov.fill((8, 12, 18, 145))
        scr.blit(ov, (MARGIN, MARGIN))

        modal = pygame.Rect(cx - 210, cy - 86, 420, 172)
        pygame.draw.rect(scr, (6, 9, 14), modal.move(0, 5), border_radius=16)
        pygame.draw.rect(scr, C_CARD_HI, modal, border_radius=16)
        pygame.draw.rect(scr, C_GOLD, modal, width=2, border_radius=16)

        t = self.fonts.title.render(status, True, C_GOLD)
        scr.blit(t, t.get_rect(center=(cx, cy - 34)))

        score_line = self.fonts.h.render(f"Black  {b}   —   {w}  White", True, C_TEXT)
        scr.blit(score_line, score_line.get_rect(center=(cx, cy + 14)))

        diff = abs(b - w)
        sub = "Perfect tie!" if diff == 0 else f"Victory margin: +{diff} discs  ·  Press [N] for rematch"
        sub_surf = self.fonts.small.render(sub, True, C_DIM)
        scr.blit(sub_surf, sub_surf.get_rect(center=(cx, cy + 52)))

    def draw(self, match, mouse, on_menu):
        """Vẽ cả màn hình chơi; trả về danh sách nút để App xử lý click."""
        self._draw_board(match, mouse)
        status, color = self._status(match)
        self._draw_panel(match, status, color)
        if match.game.is_terminal():
            self._draw_end_overlay(match, status)
        btns = self.buttons(match, on_menu)
        for b in btns:
            b.draw(self.screen, self.fonts, mouse)
        return btns
