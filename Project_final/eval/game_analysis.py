"""Phân tích ván đấu từ LOG THÔ (results/logs/<run>/games.jsonl): KHÔNG chạy lại agent, chỉ đọc log và phát lại ván.

Chạy:
    python -m eval.game_analysis --run results/logs/<run_name> --out results/analysis/<run_name>
    python -m eval.game_analysis --run results/logs/tune_xxx --focus alphabeta,mcts

Đầu ra (--out):
    matchup_summary.csv     mỗi (chế độ, cặp): W/D/L, score + Wilson CI, tỷ lệ Đen thắng, kết quả theo CẶP ván (cùng khai cuộc)
    move_stats.csv          mỗi (chế độ, agent, giai đoạn): ms/nước, p95, nodes, simulations, độ sâu, lấy góc, tặng góc, đi ô X/C
    corner_vs_result.csv    ai lấy góc đầu tiên có thắng không; chênh mobility ở nước 20 có tiên đoán kết quả không
    mcts_calibration.csv    giá trị thắng MCTS ước lượng so với kết quả thật (nếu log có stats.value)
    selected_games.md       các ván được chọn THEO QUY TẮC CỐ ĐỊNH (xem QUY_TAC_CHON_VAN), kèm bàn cờ tại nước 20/40/cuối
    fig_*.png               hình sinh từ chính các bảng trên

Nguyên tắc (đề bài mục "không chọn riêng các ván thắng"): mọi số liệu tính trên TOÀN BỘ ván trong log; ván minh họa chọn
bằng quy tắc viết sẵn ở dưới (ván thua nặng nhất, sát nút nhất, dài nhất, ngẫu nhiên có seed), không chọn theo ý muốn.
"""

import argparse
import json
import math
import random
from pathlib import Path

import numpy as np
import pandas as pd

from configs.constants import C_SQUARES, CORNERS, X_SQUARES
from eval.metrics import wilson_interval
from othello.encoding import BLACK, WHITE, opponent
from othello.game import OthelloGame
from othello.rules import legal_moves

QUY_TAC_CHON_VAN = (
    "Với mỗi (chế độ, cặp agent) được chọn (--focus): (1) `worst_loss:<agent>` = ván agent đó thua chênh lệch quân lớn nhất; "
    "(2) `closest` = ván có |chênh lệch quân| nhỏ nhất; (3) `longest` = ván có nhiều nước nhất; (4) `random1`, `random2` = "
    "2 ván bốc ngẫu nhiên bằng random.Random(SEED_CHON_VAN) trên danh sách game_id đã sắp xếp. Hòa điểm thì lấy game_id nhỏ hơn "
    "theo thứ tự chữ cái. Quy tắc cố định TRƯỚC khi xem ván, áp dụng như nhau cho mọi cặp."
)
SEED_CHON_VAN = 2026
PHASES = (("opening (nước 1-20)", 1, 20), ("midgame (21-44)", 21, 44), ("endgame (45-60)", 45, 60))


# ------------------------------------------------------------------ đọc log
def load_games(run_dir) -> list:
    path = Path(run_dir) / "games.jsonl"
    if not path.exists():
        raise FileNotFoundError(f"Không thấy {path}. Đây phải là thư mục log của một lần chạy giải đấu.")
    with open(path, encoding="utf-8") as f:
        recs = [json.loads(line) for line in f if line.strip()]
    if not recs:
        raise ValueError(f"{path} rỗng")
    return recs


def _result_for(rec, name) -> int:
    """Kết quả +1/0/-1 theo góc nhìn agent `name` (tên mục trong agents.yaml)."""
    r = rec["result_black"]
    return r if rec["black"] == name else -r


def _phase_of(ply: int) -> str:
    for label, lo, hi in PHASES:
        if lo <= ply <= hi:
            return label
    return PHASES[-1][0]


