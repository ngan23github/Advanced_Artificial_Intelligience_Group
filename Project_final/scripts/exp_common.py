"""Tiện ích dựng tác tử cho các thí nghiệm bổ sung (chạy từ thư mục gốc dự án)."""
import json
from eval.tournament import play_game, random_opening   # noqa: F401
from agents.registry import build_agent, load_agent_specs

SPECS = load_agent_specs('configs/agents.yaml')

def mk(name, seed, **over):
    """Dựng tác tử `name` theo configs/agents.yaml, ghi đè một số tham số bằng **over."""
    spec = json.loads(json.dumps(SPECS[name]))
    spec['params'].update(over)
    return build_agent(spec, seed, name)
