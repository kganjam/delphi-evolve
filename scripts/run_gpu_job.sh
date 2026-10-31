#!/usr/bin/env bash
# Submit ONE bounded Nebius H100 job for the TrpB ESM2 pipeline.
#   scripts/run_gpu_job.sh <job-name> <timeout e.g. 40m> <embed_trpb.py args...>
# Only the gpu worker submits GPU jobs.  Prints the created job id.  Never cancels other jobs.
# Requires: nebius CLI profile "hackathon" (token-file profile; no credential value is read here),
#           bucket id in $GPU_BUCKET_ID (mounted rw at /output).
set -euo pipefail
NAME="$1"; TIMEOUT="$2"; shift 2
HERE="$(cd "$(dirname "$0")/.." && pwd)"
IMAGE="${GPU_IMAGE:-nvcr.io/nvidia/pytorch:25.12-py3}"
NEB="${NEBIUS_BIN:-$HOME/.nebius/bin/nebius}"
args=""; for a in "$@"; do args+=" $(printf '%q' "$a")"; done
"$NEB" --profile hackathon ai job create --name "$NAME" \
  --image "$IMAGE" --container-command bash \
  --args "-c 'bash /work/job_entry.sh$args'" \
  --platform gpu-h100-sxm --preset 1gpu-16vcpu-200gb \
  --timeout "$TIMEOUT" --disk-size 100Gi \
  --subnet-id vpcsubnet-e00tc2metkvjckkqqp \
  --env "IMAGE_REF=$IMAGE" --env "JOB_LABEL=$NAME" \
  --inject-file "$HERE/gpu/job_entry.sh:/work/job_entry.sh" \
  --inject-file "$HERE/gpu/embed_trpb.py:/work/embed_trpb.py" \
  --inject-file "$HERE/gpu/trpb_ref.py:/work/trpb_ref.py" \
  --inject-file "$HERE/gpu/data/tm9d8s_AAs.fasta:/work/data/tm9d8s_AAs.fasta" \
  ${GPU_BUCKET_ID:+--volume "$GPU_BUCKET_ID:/output:rw"} \
  --async
