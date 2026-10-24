"""Kiểm tra các file trong configs/ khớp với code (tránh lệch tên khóa như lần trước)."""

from pathlib import Path

import pytest
import yaml

from agents.registry import AGENT_CLASSES, build_agent
from eval.tournament import build_tasks

ROOT = Path(__file__).resolve().parent.parent


def load(name):
    with open(ROOT / "configs" / name, encoding="utf-8") as f:
        return yaml.safe_load(f)


def test_every_agent_spec_has_registered_type_and_params_dict():
    for name, spec in load("agents.yaml")["agents"].items():
        assert spec.get("type") in AGENT_CLASSES, f"{name}: thiếu/sai `type`"
        assert isinstance(spec.get("params", {}), dict), f"{name}: `params` phải là dict"
        assert set(spec) <= {"type", "params"}, f"{name}: khóa lạ (registry sẽ bỏ qua): {set(spec) - {'type', 'params'}}"
        assert "seed" not in (spec.get("params") or {}), f"{name}: không ghi cứng seed (giải đấu cần tự truyền)"


def test_tournament_config_builds_tasks():
    cfg, specs = load("tournament.yaml"), load("agents.yaml")["agents"]
    assert cfg["modes"] and all("name" in m for m in cfg["modes"])
    tasks = build_tasks(cfg, specs)
    n = len(cfg["agents"])
    assert len(tasks) == len(cfg["modes"]) * (n * (n - 1) // 2) * (cfg["games_per_pair"] // 2)
    assert cfg["games_per_pair"] >= 100 and cfg["games_per_pair"] % 2 == 0


def test_tournament_agents_are_buildable():
    cfg, specs = load("tournament.yaml"), load("agents.yaml")["agents"]
    for name in cfg["agents"]:
        build_agent(specs[name], seed=0, name=name)  # lỗi ImportError nếu agent còn là stub


def test_time_budgets_are_seconds():
    for m in load("tournament.yaml")["modes"]:
        assert m.get("time_budget") is None or 0 < m["time_budget"] <= 60, "time_budget tính bằng GIÂY"


def test_checkpoint_paths_match_between_configs():
    agents = load("agents.yaml")["agents"]
    for cfg_name, agent in (("train_supervised.yaml", "nn"), ("train_rl.yaml", "rl")):
        out = load(cfg_name)["output"]
        assert str(Path(out["checkpoint_dir"]) / out["checkpoint_name"]) == str(Path(agents[agent]["params"]["checkpoint"]))


def test_reward_and_split_consistent():
    assert load("game.yaml")["reward"] == load("train_rl.yaml")["reward"]
    assert sum(load("train_supervised.yaml")["data"]["split"].values()) == pytest.approx(1.0)
