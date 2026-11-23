#!/usr/bin/env python3
"""Chạy toàn bộ thí nghiệm TUNE cho Heuristic / Alpha-Beta / MCTS bằng 1 lệnh (gọi notebooks/tune.py).

Dùng Python thay vì .sh để khỏi lỗi dấu nháy JSON trên Windows. Chạy từ thư mục gốc dự án:

    python scripts/run_tuning.py --list                       # xem các thí nghiệm
    python scripts/run_tuning.py --dry-run                    # in lệnh sẽ chạy, không chạy
    python scripts/run_tuning.py --only ab_mobility_ext ab_disc_diff --workers 4
    python scripts/run_tuning.py --only mcts_rollout mcts_c mcts_sims --workers 4
    python scripts/run_tuning.py --quick --only mcts_rollout --out-root /tmp/tune_smoke   # chạy thử nhanh

Quy ước (đúng đề: không chọn tham số bằng ván đánh giá cuối):
- Tune dùng seed 100 (seed 0-2 là giải đấu cuối). Xác nhận cuối dùng seed 200.
- Mỗi cấu hình đấu THEO CẶP: cùng khai cuộc ngẫu nhiên, đổi màu. Cùng seed => các cấu hình trong 1 thí nghiệm
  dùng cùng bộ khai cuộc, nên so sánh công bằng.
- Mỗi thí nghiệm ghi vào <out-root>/<tên>/ (games.jsonl + summary.csv). Thư mục đã có summary.csv thì BỎ QUA
  (tránh ghi trùng dòng như ab_mobility cũ); muốn chạy lại dùng --force (thư mục cũ được đổi tên .bak_<giờ>).

Chọn tham số theo kiểu "tọa độ một vòng": quét từng tham số, các tham số khác giữ giá trị hiện tại trong agents.yaml.

Thời gian ước tính (rất thô, 1 tiến trình; chia cho --workers):
- Alpha-Beta (ab_*), heur_endgame: vài giây đến vài phút mỗi cấu hình.
- MCTS 1000 mô phỏng ~0.5 s/nước => ~15 s/ván => 80 ván ~ 20 phút MỖI cấu hình. mcts_c (5 cấu hình) ~ 1.6 giờ,
  mcts_sims (250-2000) ~ 2 giờ, mcts_rollout (2 cấu hình) ~ 40 phút. Dùng --workers = số lõi vật lý - 1.
- MCTS lai (leaf_eval): mcts_leaf_scale 5 cấu hình x ~20 phút, mcts_leaf_c 4 cấu hình; "ladder_*" (6 trận + 1 đối đầu
  trực tiếp, 30 cặp, seed 200) khoảng 2-3 giờ tổng (1 tiến trình). Chạy mcts_leaf_scale TRƯỚC, cập nhật eval_scale của
  mục `mcts_leaf` trong agents.yaml theo kết quả, rồi mới chạy mcts_leaf_c và ladder_* (chúng đọc tham số từ agents.yaml).
- Thang độ sâu (scale_sims1000, scale_base05, scale_leaf05): mỗi cái 5 độ sâu x 50 ván, ~1-1.5 giờ (1 tiến trình).
Sau khi chạy: mở notebooks/08_tuning_analysis.ipynb để ra bảng, hình, lý do chọn.
"""

import argparse
import copy
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
TUNE = ROOT / "notebooks" / "tune.py"


def _yaml_params(entry, fallback):
    """Tham số của mục `entry` trong configs/agents.yaml (để cập nhật YAML sau khi tune là chạy tiếp được ngay)."""
    try:
        specs = yaml.safe_load((ROOT / "configs" / "agents.yaml").read_text(encoding="utf-8"))["agents"]
        return dict(specs[entry]["params"])
    except Exception:
        return dict(fallback)

