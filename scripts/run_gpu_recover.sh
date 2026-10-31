#!/usr/bin/env bash
# Recover compact GPU results from a finished job's log (reproducible download).
#   scripts/run_gpu_recover.sh <aijob-id> <window-start RFC3339> <window-end RFC3339> <outdir>
# Example: scripts/run_gpu_recover.sh aijob-e00whrj05xvrnbfxtx 2026-10-31T00:40:00-07:00 2026-10-31T01:30:00-07:00 artifacts/gpu/main
# Verifies every chunk and whole-file SHA-256; exits non-zero on any mismatch or gap.
set -euo pipefail
JOB="$1"; A="$2"; B="$3"; OUT="$4"
HERE="$(cd "$(dirname "$0")/.." && pwd)"
TMP="$(mktemp -d)"
python3 -I "$HERE/gpu/fetch_job_logs.py" "$JOB" "$A" "$B" "$TMP/job.log"
python3 -I "$HERE/gpu/recover_from_logs.py" "$TMP/job.log" "$OUT"
# keep a compact, chunk-free copy of the log as the run receipt
grep -v RESULT_CHUNK "$TMP/job.log" | grep -vE "flash_attn|registered at|dispatch key|previous kernel|new kernel|self.m.impl|Overriding|operator:" | cut -c1-8000 > "$OUT/job_${JOB}.log"
rm -rf "$TMP"
