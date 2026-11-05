#!/usr/bin/env bash
set -euo pipefail
python -m eval.ablations \
  --config configs/tournament.yaml \
  --out results/logs/ablations \
  "$@"
