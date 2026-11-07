#!/usr/bin/env python3
"""tune.py - chạy thí nghiệm fine-tune cho Cấp 2 (Heuristic), Cấp 3 (Alpha-Beta), Cấp 4 (MCTS) + ghi nhật ký.

Mỗi ván được đấu theo CẶP: cùng một khai cuộc ngẫu nhiên, đổi màu 2 lần -> giảm nhiễu do may rủi.
Alpha-Beta/Heuristic gần như tất định nên BẮT BUỘC có khai cuộc ngẫu nhiên (--plies) mới ra các ván khác nhau.

Đầu ra (trong --out, mặc định results/):
    games.jsonl   nhật ký MỌI ván: cấu hình 2 bên, khai cuộc, từng nước (người đi, ô, thời gian, nodes, sims, số quân...)
    summary.csv   mỗi dòng 1 cấu hình: thắng/hòa/thua, win-rate + khoảng tin cậy 95% (Wilson), thời gian/nước, nodes, sims
    bench_raw.csv, bench_summary.csv   (lệnh bench) số nút + thời gian Alpha-Beta theo độ sâu / cắt tỉa

Ví dụ:
    python tune.py match --a '{"type":"alphabeta","depth":3}' --b '{"type":"mcts","simulations":1000}' --pairs 25
    python tune.py sweep --base '{"type":"mcts","simulations":1000}' --param exploration_c --values 0.5 1 1.414 2 \
                         --opp '{"type":"alphabeta","depth":2}' --pairs 25 --workers 4
    python tune.py sweep --base '{"type":"alphabeta","depth":3}' --param weights.mobility --values 10 20 40 60 \
                         --opp '{"type":"alphabeta","depth":3}'
    python tune.py heuristic --pairs 25
    python tune.py bench --max-depth 5 --nopr-depth 4
Trường "budget" trong spec (giây/nước) -> truyền time_budget cho agent đó; không có thì agent chạy theo depth/simulations.
"""

import argparse
import copy
import csv
import json
import math
import os
import random
import sys
from pathlib import Path
import time
from multiprocessing import Pool
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
from othello.encoding import BLACK, WHITE
from othello.game import OthelloGame


# =============================================================================
# Agent: tạo từ spec (dict JSON)
# =============================================================================
class RandomAgent:
    """Đối thủ ngẫu nhiên tối thiểu (không phụ thuộc agents.base)."""

    def __init__(self, seed=None, **kw):
        self.rng = random.Random(seed)
        self.name = "Random"

    def reset(self):
        pass

    def stats(self):
        return {"nodes": 0, "simulations": 0}

    def select_action(self, game, time_budget=None):
        acts = game.legal_actions()
        return self.rng.choice(acts) if acts else None


def build_agent(spec: dict, seed: int):
    spec = dict(spec)
    kind = spec.pop("type")
    spec.pop("budget", None)
    spec.setdefault("seed", seed)
    if kind == "random":
        return RandomAgent(**spec)
    if kind == "heuristic":
        from agents.heuristic_agent import HeuristicAgent      # chỉnh đường dẫn import nếu project đặt tên khác
        spec.setdefault("config_file", None)                    # không để YAML chen vào thí nghiệm
        return HeuristicAgent(**spec)
    if kind == "alphabeta":
        from agents.alphabeta_agent import AlphaBetaAgent
        return AlphaBetaAgent(**spec)
    if kind == "mcts":
        from agents.mcts_agent import MCTSAgent
        return MCTSAgent(**spec)
    raise ValueError(f"type không biết: {kind} (random | heuristic | alphabeta | mcts)")


def short(spec: dict) -> str:
    return json.dumps(spec, ensure_ascii=False, sort_keys=True)


# =============================================================================
# Chơi 1 ván + nhật ký
# =============================================================================
def random_opening(plies: int, rng: random.Random) -> list:
    g = OthelloGame()
    moves = []
    for _ in range(plies):
        if g.is_terminal():
            break
        a = rng.choice(g.legal_actions())
        g.step(a)
        moves.append(list(a))
    return moves


