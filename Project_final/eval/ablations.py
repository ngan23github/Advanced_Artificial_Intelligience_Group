"""Chạy các thí nghiệm ablation bằng cùng runner tournament chính thức."""

import argparse
from copy import deepcopy
from pathlib import Path

from eval.tournament import load_yaml, run_round_robin


EXPERIMENTS = {
    "alphabeta_pruning": ["alphabeta", "alphabeta_nopruning"],
    "mcts_simulations": ["mcts_100", "mcts_500", "mcts", "mcts_5000"],
    "heuristic_components": [
        "alphabeta",
        "alphabeta_discs_only",
        "heuristic",
        "heuristic_discs_only",
    ],
}


def run_ablations(cfg: dict, specs: dict, out_dir, workers: int = 1,
                  games: int = None, verbose: bool = True) -> dict:
    """Chạy từng ablation vào thư mục con riêng và trả về summary theo tên."""
    out_dir = Path(out_dir)
    results = {}
    for name, agents in EXPERIMENTS.items():
        missing = [agent for agent in agents if agent not in specs]
        if missing:
            raise KeyError(f"Ablation {name} thiếu agent trong agents.yaml: {missing}")
        experiment_cfg = deepcopy(cfg)
        experiment_cfg["agents"] = agents
        experiment_cfg["run_name"] = f"{cfg.get('run_name', 'ablation')}_{name}"
        if games is not None:
            experiment_cfg["games_per_pair"] = games
        results[name] = run_round_robin(
            experiment_cfg, specs, out_dir / name, workers=workers, verbose=verbose
        )
    return results


def main(argv=None):
    parser = argparse.ArgumentParser(description="Run Othello ablation experiments")
    parser.add_argument("--config", default="configs/tournament.yaml")
    parser.add_argument("--agents-config", help="override agents YAML")
    parser.add_argument("--out", default="results/logs/ablations")
    parser.add_argument("--games", type=int, help="override games per pair")
    parser.add_argument("--workers", type=int, default=1)
    args = parser.parse_args(argv)

    cfg = load_yaml(args.config)
    specs = load_yaml(args.agents_config or cfg["agents_config"])["agents"]
    run_ablations(cfg, specs, args.out, workers=args.workers, games=args.games)


if __name__ == "__main__":
    main()
