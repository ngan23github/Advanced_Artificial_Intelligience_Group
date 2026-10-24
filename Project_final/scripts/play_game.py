

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from othello.encoding import BLACK, WHITE
from othello.game import OthelloGame
from ui.agent_factory import AGENT_TYPES, make_agent


def play_one(black_agent, white_agent, verbose=False):
    """Chơi 1 ván. Trả về (kết quả theo góc nhìn đen, số nước, quân đen, quân trắng)."""
    game = OthelloGame()
    black_agent.reset()
    white_agent.reset()
    agents = {BLACK: black_agent, WHITE: white_agent}
    if verbose:
        print(game.render(), "\n")
    while not game.is_terminal():
        action = agents[game.current_player].select_action(game.clone())
        game.step(action)
        if verbose:
            print(game.render(), "\n")
    b, w = game.score()
    return game.result(BLACK), len(game.move_history), b, w


def run_cli(args):
    a = make_agent(args.black, args.seed)
    b = make_agent(args.white, None if args.seed is None else args.seed + 1)
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


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--cli", action="store_true", help="chạy không giao diện")
    p.add_argument("--games", type=int, default=1)
    p.add_argument("--seed", type=int, default=None)
    p.add_argument("--black", default="random", choices=list(AGENT_TYPES), help="(chỉ --cli)")
    p.add_argument("--white", default="random", choices=list(AGENT_TYPES), help="(chỉ --cli)")
    args = p.parse_args()

    if args.cli:
        run_cli(args)
    else:
        from ui.app import run_gui  # import ở đây để --cli không cần pygame
        run_gui(seed=args.seed)


if __name__ == "__main__":
    main()
