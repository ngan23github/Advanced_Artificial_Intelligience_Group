"""Smoke test giải đấu: cân bằng đi trước/sau, tái lập, đúng ngân sách."""

import json
import time

from agents.base import Agent
from eval.tournament import play_game, run_round_robin
from othello.game import OthelloGame

SPECS = {"r1": {"type": "random"}, "r2": {"type": "random"}}


def cfg(**kw):
    base = {"run_name": "t", "games_per_pair": 8, "seeds": [0, 1], "opening_plies": 4, "agents": ["r1", "r2"],
            "modes": [{"name": "m", "time_budget": 0.25}]}
    base.update(kw)
    return base


def read(path):
    return [json.loads(l) for l in open(path / "games.jsonl", encoding="utf-8")]


def test_balanced_sides_and_budget(tmp_path):
    run_round_robin(cfg(), SPECS, tmp_path / "a", verbose=False)
    recs = read(tmp_path / "a")
    assert len(recs) == 8
    assert sum(r["a_is_black"] for r in recs) == 4
    assert all(r["budget"]["black"] == 0.25 for r in recs)
    summary = json.loads((tmp_path / "a" / "summary.json").read_text(encoding="utf-8"))
    budget = summary["modes"]["m"]["budget"]
    assert budget["over_budget_moves"] == 0
    assert budget["over_budget_games"] == 0
    assert set(budget["by_agent"]) == {"r1", "r2"}


def test_reproducible(tmp_path):
    run_round_robin(cfg(), SPECS, tmp_path / "a", verbose=False)
    run_round_robin(cfg(), SPECS, tmp_path / "b", verbose=False)
    strip = lambda rs: [([m["a"] for m in r["move_log"]], r["result_black"]) for r in rs]
    assert strip(read(tmp_path / "a")) == strip(read(tmp_path / "b"))


class SlowAgent(Agent):
    def select_action(self, game: OthelloGame, time_budget=None):
        time.sleep(0.002)
        return game.legal_actions()[0]


def test_over_budget_is_recorded_per_move():
    record = play_game(SlowAgent(), SlowAgent(), 0.001, 0.001)
    assert record["move_log"]
    assert all("over_budget" in move for move in record["move_log"])
    assert any(move["over_budget"] for move in record["move_log"])
