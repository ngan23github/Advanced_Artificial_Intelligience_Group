"""Giải đấu round-robin cho các agent Othello.

Chạy:
    python -m eval.tournament --config configs/tournament.yaml
    python -m eval.tournament --config configs/tournament.yaml --games 20 --run-name smoke --workers 2

Thiết kế (để công bằng và tái lập được):
- Mỗi cặp (A, B) đấu `games_per_pair` ván, chia thành các "cặp ván": 2 ván cùng khai cuộc,
  A cầm Đen ở ván đầu và cầm Trắng ở ván sau => đi trước/sau chia đều tuyệt đối.
- Khai cuộc: `opening_plies` nước đầu chọn ngẫu nhiên theo seed (agent không bị tính giờ ở các nước này).
  Cần thiết vì agent tất định (Alpha-Beta) đấu nhau sẽ lặp đúng 1 ván nếu không có khai cuộc ngẫu nhiên.
- Mỗi ván tạo agent MỚI từ cấu hình với seed xác định => chạy lại ra đúng nước đi (trừ thời gian).
- Agent nhận `game.clone()`, nên không thể làm hỏng ván thật; nước đi sai sẽ làm giải đấu dừng với lỗi rõ ràng.
- Chạy nhiều chế độ ngân sách (time_budget khác nhau) trên cùng cấu hình.

Đầu ra trong <output_dir>/<run_name>/:
    games.jsonl          log thô, 1 dòng / ván (KHÔNG chỉnh tay)
    summary.json         độ đo từng cặp + ma trận score theo từng chế độ
    matrix_<mode>.csv    ma trận score (hàng thắng cột) để dán vào báo cáo
    config_snapshot.yaml, agents_snapshot.yaml, meta.json   để tái lập
"""

import argparse
import csv
import itertools
import json
import os
import platform
import random
import subprocess
import sys
import time
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime
from pathlib import Path
from typing import Optional

import numpy as np
import yaml

from agents.base import Agent
from agents.registry import build_agent
from eval.metrics import aggregate_match
from othello.encoding import BLACK, WHITE
from othello.game import OthelloGame


class IllegalAgentMove(RuntimeError):
    """Agent trả về nước đi không hợp lệ hoặc sai định dạng."""


# ---------- một ván ----------
def random_opening(seed: int, plies: int) -> list:
    """`plies` nước đầu chọn ngẫu nhiên (có seed) từ vị trí đầu."""
    rng = random.Random(seed)
    game = OthelloGame()
    opening = []
    for _ in range(plies):
        if game.is_terminal():
            break
        action = rng.choice(game.legal_actions())
        game.step(action)
        opening.append(action)
    return opening


def play_game(black: Agent, white: Agent,
              budget_black: Optional[float] = None, budget_white: Optional[float] = None,
              opening=()) -> dict:
    """Chơi 1 ván. Trả về record (chưa có tên/seed; play_pair sẽ bổ sung).

    Thời gian mỗi nước đo bằng perf_counter, chỉ tính các nước do agent chọn (không tính khai cuộc).
    """
    game = OthelloGame()
    for action in opening:
        game.step(action)
    black.reset()
    white.reset()
    players = {BLACK: (black, budget_black), WHITE: (white, budget_white)}

    move_log = []
    while not game.is_terminal():
        player = game.current_player
        agent, budget = players[player]
        legal = game.legal_actions()
        t0 = time.perf_counter()
        raw = agent.select_action(game.clone(), budget)  # clone: agent không phá được ván thật
        ms = (time.perf_counter() - t0) * 1000.0
        try:
            action = tuple(int(x) for x in raw)
        except (TypeError, ValueError):
            raise IllegalAgentMove(f"{agent.name} trả về action sai định dạng: {raw!r}")
        if action not in legal:
            raise IllegalAgentMove(
                f"{agent.name} đi nước không hợp lệ {action}; hợp lệ: {legal}")
        entry = {"p": player, "a": list(action), "ms": round(ms, 3)}
        stats = agent.stats()
        if stats:
            entry["stats"] = dict(stats)
        move_log.append(entry)
        game.step(action)

    black_discs, white_discs = game.score()
    return {
        "result_black": game.result(BLACK),
        "black_discs": black_discs,
        "white_discs": white_discs,
        "n_moves": len(game.move_history),
        "opening": [list(a) for a in opening],
        "move_log": move_log,
    }