def play_game(black_spec, white_spec, opening, seed):
    agents = {BLACK: build_agent(black_spec, seed), WHITE: build_agent(white_spec, seed + 1)}
    budgets = {BLACK: black_spec.get("budget"), WHITE: white_spec.get("budget")}
    for a in agents.values():
        a.reset()
    game = OthelloGame()
    for mv in opening:
        game.step(tuple(mv))
    moves = []
    while not game.is_terminal():
        p = game.current_player
        legal = game.legal_actions()
        t0 = time.perf_counter()
        action = agents[p].select_action(game, budgets[p])
        dt = time.perf_counter() - t0
        st = agents[p].stats()
        if action is None or tuple(action) not in legal:
            raise RuntimeError(f"Agent {'đen' if p == BLACK else 'trắng'} trả nước không hợp lệ: {action}")
        game.step(tuple(action))
        b, w = game.score()
        moves.append({
            "ply": len(opening) + len(moves) + 1, "player": p, "move": list(action), "n_legal": len(legal),
            "time": round(dt, 5), "nodes": st.get("nodes", 0), "sims": st.get("simulations", 0),
            "value": st.get("value"), "black": b, "white": w,
        })
    b, w = game.score()
    return {"opening": opening, "moves": moves, "black": b, "white": w, "result_black": game.result(BLACK)}


def _task(t):
    spec_a, spec_b, a_black, opening, seed = t
    rec = play_game(spec_a if a_black else spec_b, spec_b if a_black else spec_a, opening, seed)
    rec["a_black"] = a_black
    rec["result_a"] = rec["result_black"] * (1 if a_black else -1)
    return rec


# =============================================================================
# Chạy 1 cấu hình A vs B (theo cặp, đổi màu) + tổng hợp
# =============================================================================
def wilson(score, n, z=1.96):
    if n == 0:
        return 0.0, 0.0
    p = score / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (c - h) / d, (c + h) / d


def run_match(tag, spec_a, spec_b, pairs, plies, seed, workers, out):
    os.makedirs(out, exist_ok=True)
    rng = random.Random(seed)
    tasks = []
    for _ in range(pairs):
        op = random_opening(plies, rng)
        for a_black in (True, False):
            tasks.append((spec_a, spec_b, a_black, op, seed * 100003 + len(tasks) * 7))

    t0 = time.time()
    if workers > 1:
        with Pool(workers) as pool:
            recs = pool.map(_task, tasks, chunksize=1)
    else:
        recs = [_task(t) for t in tasks]

    w = sum(r["result_a"] == 1 for r in recs)
    d = sum(r["result_a"] == 0 for r in recs)
    l = sum(r["result_a"] == -1 for r in recs)
    n = len(recs)
    lo, hi = wilson(w + 0.5 * d, n)

    def side_stats(is_a):
        ts, nodes, sims = [], [], []
        for r in recs:
            mine = BLACK if (r["a_black"] == is_a) else WHITE
            for m in r["moves"]:
                if m["player"] == mine:
                    ts.append(m["time"]); nodes.append(m["nodes"]); sims.append(m["sims"])
        k = max(len(ts), 1)
        return sum(ts) / k, sum(nodes) / k, sum(sims) / k

    ta, na, sa = side_stats(True)
    tb, nb, sb = side_stats(False)
    row = {
        "tag": tag, "A": short(spec_a), "B": short(spec_b), "games": n, "A_wins": w, "draws": d, "A_losses": l,
        "A_winrate": round((w + 0.5 * d) / n, 3), "ci95_lo": round(lo, 3), "ci95_hi": round(hi, 3),
        "A_time_per_move": round(ta, 4), "A_nodes": round(na, 1), "A_sims": round(sa, 1),
        "B_time_per_move": round(tb, 4), "B_nodes": round(nb, 1), "B_sims": round(sb, 1),
        "plies_random": plies, "seed": seed, "wall_s": round(time.time() - t0, 1),
    }

    with open(os.path.join(out, "games.jsonl"), "a", encoding="utf-8") as f:
        for i, r in enumerate(recs):
            f.write(json.dumps({"tag": tag, "A": spec_a, "B": spec_b, "game": i, **r}, ensure_ascii=False) + "\n")
    path = os.path.join(out, "summary.csv")
    new = not os.path.exists(path)
    with open(path, "a", newline="", encoding="utf-8") as f:
        wr = csv.DictWriter(f, fieldnames=list(row))
        if new:
            wr.writeheader()
        wr.writerow(row)

    print(f"[{tag}] A {w}-{d}-{l} B | winrate A = {row['A_winrate']:.3f} "
          f"(95% CI {lo:.3f}-{hi:.3f}) | A {ta*1000:.0f}ms/nước, B {tb*1000:.0f}ms/nước | {row['wall_s']}s")
    return row


