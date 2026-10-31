#!/usr/bin/env bash
# Container entrypoint for the TrpB ESM2 jobs (injected at /work/job_entry.sh).
# Credentials are never read here; the job has no secrets and downloads public HF files only.
set -uo pipefail
echo "ENTRY start $(date -u +%FT%TZ) host=$(hostname)"
nvidia-smi
export PIP_CONSTRAINT=""          # NGC images pin a constraints file that blocks upgrades
export HF_HOME=/tmp/hf
export PYTHONUNBUFFERED=1
python -m pip install -q "transformers==5.5.0" 2>&1 | tail -3
echo "ENTRY pip_list_begin"; python -m pip list 2>/dev/null | grep -iE "^(torch|transformer|numpy|tokenizers|huggingface|safetensors|flash)" ; echo "ENTRY pip_list_end"
python /work/embed_trpb.py "$@"
rc=$?
echo "ENTRY exit=$rc $(date -u +%FT%TZ)"
ls -la /output 2>&1 | head
exit $rc
