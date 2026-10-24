"""Giao diện Pygame cho Othello: Menu -> Game. Toàn bộ chữ trên UI là tiếng Anh."""

import threading
import time

import pygame
import pygame.gfxdraw as gfx

from othello.encoding import BLACK, WHITE, opponent
from othello.game import OthelloGame
from ui.agent_factory import AGENT_TYPES, is_available, make_agent

# ---------- layout ----------
CELL, N, MARGIN = 72, 8, 28
BOARD_PX = CELL * N
BOARD_W = BOARD_PX + 2 * MARGIN
PANEL_W = 300
WIN_W, WIN_H = BOARD_W + PANEL_W, BOARD_W
AGENT_DELAY = 0.4  # seconds; min visible time per agent move

# ---------- colors ----------
C_BG = (24, 26, 31)
C_PANEL = (32, 35, 42)
C_CARD = (42, 46, 55)
C_ACCENT = (46, 125, 90)
C_BTN = (58, 63, 74)
C_BTN_HOVER = (74, 80, 93)
C_BTN_OFF = (36, 39, 46)
C_TEXT = (236, 238, 242)
C_DIM = (135, 142, 155)
C_WARN = (255, 196, 80)
C_ERR = (240, 100, 90)
C_BOARD = (38, 128, 78)
C_BOARD_ALT = (34, 120, 72)
C_GRID = (22, 80, 48)
C_DISC_B = (22, 22, 24)
C_DISC_W = (246, 246, 244)
C_LAST = (235, 80, 70)

NAME = {BLACK: "Black", WHITE: "White"}
MODES = [("Human vs Agent", "hva"), ("Agent vs Agent", "ava"), ]
TIMES = [("Default", None), ("0.5 s", 0.5), ("1 s", 1.0), ("2 s", 2.0), ("5 s", 5.0)]


def sq(action) -> str:
    """(row, col) -> 'd3' (cột = chữ, hàng = số)."""
    return "abcdefgh"[action[1]] + str(action[0] + 1)


def replay(actions) -> OthelloGame:
    g = OthelloGame()
    for a in actions:
        g.step(a)
    return g


def disc(surf, color, center, r):
    x, y = center
    gfx.filled_circle(surf, x, y, r, color)
    gfx.aacircle(surf, x, y, r, color)


class Fonts:
    def __init__(self):
        names = "segoeui,arial,helvetica,dejavusans,freesans"
        mk = lambda size, bold=False: pygame.font.SysFont(names, size, bold=bold)
        self.title, self.big = mk(48, True), mk(38, True)
        self.h, self.body, self.bold, self.small = mk(22, True), mk(19), mk(19, True), mk(15)


class Button:
    def __init__(self, rect, label, action, selected=False, enabled=True, sub=""):
        self.rect = pygame.Rect(rect)
        self.label, self.action, self.selected, self.enabled, self.sub = label, action, selected, enabled, sub

    def draw(self, screen, fonts, mouse):
        if not self.enabled:
            bg, fg = C_BTN_OFF, C_DIM
        elif self.selected:
            bg, fg = C_ACCENT, (255, 255, 255)
        elif self.rect.collidepoint(mouse):
            bg, fg = C_BTN_HOVER, C_TEXT
        else:
            bg, fg = C_BTN, C_TEXT
        pygame.draw.rect(screen, bg, self.rect, border_radius=8)
        font = fonts.bold if self.selected else fonts.body
        dy = -9 if self.sub else 0
        t = font.render(self.label, True, fg)
        screen.blit(t, t.get_rect(center=(self.rect.centerx, self.rect.centery + dy)))
        if self.sub:
            s = fonts.small.render(self.sub, True, C_DIM)
            screen.blit(s, s.get_rect(center=(self.rect.centerx, self.rect.centery + 12)))