# ----- cấu hình nền (khớp configs/agents.yaml hiện tại) -----
MCTS_BASE = {"type": "mcts", "simulations": 1000, "exploration_c": 1.414, "rollout_policy": "heuristic"}
AB2 = {"type": "alphabeta", "depth": 2}      # đối thủ vừa sức: MCTS ~0.5 điểm (đối thủ depth 4 làm điểm MCTS chạm sàn)
AB3 = {"type": "alphabeta", "depth": 3}
AB3_M80 = {"type": "alphabeta", "depth": 3, "weights": {"mobility": 80}}
AB3_M80_D5 = {"type": "alphabeta", "depth": 3, "weights": {"mobility": 80, "disc_diff": 5}}

# MCTS lai: đánh giá nút lá bằng hàm đánh giá Alpha-Beta; chạy THEO GIỜ (0.5 s/nước) như giải đấu
LEAF_BASE = {"type": "mcts", "budget": 0.5, **_yaml_params("mcts_leaf", {
    "leaf_eval": True, "eval_scale": 100.0, "eval_weights": {"mobility": 80.0, "disc_diff": 5.0}, "exploration_c": 1.414})}
BASE_MCTS_T = {"type": "mcts", "rollout_policy": "heuristic", "exploration_c": 1.414, "budget": 0.5}   # MCTS gốc, cùng giờ
AB_T = {"type": "alphabeta", "weights": {"mobility": 80, "disc_diff": 5}, "budget": 0.5}                  # đối thủ của giải đấu
AB4 = {"type": "alphabeta", "depth": 4}

EXPERIMENTS = {
    # ---- MCTS ----
    "mcts_rollout": dict(kind="sweep", base=MCTS_BASE, param="rollout_policy", values=["random", "heuristic"],
                         opp=AB2, pairs=40, plies=6, seed=100,
                         note="rollout random vs heuristic (đối thủ Alpha-Beta depth 2)"),
    "mcts_c": dict(kind="sweep", base=MCTS_BASE, param="exploration_c", values=[0.5, 0.8, 1.0, 1.414, 2.0],
                   opp=AB2, pairs=40, plies=6, seed=100, note="hằng số khám phá UCT"),
    "mcts_sims": dict(kind="sweep", base=MCTS_BASE, param="simulations", values=[250, 500, 1000, 2000],
                      opp=AB2, pairs=40, plies=6, seed=100,
                      note="số mô phỏng (chỉ có tác dụng ở default_config; có time_budget thì bị bỏ qua)"),
    # ---- MCTS lai (leaf_eval): quét K, rồi c, rồi đo "thang cải tiến" trên tập kiểm chứng ----
    "mcts_leaf_scale": dict(kind="sweep", base=LEAF_BASE, param="eval_scale", values=[25, 50, 100, 200, 400],
                            opp=AB2, pairs=40, plies=6, seed=100,
                            note="MCTS leaf_eval: K trong sigmoid(điểm/K), 0.5 s/nước (đối thủ Alpha-Beta depth 2)"),
    "mcts_leaf_scale_low": dict(kind="sweep", base=LEAF_BASE, param="eval_scale", values=[5, 10, 15],
                                opp=AB2, pairs=40, plies=6, seed=100,
                                note="mở rộng dải K xuống thấp (log mcts_leaf_scale: score tăng khi K giảm, tốt nhất ở biên 25)"),
    "mcts_leaf_c": dict(kind="sweep", base=LEAF_BASE, param="exploration_c", values=[0.5, 1.0, 1.414, 2.0],
                        opp=AB2, pairs=40, plies=6, seed=100,
                        note="MCTS leaf_eval: hằng số c (chạy sau khi đã chốt eval_scale trong agents.yaml)"),
    # ---- Alpha-Beta (cùng seed/pairs/plies với ab_mobility cũ để dùng lại được) ----
    "ab_mobility_ext": dict(kind="sweep", base=AB3, param="weights.mobility", values=[100, 150, 200],
                            opp=AB3, pairs=30, plies=6, seed=100,
                            note="mở rộng dải mobility (log cũ dừng ở 80 = biên); gộp với ab_mobility khi phân tích"),
    "ab_disc_diff": dict(kind="sweep", base=AB3_M80, param="weights.disc_diff", values=[1, 2.5, 5, 10, 20],
                         opp=AB3_M80, pairs=30, plies=6, seed=100, note="hệ số chênh quân (mặc định 10)"),
    "ab_corners": dict(kind="sweep", base=AB3_M80_D5, param="weights.corners", values=[50, 100, 200, 300],
                       opp=AB3_M80_D5, pairs=30, plies=6, seed=100, note="hệ số góc (mặc định 100)"),
    "ab_xc": dict(kind="sweep", base=AB3_M80_D5, param="weights.x_c_squares", values=[0, 0.5, 1, 2, 3],
                  opp=AB3_M80_D5, pairs=30, plies=6, seed=100, note="hệ số phạt ô X/C (mặc định 1.0)"),
    "ab_confirm": dict(kind="match",
                       a={"type": "alphabeta", "depth": 4, "weights": {"mobility": 80, "disc_diff": 5}},
                       b={"type": "alphabeta", "depth": 4}, tag="yaml_vs_default_d4",
                       pairs=40, plies=6, seed=200,
                       note="xác nhận bộ trọng số trong agents.yaml ở depth 4, seed 200 (tập kiểm chứng)"),
    # ---- Heuristic ----
    "heur_endgame": dict(kind="sweep", base={"type": "heuristic"}, param="endgame_empties",
                         values=[0, 6, 8, 10, 12, 14], opp={"type": "heuristic", "endgame_empties": 10},
                         pairs=100, plies=6, seed=100,
                         note="số ô trống để chuyển sang luật tàn cuộc (mặc định 10; 10 vs 10 là mốc kiểm tra ~0.5)"),
}