# ------------------------------------------------------------------ phát lại ván
def replay(rec) -> list:
    """Phát lại ván, trả về 1 dict/nước của AGENT (không tính khai cuộc) với các đặc trưng thế cờ."""
    game = OthelloGame()
    for a in rec["opening"]:
        game.step(tuple(a))
    rows = []
    for entry in rec["move_log"]:
        p, action = entry["p"], tuple(entry["a"])
        opp = opponent(p)
        board = game.board
        legal_before = game.legal_actions()
        opp_before = set(legal_moves(board, opp))
        ply = len(game.move_history) + 1
        game.step(action)
        after = game.board
        opp_after = set(legal_moves(after, opp))
        mine_after = len(legal_moves(after, p))
        b, w = game.score()
        danger = 0
        if action in X_SQUARES and board[X_SQUARES[action]] == 0:
            danger = 2
        elif action in C_SQUARES and board[C_SQUARES[action]] == 0:
            danger = 1
        st = entry.get("stats") or {}
        rows.append({
            "ply": ply, "phase": _phase_of(ply), "p": p, "action": action, "ms": entry["ms"],
            "over_budget": bool(entry.get("over_budget", False)),
            "n_legal": len(legal_before),
            "corner_available": any(m in CORNERS for m in legal_before),
            "took_corner": action in CORNERS,
            # tặng góc: nước đi MỞ cho đối thủ một góc mà trước đó họ chưa lấy được
            "gave_corner": bool((opp_after & CORNERS) - (opp_before & CORNERS)),
            "danger": danger,
            "mob_diff": mine_after - len(opp_after),
            "disc_diff_black": b - w,
            "nodes": st.get("nodes"), "simulations": st.get("simulations"),
            "depth": st.get("depth"), "value": st.get("value"),
        })
    return rows


def _game_features(rec, moves) -> dict:
    first_corner = next((m["p"] for m in moves if m["took_corner"]), 0)
    mob20 = next((m for m in moves if m["ply"] >= 20), None)
    # mob_diff của nước ở ply>=20 đo từ góc nhìn người vừa đi; quy về Đen
    mob_black = None
    if mob20 is not None:
        mob_black = mob20["mob_diff"] * (1 if mob20["p"] == BLACK else -1)
    return {"first_corner_owner": first_corner, "mob_diff_black_at20": mob_black}


# ------------------------------------------------------------------ bảng tổng hợp
def build_tables(recs) -> dict:
    game_rows, move_rows = [], []
    for rec in recs:
        moves = replay(rec)
        g = {k: rec.get(k) for k in ("game_id", "mode", "a", "b", "a_is_black", "black", "white", "seed", "pair")}
        g.update(result_black=rec["result_black"], n_moves=rec["n_moves"],
                 disc_diff_black=rec["black_discs"] - rec["white_discs"], **_game_features(rec, moves))
        game_rows.append(g)
        for m in moves:
            agent = rec["black"] if m["p"] == BLACK else rec["white"]
            other = rec["white"] if m["p"] == BLACK else rec["black"]
            move_rows.append({"game_id": rec["game_id"], "mode": rec["mode"], "agent": agent, "opponent": other, **m})
    return {"games": pd.DataFrame(game_rows), "moves": pd.DataFrame(move_rows)}