# =====================================================================
#  MENU
# =====================================================================
class Menu:
    def __init__(self, on_start):
        self.on_start = on_start
        self.mode = "hva"
        self.human_side = BLACK
        avail = [k for k in AGENT_TYPES if is_available(k)]
        first = avail[0] if avail else next(iter(AGENT_TYPES))
        self.opponent = first
        self.black_agent = first
        self.white_agent = avail[1] if len(avail) > 1 else first
        self.time_idx = 0
        self.error = ""

    def _agents_needed(self):
        if self.mode == "hva":
            return [self.opponent]
        if self.mode == "ava":
            return [self.black_agent, self.white_agent]
        return []

    def can_start(self):
        return all(is_available(k) for k in self._agents_needed())

    def start(self):
        cfg = {"time": TIMES[self.time_idx][1], "black": None, "white": None}
        if self.mode == "hva":
            agent_side = opponent(self.human_side)
            cfg["black" if agent_side == BLACK else "white"] = self.opponent
        elif self.mode == "ava":
            cfg["black"], cfg["white"] = self.black_agent, self.white_agent
        self.on_start(cfg)

    def _grid(self, y, current, setter, cols, w, h, gap=10):
        keys = list(AGENT_TYPES)
        x0 = (WIN_W - (cols * w + (cols - 1) * gap)) // 2
        out = []
        for i, k in enumerate(keys):
            r, c = divmod(i, cols)
            ok = is_available(k)
            out.append(Button((x0 + c * (w + gap), y + r * (h + gap), w, h), AGENT_TYPES[k].label,
                              lambda k=k: setter(k), selected=(current == k), enabled=ok,
                              sub="" if ok else "not implemented"))
        return out

    def layout(self):
        btns, labels = [], []
        bw, gap = 260, 16
        x0 = (WIN_W - (3 * bw + 2 * gap)) // 2
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
            btns += self._grid(338, self.opponent, lambda k: setattr(self, "opponent", k), 3, bw, 52, 16)
        elif self.mode == "ava":
            labels.append(("Black agent", (x0, 216)))
            btns += self._grid(242, self.black_agent, lambda k: setattr(self, "black_agent", k), 3, bw, 46, 16)
            # white grid sits below black grid
            labels.append(("White agent", (x0, 360)))
            btns += self._grid(388, self.white_agent, lambda k: setattr(self, "white_agent", k), 3, bw, 46, 16)

        btns.append(Button((WIN_W - 300, WIN_H - 50, 280, 40), "Start game", self.start, enabled=self.can_start()))
        return btns, labels

    def draw(self, screen, fonts, mouse):
        screen.fill(C_BG)
        t = fonts.title.render("OTHELLO", True, C_TEXT)
        screen.blit(t, (60, 28))
        sub = self.error or ("Pick a mode and agents, then start." if self.can_start()
                             else "Selected agent is not implemented yet.")
        screen.blit(fonts.body.render(sub, True, C_ERR if self.error else C_DIM), (60, WIN_H - 40))
        btns, labels = self.layout()
        for text, pos in labels:
            screen.blit(fonts.h.render(text, True, C_TEXT), pos)
        for b in btns:
            b.draw(screen, fonts, mouse)
        return btns


