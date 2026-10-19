"""Smoke test giải đấu: cân bằng đi trước/sau, tái lập, đúng ngân sách."""

import json

from eval.tournament import run_round_robin

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


def test_reproducible(tmp_path):
    run_round_robin(cfg(), SPECS, tmp_path / "a", verbose=False)
    run_round_robin(cfg(), SPECS, tmp_path / "b", verbose=False)
    strip = lambda rs: [([m["a"] for m in r["move_log"]], r["result_black"]) for r in rs]
    assert strip(read(tmp_path / "a")) == strip(read(tmp_path / "b"))