# =============================================================================
# Lệnh: sweep (quét 1 tham số, hỗ trợ khóa lồng: weights.mobility, eval.mobility, ...)
# =============================================================================
def set_nested(d, key, val):
    parts = key.split(".")
    for p in parts[:-1]:
        d = d.setdefault(p, {})
    d[parts[-1]] = val


def parse_val(s):
    try:
        return json.loads(s)
    except json.JSONDecodeError:
        return s


def cmd_sweep(a):
    base, opp = json.loads(a.base), json.loads(a.opp)
    for v in a.values:
        val = parse_val(v)
        spec = copy.deepcopy(base)
        set_nested(spec, a.param, val)
        run_match(f"{a.param}={v}", spec, opp, a.pairs, a.plies, a.seed, a.workers, a.out)


def cmd_match(a):
    run_match(a.tag or "match", json.loads(a.a), json.loads(a.b), a.pairs, a.plies, a.seed, a.workers, a.out)


# =============================================================================
# Lệnh: heuristic (so các thứ tự ưu tiên: vs Random và round-robin)
# =============================================================================
def heuristic_candidates():
    from configs.constants import DEFAULT_PRIORITIES
    default = list(DEFAULT_PRIORITIES)
    return {
        "default": default,
        "no_deny_corner": [r for r in default if r != "deny_corner"],
        "mobility_first": ["win_now", "take_corner", "deny_corner", "maximize_mobility",
                           "avoid_x_square", "avoid_c_square", "maximize_discs"],
        "discs_before_mobility": ["win_now", "take_corner", "deny_corner", "avoid_x_square",
                                  "avoid_c_square", "maximize_discs", "maximize_mobility"],
        "corner_only": ["win_now", "take_corner", "avoid_x_square", "avoid_c_square", "maximize_discs"],
        "greedy_discs": ["win_now", "maximize_discs"],
    }


def cmd_heuristic(a):
    cands = heuristic_candidates()
    specs = {k: {"type": "heuristic", "priorities": v, "name": k} for k, v in cands.items()}
    rnd = {"type": "random"}
    print("== Heuristic vs Random ==")
    for k, s in specs.items():
        run_match(f"heur:{k} vs random", s, rnd, a.pairs, a.plies, a.seed, a.workers, a.out)
    print("== Round-robin giữa các thứ tự ==")
    names = list(specs)
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            run_match(f"heur:{names[i]} vs {names[j]}", specs[names[i]], specs[names[j]],
                      a.pairs, a.plies, a.seed, a.workers, a.out)


# =============================================================================
# Lệnh: bench (số nút + thời gian Alpha-Beta theo độ sâu, có/không cắt tỉa, có/không ordering)
# =============================================================================
def sample_positions(per_phase, plies_list, seed):
    rng = random.Random(seed)
    out = []
    for ply in plies_list:
        got = 0
        while got < per_phase:
            mv = random_opening(ply, rng)
            if len(mv) < ply:
                continue
            g = OthelloGame()
            for m in mv:
                g.step(tuple(m))
            if not g.is_terminal():
                out.append((ply, mv))
                got += 1
    return out