# =====================================================================
#  MATCH (một ván đang chơi)
# =====================================================================
class Match:
    def __init__(self, black_key, white_key, time_budget=None, seed=None):
        self.keys = {BLACK: black_key, WHITE: white_key}  # None = human
        self.agents = {
            BLACK: make_agent(black_key, seed) if black_key else None,
            WHITE: make_agent(white_key, None if seed is None else seed + 1) if white_key else None,
        }
        self.labels = {p: ("Human" if k is None else AGENT_TYPES[k].label) for p, k in self.keys.items()}
        self.time_budget = time_budget
        self.has_human = any(a is None for a in self.agents.values())
        self.gen = 0
        self.thinking = False
        self.result = None
        self.paused = False
        self.new_game()

    def new_game(self):
        self.gen += 1
        for a in self.agents.values():
            if a is not None:
                try:
                    a.reset()
                except Exception:  # noqa: BLE001
                    pass
        self.game = OthelloGame()
        self.last_move = None
        self.msg = ""
        self.halted = False
        self.info = {BLACK: ("", ""), WHITE: ("", "")}

    def undo(self):
        hist = [a for _, a in self.game.move_history]
        if not hist:
            return
        while hist:
            hist.pop()
            if not self.has_human or self.agents[replay(hist).current_player] is None:
                break
        self.gen += 1
        self.game = replay(hist)
        self.last_move = self.game.move_history[-1][1] if self.game.move_history else None
        self.msg, self.halted = "", False

    def apply(self, action):
        mover = self.game.current_player
        self.game.step(action)
        self.last_move = tuple(action)
        self.msg = ""
        if not self.game.is_terminal() and self.game.current_player == mover:
            self.msg = f"{NAME[opponent(mover)]} has no legal move: pass"
        return mover

    def _start_agent(self):
        player = self.game.current_player
        agent = self.agents[player]
        snapshot = self.game.clone()  # agent không được sửa game thật
        gen, budget = self.gen, self.time_budget
        self.thinking = True

        def work():
            t0 = time.time()
            try:
                action = agent.select_action(snapshot) if budget is None else \
                    agent.select_action(snapshot, time_budget=budget)
                dt = time.time() - t0
                try:
                    stats = dict(agent.stats())
                except Exception:  # noqa: BLE001
                    stats = {}
                out = (action, dt, stats)
            except Exception as e:  # noqa: BLE001
                out = e
            wait = AGENT_DELAY - (time.time() - t0)
            if wait > 0:
                time.sleep(wait)
            self.result = (gen, player, out)

        threading.Thread(target=work, daemon=True).start()

    def update(self):
        if self.thinking:
            if self.result is None or self.paused:
                return
            gen, player, out = self.result
            self.result, self.thinking = None, False
            if gen != self.gen:
                return
            if isinstance(out, Exception):
                self.msg, self.halted = f"Agent error: {out}"[:60], True
                return
            action, dt, stats = out
            try:
                self.apply(action)
            except Exception as e:  # noqa: BLE001
                self.msg, self.halted = f"Illegal agent move {action}"[:60], True
                return
            parts = []
            if stats.get("nodes"):
                parts.append(f"{int(stats['nodes']):,} nodes")
            if stats.get("simulations"):
                parts.append(f"{int(stats['simulations']):,} sims")
            self.info[player] = (f"{sq(action)} in {dt:.2f} s", " · ".join(parts))
            return
        g = self.game
        if (not g.is_terminal() and not self.halted and not self.paused
                and self.agents[g.current_player] is not None):
            self._start_agent()

    def click(self, pos):
        g = self.game
        if g.is_terminal() or self.thinking or self.agents[g.current_player] is not None:
            return
        x, y = pos[0] - MARGIN, pos[1] - MARGIN
        if not (0 <= x < BOARD_PX and 0 <= y < BOARD_PX):
            return
        action = (y // CELL, x // CELL)  # (row, col) = (y, x)
        if action in g.legal_actions():
            player = self.apply(action)
            self.info[player] = (sq(action), "")


# =====================================================================
#  APP
# =====================================================================
class App:
    def __init__(self, seed=None):
        self.seed = seed
        self.state = "menu"
        self.match = None
        self.menu = Menu(self.start_match)
        self.running = True

    def start_match(self, cfg):
        try:
            self.match = Match(cfg["black"], cfg["white"], cfg["time"], self.seed)
        except Exception as e:  # noqa: BLE001
            self.menu.error = f"Could not create agent: {e}"[:80]
            return
        self.menu.error = ""
        self.state = "game"

    def to_menu(self):
        if self.match:
            self.match.gen += 1
        self.match, self.state = None, "menu"

    def init_graphics(self):
        pygame.init()
        pygame.display.set_caption("Othello")
        self.screen = pygame.display.set_mode((WIN_W, WIN_H))
        self.fonts = Fonts()
        self.board_bg = self._make_board_bg()

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

    # ---------- game screen ----------
    def game_buttons(self):
        m = self.match
        x0 = BOARD_W + 20
        w = PANEL_W - 40
        btns = []
        if not m.has_human:
            btns.append(Button((x0, WIN_H - 124, w, 36), "Resume (Space)" if m.paused else "Pause (Space)",
                               lambda: setattr(m, "paused", not m.paused)))
        bw = (w - 20) // 3
        for i, (name, fn) in enumerate([("New", m.new_game), ("Undo", m.undo), ("Menu", self.to_menu)]):
            btns.append(Button((x0 + i * (bw + 10), WIN_H - 76, bw, 40), name, fn))
        return btns

    def _card(self, y, player):
        m, g = self.match, self.match.game
        x = BOARD_W + 14
        rect = pygame.Rect(x, y, PANEL_W - 28, 118)
        pygame.draw.rect(self.screen, C_CARD, rect, border_radius=10)
        if g.current_player == player and not g.is_terminal():
            pygame.draw.rect(self.screen, C_ACCENT, rect, width=3, border_radius=10)
        disc(self.screen, C_DISC_B if player == BLACK else C_DISC_W, (x + 26, y + 26), 11)
        gfx.aacircle(self.screen, x + 26, y + 26, 11, C_DIM)
        self.screen.blit(self.fonts.bold.render(f"{NAME[player]} · {m.labels[player]}", True, C_TEXT), (x + 48, y + 14))
        b, w = g.score()
        self.screen.blit(self.fonts.big.render(str(b if player == BLACK else w), True, C_TEXT), (x + 16, y + 38))
        l1, l2 = m.info[player]
        self.screen.blit(self.fonts.small.render(l1, True, C_DIM), (x + 16, y + 86))
        self.screen.blit(self.fonts.small.render(l2, True, C_DIM), (x + 16, y + 100))

    def draw_game(self, mouse):
        m, g, scr = self.match, self.match.game, self.screen
        scr.blit(self.board_bg, (0, 0))
        center = lambda r, c: (MARGIN + c * CELL + CELL // 2, MARGIN + r * CELL + CELL // 2)
        for r in range(N):
            for c in range(N):
                v = int(g.board[r, c])
                if v:
                    cx, cy = center(r, c)
                    disc(scr, (0, 0, 0, 80), (cx + 2, cy + 3), CELL // 2 - 8)
                    disc(scr, C_DISC_B if v == BLACK else C_DISC_W, (cx, cy), CELL // 2 - 8)
        if not g.is_terminal() and m.agents[g.current_player] is None:
            for r, c in g.legal_actions():
                disc(scr, (0, 0, 0, 90), center(r, c), 8)
        if m.last_move is not None:
            cx, cy = center(*m.last_move)
            disc(scr, C_LAST, (cx, cy), 6)

        scr.fill(C_PANEL, (BOARD_W, 0, PANEL_W, WIN_H))
        scr.blit(self.fonts.h.render("OTHELLO", True, C_TEXT), (BOARD_W + 20, 18))
        self._card(52, BLACK)
        self._card(182, WHITE)

        x0 = BOARD_W + 20
        if g.is_terminal():
            res = g.result(BLACK)
            text = "Draw" if res == 0 else f"{NAME[BLACK if res > 0 else WHITE]} wins"
            status, color = text, C_WARN
        elif m.paused:
            status, color = "Paused", C_DIM
        elif m.thinking:
            status, color = f"{NAME[g.current_player]} is thinking...", C_DIM
        elif m.agents[g.current_player] is None:
            status, color = f"{NAME[g.current_player]}: your move", C_TEXT
        else:
            status, color = "", C_TEXT
        scr.blit(self.fonts.h.render(status, True, color), (x0, 318))
        if m.msg:
            scr.blit(self.fonts.small.render(m.msg, True, C_WARN), (x0, 350))
        scr.blit(self.fonts.small.render(f"Moves played: {len(g.move_history)}", True, C_DIM), (x0, 374))
        keys = "N new   U undo   M / Esc menu" + ("" if m.has_human else "   Space pause")
        scr.blit(self.fonts.small.render(keys, True, C_DIM), (x0, WIN_H - 22))

        if g.is_terminal():
            b, w = g.score()
            ov = pygame.Surface((BOARD_PX, 150), pygame.SRCALPHA)
            ov.fill((0, 0, 0, 170))
            scr.blit(ov, (MARGIN, MARGIN + BOARD_PX // 2 - 75))
            t = self.fonts.title.render(status, True, C_WARN)
            scr.blit(t, t.get_rect(center=(MARGIN + BOARD_PX // 2, MARGIN + BOARD_PX // 2 - 22)))
            t = self.fonts.h.render(f"Black {b}  -  {w} White", True, C_TEXT)
            scr.blit(t, t.get_rect(center=(MARGIN + BOARD_PX // 2, MARGIN + BOARD_PX // 2 + 28)))

        btns = self.game_buttons()
        for b in btns:
            b.draw(scr, self.fonts, mouse)
        return btns

    # ---------- main loop ----------
    def frame(self, events, mouse):
        """Xử lý event + vẽ đúng 1 frame (tách ra để test được)."""
        if self.state == "menu":
            btns = self.menu.draw(self.screen, self.fonts, mouse)
        else:
            self.match.update()
            btns = self.draw_game(mouse)
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
