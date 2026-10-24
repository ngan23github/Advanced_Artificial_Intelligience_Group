"""Tạo agent theo tên (khớp bảng trong API.md). Không import pygame ở đây.

Agent chưa code (file chưa tồn tại) sẽ hiện mờ trong menu, code xong là tự sáng lên.
"""

import importlib
import importlib.util
import inspect
from dataclasses import dataclass


@dataclass(frozen=True)
class AgentType:
    module: str
    cls: str
    label: str


# key = `type` trong configs/agents.yaml
AGENT_TYPES = {
    "random": AgentType("agents.random_agent", "RandomAgent", "Random"),
    "heuristic": AgentType("agents.heuristic_agent", "HeuristicAgent", "Heuristic"),
    "alphabeta": AgentType("agents.alphabeta_agent", "AlphaBetaAgent", "Alpha-Beta"),
    "mcts": AgentType("agents.mcts_agent", "MCTSAgent", "MCTS"),
    "nn": AgentType("agents.nn_agent", "NNAgent", "Neural Net"),
    "rl": AgentType("agents.rl_agent", "RLAgent", "RL"),
}

_available_cache: dict = {}


def is_available(key: str) -> bool:
    """File module của agent đã tồn tại chưa (không import nặng như torch)."""
    if key not in _available_cache:
        try:
            ok = importlib.util.find_spec(AGENT_TYPES[key].module) is not None
        except (ImportError, ValueError):
            ok = False
        _available_cache[key] = ok
    return _available_cache[key]


def make_agent(key: str, seed=None):
    """Tạo agent với tham số mặc định. Truyền seed nếu __init__ có tham số `seed`."""
    t = AGENT_TYPES[key]
    cls = getattr(importlib.import_module(t.module), t.cls)
    kwargs = {}
    if "seed" in inspect.signature(cls.__init__).parameters:
        kwargs["seed"] = seed
    return cls(**kwargs)
