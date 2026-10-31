#!/usr/bin/env bash
# Container entrypoint for delphi-evolve-scale-* shard jobs (injected at /work/job_entry_scale.sh).
# No secrets are read or needed: public Hugging Face files only, results go to the job log (+ /output if mounted).
set -uo pipefail
echo "ENTRY start $(date -u +%FT%TZ) host=$(hostname) label=${JOB_LABEL:-}"
nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv,noheader
export PIP_CONSTRAINT=""          # NGC images pin a constraints file that blocks upgrades
export HF_HOME=/tmp/hf
export PYTHONUNBUFFERED=1
python -m pip install -q "transformers==5.5.0" 2>&1 | tail -3
echo "ENTRY pip_list_begin"; python -m pip list 2>/dev/null | grep -iE "^(torch|transformer|numpy|tokenizers|huggingface|safetensors|flash)" ; echo "ENTRY pip_list_end"
df -h /tmp | tail -1
cd /work && python /work/shard_runner.py "$@"
rc=$?
echo "ENTRY exit=$rc $(date -u +%FT%TZ)"
exit $rc
