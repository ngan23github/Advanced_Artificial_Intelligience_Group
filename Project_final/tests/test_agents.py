"""Test chung cho mọi agent: trả về action hợp lệ, không sửa game, tái lập theo seed.

Khi có agent mới, thêm vào AGENT_FACTORIES là được test tự động.
"""

import tempfile
from pathlib import Path

import pytest

from agents.alphabeta_agent import AlphaBetaAgent
from agents.random_agent import RandomAgent
from othello.encoding import BLACK, WHITE
from othello.game import OthelloGame

AGENT_FACTORIES = {
    "random": lambda seed: RandomAgent(seed=seed),
    "alphabeta": lambda seed: AlphaBetaAgent(depth=2, seed=seed),
}

# NN (cấp 5) và RL (cấp 6): dùng checkpoint NHỎ, chưa train, tạo tại chỗ (không phụ thuộc file trong checkpoints/).
# Test này chỉ kiểm tra hợp đồng agent (nước hợp lệ, không sửa game, tái lập theo seed), không kiểm tra độ mạnh.
try:
    import torch

    from agents.nn_agent import NNAgent
    from agents.rl_agent import RLAgent
    from models.nets import PolicyValueNet, save_checkpoint

    _CKPT = Path(tempfile.mkdtemp()) / "tiny.pt"
    torch.manual_seed(0)
    save_checkpoint(_CKPT, PolicyValueNet(channels=8, hidden=16))
    AGENT_FACTORIES["nn"] = lambda seed: NNAgent(checkpoint=str(_CKPT), seed=seed, temperature=1.0)
    AGENT_FACTORIES["rl"] = lambda seed: RLAgent(checkpoint=str(_CKPT), seed=seed, temperature=1.0)
except ImportError:  # chưa cài torch: bỏ qua agent học được
    pass


def play(agent_b, agent_w, check_untouched=True):
    g = OthelloGame()
    agents = {BLACK: agent_b, WHITE: agent_w}
    while not g.is_terminal():
        snapshot = g.board.copy(), g.current_player, len(g.move_history)
        a = agents[g.current_player].select_action(g)
        assert a in g.legal_actions()
        if check_untouched:  # agent không được sửa game thật
            assert (g.board == snapshot[0]).all()
            assert g.current_player == snapshot[1]
            assert len(g.move_history) == snapshot[2]
        g.step(a)
    return g


@pytest.mark.parametrize("name", AGENT_FACTORIES)
def test_agent_plays_full_game_legally(name):
    g = play(AGENT_FACTORIES[name](0), AGENT_FACTORIES[name](1))
    assert g.is_terminal()
    assert g.result(BLACK) in (-1, 0, 1)


def test_random_is_reproducible_with_seed():
    g1 = play(RandomAgent(seed=7), RandomAgent(seed=8))
    g2 = play(RandomAgent(seed=7), RandomAgent(seed=8))
    assert g1.move_history == g2.move_history


def test_random_different_seeds_differ():
    g1 = play(RandomAgent(seed=1), RandomAgent(seed=2))
    g2 = play(RandomAgent(seed=3), RandomAgent(seed=4))
    assert g1.move_history != g2.move_history


@pytest.mark.parametrize("name", [n for n in ("nn", "rl") if n in AGENT_FACTORIES])
def test_learned_agents_reproducible_with_seed(name):
    g1 = play(AGENT_FACTORIES[name](7), AGENT_FACTORIES[name](8))
    g2 = play(AGENT_FACTORIES[name](7), AGENT_FACTORIES[name](8))
    assert g1.move_history == g2.move_history