def play_pair(task: dict) -> list:
    """Chơi 2 ván cùng khai cuộc, đổi màu. `task` là dict thuần (để gửi sang tiến trình khác)."""
    base = task["seed"] * 1_000_000 + task["pair"] * 10
    seeds = {"a": base + 1, "b": base + 2, "opening": base + 3}
    opening = random_opening(seeds["opening"], task["opening_plies"])

    records = []
    for a_is_black in (True, False):
        a = build_agent(task["a_spec"], seed=seeds["a"], name=task["a"])
        b = build_agent(task["b_spec"], seed=seeds["b"], name=task["b"])
        black, white = (a, b) if a_is_black else (b, a)
        budget_black = task["budget_a"] if a_is_black else task["budget_b"]
        budget_white = task["budget_b"] if a_is_black else task["budget_a"]
        record = play_game(black, white, budget_black, budget_white, opening)
        record.update({
            "game_id": f"{task['mode']}|{task['a']}|{task['b']}|s{task['seed']}|p{task['pair']}|"
                       f"{'AB' if a_is_black else 'BA'}",
            "mode": task["mode"],
            "a": task["a"],
            "b": task["b"],
            "a_is_black": a_is_black,
            "black": task["a"] if a_is_black else task["b"],
            "white": task["b"] if a_is_black else task["a"],
            "seed": task["seed"],
            "pair": task["pair"],
            "agent_seeds": seeds,
            "budget": {"black": budget_black, "white": budget_white},
        })
        records.append(record)
    return records


# ---------- lập kế hoạch giải đấu ----------
def split_pairs(games_per_pair: int, seeds: list) -> dict:
    """Chia số cặp ván (= games_per_pair / 2) đều cho các seed. Trả về {seed: số cặp ván}."""
    if games_per_pair <= 0 or games_per_pair % 2:
        raise ValueError(f"games_per_pair phải là số chẵn dương (để chia đều đi trước/sau), nhận {games_per_pair}")
    if not seeds or len(set(seeds)) != len(seeds):
        raise ValueError("seeds phải không rỗng và không trùng nhau")
    pairs = games_per_pair // 2
    base, extra = divmod(pairs, len(seeds))
    return {s: base + (1 if i < extra else 0) for i, s in enumerate(seeds)}


def _budget_for(mode: dict, agent_name: str):
    return (mode.get("per_agent") or {}).get(agent_name, mode.get("time_budget"))


def build_tasks(cfg: dict, specs: dict) -> list:
    names = list(cfg["agents"])
    if len(names) < 2 or len(set(names)) != len(names):
        raise ValueError("Cần ít nhất 2 agent khác tên trong `agents`.")
    missing = [n for n in names if n not in specs]
    if missing:
        raise KeyError(f"Agent chưa khai báo trong agents.yaml: {missing}")
    if not cfg.get("modes"):
        raise ValueError("Cần ít nhất 1 chế độ trong `modes`.")
    chunks = split_pairs(int(cfg["games_per_pair"]), list(cfg["seeds"]))

    tasks = []
    for mode in cfg["modes"]:
        for a, b in itertools.combinations(names, 2):
            for seed, n_pairs in chunks.items():
                for pair in range(n_pairs):
                    tasks.append({
                        "mode": mode["name"], "a": a, "b": b,
                        "a_spec": specs[a], "b_spec": specs[b],
                        "budget_a": _budget_for(mode, a), "budget_b": _budget_for(mode, b),
                        "seed": seed, "pair": pair,
                        "opening_plies": int(cfg.get("opening_plies", 4)),
                    })
    return tasks


# ---------- chạy và ghi kết quả ----------
def _json_default(o):
    if isinstance(o, np.integer):
        return int(o)
    if isinstance(o, np.floating):
        return float(o)
    if isinstance(o, np.ndarray):
        return o.tolist()
    raise TypeError(f"Không ghi được kiểu {type(o)} ra JSON")


def _git_commit() -> Optional[str]:
    try:
        out = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, timeout=5)
        return out.stdout.strip() or None
    except Exception:
        return None


def _write_matrix_csv(path: Path, names: list, matrix: dict):
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["agent \\ đối thủ"] + names)
        for row in names:
            writer.writerow([row] + ["-" if row == col else f"{matrix[row][col]:.4f}" for col in names])


