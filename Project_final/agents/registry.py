"""NGUỒN DUY NHẤT để tạo agent từ cấu hình. Giải đấu, UI, scripts và notebook đều dùng file này.
(Trước đây UI có `ui/agent_factory.py` riêng chỉ tạo agent với tham số mặc định; đã gộp vào đây.)

Một "spec" của agent trong configs/agents.yaml trông như:

    alphabeta:
      type: alphabeta       # khóa trong AGENT_CLASSES bên dưới
      params: {depth: 4}    # tham số truyền vào __init__ của agent

Các hàm chính:
    build_agent(spec, seed, name)         tạo agent từ 1 spec (giải đấu dùng)
    build_agent_by_name(name, seed)       tạo agent theo TÊN MỤC trong agents.yaml (UI, notebook, scripts)
    load_agent_specs(path)                đọc agents.yaml -> {tên: spec}
    list_presets(path)                    danh sách preset kèm nhãn hiển thị và trạng thái dùng được (UI dùng)
    check_spec(spec)                      (dùng được?, lý do) mà KHÔNG tạo agent

Thêm agent mới: thêm 1 dòng vào AGENT_CLASSES (tên lớp phải đúng như ghi ở đây, xem API.md) và 1 mục trong agents.yaml.
Import là lazy, nên agent chưa có code không làm hỏng các agent khác.
"""

import importlib
import inspect
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import yaml

from agents.base import Agent

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_AGENTS_CONFIG = REPO_ROOT / "configs" / "agents.yaml"

# type -> "module:ClassName". Người làm agent nào phải đặt đúng tên lớp tương ứng.
AGENT_CLASSES = {
    "random": "agents.random_agent:RandomAgent",
    "heuristic": "agents.heuristic_agent:HeuristicAgent",
    "alphabeta": "agents.alphabeta_agent:AlphaBetaAgent",
    "mcts": "agents.mcts_agent:MCTSAgent",
    "nn": "agents.nn_agent:NNAgent",
    "rl": "agents.rl_agent:RLAgent",
    "temp_positional": "agents.temp_positional_agent:TempPositionalAgent",  # expert tạm của Người 3
}

# Nhãn hiển thị (UI) cho mục có tên trùng `type`; mục biến thể (mcts_100...) hiển thị bằng chính tên mục.
AGENT_LABELS = {
    "random": "Random", "heuristic": "Heuristic", "alphabeta": "Alpha-Beta", "mcts": "MCTS",
    "nn": "Neural Net", "rl": "RL", "temp_positional": "Temp expert",
}


def get_agent_class(type_name: str):
    if type_name not in AGENT_CLASSES:
        raise KeyError(f"Agent type '{type_name}' chưa đăng ký. Có: {sorted(AGENT_CLASSES)}")
    module_name, class_name = AGENT_CLASSES[type_name].split(":")
    module = importlib.import_module(module_name)
    if not hasattr(module, class_name):
        raise ImportError(f"{module_name} chưa có lớp {class_name} (agent này còn là stub?)")
    return getattr(module, class_name)


def _resolve_params(params: dict) -> dict:
    """Đường dẫn `checkpoint` tương đối được hiểu là tương đối so với thư mục gốc repo (chạy từ đâu cũng được)."""
    params = dict(params or {})
    ckpt = params.get("checkpoint")
    if ckpt and not Path(ckpt).is_absolute():
        params["checkpoint"] = str(REPO_ROOT / ckpt)
    return params


def build_agent(spec: dict, seed: Optional[int] = None, name: Optional[str] = None) -> Agent:
    """Tạo agent mới từ spec {"type": ..., "params": {...}}.

    - Nếu __init__ của agent có tham số `seed` mà params chưa đặt, dùng `seed` truyền vào.
    - `name` (nếu có) được gán vào agent.name để log hiển thị đúng tên trong config.
    """
    cls = get_agent_class(spec["type"])
    params = _resolve_params(spec.get("params"))
    if "seed" in inspect.signature(cls.__init__).parameters:
        params.setdefault("seed", seed)
    agent = cls(**params)
    if name is not None:
        agent.name = name
    return agent


# ---------- tạo theo tên mục trong agents.yaml ----------
def load_agent_specs(agents_config=None) -> dict:
    with open(agents_config or DEFAULT_AGENTS_CONFIG, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)["agents"]


def build_agent_by_name(name: str, seed: Optional[int] = None, agents_config=None, specs: Optional[dict] = None) -> Agent:
    specs = specs if specs is not None else load_agent_specs(agents_config)
    if name not in specs:
        raise KeyError(f"Agent '{name}' không có trong agents.yaml (có: {sorted(specs)})")
    return build_agent(specs[name], seed=seed, name=name)


def check_spec(spec: dict) -> tuple:
    """(dùng được?, lý do nếu không). Không tạo agent nên nhanh; có import module (agent stub bị phát hiện ở đây)."""
    try:
        get_agent_class(spec["type"])
    except (KeyError, ImportError, ModuleNotFoundError) as e:
        return False, "not implemented yet" if isinstance(e, ImportError) else str(e)
    ckpt = _resolve_params(spec.get("params")).get("checkpoint")
    if ckpt and not Path(ckpt).exists():
        return False, f"missing checkpoint: {Path(ckpt).name}"
    return True, ""


def is_available(name: str, agents_config=None, specs: Optional[dict] = None) -> bool:
    specs = specs if specs is not None else load_agent_specs(agents_config)
    return name in specs and check_spec(specs[name])[0]


@dataclass(frozen=True)
class Preset:
    name: str          # tên mục trong agents.yaml (khóa dùng để tạo agent)
    label: str         # nhãn hiển thị
    spec: dict
    available: bool
    reason: str        # vì sao không dùng được ("" nếu dùng được)

    @property
    def summary(self) -> str:
        """Tóm tắt tham số (bỏ dict lồng nhau và đường dẫn) để UI hiện dưới tên agent."""
        parts = []
        for k, v in (self.spec.get("params") or {}).items():
            if isinstance(v, (dict, list)):
                continue
            parts.append(f"{k}={Path(v).name if k == 'checkpoint' else v}")
        return ", ".join(parts)


def list_presets(agents_config=None) -> list:
    """Mọi mục trong agents.yaml dưới dạng Preset, đúng thứ tự trong file. UI chọn agent từ danh sách này."""
    out = []
    for name, spec in load_agent_specs(agents_config).items():
        ok, reason = check_spec(spec)
        label = AGENT_LABELS.get(spec["type"], spec["type"]) if name == spec["type"] else name
        out.append(Preset(name, label, spec, ok, reason))
    return out
