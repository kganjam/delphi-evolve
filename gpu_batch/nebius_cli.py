"""Thin wrappers around the nebius CLI (profile 'hackathon'). No credential value is read or printed."""
import json
import os
import re
import subprocess
from pathlib import Path

NEB = os.environ.get("NEBIUS_BIN", os.path.expanduser("~/.nebius/bin/nebius"))
PROFILE = os.environ.get("NEBIUS_PROFILE", "hackathon")
SUBNET = "vpcsubnet-e00tc2metkvjckkqqp"
PKG = Path(__file__).resolve().parent
IMAGE = "nvcr.io/nvidia/pytorch:25.12-py3"     # same image the gpu worker validated on the H100 probe
INJECT = [("job_entry_scale.sh", "/work/job_entry_scale.sh"), ("shard_runner.py", "/work/shard_runner.py"),
          ("vendor/embed_trpb.py", "/work/embed_trpb.py"), ("vendor/trpb_ref.py", "/work/trpb_ref.py"),
          ("vendor/data/tm9d8s_AAs.fasta", "/work/data/tm9d8s_AAs.fasta")]


def _run(argv, timeout=120):
    r = subprocess.run(argv, capture_output=True, text=True, timeout=timeout)
    return r.returncode, r.stdout, r.stderr


def create_args(name, timeout, runner_args, image=IMAGE, disk="100Gi"):
    """argv for `ai job create`: one H100, hard job timeout, async."""
    ra = " ".join(__import__("shlex").quote(a) for a in runner_args)
    argv = [NEB, "--profile", PROFILE, "ai", "job", "create", "--name", name, "--image", image,
            "--container-command", "bash", "--args", f"-c 'bash /work/job_entry_scale.sh {ra}'",
            "--platform", "gpu-h100-sxm", "--preset", "1gpu-16vcpu-200gb", "--timeout", timeout,
            "--disk-size", disk, "--subnet-id", SUBNET, "--env", f"IMAGE_REF={image}", "--env", f"JOB_LABEL={name}"]
    for src, dst in INJECT:
        argv += ["--inject-file", f"{PKG / src}:{dst}"]
    return argv + ["--async"]


def create_job(name, timeout, runner_args, **kw):
    rc, out, err = _run(create_args(name, timeout, runner_args, **kw), 180)
    ids = re.findall(r"aijob-[a-z0-9]+", out + err)
    if rc != 0 or not ids:
        raise RuntimeError(f"create failed rc={rc}: {(err or out).strip()[:300]}")
    return ids[0]


def get_job(job_id):
    rc, out, err = _run([NEB, "--profile", PROFILE, "ai", "job", "get", "--id", job_id, "--format", "json"], 60)
    if rc != 0:
        raise RuntimeError(f"get failed rc={rc}: {err.strip()[:200]}")
    return json.loads(out)


def cancel_job(job_id):
    rc, out, err = _run([NEB, "--profile", PROFILE, "ai", "job", "cancel", "--id", job_id], 90)
    return rc, (out + err).strip()[:300]
