#!/usr/bin/env python3
"""Vendor the gpu worker's model-loading/scoring payload at a pinned commit (read-only `git show`).

  python -m gpu_batch.vendor <commit> [--repo-dir DIR]

Writes gpu_batch/vendor/{embed_trpb.py,trpb_ref.py,tm9d8s_AAs.fasta,recover_from_logs.py} and
gpu_batch/vendor/VENDOR.json (source commit, per-file sha256).  We do not edit these copies.
"""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

FILES = {"gpu/embed_trpb.py": "embed_trpb.py", "gpu/trpb_ref.py": "trpb_ref.py",
         "gpu/data/tm9d8s_AAs.fasta": "data/tm9d8s_AAs.fasta", "gpu/recover_from_logs.py": "recover_from_logs.py", "gpu/fetch_job_logs.py": "fetch_job_logs.py"}


def main(commit, repo_dir):
    out = Path(__file__).resolve().parent / "vendor"
    rec = {"source_commit": subprocess.check_output(["git", "-C", repo_dir, "rev-parse", commit], text=True).strip(), "files": {}}
    for src, dst in FILES.items():
        raw = subprocess.check_output(["git", "-C", repo_dir, "show", f"{commit}:{src}"])
        p = out / dst
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(raw)
        rec["files"][dst] = {"from": src, "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}
    (out / "VENDOR.json").write_text(json.dumps(rec, indent=1) + "\n")
    print(json.dumps(rec, indent=1))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[3] if len(sys.argv) > 3 and sys.argv[2] == "--repo-dir" else ".")
