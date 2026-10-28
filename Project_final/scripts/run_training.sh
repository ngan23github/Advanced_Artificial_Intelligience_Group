#!/usr/bin/env bash
# Chạy tuần tự 3 notebook huấn luyện (Người 3) không cần mở Jupyter: sinh dữ liệu -> NN supervised -> RL self-play.
# Chạy từ thư mục gốc repo:  bash scripts/run_training.sh
# Bản đã chạy (kèm đầu ra, hình) lưu ở results/executed_notebooks/ để làm bằng chứng quá trình train.
# Muốn theo dõi trực tiếp thì mở từng notebook trong notebooks/ và chạy (hình tự cập nhật sau mỗi epoch/lần đánh giá).
# Mỗi lần chạy chính thức đổi RUN_NAME trong notebook 05 và 06 (không ghi đè log thô); xóa/đổi data.output_dir để sinh lại dữ liệu.
set -euo pipefail
OUT=results/executed_notebooks
mkdir -p "$OUT"
for nb in 04_generate_data 05_train_supervised 06_train_rl; do
  jupyter nbconvert --to notebook --execute --ExecutePreprocessor.timeout=-1 \
      "notebooks/$nb.ipynb" --output-dir "$OUT"
done
