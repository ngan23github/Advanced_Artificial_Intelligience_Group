"""Đo chi phí suy nghĩ của agent trên các vị trí mở đầu tái lập được."""

import argparse
import json
import random
import time
import tracemalloc
from pathlib import Path

import numpy as np
import yaml

from agents.registry import build_agent
from eval.metrics import latency_summary
from othello.game import OthelloGame


def _positions(samples: int, seed: int):
    rng = random.Random(seed)
    for _ in range(samples):
        game = OthelloGame()
        for _ in range(rng.randint(0, 8)):
            if game.is_terminal():
                break
            game.step(rng.choice(game.legal_actions()))
        if not game.is_terminal():
            yield game


def profile_agent(spec: dict, name: str, samples: int = 20,
                  seed: int = 0, time_budget=None) -> dict:
    agent = build_agent(spec, seed=seed, name=name)
    times, nodes, simulations, peak_memory = [], [], [], []
    for game in _positions(samples, seed):
        agent.reset()
        tracemalloc.start()
        started = time.perf_counter()
        action = agent.select_action(game.clone(), time_budget)
        elapsed_ms = (time.perf_counter() - started) * 1000.0
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        if action not in game.legal_actions():
            raise RuntimeError(f"{name} trả về nước không hợp lệ: {action}")
        stats = agent.stats()
        times.append(elapsed_ms)
        peak_memory.append(peak / (1024 * 1024))
        if "nodes" in stats:
            nodes.append(stats["nodes"])
        if "simulations" in stats:
            simulations.append(stats["simulations"])
    return {
        "agent": name,
        "samples": len(times),
        "latency": latency_summary(times),
        "peak_tracemalloc_mb": max(peak_memory) if peak_memory else None,
        "nodes_mean": float(np.mean(nodes)) if nodes else None,
        "simulations_mean": float(np.mean(simulations)) if simulations else None,
        "seed": seed,
        "time_budget": time_budget,
    }


def profile_cost(specs: dict, names: list, samples: int = 20,
                 seed: int = 0, time_budget=None) -> dict:
    return {
        "profiles": [
            profile_agent(specs[name], name, samples, seed, time_budget)
            for name in names
        ]
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description="Profile Othello agent cost")
    parser.add_argument("--config", default="configs/agents.yaml")
    parser.add_argument("--agents", default="random,heuristic,alphabeta,mcts")
    parser.add_argument("--samples", type=int, default=20)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--time-budget", type=float)
    parser.add_argument("--out", default="results/logs/profile_cost.json")
    args = parser.parse_args(argv)

    with open(args.config, encoding="utf-8") as f:
        specs = yaml.safe_load(f)["agents"]
    names = [name.strip() for name in args.agents.split(",") if name.strip()]
    missing = [name for name in names if name not in specs]
    if missing:
        parser.error(f"unknown agents: {missing}")
    output = profile_cost(specs, names, args.samples, args.seed, args.time_budget)
    output["config"] = args.config
    output["agents"] = names
    path = Path(args.out)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Profile written to {path}")


if __name__ == "__main__":
    main()
