#!/usr/bin/env python3
"""Chấm chất lượng TỪNG NƯỚC ĐI của một agent (thường là MCTS) bằng Alpha-Beta tham chiếu.

Phân tích bổ sung, không thay win-rate: win-rate nói agent thắng hay thua, còn cách này nói agent yếu ở GIAI ĐOẠN nào.

Quy trình:
  1. Đọc games.jsonl của giải đấu, dựng lại thế cờ trước mỗi nước đi của agent (replay bằng bitboard).
  2. Chọn mẫu phân tầng theo giai đoạn (số ô trống), tránh để một giai đoạn chiếm hết mẫu.
  3. Với mỗi thế cờ, Alpha-Beta tham chiếu tìm giá trị tốt nhất V* và giá trị nước agent đã đi V_agent.
       - tàn cuộc chính xác (số ô trống <= --exact-empties): giải TỚI HẾT VÁN, giá trị = chênh lệch quân cuối ván
         với hai bên chơi tối ưu. Đây là CHUẨN THẬT SỰ, không phụ thuộc hàm đánh giá.
       - còn lại: Alpha-Beta độ sâu --depth với hàm đánh giá tĩnh (trọng số --weights). "Nước tốt nhất" ở đây
         CHỈ LÀ ƯỚC LƯỢNG theo hàm đánh giá của Alpha-Beta, không phải sự thật. Báo cáo phải nói rõ.
  4. Chỉ số theo giai đoạn:
       tối ưu   : V_agent == V* (nước khác nhưng cùng giá trị vẫn tính tối ưu; nhiều nước tàn cuộc bằng giá trị)
       trùng    : đúng nước tham chiếu chọn
       regret   : V* - V_agent (>= 0; tàn cuộc tính bằng số quân, còn lại bằng điểm đánh giá)
       sai nặng : tàn cuộc = làm xấu kết quả (thắng->hòa/thua, hòa->thua); còn lại = regret >= --blunder-eval

Cách dùng (từ thư mục gốc dự án):
    python -m eval.move_quality --games results/logs/round_robin_v2/games.jsonl --agent mcts alphabeta random \\
        --mode time_per_move --per-phase 40 --depth 8 --exact-empties 12 --out results/analysis/move_quality
Chạy cùng lúc alphabeta và random để có mốc: Alpha-Beta (cận trên) và Random (cận dưới) giúp đọc con số của MCTS.
Chạy thử nhanh: thêm --per-phase 5 --depth 4 --exact-empties 8. Tốc độ đo được (Python): độ sâu 6 ~0.2 s/tìm kiếm, độ sâu 8 ~1.6 s,
giải chính xác 10 ô trống ~0.2 s, 12 ô trống ~0.7 s; mỗi thế cờ cần tối đa 2 lần tìm kiếm.
"""

import argparse
import json
import math
import random
import sys
import time
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from configs.constants import C_SQUARES, X_SQUARES  # noqa: E402
from eval.evaluation import _evaluate_bb, normalize_eval_config, normalize_weights  # noqa: E402
from othello.bitboard import CORNER_MASK, board_to_bb, flips_mask, legal_mask, popcount  # noqa: E402
from othello.encoding import BLACK  # noqa: E402
from othello.game import OthelloGame  # noqa: E402

BIG = 10_000          # giá trị thắng/thua ván trong tìm kiếm có giới hạn độ sâu (lớn hơn mọi điểm đánh giá)
INF = 10 ** 9
PHASES = ("khai cuộc", "giữa ván", "cuối ván (ước lượng)", "tàn cuộc (chính xác)")


def _bit(pos) -> int:
    return 1 << (pos[0] * 8 + pos[1])


_XC = sum(_bit(p) for p in (*X_SQUARES, *C_SQUARES))


def _bits(x):
    while x:
        b = x & -x
        yield b
        x ^= b


def _ordered(moves: int) -> list:
    """Góc trước, ô X/C sau, còn lại ở giữa (đủ để cắt tỉa tốt)."""
    corner, mid, xc = [], [], []
    for b in _bits(moves):
        (corner if b & CORNER_MASK else (xc if b & _XC else mid)).append(b)
    return corner + mid + xc