# "Thang cải tiến" (ablation trong báo cáo): MCTS gốc và MCTS leaf_eval đấu cùng đối thủ, seed 200 (tập kiểm chứng)
for _tag, _opp, _label in (("d2", AB2, "Alpha-Beta depth 2"), ("d4", AB4, "Alpha-Beta depth 4"),
                           ("ab05", AB_T, "Alpha-Beta 0.5 s/nước (đối thủ giải đấu)")):
    for _who, _spec in (("base", BASE_MCTS_T), ("leaf", LEAF_BASE)):
        EXPERIMENTS[f"ladder_{_who}_{_tag}"] = dict(
            kind="match", a=_spec, b=_opp, tag=f"{_who}_vs_{_tag}", pairs=30, plies=6, seed=200,
            note=f"thang cải tiến: MCTS {'gốc' if _who == 'base' else 'leaf_eval'} vs {_label}")
# "Thang độ sâu": Alpha-Beta độ sâu 1..5 (không giới hạn giờ, trọng số đã tune) đấu MCTS; notebook đổi thành
# "MCTS tương đương Alpha-Beta độ sâu ~X". A = Alpha-Beta, nên score của MCTS = 1 - score trong log.
MCTS_SIMS1000 = {"type": "mcts", "rollout_policy": "heuristic", "simulations": 1000, "exploration_c": 1.414}
for _name, _mcts, _label in (("sims1000", MCTS_SIMS1000, "MCTS 1000 mô phỏng (default_config)"),
                             ("base05", BASE_MCTS_T, "MCTS gốc 0.5 s/nước"),
                             ("leaf05", LEAF_BASE, "MCTS leaf_eval 0.5 s/nước")):
    EXPERIMENTS[f"scale_{_name}"] = dict(
        kind="sweep", base={"type": "alphabeta", "weights": {"mobility": 80, "disc_diff": 5}}, param="depth",
        values=[1, 2, 3, 4, 5], opp=_mcts, pairs=25, plies=6, seed=200,
        note=f"thang độ sâu: Alpha-Beta depth 1-5 đấu {_label}")

EXPERIMENTS["ladder_leaf_vs_base"] = dict(
    kind="match", a=LEAF_BASE, b=BASE_MCTS_T, tag="leaf_vs_base", pairs=30, plies=6, seed=200,
    note="đối đầu trực tiếp: MCTS leaf_eval vs MCTS gốc (cùng 0.5 s/nước)")


