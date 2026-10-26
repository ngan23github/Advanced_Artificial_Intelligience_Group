"""Một ván đang chơi: trạng thái game, người/agent cầm mỗi bên, thread suy nghĩ của AI, undo.

KHÔNG import pygame (chỉ logic) nên test được không cần màn hình.
"""

import threading
import time

from agents.registry import build_agent_by_name, list_presets
from othello.encoding import BLACK, WHITE, opponent
from othello.game import OthelloGame
from ui.config import AGENT_DELAY, BOARD_PX, CELL, MARGIN, NAME


def sq(action) -> str:
    """(row, col) -> 'd3' (cột = chữ, hàng = số)."""
    return "abcdefgh"[action[1]] + str(action[0] + 1)


def replay(actions) -> OthelloGame:
    g = OthelloGame()
    for a in actions:
        g.step(a)
    return g


def describe_stats(stats: dict) -> str:
    """Dòng giải thích nước đi của AI: số nút (Alpha-Beta), số mô phỏng (MCTS), giá trị đánh giá (NN/RL)."""
    parts = []
    if stats.get("nodes"):
        parts.append(f"{int(stats['nodes']):,} nodes")
    if stats.get("simulations"):
        parts.append(f"{int(stats['simulations']):,} sims")
    if "value_estimate" in stats:
        parts.append(f"value {stats['value_estimate']:+.2f}")   # NN/RL: đầu value đánh giá thế cờ (+ = bên đi đang tốt)
    return " · ".join(parts)


class Match:
    def __init__(self, black_key, white_key, time_budget=None, seed=None, agents_config=None):
        """black_key / white_key: tên mục trong agents.yaml (xem registry) hoặc None = người chơi."""
        self.keys = {BLACK: black_key, WHITE: white_key}
        labels = {p.name: p.label for p in list_presets(agents_config)}
        self.agents = {
            BLACK: build_agent_by_name(black_key, seed, agents_config) if black_key else None,
            WHITE: build_agent_by_name(white_key, None if seed is None else seed + 1, agents_config) if white_key else None,
        }
        self.labels = {p: ("Human" if k is None else labels.get(k, k)) for p, k in self.keys.items()}
        self.time_budget = time_budget
        self.has_human = any(a is None for a in self.agents.values())
        self.gen = 0               # tăng mỗi khi ván mới/undo để bỏ kết quả cũ của thread đang chạy
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
        """Gọi mỗi frame: nhận kết quả của thread AI (nếu có) hoặc bắt đầu cho AI nghĩ nước tiếp theo."""
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
            except Exception:  # noqa: BLE001
                self.msg, self.halted = f"Illegal agent move {action}"[:60], True
                return
            self.info[player] = (f"{sq(action)} in {dt:.2f} s", describe_stats(stats))
            return
        g = self.game
        if (not g.is_terminal() and not self.halted and not self.paused
                and self.agents[g.current_player] is not None):
            self._start_agent()

    def click(self, pos):
        """Người chơi bấm vào bàn cờ (chỉ có tác dụng khi đến lượt người)."""
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