class Solver:
    """Alpha-Beta negamax trên bitboard. Giá trị luôn theo góc nhìn của người ĐANG ĐẾN LƯỢT."""

    def __init__(self, weights=None, eval_config=None):
        self.w = normalize_weights(weights)
        self.cfg = normalize_eval_config(eval_config)
        self.nodes = 0

    # --- tìm kiếm có giới hạn độ sâu, lá = hàm đánh giá tĩnh ---
    def depth_search(self, me, opp, depth, alpha, beta):
        self.nodes += 1
        moves = legal_mask(me, opp)
        if not moves:
            if not legal_mask(opp, me):                       # hết ván
                d = popcount(me) - popcount(opp)
                return BIG + d if d > 0 else (-BIG + d if d < 0 else 0)
            return -self.depth_search(opp, me, depth, -beta, -alpha)   # pass
        if depth <= 0:
            return _evaluate_bb(me, opp, self.cfg, self.w)
        best = -INF
        for b in _ordered(moves):
            f = flips_mask(me, opp, b)
            v = -self.depth_search(opp & ~f, me | b | f, depth - 1, -beta, -alpha)
            if v > best:
                best = v
                if v > alpha:
                    alpha = v
                    if alpha >= beta:
                        break
        return best

    # --- giải chính xác tới hết ván: giá trị = chênh lệch quân cuối ván ---
    def exact_search(self, me, opp, alpha, beta):
        self.nodes += 1
        moves = legal_mask(me, opp)
        if not moves:
            if not legal_mask(opp, me):
                return popcount(me) - popcount(opp)
            return -self.exact_search(opp, me, -beta, -alpha)
        best = -INF
        for b in _ordered(moves):
            f = flips_mask(me, opp, b)
            v = -self.exact_search(opp & ~f, me | b | f, -beta, -alpha)
            if v > best:
                best = v
                if v > alpha:
                    alpha = v
                    if alpha >= beta:
                        break
        return best

    def value_after(self, me, opp, bit, exact, depth):
        """Giá trị (góc nhìn người vừa đi) của nước `bit`, cửa sổ đầy đủ."""
        f = flips_mask(me, opp, bit)
        o2, m2 = opp & ~f, me | bit | f
        if exact:
            return -self.exact_search(o2, m2, -INF, INF)
        return -self.depth_search(o2, m2, depth - 1, -INF, INF)

    def best(self, me, opp, exact, depth):
        """(bit tốt nhất, giá trị) tại thế cờ; mọi nước được tìm với cửa sổ (alpha, INF)."""
        best_bit, best_val, alpha = None, -INF, -INF
        for b in _ordered(legal_mask(me, opp)):
            f = flips_mask(me, opp, b)
            o2, m2 = opp & ~f, me | b | f
            v = -(self.exact_search(o2, m2, -INF, -alpha) if exact else self.depth_search(o2, m2, depth - 1, -INF, -alpha))
            if v > best_val:
                best_bit, best_val, alpha = b, v, v
        return best_bit, best_val


# ------------------------------------------------------------------ đọc ván và dựng lại thế cờ
def replay_moves(rec, agent_color):
    """Sinh (black, white, màu_người_đi, bit_nước_đi, số_nước_đã_đi) trước mỗi nước đi của agent_color."""
    black, white = board_to_bb(OthelloGame().board)
    seq = []
    for i, m in enumerate(rec["opening"]):
        seq.append((BLACK if i % 2 == 0 else -BLACK, m, False))
    for mv in rec["move_log"]:
        seq.append((mv["p"], mv["a"], True))
    for idx, (p, a, from_log) in enumerate(seq):
        bit = _bit(a)
        me, opp = (black, white) if p == BLACK else (white, black)
        f = flips_mask(me, opp, bit)
        if not f:                                     # khai cuộc có pass: đổi bên rồi thử lại
            p = -p
            me, opp = (black, white) if p == BLACK else (white, black)
            f = flips_mask(me, opp, bit)
            if not f:
                raise ValueError(f"nước đi không hợp lệ khi replay: ván {rec.get('game_id')}, nước {idx}")
        if from_log and p == agent_color:
            yield black, white, p, bit, idx
        me, opp = me | bit | f, opp & ~f
        black, white = (me, opp) if p == BLACK else (opp, me)


def phase_of(empties: int, exact_empties: int) -> str:
    if empties <= exact_empties:
        return PHASES[3]
    if empties >= 44:
        return PHASES[0]
    if empties >= 24:
        return PHASES[1]
    return PHASES[2]