def cmd_bench(a):
    from agents.alphabeta_agent import AlphaBetaAgent
    os.makedirs(a.out, exist_ok=True)
    positions = sample_positions(a.per_phase, [8, 16, 24, 32, 40, 48], a.seed)
    base_kw = json.loads(a.base) if a.base else {}
    rows, chosen = [], {}
    configs = [(False, False), (True, False), (False, True), (True, True)]   # (pruning, ordering)
    for depth in range(1, a.max_depth + 1):
        for pruning, ordering in configs:
            if not pruning and depth > a.nopr_depth:
                continue
            for pi, (ply, mv) in enumerate(positions):
                g = OthelloGame()
                for m in mv:
                    g.step(tuple(m))
                ag = AlphaBetaAgent(depth=depth, pruning=pruning, move_ordering=ordering, **base_kw)
                t0 = time.perf_counter()
                act = ag.select_action(g)
                dt = time.perf_counter() - t0
                chosen[(depth, pruning, ordering, pi)] = tuple(act)
                rows.append({"depth": depth, "pruning": pruning, "ordering": ordering, "pos": pi, "ply": ply,
                             "nodes": ag.stats()["nodes"], "time": round(dt, 5), "move": list(act)})
            print(f"depth {depth} pruning={pruning} ordering={ordering} xong")
    with open(os.path.join(a.out, "bench_raw.csv"), "w", newline="", encoding="utf-8") as f:
        wr = csv.DictWriter(f, fieldnames=list(rows[0]))
        wr.writeheader()
        wr.writerows(rows)

    summ = []
    for depth in range(1, a.max_depth + 1):
        for pruning, ordering in configs:
            rs = [r for r in rows if r["depth"] == depth and r["pruning"] == pruning and r["ordering"] == ordering]
            if not rs:
                continue
            mism = ""
            if pruning and (depth, False, ordering, 0) in chosen:     # so với cùng cấu hình KHÔNG cắt tỉa
                mism = sum(chosen[(depth, True, ordering, i)] != chosen[(depth, False, ordering, i)]
                           for i in range(len(positions)))
            summ.append({"depth": depth, "pruning": pruning, "ordering": ordering,
                         "mean_nodes": round(sum(r["nodes"] for r in rs) / len(rs), 1),
                         "mean_time_s": round(sum(r["time"] for r in rs) / len(rs), 4),
                         "move_mismatch_vs_no_pruning": mism, "positions": len(rs)})
    with open(os.path.join(a.out, "bench_summary.csv"), "w", newline="", encoding="utf-8") as f:
        wr = csv.DictWriter(f, fieldnames=list(summ[0]))
        wr.writeheader()
        wr.writerows(summ)
    print("\ndepth pruning ordering  mean_nodes  mean_time_s  mismatch(prune vs no-prune)")
    for s in summ:
        print(f"{s['depth']:>5} {str(s['pruning']):>7} {str(s['ordering']):>8} {s['mean_nodes']:>11} "
              f"{s['mean_time_s']:>12} {str(s['move_mismatch_vs_no_pruning']):>10}")


# =============================================================================
def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    def common(sp):
        sp.add_argument("--pairs", type=int, default=25, help="số cặp khai cuộc (mỗi cặp = 2 ván đổi màu)")
        sp.add_argument("--plies", type=int, default=6, help="số nước ngẫu nhiên mở đầu mỗi cặp")
        sp.add_argument("--seed", type=int, default=0)
        sp.add_argument("--workers", type=int, default=1, help="số tiến trình song song (<= số nhân CPU - 1)")
        sp.add_argument("--out", default="results")

    s = sub.add_parser("match"); common(s)
    s.add_argument("--a", required=True); s.add_argument("--b", required=True); s.add_argument("--tag")
    s.set_defaults(fn=cmd_match)

    s = sub.add_parser("sweep"); common(s)
    s.add_argument("--base", required=True); s.add_argument("--param", required=True)
    s.add_argument("--values", nargs="+", required=True); s.add_argument("--opp", required=True)
    s.set_defaults(fn=cmd_sweep)

    s = sub.add_parser("heuristic"); common(s); s.set_defaults(fn=cmd_heuristic)

    s = sub.add_parser("bench")
    s.add_argument("--max-depth", type=int, default=5)
    s.add_argument("--nopr-depth", type=int, default=4, help="độ sâu tối đa khi TẮT cắt tỉa (rất chậm nếu cao)")
    s.add_argument("--per-phase", type=int, default=5, help="số vị trí mỗi giai đoạn ván")
    s.add_argument("--base", help='JSON tham số thêm cho AlphaBetaAgent, vd {"weights":{"mobility":40}}')
    s.add_argument("--seed", type=int, default=0); s.add_argument("--out", default="results")
    s.set_defaults(fn=cmd_bench)

    a = p.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()