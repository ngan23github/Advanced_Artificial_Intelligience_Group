"""Ablation cho HeuristicAgent: bỏ từng luật xem sức mạnh giảm bao nhiêu.

    python scripts/run_heuristic_ablation.py --games 200                 # chạy đầy đủ (báo cáo)
    python scripts/run_heuristic_ablation.py --games 20 --out /tmp/abl   # chạy thử nhanh

Với mỗi biến thể V (bỏ 1 luật), đấu:  V vs Heuristic đầy đủ  và  V vs Random.
Mỗi cặp chơi --games ván, chia đều quyền đi trước (ván chẵn A cầm Đen, ván lẻ A cầm Trắng).
Seed mỗi ván = seed-base + chỉ số ván, nên chạy lại ra đúng kết quả. Dùng seed-base KHÁC với
seed lúc tune tham số (đề cấm chọn siêu tham số bằng chính các ván đánh giá cuối).

Kết quả (trong --out, mặc định results/heuristic_ablation/):
    games.csv     1 dòng / ván (log thô)
    summary.csv   bảng tổng hợp; summary.md  cùng bảng dạng markdown để dán vào báo cáo
Độ đo: score = (thắng + 0.5*hòa)/số ván của A; khoảng tin cậy Wilson 95% tính trên score
(xấp xỉ, coi mỗi hòa như nửa thắng); thời gian/nước (ms) trung bình và p95 của A.
"""

import argparse
import csv
import math
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.heuristic_agent import DEFAULT_PRIORITIES, HeuristicAgent
from agents.random_agent import RandomAgent
from othello.encoding import BLACK, WHITE
from othello.game import OthelloGame

ALL = list(DEFAULT_PRIORITIES)


def without(*rules):
    return {"priorities": [r for r in ALL if r not in rules]}


VARIANTS = {
    "full": {},
    "no_win_now": without("win_now"),
    "no_corner": without("take_corner"),
    "no_xc": without("avoid_x_square", "avoid_c_square"),
    "no_mobility": without("maximize_mobility"),
    "no_discs": without("maximize_discs"),
    "no_endgame_mode": {"endgame_empties": 0},
    "discs_only": {"priorities": ["maximize_discs"]},   # ablation "heuristic chỉ đếm quân"
    "all_off": {"priorities": []},                      # tương đương Random
}


def make_heuristic(kwargs):
    return lambda seed: HeuristicAgent(seed=seed, **kwargs)


def make_random():
    return lambda seed: RandomAgent(seed=seed)


def play(black, white):
    """1 ván. Trả về (result theo Đen, (đen, trắng), số nước, {player: [ms mỗi nước]})."""
    g = OthelloGame()
    black.reset()
    white.reset()
    agents, times = {BLACK: black, WHITE: white}, {BLACK: [], WHITE: []}
    while not g.is_terminal():
        p = g.current_player
        t0 = time.perf_counter()
        action = agents[p].select_action(g.clone())
        times[p].append((time.perf_counter() - t0) * 1000)
        g.step(action)
    return g.result(BLACK), g.score(), len(g.move_history), times


def wilson(p, n, z=1.96):
    if n == 0:
        return 0.0, 0.0
    den = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / den
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return max(0.0, centre - half), min(1.0, centre + half)


def p95(xs):
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(0.95 * len(xs)))] if xs else 0.0


def run_pair(name_a, make_a, name_b, make_b, games, seed_base, writer):
    results, a_times = [], []
    for i in range(games):
        a, b = make_a(seed_base + 2 * i), make_b(seed_base + 2 * i + 1)
        a_black = i % 2 == 0
        res_black, (nb, nw), plies, times = play(*((a, b) if a_black else (b, a)))
        res_a = res_black if a_black else -res_black
        results.append(res_a)
        a_times += times[BLACK if a_black else WHITE]
        writer.writerow([name_a, name_b, i, int(a_black), res_a, nb, nw, plies, seed_base + 2 * i])
    w, d, l = results.count(1), results.count(0), results.count(-1)
    score = (w + 0.5 * d) / games
    lo, hi = wilson(score, games)
    return dict(a=name_a, b=name_b, games=games, win=w, draw=d, loss=l, score=score, ci_lo=lo, ci_hi=hi,
                ms_mean=sum(a_times) / len(a_times), ms_p95=p95(a_times))


def to_markdown(rows):
    head = "| A | B | games | W | D | L | score | 95% CI | ms/move | p95 ms |\n|---|---|---|---|---|---|---|---|---|---|\n"
    body = "".join(
        f"| {r['a']} | {r['b']} | {r['games']} | {r['win']} | {r['draw']} | {r['loss']} | {r['score']:.3f} | "
        f"[{r['ci_lo']:.3f}, {r['ci_hi']:.3f}] | {r['ms_mean']:.2f} | {r['ms_p95']:.2f} |\n" for r in rows)
    return head + body


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--games", type=int, default=200, help="số ván mỗi cặp (đề: tối thiểu 100, khuyến nghị 200)")
    p.add_argument("--seed-base", type=int, default=1000)
    p.add_argument("--out", default="results/heuristic_ablation")
    p.add_argument("--variants", nargs="*", default=list(VARIANTS), choices=list(VARIANTS))
    args = p.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    rows = []
    with open(out / "games.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["a", "b", "game", "a_is_black", "result_a", "black_discs", "white_discs", "plies", "seed"])
        for name in args.variants:
            if name != "full":
                rows.append(run_pair(name, make_heuristic(VARIANTS[name]), "full",
                                     make_heuristic(VARIANTS["full"]), args.games, args.seed_base, w))
                print(f"{name} vs full done", flush=True)
            rows.append(run_pair(name, make_heuristic(VARIANTS[name]), "random", make_random(),
                                 args.games, args.seed_base, w))
            print(f"{name} vs random done", flush=True)

    with open(out / "summary.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    md = to_markdown(rows)
    (out / "summary.md").write_text(md, encoding="utf-8")
    print("\n" + md)


if __name__ == "__main__":
    main()
