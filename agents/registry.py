"""Tạo agent từ cấu hình (dict đọc từ YAML), để giải đấu/UI không phải import từng agent bằng tay.

Một "spec" của agent trong configs/agents.yaml trông như:

    random:
      type: random          # khóa trong AGENT_CLASSES bên dưới
      params: {}            # tham số truyền vào __init__ của agent

Thêm agent mới: chỉ cần thêm 1 dòng vào AGENT_CLASSES (tên lớp phải đúng như ghi ở đây,
xem API.md). Import là lazy, nên agent chưa có code không làm hỏng các agent khác.
"""

import importlib
import inspect
from typing import Optional

from agents.base import Agent

# type -> "module:ClassName". Người làm agent nào phải đặt đúng tên lớp tương ứng.
AGENT_CLASSES = {
    "random": "agents.random_agent:RandomAgent",
    "heuristic": "agents.heuristic_agent:HeuristicAgent",
    "alphabeta": "agents.alphabeta_agent:AlphaBetaAgent",
    "mcts": "agents.mcts_agent:MCTSAgent",
    "nn": "agents.nn_agent:NNAgent",
    "rl": "agents.rl_agent:RLAgent",
}


def get_agent_class(type_name: str):
    if type_name not in AGENT_CLASSES:
        raise KeyError(f"Agent type '{type_name}' chưa đăng ký. Có: {sorted(AGENT_CLASSES)}")
    module_name, class_name = AGENT_CLASSES[type_name].split(":")
    module = importlib.import_module(module_name)
    if not hasattr(module, class_name):
        raise ImportError(f"{module_name} chưa có lớp {class_name} (agent này còn là stub?)")
    return getattr(module, class_name)


def build_agent(spec: dict, seed: Optional[int] = None, name: Optional[str] = None) -> Agent:
    """Tạo agent mới từ spec {"type": ..., "params": {...}}.

    - Nếu __init__ của agent có tham số `seed` mà params chưa đặt, dùng `seed` truyền vào.
    - `name` (nếu có) được gán vào agent.name để log hiển thị đúng tên trong config.
    """
    cls = get_agent_class(spec["type"])
    params = dict(spec.get("params") or {})
    if "seed" in inspect.signature(cls.__init__).parameters:
        params.setdefault("seed", seed)
    agent = cls(**params)
    if name is not None:
        agent.name = name
    return agent
