"""Chạy thử đường ống end-to-end: engine + agent.

    python scripts/play_game.py                # 1 ván Random vs Random, in bàn cờ
    python scripts/play_game.py --games 1000   # chạy nhiều ván, thống kê (có seed)
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.random_agent import RandomAgent
from othello.encoding import BLACK, WHITE
from othello.game import OthelloGame


def play_one(black_agent, white_agent, verbose=False):
    """Chơi 1 ván. Trả về (kết quả theo góc nhìn đen, số nước, quân đen, quân trắng)."""
    game = OthelloGame()
    black_agent.reset()
    white_agent.reset()
    agents = {BLACK: black_agent, WHITE: white_agent}
    print(game.render(), "\n")
    while not game.is_terminal():
        action = agents[game.current_player].select_action(game)
        game.step(action)
        if verbose:
            print(game.render(), "\n")
    b, w = game.score()
    return game.result(BLACK), len(game.move_history), b, w


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--games", type=int, default=1)
    p.add_argument("--seed", type=int, default=None)
    args = p.parse_args()

    a, b = RandomAgent(seed=args.seed, name="R1"), RandomAgent(seed=None if args.seed is None else args.seed + 1, name="R2")
    if args.games == 1:
        res, n, bl, wh = play_one(a, b, verbose=True)
        print(f"Kết quả (góc nhìn Đen): {res}, {n} nước, Đen {bl} - Trắng {wh}")
        return
    black_wins = white_wins = draws = 0
    for _ in range(args.games):
        res, *_ = play_one(a, b)
        black_wins += res == 1
        white_wins += res == -1
        draws += res == 0
    print(f"{args.games} ván | Đen thắng {black_wins} | Trắng thắng {white_wins} | Hòa {draws}")


if __name__ == "__main__":
    main()
