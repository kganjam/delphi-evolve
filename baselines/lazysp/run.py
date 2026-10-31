"""Driver: run the LazySP baseline on the frozen core panel using the core replay machinery.

The driver only IMPORTS `evolve.replay.run_episode` (same initial observations, same oracle,
same ledger certificate, same full-data audit) and registers the LazySP policy under a new
name in the in-process POLICIES table; no core file is modified and no core logic is copied.

Task = (variant, seed, k) where k in 0..4 indexes the five episodes of that seed in
`replay.make_episodes` order (family A pair, then four family-B pairs).  One shard file per task.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")

import numpy as np

from evolve import data, replay

from .policy import LazySP, SELECTORS

ROOT = Path(__file__).resolve().parents[2]
RECOVERY = ROOT / "artifacts" / "recovery"
PANEL_SEEDS = 20
EPISODES_PER_SEED = 5
BMAX = replay.BMAX
_LAST = {}


def register(selector, cap):
    name = f"lazysp_{selector}"

    def factory(ctx, rng):
        pol = LazySP(ctx, rng, selector=selector, runtime_cap_s=cap)
        _LAST["pol"] = pol
        return pol

    replay.POLICIES[name] = factory
    return name


def code_sha():
    try:
        return subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()
    except Exception:
        return None


def baselines_hash():
    h = hashlib.sha256()
    for p in sorted((ROOT / "baselines").rglob("*.py")):
        h.update(p.name.encode()); h.update(p.read_bytes())
    return h.hexdigest()


def panel_check(land):
    """The panel is rebuilt from code and must equal the frozen original protocol's panel hash."""
    prot = json.loads((RECOVERY / "protocol.json").read_text())
    mine = replay.protocol(land, PANEL_SEEDS)["panel_sha256"]
    if mine != prot["panel_sha256"]:
        raise RuntimeError(f"panel hash mismatch: rebuilt {mine} vs frozen {prot['panel_sha256']}")
    return mine


def episode_for(land, seed, k):
    eps = [e for e in replay.make_episodes(land, seed + 1) if e["seed"] == seed]
    return eps[k]


def run_task(land, variant, seed, k, cap, bmax=BMAX, ep=None):
    """ep may be injected by tests (synthetic fixtures); production always uses the frozen panel."""
    name = register(variant, cap)
    ep = ep or episode_for(land, seed, k)
    out, qlog, _, log = replay.run_episode(land, ep, name, bmax=bmax)
    pol = _LAST["pol"]; _LAST["log"] = log
    reason = None
    if out["censored"]:
        reason = pol.abort_reason if out["stuck"] else "assay_budget"
    out["abstain_reason"] = reason
    out["variant"] = variant
    out["lazysp"] = {**pol.stats, "native_infeasible_at": pol.native_infeasible_at, "iterations": pol.iteration,
                     "search_wall_s": round(pol.stats["search_wall_s"], 3), "runtime_cap_s": cap}
    out["event_chain_valid"] = bool(log.verify())
    return out, qlog


def shard_file(outdir, variant, seed, k):
    return Path(outdir) / "shards" / f"lazysp_{variant}__seed{seed:02d}__ep{k}.json.gz"


def cmd_run_task(a):
    p = shard_file(a.out, a.variant, a.seed, a.k)
    if p.exists():
        print("exists", p); return 0
    land = data.load()
    panel = panel_check(land)
    t0 = time.time()
    out, qlog = run_task(land, a.variant, a.seed, a.k, a.cap, a.bmax)
    meta = {"panel_sha256": panel, "dataset_sha256": land.sha, "code_commit": code_sha(), "baselines_sha256": baselines_hash(),
            "kappa": land.kappa, "bmax": a.bmax, "runtime_cap_s": a.cap, "task_wall_s": round(time.time() - t0, 3),
            "finished_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".tmp")
    with gzip.open(tmp, "wt") as f:
        json.dump({"row": out, "qlog": qlog, "meta": meta}, f, default=int)
    tmp.rename(p)
    print(json.dumps({k: out[k] for k in ("family", "seed", "start", "target", "status", "assays", "correct", "abstain_reason", "wall_s")}))
    return 0


def cmd_list(a):
    for v in a.variants.split(","):
        for s in range(a.seed_lo, a.seed_hi + 1):
            for k in range(EPISODES_PER_SEED):
                if not shard_file(a.out, v, s, k).exists():
                    print(v, s, k)
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(prog="python -m baselines.lazysp")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run-task", help="run one (variant, seed, episode) task and write a shard")
    r.add_argument("--variant", choices=SELECTORS, required=True)
    r.add_argument("--seed", type=int, required=True)
    r.add_argument("--k", type=int, required=True, choices=range(EPISODES_PER_SEED))
    r.add_argument("--out", required=True)
    r.add_argument("--cap", type=float, default=None, help="per-episode wall-clock bound (s); hitting it abstains with reason runtime_bound")
    r.add_argument("--bmax", type=int, default=BMAX)
    r.set_defaults(fn=cmd_run_task)
    l = sub.add_parser("list-tasks", help="print tasks whose shard does not exist yet")
    l.add_argument("--variants", default="alternate"); l.add_argument("--seed-lo", type=int, default=0); l.add_argument("--seed-hi", type=int, default=19)
    l.add_argument("--out", required=True)
    l.set_defaults(fn=cmd_list)
    from . import analyze
    analyze.add_parser(sub)
    a = ap.parse_args(argv)
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
