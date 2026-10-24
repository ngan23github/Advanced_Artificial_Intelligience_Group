"""Test chung cho mọi agent: trả về action hợp lệ, không sửa game, tái lập theo seed.

Khi có agent mới, thêm vào AGENT_FACTORIES là được test tự động.
"""

import pytest

from agents.random_agent import RandomAgent
from othello.encoding import BLACK, WHITE
from othello.game import OthelloGame

AGENT_FACTORIES = {
    "random": lambda seed: RandomAgent(seed=seed),
}


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
