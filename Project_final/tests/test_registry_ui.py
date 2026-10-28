"""Test registry hợp nhất (agents/registry.py) và giao diện (logic Match/Menu + vài frame Pygame chạy không màn hình)."""

import os
import time

import pytest
import yaml

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")   # Pygame không cần màn hình thật
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from agents import registry  # noqa: E402
from othello.encoding import BLACK, WHITE  # noqa: E402


@pytest.fixture()
def agents_cfg(tmp_path):
    """agents.yaml tạm: random + nn/rl trỏ tới checkpoint nhỏ chưa train (có `torch`) + 1 mục thiếu checkpoint."""
    torch = pytest.importorskip("torch")
    from models.nets import PolicyValueNet, save_checkpoint
    torch.manual_seed(0)
    save_checkpoint(tmp_path / "tiny.pt", PolicyValueNet(channels=8, hidden=16))
    cfg = {"agents": {
        "random": {"type": "random", "params": {}},
        "nn": {"type": "nn", "params": {"checkpoint": str(tmp_path / "tiny.pt")}},
        "rl": {"type": "rl", "params": {"checkpoint": str(tmp_path / "tiny.pt"), "temperature": 1.0}},
        "nn_missing": {"type": "nn", "params": {"checkpoint": str(tmp_path / "khong_co.pt")}},
    }}
    path = tmp_path / "agents.yaml"
    path.write_text(yaml.safe_dump(cfg), encoding="utf-8")
    return path


# ---------- registry ----------
def test_presets_cover_yaml_and_availability_matches_buildability():
    """Với MỌI mục trong agents.yaml thật: available đúng khi và chỉ khi tạo được agent (không phụ thuộc agent nào đã code)."""
    presets = registry.list_presets()
    assert [p.name for p in presets] == list(registry.load_agent_specs())
    for p in presets:
        if p.available:
            registry.build_agent_by_name(p.name, seed=0)
        else:
            assert p.reason
            with pytest.raises((ImportError, FileNotFoundError)):
                registry.build_agent_by_name(p.name, seed=0)


def test_registry_passes_params_and_seed(agents_cfg):
    rl = registry.build_agent_by_name("rl", seed=5, agents_config=agents_cfg)
    assert type(rl).__name__ == "RLAgent" and rl.temperature == 1.0 and rl.seed == 5 and rl.name == "rl"


def test_missing_checkpoint_is_reported_not_crashing(agents_cfg):
    by = {p.name: p for p in registry.list_presets(agents_cfg)}
    assert by["nn"].available and by["nn_missing"].available is False and "missing checkpoint" in by["nn_missing"].reason
    assert "checkpoint=tiny.pt" in by["nn"].summary


def test_relative_checkpoint_resolves_from_repo_root():
    params = registry._resolve_params({"checkpoint": "checkpoints/x.pt", "depth": 3})
    assert params["checkpoint"] == str(registry.REPO_ROOT / "checkpoints" / "x.pt") and params["depth"] == 3


# ---------- Match (logic ván, không cần pygame) ----------
def play_match(m, timeout=60):
    t0 = time.time()
    while not m.game.is_terminal() and time.time() - t0 < timeout:
        m.update()
        time.sleep(0.001)
    return m


@pytest.mark.parametrize("black,white", [("random", "random"), ("nn", "rl")])
def test_match_agent_vs_agent_plays_full_game(monkeypatch, agents_cfg, black, white):
    from ui import match as M
    monkeypatch.setattr(M, "AGENT_DELAY", 0.0)
    m = play_match(M.Match(black, white, seed=1, agents_config=agents_cfg))
    assert m.game.is_terminal() and not m.halted and m.msg == ""
    if black == "nn":
        assert "value" in m.info[BLACK][1]          # UI hiện đánh giá của đầu value (giải thích nước đi)
    assert m.labels[BLACK] != "Human"


def test_match_human_click_then_agent_replies(monkeypatch, agents_cfg):
    from ui import match as M
    from ui.config import CELL, MARGIN
    monkeypatch.setattr(M, "AGENT_DELAY", 0.0)
    m = M.Match(None, "nn", agents_config=agents_cfg)
    r, c = m.game.legal_actions()[0]
    m.click((MARGIN + c * CELL + 5, MARGIN + r * CELL + 5))
    assert len(m.game.move_history) == 1
    t0 = time.time()
    while len(m.game.move_history) < 2 and time.time() - t0 < 10:
        m.update(); time.sleep(0.001)
    assert len(m.game.move_history) == 2 and m.game.move_history[1][0] == WHITE


def test_describe_stats():
    from ui.match import describe_stats
    assert describe_stats({"nodes": 1234, "value_estimate": -0.5}) == "1,234 nodes · value -0.50"
    assert describe_stats({}) == ""


# ---------- Menu ----------
def test_menu_start_config_and_availability(agents_cfg):
    pytest.importorskip("pygame")
    from ui.menu import Menu
    got = []
    menu = Menu(got.append, agents_cfg)
    names = [p.name for p in menu.presets]
    menu.human_side = WHITE                                # người cầm Trắng => agent cầm Đen
    menu.sel_opponent.index = names.index("nn")
    menu.start()
    assert got[-1] == {"time": None, "black": "nn", "white": None}
    menu.sel_opponent.index = names.index("nn_missing")
    assert not menu.can_start()                            # agent thiếu checkpoint -> nút Start bị khóa
    menu.mode = "ava"
    menu.sel_black.index, menu.sel_white.index = names.index("random"), names.index("rl")
    assert menu.can_start()
    menu.start()
    assert got[-1]["black"] == "random" and got[-1]["white"] == "rl"


def test_app_frames_menu_to_game_and_error_on_bad_agent(monkeypatch, agents_cfg):
    pygame = pytest.importorskip("pygame")
    from ui import match as M
    from ui.app import App
    monkeypatch.setattr(M, "AGENT_DELAY", 0.0)
    app = App(seed=0, agents_config=agents_cfg)
    app.init_graphics()
    app.frame([], (0, 0))                                  # vẽ menu
    app.start_match({"black": "random", "white": "nn", "time": None})
    assert app.state == "game"
    t0 = time.time()
    while len(app.match.game.move_history) < 4 and time.time() - t0 < 10:
        app.frame([], (0, 0))
        time.sleep(0.005)
    assert len(app.match.game.move_history) >= 4
    app.frame([pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE)], (0, 0))
    assert app.state == "menu"
    app.start_match({"black": "nn_missing", "white": None, "time": None})   # tạo agent lỗi -> báo trên menu, không văng lỗi
    assert app.state == "menu" and "Could not create agent" in app.menu.error
    pygame.quit()