def collect_positions(path, agents, mode, exact_empties, rng, per_phase, max_games):
    """Mẫu phân tầng: {agent: {phase: [(game_id, opponent, black, white, p, bit, ply)]}} (reservoir sampling)."""
    pools = {a: {ph: [] for ph in PHASES} for a in agents}
    seen = {a: {ph: 0 for ph in PHASES} for a in agents}
    n_games = 0
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            rec = json.loads(line)
            if mode and rec.get("mode") != mode:
                continue
            for a in agents:
                if rec["black"] == a and rec["white"] == a:
                    continue
                if rec["black"] == a:
                    color, opp_name = BLACK, rec["white"]
                elif rec["white"] == a:
                    color, opp_name = -BLACK, rec["black"]
                else:
                    continue
                n_games += 1
                for black, white, p, bit, ply in replay_moves(rec, color):
                    empties = 64 - popcount(black | white)
                    ph = phase_of(empties, exact_empties)
                    seen[a][ph] += 1
                    item = (rec["game_id"], opp_name, black, white, p, bit, ply)
                    pool = pools[a][ph]
                    if len(pool) < per_phase:
                        pool.append(item)
                    else:
                        j = rng.randrange(seen[a][ph])
                        if j < per_phase:
                            pool[j] = item
            if max_games and n_games >= max_games:
                break
    return pools, seen


def grade(solver, item, exact_empties, depth, blunder_eval):
    game_id, opp_name, black, white, p, bit, ply = item
    me, opp = (black, white) if p == BLACK else (white, black)
    empties = 64 - popcount(black | white)
    exact = empties <= exact_empties
    best_bit, v_best = solver.best(me, opp, exact, depth)
    v_agent = v_best if bit == best_bit else solver.value_after(me, opp, bit, exact, depth)
    regret = v_best - v_agent
    if exact:                                         # sai nặng = làm xấu KẾT QUẢ (thắng/hòa/thua)
        cls = lambda v: (v > 0) - (v < 0)             # noqa: E731
        blunder = cls(v_agent) < cls(v_best)
    else:
        blunder = regret >= blunder_eval
    return dict(game_id=game_id, đối_thủ=opp_name, ply=ply, ô_trống=empties, giai_đoạn=phase_of(empties, exact_empties),
                chính_xác=exact, số_nước_hợp_lệ=popcount(legal_mask(me, opp)),
                nước_agent=int(math.log2(bit)), nước_tham_chiếu=int(math.log2(best_bit)),
                trùng_nước=bit == best_bit, tối_ưu=regret == 0, v_tham_chiếu=v_best, v_agent=v_agent,
                regret=regret, sai_nặng=bool(blunder))