def build_cmd(name, exp, out_root, workers, pairs_override, quick):
    exp = copy.deepcopy(exp)
    pairs = pairs_override or exp["pairs"]
    if quick:
        pairs = 2
        for key in ("base", "a", "b", "opp"):                  # MCTS chạy thử với 100 mô phỏng cho nhanh
            if key in exp and exp[key].get("type") == "mcts" and exp.get("param") != "simulations":
                exp[key]["simulations"] = 100
        for key in ("base", "a", "b", "opp"):                  # chạy thử: ngân sách giờ cũng thu nhỏ
            if key in exp and exp[key].get("budget"):
                exp[key]["budget"] = 0.05
        if exp.get("param") == "simulations":
            exp["values"] = [50, 100]
    out = Path(out_root) / name
    common = ["--pairs", str(pairs), "--plies", str(exp["plies"]), "--seed", str(exp["seed"]),
              "--workers", str(workers), "--out", str(out)]
    if exp["kind"] == "sweep":
        cmd = [sys.executable, str(TUNE), "sweep", "--base", json.dumps(exp["base"]), "--param", exp["param"],
               "--values", *[json.dumps(v) if not isinstance(v, str) else v for v in exp["values"]],
               "--opp", json.dumps(exp["opp"]), *common]
    else:
        cmd = [sys.executable, str(TUNE), "match", "--a", json.dumps(exp["a"]), "--b", json.dumps(exp["b"]),
               "--tag", exp["tag"], *common]
    return cmd, out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--only", nargs="+", choices=list(EXPERIMENTS), help="chỉ chạy các thí nghiệm này (mặc định: tất cả)")
    ap.add_argument("--workers", type=int, default=1, help="số tiến trình song song (<= số lõi vật lý - 1)")
    ap.add_argument("--pairs", type=int, help="ghi đè số cặp ván của mọi thí nghiệm (mỗi cặp = 2 ván)")
    ap.add_argument("--quick", action="store_true", help="chạy thử: 2 cặp ván, MCTS 100 mô phỏng (KHÔNG dùng làm kết quả)")
    ap.add_argument("--out-root", default=str(ROOT / "results" / "logs" / "tune_search"))
    ap.add_argument("--force", action="store_true", help="chạy lại cả thí nghiệm đã có summary.csv (thư mục cũ đổi tên .bak)")
    ap.add_argument("--dry-run", action="store_true", help="chỉ in lệnh")
    ap.add_argument("--list", action="store_true", help="liệt kê thí nghiệm rồi thoát")
    a = ap.parse_args()

    if a.list:
        for k, e in EXPERIMENTS.items():
            what = f"{e['param']} in {e['values']}" if e["kind"] == "sweep" else e["tag"]
            print(f"{k:16} {e['pairs']:>3} cặp  seed {e['seed']}  {what}\n{'':16} {e['note']}")
        return

    names = a.only or list(EXPERIMENTS)
    for name in names:
        cmd, out = build_cmd(name, EXPERIMENTS[name], a.out_root, a.workers, a.pairs, a.quick)
        print(f"\n=== {name}: {EXPERIMENTS[name]['note']}")
        if a.dry_run:
            print(" ".join(f'"{c}"' if " " in c or "{" in c else c for c in cmd))
            continue
        if (out / "summary.csv").exists():
            if not a.force:
                print(f"  bỏ qua: {out / 'summary.csv'} đã có (dùng --force để chạy lại)")
                continue
            bak = out.with_name(f"{out.name}.bak_{time.strftime('%Y%m%d_%H%M%S')}")
            shutil.move(str(out), str(bak))
            print(f"  đã đổi tên thư mục cũ -> {bak.name}")
        t0 = time.time()
        subprocess.run(cmd, cwd=ROOT, check=True)
        print(f"  xong {name} sau {(time.time() - t0) / 60:.1f} phút")


if __name__ == "__main__":
    main()