def run_round_robin(cfg: dict, specs: dict, out_dir, workers: int = 1, verbose: bool = True) -> dict:
    """Chạy toàn bộ giải đấu theo cấu hình, ghi log + tóm tắt vào out_dir. Trả về summary."""
    out_dir = Path(out_dir)
    if out_dir.exists() and any(out_dir.iterdir()):
        raise FileExistsError(f"{out_dir} đã có dữ liệu. Đổi run_name hoặc xóa thư mục để tránh ghi đè log thô.")
    tasks = build_tasks(cfg, specs)
    out_dir.mkdir(parents=True, exist_ok=True)

    names = list(cfg["agents"])
    with open(out_dir / "config_snapshot.yaml", "w", encoding="utf-8") as f:
        yaml.safe_dump(cfg, f, allow_unicode=True, sort_keys=False)
    with open(out_dir / "agents_snapshot.yaml", "w", encoding="utf-8") as f:
        yaml.safe_dump({n: specs[n] for n in names}, f, allow_unicode=True, sort_keys=False)

    started = datetime.now().astimezone()
    t0 = time.perf_counter()
    grouped = defaultdict(list)
    total, done = len(tasks), 0
    step = max(1, total // 20)

    def consume(results_iter):
        nonlocal done
        with open(out_dir / "games.jsonl", "w", encoding="utf-8") as log:
            for records in results_iter:
                for rec in records:
                    log.write(json.dumps(rec, ensure_ascii=False, default=_json_default) + "\n")
                    grouped[(rec["mode"], rec["a"], rec["b"])].append(rec)
                log.flush()
                done += 1
                if verbose and (done % step == 0 or done == total):
                    print(f"  {done}/{total} cặp ván ({100 * done // total}%)", flush=True)

    if verbose:
        print(f"Giải đấu '{cfg.get('run_name', '')}': {len(names)} agent, {total} cặp ván "
              f"({2 * total} ván), workers={workers}")
    if workers and workers > 1:
        with ProcessPoolExecutor(max_workers=workers) as pool:
            consume(pool.map(play_pair, tasks, chunksize=1))  # map giữ nguyên thứ tự => log tất định
    else:
        consume(play_pair(t) for t in tasks)

    # ----- tóm tắt -----
    modes_summary = {}
    for mode in cfg["modes"]:
        matches, matrix = [], {n: {} for n in names}
        for a, b in itertools.combinations(names, 2):
            agg = aggregate_match(grouped[(mode["name"], a, b)], a, b)
            matches.append(agg)
            score = agg["a_summary"]["score"]
            matrix[a][b], matrix[b][a] = score, 1.0 - score
        mean_score = {n: float(np.mean([matrix[n][m] for m in names if m != n])) for n in names}
        modes_summary[mode["name"]] = {
            "time_budget": mode.get("time_budget"),
            "per_agent": mode.get("per_agent"),
            "matches": matches,
            "score_matrix": matrix,
            "mean_score": mean_score,
        }
        _write_matrix_csv(out_dir / f"matrix_{mode['name']}.csv", names, matrix)

    meta = {
        "started_at": started.isoformat(timespec="seconds"),
        "elapsed_seconds": round(time.perf_counter() - t0, 2),
        "python": sys.version.split()[0],
        "numpy": np.__version__,
        "platform": platform.platform(),
        "processor": platform.processor(),
        "cpu_count": os.cpu_count(),
        "workers": workers,
        "git_commit": _git_commit(),
        "total_games": 2 * total,
    }
    summary = {"run_name": cfg.get("run_name"), "meta": meta, "config": cfg, "modes": modes_summary}
    with open(out_dir / "summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2, default=_json_default)
    with open(out_dir / "meta.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    if verbose:
        print(f"Xong trong {meta['elapsed_seconds']}s. Kết quả: {out_dir}")
        for mode_name, ms in modes_summary.items():
            ranking = sorted(ms["mean_score"].items(), key=lambda kv: -kv[1])
            print(f"  [{mode_name}] " + " > ".join(f"{n} ({s:.3f})" for n, s in ranking))
    return summary


# ---------- dòng lệnh ----------
def load_yaml(path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Giải đấu round-robin Othello")
    parser.add_argument("--config", default="configs/tournament.yaml")
    parser.add_argument("--out", help="ghi đè output_dir trong config")
    parser.add_argument("--run-name", help="ghi đè run_name trong config")
    parser.add_argument("--games", type=int, help="ghi đè games_per_pair (để chạy thử nhanh)")
    parser.add_argument("--workers", type=int, help="ghi đè workers")
    args = parser.parse_args(argv)

    cfg = load_yaml(args.config)
    if args.games is not None:
        cfg["games_per_pair"] = args.games
    if args.run_name:
        cfg["run_name"] = args.run_name

    agents_path = Path(cfg["agents_config"])
    if not agents_path.exists():  # cho phép chạy từ thư mục khác
        agents_path = Path(args.config).parent / agents_path.name
    specs = load_yaml(agents_path)["agents"]

    out_dir = Path(args.out or cfg.get("output_dir", "results/logs")) / cfg["run_name"]
    workers = args.workers if args.workers is not None else int(cfg.get("workers", 1))
    run_round_robin(cfg, specs, out_dir, workers=workers)


if __name__ == "__main__":
    main()
