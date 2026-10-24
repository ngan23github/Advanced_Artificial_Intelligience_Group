"""Độ đo cho giải đấu: thắng/hòa/thua, score, khoảng tin cậy, độ trễ, chi phí tính toán.

Tất cả là hàm thuần (không đọc/ghi file, không chạy game) nên test được dễ.

Quy ước kết quả: mỗi ván có `result` theo góc nhìn của một agent: +1 thắng, 0 hòa, -1 thua.
score = (thắng + 0.5 * hòa) / tổng số ván   (công thức của đề bài).
"""

import math
from typing import Iterable, Optional, Sequence

import numpy as np


# ---------- khoảng tin cậy ----------
def wilson_interval(successes: float, n: int, z: float = 1.96) -> tuple:
    """Khoảng tin cậy Wilson (mặc định 95%) cho tỷ lệ `successes / n`.

    Dùng cho tỷ lệ thắng. Với score có hòa (0.5 điểm) đây là xấp xỉ: coi `successes`
    = thắng + 0.5 * hòa như một số đếm. Muốn chặt hơn thì dùng bootstrap_score_ci.
    """
    if n <= 0:
        return (0.0, 1.0)  # chưa có dữ liệu: không biết gì
    p = successes / n
    z2 = z * z
    denom = 1.0 + z2 / n
    centre = (p + z2 / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z2 / (4 * n * n)) / denom
    return (max(0.0, centre - half), min(1.0, centre + half))


def bootstrap_score_ci(results: Sequence[int], n_boot: int = 2000,
                       alpha: float = 0.05, seed: int = 0) -> tuple:
    """Khoảng tin cậy bootstrap (percentile) cho score từ danh sách kết quả +1/0/-1."""
    if len(results) == 0:
        return (0.0, 1.0)
    per_game = (np.asarray(results, dtype=float) + 1.0) / 2.0  # +1 -> 1, 0 -> 0.5, -1 -> 0
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(per_game), size=(n_boot, len(per_game)))
    means = per_game[idx].mean(axis=1)
    return (float(np.quantile(means, alpha / 2)), float(np.quantile(means, 1 - alpha / 2)))


# ---------- thắng / hòa / thua ----------
def score_from_counts(wins: int, draws: int, losses: int) -> float:
    n = wins + draws + losses
    return (wins + 0.5 * draws) / n if n else float("nan")


def summarize_outcomes(results: Sequence[int], z: float = 1.96) -> dict:
    """Tóm tắt danh sách kết quả +1/0/-1 (góc nhìn một agent)."""
    n = len(results)
    wins = sum(1 for r in results if r == 1)
    draws = sum(1 for r in results if r == 0)
    losses = sum(1 for r in results if r == -1)
    score_lo, score_hi = wilson_interval(wins + 0.5 * draws, n, z)
    win_lo, win_hi = wilson_interval(wins, n, z)
    return {
        "games": n,
        "wins": wins,
        "draws": draws,
        "losses": losses,
        "win_rate": wins / n if n else float("nan"),
        "draw_rate": draws / n if n else float("nan"),
        "loss_rate": losses / n if n else float("nan"),
        "score": score_from_counts(wins, draws, losses),
        "score_ci": [score_lo, score_hi],
        "win_rate_ci": [win_lo, win_hi],
    }


# ---------- độ trễ ----------
def percentile(values: Sequence[float], q: float) -> float:
    """Percentile q (0..100), nội suy tuyến tính."""
    return float(np.percentile(np.asarray(values, dtype=float), q))


def latency_summary(times_ms: Sequence[float]) -> dict:
    """Thống kê thời gian suy nghĩ mỗi nước (ms): mean, p50, p95, max."""
    if len(times_ms) == 0:
        return {"moves": 0, "mean_ms": None, "p50_ms": None, "p95_ms": None, "max_ms": None}
    return {
        "moves": len(times_ms),
        "mean_ms": float(np.mean(times_ms)),
        "p50_ms": percentile(times_ms, 50),
        "p95_ms": percentile(times_ms, 95),
        "max_ms": float(np.max(times_ms)),
    }


def _mean_stat(entries: Iterable[dict], key: str) -> Optional[float]:
    vals = [e["stats"][key] for e in entries if e.get("stats") and key in e["stats"]]
    return float(np.mean(vals)) if vals else None


# ---------- gộp nhiều ván của một cặp agent ----------
def result_for_a(record: dict) -> int:
    """Kết quả (+1/0/-1) của agent A trong 1 ván log."""
    return record["result_black"] if record["a_is_black"] else -record["result_black"]


def aggregate_match(records: Sequence[dict], a_name: str, b_name: str) -> dict:
    """Gộp các ván log của cặp (A, B) thành các độ đo.

    Mỗi record cần: a_is_black, result_black, move_log (mỗi nước: p, ms, stats tùy chọn).
    Trả về dict có thể ghi thẳng ra JSON.
    """
    a_results = [result_for_a(r) for r in records]
    as_black = [result_for_a(r) for r in records if r["a_is_black"]]
    as_white = [result_for_a(r) for r in records if not r["a_is_black"]]

    # lợi thế đi trước: tỷ lệ ván mà quân Đen thắng / hòa (bất kể agent nào cầm Đen)
    n = len(records)
    black_wins = sum(1 for r in records if r["result_black"] == 1)
    black_draws = sum(1 for r in records if r["result_black"] == 0)

    latency, cost = {}, {}
    for name, is_a in ((a_name, True), (b_name, False)):
        moves = []
        for r in records:
            agent_is_black = r["a_is_black"] if is_a else (not r["a_is_black"])
            my_player = 1 if agent_is_black else -1
            moves.extend(m for m in r["move_log"] if m["p"] == my_player)
        latency[name] = latency_summary([m["ms"] for m in moves])
        cost[name] = {
            "nodes_mean": _mean_stat(moves, "nodes"),
            "simulations_mean": _mean_stat(moves, "simulations"),
        }

    return {
        "a": a_name,
        "b": b_name,
        "a_summary": summarize_outcomes(a_results),
        "a_score_bootstrap_ci": list(bootstrap_score_ci(a_results)),
        "a_as_black": summarize_outcomes(as_black),   # A đi trước
        "a_as_white": summarize_outcomes(as_white),   # A đi sau
        "black_win_rate": black_wins / n if n else float("nan"),
        "black_draw_rate": black_draws / n if n else float("nan"),
        "avg_game_length": float(np.mean([r["n_moves"] for r in records])) if n else None,
        "latency": latency,
        "cost": cost,
    }
