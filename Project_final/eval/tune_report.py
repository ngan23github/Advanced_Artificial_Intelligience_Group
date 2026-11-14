"""Tổng hợp log tune thành bảng phụ lục (markdown) + hình, đọc từ results/logs/tune_search/*/summary.csv.

Chạy: python -m eval.tune_report [--dir results/logs/tune_search] [--out results/analysis/tune_search]
Mỗi thư mục con = 1 thí nghiệm (ab_weights, mcts_rollout_c, ...). Chỉ ĐỌC log do notebooks/tune.py ghi, không chạy lại ván.
Log tune dùng seed >= 100, tách khỏi seed đánh giá cuối (0-2).
"""

import argparse
from pathlib import Path

import pandas as pd


def build(tune_dir: Path, out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    lines = ["# Bảng tune (tập tune, seed >= 100)\n",
             "Cột `A_winrate` = (thắng + 0.5 hòa)/số ván của cấu hình A (đối thủ B ghi ở cột B); CI 95% Wilson.\n"]
    for sub in sorted(p for p in tune_dir.iterdir() if (p / "summary.csv").exists()):
        df = pd.read_csv(sub / "summary.csv")
        lines.append(f"\n## {sub.name}\n")
        lines.append(f"Đối thủ B: `{df['B'].iloc[0]}`" if df["B"].nunique() == 1 else "Nhiều đối thủ (xem cột B).")
        lines.append("\n| cấu hình (tag) | ván | thắng-hòa-thua | score | CI 95% | ms/nước A | nodes A | sims A |\n|---|---|---|---|---|---|---|---|")
        for _, r in df.iterrows():
            lines.append(f"| {r['tag']} | {r['games']} | {r['A_wins']}-{r['draws']}-{r['A_losses']} | {r['A_winrate']:.3f} | "
                         f"[{r['ci95_lo']:.3f}, {r['ci95_hi']:.3f}] | {r['A_time_per_move'] * 1000:.0f} | "
                         f"{r['A_nodes']:.0f} | {r['A_sims']:.0f} |")
        if len(df) > 1:
            fig, ax = plt.subplots(figsize=(7, max(2.5, 0.35 * len(df) + 1)))
            y = range(len(df))
            err = [df["A_winrate"] - df["ci95_lo"], df["ci95_hi"] - df["A_winrate"]]
            ax.errorbar(df["A_winrate"], list(y), xerr=err, fmt="o", capsize=3)
            ax.axvline(0.5, color="gray", ls="--")
            ax.set_yticks(list(y), df["tag"], fontsize=7)
            ax.invert_yaxis()
            ax.set_xlim(0, 1)
            ax.set_xlabel("score của cấu hình A trước đối thủ B (CI 95%)")
            ax.set_title(sub.name, fontsize=9)
            fig.tight_layout()
            fig.savefig(out_dir / f"tune_{sub.name}.png", dpi=140)
            plt.close(fig)
    md = out_dir / "tune_summary.md"
    md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return md


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--dir", default="results/logs/tune_search")
    p.add_argument("--out", default="results/analysis/tune_search")
    a = p.parse_args()
    print(build(Path(a.dir), Path(a.out)))


if __name__ == "__main__":
    main()
