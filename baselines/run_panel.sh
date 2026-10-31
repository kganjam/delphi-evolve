#!/usr/bin/env bash
# Bounded sharded runner. usage: run_panel.sh OUTDIR VARIANTS(comma) CAP_SECONDS [SEED_LO SEED_HI]
# One systemd scope per (variant, seed, episode) task; at most 2 tasks in parallel (<=2 CPU threads).
set -u
OUT=$1; VARS=$2; CAP=$3; LO=${4:-0}; HI=${5:-19}
cd "$(dirname "$0")/.."
python -m baselines.lazysp list-tasks --variants "$VARS" --seed-lo "$LO" --seed-hi "$HI" --out "$OUT" |
  xargs -P 2 -L 1 bash -c 'systemd-run --user --scope -q -p TasksMax=128 -p MemoryMax=4G -p MemorySwapMax=0 -p RuntimeMaxSec=600 \
    python -m baselines.lazysp run-task --variant "$0" --seed "$1" --k "$2" --out "'"$OUT"'" --cap "'"$CAP"'" >> "'"$OUT"'/log.txt" 2>&1 || echo "FAILED $0 $1 $2" >> "'"$OUT"'/failed.txt"'