def summarize(rows):
    out = []
    by = defaultdict(list)
    for r in rows:
        by[(r["agent"], r["giai_đoạn"])].append(r)
    for (agent, ph), rs in by.items():
        n = len(rs)
        out.append(dict(agent=agent, giai_đoạn=ph, n=n,
                        tối_ưu=sum(r["tối_ưu"] for r in rs) / n, trùng_nước=sum(r["trùng_nước"] for r in rs) / n,
                        sai_nặng=sum(r["sai_nặng"] for r in rs) / n, regret_tb=sum(r["regret"] for r in rs) / n,
                        regret_trung_vị=sorted(r["regret"] for r in rs)[n // 2]))
    order = {p: i for i, p in enumerate(PHASES)}
    out.sort(key=lambda r: (r["agent"], order[r["giai_đoạn"]]))
    return out


def wilson(k, n, z=1.96):
    if n == 0:
        return 0.0, 0.0
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (c - h) / d, (c + h) / d


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--games", default=str(ROOT / "results/logs/round_robin_v2/games.jsonl"))
    ap.add_argument("--agent", nargs="+", default=["mcts"], help="tên agent trong games.jsonl (vd. mcts alphabeta random)")
    ap.add_argument("--mode", default="time_per_move", help="chế độ giải đấu để lọc ('' = tất cả)")
    ap.add_argument("--per-phase", type=int, default=40, help="số thế cờ lấy mẫu MỖI giai đoạn, MỖI agent")
    ap.add_argument("--depth", type=int, default=8, help="độ sâu Alpha-Beta tham chiếu (ngoài tàn cuộc chính xác)")
    ap.add_argument("--exact-empties", type=int, default=12, help="còn <= số ô trống này thì giải chính xác tới hết ván")
    ap.add_argument("--blunder-eval", type=float, default=100.0, help="regret (điểm đánh giá) từ mức này là 'sai nặng' ngoài tàn cuộc")
    ap.add_argument("--weights", default='{"mobility": 80, "disc_diff": 5}', help="JSON trọng số hàm đánh giá tham chiếu")
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--max-games", type=int, default=0, help="giới hạn số ván đọc cho mỗi lần (0 = hết)")
    ap.add_argument("--out", default=str(ROOT / "results/analysis/move_quality"))
    a = ap.parse_args()

    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    rng = random.Random(a.seed)
    t0 = time.time()
    print(f"Đọc {a.games} ...", flush=True)
    pools, seen = collect_positions(a.games, a.agent, a.mode or None, a.exact_empties, rng, a.per_phase, a.max_games)
    for ag in a.agent:
        print(f"  {ag}: số thế cờ có sẵn theo giai đoạn: " + ", ".join(f"{ph}={seen[ag][ph]}" for ph in PHASES))

    solver = Solver(json.loads(a.weights))
    rows = []
    total = sum(len(v) for pl in pools.values() for v in pl.values())
    done = 0
    for ag in a.agent:
        for ph in PHASES:
            for item in pools[ag][ph]:
                r = grade(solver, item, a.exact_empties, a.depth, a.blunder_eval)
                r["agent"] = ag
                rows.append(r)
                done += 1
                if done % 20 == 0 or done == total:
                    print(f"  chấm {done}/{total} thế cờ ({time.time() - t0:.0f}s, {solver.nodes:,} nút)", flush=True)

    # ---- ghi kết quả ----
    cols = list(rows[0]) if rows else []
    with open(out / "moves.csv", "w", encoding="utf-8") as fh:
        fh.write(",".join(cols) + "\n")
        for r in rows:
            fh.write(",".join(str(r[c]) for c in cols) + "\n")
    summ = summarize(rows)
    with open(out / "summary.csv", "w", encoding="utf-8") as fh:
        keys = list(summ[0]) if summ else []
        fh.write(",".join(keys) + "\n")
        for s in summ:
            fh.write(",".join(f"{s[k]:.4f}" if isinstance(s[k], float) else str(s[k]) for k in keys) + "\n")

    lines = ["# Chất lượng từng nước đi so với Alpha-Beta tham chiếu\n",
             f"- Tham chiếu: Alpha-Beta độ sâu {a.depth} (trọng số `{a.weights}`), giải chính xác khi còn <= {a.exact_empties} ô trống.",
             f"- Mẫu: {a.per_phase} thế cờ/giai đoạn/agent, ván lọc theo mode `{a.mode or 'tất cả'}`, seed {a.seed}. "
             f"Sai nặng ngoài tàn cuộc: regret >= {a.blunder_eval:g} điểm đánh giá.",
             "- **Chỉ tàn cuộc chính xác là chuẩn thật sự.** Ở các giai đoạn còn lại \"nước tốt nhất\" chỉ là ước lượng theo hàm đánh giá của "
             "chính Alpha-Beta; agent dùng hàm đánh giá khác sẽ bị chấm thấp dù nước đi không tệ, và Alpha-Beta tự chấm mình có xu hướng thiên vị.\n",
             "- Regret: tàn cuộc chính xác tính bằng SỐ QUÂN, các giai đoạn còn lại bằng ĐIỂM ĐÁNH GIÁ (không so sánh trực tiếp hai đơn vị).\n",
             "| agent | giai đoạn | n | tối ưu (CI95) | trùng nước tham chiếu | sai nặng (CI95) | regret TB |", "|---|---|---|---|---|---|---|"]
    for s in summ:
        n = s["n"]
        lo, hi = wilson(round(s["tối_ưu"] * n), n)
        blo, bhi = wilson(round(s["sai_nặng"] * n), n)
        lines.append(f"| {s['agent']} | {s['giai_đoạn']} | {n} | {s['tối_ưu']:.2f} [{lo:.2f}, {hi:.2f}] | {s['trùng_nước']:.2f} | "
                     f"{s['sai_nặng']:.2f} [{blo:.2f}, {bhi:.2f}] | {s['regret_tb']:.1f} |")
    (out / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    print(f"\nĐã ghi {out / 'moves.csv'}, summary.csv, summary.md ({time.time() - t0:.0f}s)")


if __name__ == "__main__":
    main()