def matchup_summary(games: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (mode, a, b), d in games.groupby(["mode", "a", "b"], sort=True):
        res_a = np.where(d["a_is_black"], d["result_black"], -d["result_black"])
        w, dr, l = int((res_a == 1).sum()), int((res_a == 0).sum()), int((res_a == -1).sum())
        n = len(d)
        lo, hi = wilson_interval(w + 0.5 * dr, n)
        diff_a = np.where(d["a_is_black"], d["disc_diff_black"], -d["disc_diff_black"])
        # theo CẶP ván (cùng khai cuộc, đổi màu): +2 = a thắng cả hai, -2 = b thắng cả hai, còn lại chia
        d2 = d.assign(res_a=res_a)
        pair_sum = d2.groupby(["seed", "pair"])["res_a"].sum()
        rows.append({
            "mode": mode, "a": a, "b": b, "games": n, "a_wins": w, "draws": dr, "a_losses": l,
            "a_score": round((w + 0.5 * dr) / n, 3), "ci95_lo": round(lo, 3), "ci95_hi": round(hi, 3),
            "black_win_rate": round(float((d["result_black"] == 1).mean()), 3),
            "pairs": len(pair_sum), "pairs_a_sweep": int((pair_sum == 2).sum()),
            "pairs_b_sweep": int((pair_sum == -2).sum()), "pairs_split": int((pair_sum.abs() < 2).sum()),
            "a_mean_disc_diff": round(float(diff_a.mean()), 2), "mean_moves": round(float(d["n_moves"].mean()), 1),
        })
    return pd.DataFrame(rows)


def move_stats(moves: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (mode, agent, phase), d in moves.groupby(["mode", "agent", "phase"], sort=True):
        avail = d[d["corner_available"]]
        rows.append({
            "mode": mode, "agent": agent, "phase": phase, "moves": len(d),
            "ms_mean": round(float(d["ms"].mean()), 1), "ms_p95": round(float(d["ms"].quantile(0.95)), 1),
            "over_budget_rate": round(float(d["over_budget"].mean()), 4),
            "nodes_mean": round(float(d["nodes"].mean()), 1) if d["nodes"].notna().any() else None,
            "sims_mean": round(float(d["simulations"].mean()), 1) if d["simulations"].notna().any() else None,
            "depth_mean": round(float(d["depth"].mean()), 2) if d["depth"].notna().any() else None,
            "corner_taken_when_available": round(float(avail["took_corner"].mean()), 3) if len(avail) else None,
            "corner_chances": len(avail),
            "gave_corner_rate": round(float(d["gave_corner"].mean()), 4),
            "xc_move_rate": round(float((d["danger"] > 0).mean()), 4),
        })
    return pd.DataFrame(rows)


def corner_vs_result(games: pd.DataFrame) -> pd.DataFrame:
    rows = []
    dec = games[(games["first_corner_owner"] != 0) & (games["result_black"] != 0)]
    for mode, d in dec.groupby("mode"):
        won = (d["first_corner_owner"] == d["result_black"])
        rows.append({"question": "người lấy góc đầu tiên thắng ván", "mode": mode, "n": len(d),
                     "rate": round(float(won.mean()), 3), "note": "chỉ tính ván có góc được lấy và không hòa"})
    mob = games[games["mob_diff_black_at20"].notna() & (games["result_black"] != 0)]
    for mode, d in mob.groupby("mode"):
        lead = np.sign(d["mob_diff_black_at20"])
        d = d[lead != 0]
        lead = np.sign(d["mob_diff_black_at20"])
        if len(d):
            rows.append({"question": "bên hơn mobility ở nước 20 thắng ván", "mode": mode, "n": len(d),
                         "rate": round(float((lead == d["result_black"]).mean()), 3),
                         "note": "mobility sau nước thứ 20, bỏ ván bằng nhau"})
    return pd.DataFrame(rows)


def mcts_calibration(moves: pd.DataFrame, games: pd.DataFrame) -> pd.DataFrame:
    m = moves[moves["value"].notna() & moves["simulations"].gt(0)].merge(
        games[["game_id", "result_black"]], on="game_id")
    if m.empty:
        return pd.DataFrame()
    outcome = (m["result_black"] * m["p"] + 1) / 2          # theo góc nhìn người đi: 1 / 0.5 / 0
    m = m.assign(outcome=outcome, bin=pd.cut(m["value"], [0, .2, .4, .6, .8, 1.0], include_lowest=True))
    out = m.groupby(["agent", "bin"], observed=True).agg(moves=("value", "size"), est=("value", "mean"),
                                                         actual=("outcome", "mean")).reset_index()
    out["bin"] = out["bin"].astype(str)
    brier = m.groupby("agent").apply(lambda d: float(((d["value"] - d["outcome"]) ** 2).mean()), include_groups=False)
    out["brier_agent"] = out["agent"].map(brier)
    return out.round(3)


# ------------------------------------------------------------------ chọn ván theo quy tắc
def select_games(games: pd.DataFrame, focus) -> pd.DataFrame:
    rng = random.Random(SEED_CHON_VAN)
    rows = []
    for (mode, a, b), d in games.groupby(["mode", "a", "b"], sort=True):
        if focus and not ({a, b} <= set(focus)):
            continue
        d = d.sort_values("game_id")
        margin = d["disc_diff_black"].abs()

        def add(rule, row):
            rows.append({"mode": mode, "a": a, "b": b, "rule": rule, "game_id": row["game_id"],
                         "black": row["black"], "result_black": row["result_black"],
                         "disc_diff_black": row["disc_diff_black"], "n_moves": row["n_moves"]})

        for agent in (a, b):
            loss = d.assign(m=np.where(d["black"] == agent, -d["disc_diff_black"], d["disc_diff_black"]))
            worst = loss.sort_values(["m", "game_id"], ascending=[False, True]).iloc[0]
            # nếu agent chưa từng thua trong nhóm này thì đây chỉ là ván thắng sát nhất của nó -> ghi rõ ở tên quy tắc
            add(f"worst_loss:{agent}" if worst["m"] > 0 else f"worst_loss:{agent} (không có ván thua; ván thắng sát nhất)", worst)
        add("closest", d.assign(m=margin).sort_values(["m", "game_id"]).iloc[0])
        add("longest", d.sort_values(["n_moves", "game_id"], ascending=[False, True]).iloc[0])
        ids = list(d["game_id"])
        for k in (1, 2):
            gid = rng.choice(ids)
            add(f"random{k}", d[d["game_id"] == gid].iloc[0])
    return pd.DataFrame(rows)


def _board_after(rec, upto_ply=None) -> OthelloGame:
    """Bàn cờ sau `upto_ply` nước (tính cả khai cuộc); None = chơi hết ván."""
    game = OthelloGame()
    for a in rec["opening"]:
        game.step(tuple(a))
    for entry in rec["move_log"]:
        if upto_ply is not None and len(game.move_history) >= upto_ply:
            break
        game.step(tuple(entry["a"]))
    return game


def write_selected_md(path, selected: pd.DataFrame, recs_by_id: dict):
    lines = ["# Ván được chọn theo quy tắc cố định\n", QUY_TAC_CHON_VAN + "\n"]
    for _, s in selected.iterrows():
        rec = recs_by_id[s["game_id"]]
        outcome = {1: "Đen thắng", -1: "Trắng thắng", 0: "Hòa"}[int(s["result_black"])]
        lines.append(f"\n## [{s['rule']}] {s['game_id']}\n")
        lines.append(f"Đen = {s['black']}, {outcome}, chênh lệch quân (Đen - Trắng) = {int(s['disc_diff_black'])}, "
                     f"{int(s['n_moves'])} nước.\n")
        for ply in (20, 40, None):
            g = _board_after(rec, ply)
            title = "kết thúc" if ply is None else f"sau nước {ply}"
            lines.append(f"\n{title} (Đen X / Trắng O):\n```\n{g.render()}\n```\n")
    Path(path).write_text("\n".join(lines), encoding="utf-8")


# ------------------------------------------------------------------ hình
def make_figures(out: Path, summary, mstats, games, moves, calib):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    # 1) score của a trước b, theo chế độ, kèm CI
    if not summary.empty:
        lab = summary["a"] + " vs " + summary["b"] + " [" + summary["mode"] + "]"
        fig, ax = plt.subplots(figsize=(8, max(3, 0.45 * len(summary) + 1)))
        y = np.arange(len(summary))
        err = [summary["a_score"] - summary["ci95_lo"], summary["ci95_hi"] - summary["a_score"]]
        ax.errorbar(summary["a_score"], y, xerr=err, fmt="o", capsize=3)
        ax.axvline(0.5, color="gray", ls="--")
        ax.set_yticks(y, lab)
        ax.set_xlim(0, 1)
        ax.set_xlabel("score của agent đứng trước (thắng + 0.5 hòa)/số ván, CI 95% Wilson")
        ax.invert_yaxis()
        fig.tight_layout()
        fig.savefig(out / "fig_matchup_scores.png", dpi=150)
        plt.close(fig)

    # 2) tài nguyên theo giai đoạn: nodes/sims và ms
    if not mstats.empty:
        fig, axes = plt.subplots(1, 2, figsize=(11, 4))
        order = [p[0] for p in PHASES]
        for (mode, agent), d in mstats.groupby(["mode", "agent"]):
            d = d.set_index("phase").reindex(order)
            axes[0].plot(order, d["ms_mean"], marker="o", label=f"{agent} [{mode}]")
            work = d["sims_mean"].where(d["sims_mean"].fillna(0) > 0, d["nodes_mean"])
            axes[1].plot(order, work, marker="o", label=f"{agent} [{mode}]")
        axes[0].set_ylabel("ms / nước")
        axes[1].set_ylabel("nút (Alpha-Beta/Heuristic) hoặc mô phỏng (MCTS) / nước")
        axes[1].set_yscale("log")
        axes[0].legend(fontsize=6)
        for ax in axes:
            ax.tick_params(axis="x", labelrotation=15)
        fig.tight_layout()
        fig.savefig(out / "fig_cost_by_phase.png", dpi=150)
        plt.close(fig)

        # 3) lấy góc / tặng góc
        agg = moves.groupby(["mode", "agent"]).agg(
            gave=("gave_corner", "mean"), xc=("danger", lambda s: float((s > 0).mean()))).reset_index()
        avail = moves[moves["corner_available"]].groupby(["mode", "agent"])["took_corner"].mean().rename("took")
        agg = agg.merge(avail.reset_index(), on=["mode", "agent"], how="left")
        fig, ax = plt.subplots(figsize=(9, 4))
        x = np.arange(len(agg))
        ax.bar(x - 0.27, agg["took"].fillna(0), 0.27, label="lấy góc khi có thể")
        ax.bar(x, agg["gave"], 0.27, label="tặng góc cho đối thủ / nước")
        ax.bar(x + 0.27, agg["xc"], 0.27, label="đi ô X/C khi góc còn trống / nước")
        ax.set_xticks(x, agg["agent"] + "\n" + agg["mode"], fontsize=7)
        ax.legend(fontsize=7)
        fig.tight_layout()
        fig.savefig(out / "fig_corner_behaviour.png", dpi=150)
        plt.close(fig)

    # 4) quỹ đạo chênh lệch quân của agent đứng trước (a), tách thắng / hòa / thua (KHÔNG chỉ ván thắng)
    traj = moves.merge(games[["game_id", "a", "b", "a_is_black", "result_black"]], on="game_id")
    traj["diff_a"] = np.where(traj["a_is_black"], traj["disc_diff_black"], -traj["disc_diff_black"])
    traj["res_a"] = np.where(traj["a_is_black"], traj["result_black"], -traj["result_black"])
    for (mode, a, b), d in traj.groupby(["mode", "a", "b"]):
        if d["game_id"].nunique() < 4:
            continue
        fig, ax = plt.subplots(figsize=(6, 3.5))
        for res, name in ((1, f"{a} thắng"), (0, "hòa"), (-1, f"{a} thua")):
            s = d[d["res_a"] == res].groupby("ply")["diff_a"]
            if s.ngroups == 0:
                continue
            mean, n = s.mean(), s.size()
            ax.plot(mean.index, mean.values, label=f"{name} (n={d[d['res_a'] == res]['game_id'].nunique()})")
        ax.axhline(0, color="gray", lw=0.5)
        ax.set_xlabel("nước đi")
        ax.set_ylabel(f"quân {a} - quân {b} (trung bình)")
        ax.set_title(f"{a} vs {b} [{mode}]", fontsize=9)
        ax.legend(fontsize=7)
        fig.tight_layout()
        fig.savefig(out / f"fig_trajectory_{mode}_{a}_vs_{b}.png", dpi=130)
        plt.close(fig)

    # 5) hiệu chỉnh ước lượng thắng của MCTS
    if calib is not None and not calib.empty:
        fig, ax = plt.subplots(figsize=(4.5, 4.5))
        for agent, d in calib.groupby("agent"):
            ax.plot(d["est"], d["actual"], marker="o", label=f"{agent} (Brier {d['brier_agent'].iloc[0]:.3f})")
        ax.plot([0, 1], [0, 1], "k--", lw=0.8)
        ax.set_xlabel("tỷ lệ thắng MCTS ước lượng")
        ax.set_ylabel("tỷ lệ thắng thực tế")
        ax.legend(fontsize=7)
        fig.tight_layout()
        fig.savefig(out / "fig_mcts_calibration.png", dpi=150)
        plt.close(fig)


# ------------------------------------------------------------------ điều phối
def analyze(run_dir, out_dir, focus=None) -> dict:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    recs = load_games(run_dir)
    t = build_tables(recs)
    games, moves = t["games"], t["moves"]
    summary, mstats = matchup_summary(games), move_stats(moves)
    cvr, calib = corner_vs_result(games), mcts_calibration(moves, games)
    selected = select_games(games, focus)

    summary.to_csv(out / "matchup_summary.csv", index=False)
    mstats.to_csv(out / "move_stats.csv", index=False)
    cvr.to_csv(out / "corner_vs_result.csv", index=False)
    if not calib.empty:
        calib.to_csv(out / "mcts_calibration.csv", index=False)
    selected.to_csv(out / "selected_games.csv", index=False)
    write_selected_md(out / "selected_games.md", selected, {r["game_id"]: r for r in recs})
    make_figures(out, summary, mstats, games, moves, calib)
    return {"summary": summary, "move_stats": mstats, "corner_vs_result": cvr, "calibration": calib,
            "selected": selected, "games": games, "moves": moves, "n_games": len(recs)}


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--run", required=True, help="thư mục log của 1 lần chạy (chứa games.jsonl)")
    p.add_argument("--out", help="thư mục ghi kết quả (mặc định results/analysis/<tên run>)")
    p.add_argument("--focus", help="các agent cần chọn ván minh họa, ví dụ alphabeta,mcts (mặc định: mọi cặp)")
    a = p.parse_args()
    out = a.out or str(Path("results/analysis") / Path(a.run).name)
    r = analyze(a.run, out, a.focus.split(",") if a.focus else None)
    pd.set_option("display.width", 200, "display.max_columns", 30)
    print(f"{r['n_games']} ván -> {out}\n")
    print(r["summary"].to_string(index=False))
    print()
    print(r["corner_vs_result"].to_string(index=False))


if __name__ == "__main__":
    main()
