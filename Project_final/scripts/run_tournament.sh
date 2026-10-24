#!/usr/bin/env bash
# Chạy giải đấu round-robin theo configs/tournament.yaml. Tham số thêm được chuyển thẳng cho eval.tournament, ví dụ:
#   bash scripts/run_tournament.sh --run-name round_robin_v2 --workers 3
set -euo pipefail
cd "$(dirname "$0")/.."
python -m eval.tournament --config configs/tournament.yaml "$@"
