#!/usr/bin/env python3
"""Downstream use of the GPU priors: replay core's query-to-certify policies with and without an ESM2 prior.

  python -m gpu_batch.prior_replay run --core-commit <sha> --core-repo DIR --raw DIR \
         --policy q2c --tag none|esm_<model>_<protocol>|shuf_<model>_<protocol> --priors DIR --seeds 0-19 --out DIR
  python -m gpu_batch.prior_replay summarize --out DIR [--core-shards DIR]

Policy-legality of the prior (frozen before any prior was scored against a label):
  * the library-wide z-scored ESM2 score is label-free (see assemble.scalar_priors);
  * per episode it is mapped to score units by ordinary least squares on the episode's FREE initial
    observations only (start, target and the 96 random initial rows, i.e. exactly what every policy already
    sees): prior = a + b z.  No other label, no cross-episode tuning, no shared slope;
  * a shuffled control (same z values permuted over genotypes with a fixed seed) goes through the identical map,
    so a gain must come from sequence-specific information, not from the extra smoother.
The prior only guides which row to assay next.  Certificates still use revealed measurements.
Core code is executed from a `git archive` export at --core-commit (never from the live worktree).
"""
from __future__ import annotations

import os

for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_v, "1")
os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")

import argparse  # noqa: E402
import json  # noqa: E402
import subprocess  # noqa: E402
import sys  # noqa: E402
import tempfile  # noqa: E402
import time  # noqa: E402
from pathlib import Path  # noqa: E402

import numpy as np  # noqa: E402

SHUFFLE_SEED = 20261102
BUDGETS = (100, 250, 500, 1000)


def export_core(commit, core_repo, raw_dir, workdir):
    """git archive the pinned core commit; link read-only raw data; return export root."""
    root = Path(workdir) / f"core_{commit[:10]}"
    if not root.exists():
        root.mkdir(parents=True)
        arch = subprocess.run(["git", "-C", core_repo, "archive", commit], check=True, capture_output=True).stdout
        subprocess.run(["tar", "-x", "-C", str(root)], input=arch, check=True)
    raw = root / "data" / "raw"
    if not raw.exists():
        raw.parent.mkdir(parents=True, exist_ok=True)
        raw.symlink_to(Path(raw_dir).resolve())
    return root


def calibrate(z, nodes, y):
    """OLS y ~ a + b z on the given free observations -> (a, b).  Pure; unit-tested."""
    zz = np.asarray(z, float)[np.asarray(nodes)]
    yy = np.asarray(y, float)
    zc = zz - zz.mean()
    var = float((zc ** 2).sum())
    b = float((zc * (yy - yy.mean())).sum() / var) if var > 0 else 0.0
    return float(yy.mean() - b * zz.mean()), b


def shuffled(z):
    z = np.asarray(z, float).copy()
    np.random.default_rng(SHUFFLE_SEED).shuffle(z)
    return z


def episode_prior(z, land_scores, ep, units):
    nodes = sorted(set([ep["start"], ep["target"]] + list(ep["init"])))
    a, b = calibrate(z, nodes, np.asarray(land_scores)[nodes] / units)
    return a + b * np.asarray(z, float), a, b, len(nodes)


def parse_seeds(s):
    out = []
    for p in s.split(","):
        if "-" in p:
            a, b = p.split("-")
            out += list(range(int(a), int(b) + 1))
        else:
            out.append(int(p))
    return out


def run(a):
    root = export_core(a.core_commit, a.core_repo, a.raw, tempfile.gettempdir() + "/scale_core_export")
    sys.path.insert(0, str(root))
    from evolve import data, replay  # noqa: E402
    land = data.load()
    z = None
    if a.tag != "none":
        kind, model, proto = a.tag.split("_", 2)
        lib = np.load(Path(a.priors) / f"{model}_library.npz")
        if not bool(lib["have"].all()):
            raise SystemExit(f"{model}: library coverage incomplete; the core hook requires all 160000 entries")
        z = lib[f"z_{proto}"].astype(float)
        assert z.shape == (data.N_GENO,) and np.isfinite(z).all()
        if kind == "shuf":
            z = shuffled(z)
    out = Path(a.out) / "shards"
    out.mkdir(parents=True, exist_ok=True)
    eps_all = replay.make_episodes(land, 20)
    for seed in parse_seeds(a.seeds):
        p = out / f"{a.policy}__{a.tag}__seed{seed:02d}.json"
        if p.exists():
            continue
        rows, t0 = [], time.time()
        for ep in [e for e in eps_all if e["seed"] == seed]:
            prior, ia, ib, nn = (None, None, None, None) if z is None else episode_prior(z, land.s, ep, data.UNITS)
            row, _q, _o, _l = replay.run_episode(land, ep, a.policy, bmax=1000, prior=prior)
            row.update(prior_tag=a.tag, calib_n=nn, calib_a=ia, calib_b=ib, core_commit=a.core_commit)
            rows.append(row)
        p.write_text(json.dumps({"rows": rows, "seconds": round(time.time() - t0, 1)}, default=int))
        print(json.dumps({"seed": seed, "tag": a.tag, "policy": a.policy, "seconds": round(time.time() - t0, 1)}), flush=True)


def summarize(a):
    import pandas as pd
    rows = []
    for p in sorted((Path(a.out) / "shards").glob("*.json")):
        pol, tag, _ = p.stem.split("__")
        for r in json.loads(p.read_text())["rows"]:
            r["policy"], r["prior_tag"] = pol, tag
            rows.append(r)
    df = pd.DataFrame(rows)
    df["t"] = df["assays"].where(df["certificate"].notna(), np.inf)
    rng = np.random.default_rng(7)
    res = []
    base = df[df.prior_tag == "none"]
    for (pol, tag), g in df.groupby(["policy", "prior_tag"]):
        row = {"policy": pol, "tag": tag, "episodes": len(g), "seeds": int(g.seed.nunique())}
        for b in BUDGETS:
            c = g.t <= b
            row[f"cert@{b}"] = int(c.sum())
            row[f"false@{b}"] = int((c & (g.correct == False)).sum())  # noqa: E712
        row["rmst@1000"] = float(np.minimum(g.t, 1000).mean())
        if tag != "none" and not base[base.policy == pol].empty:
            b0 = base[base.policy == pol].set_index(["family", "seed", "start", "target"])
            g1 = g.set_index(["family", "seed", "start", "target"])
            idx = g1.index.intersection(b0.index)
            d = (np.minimum(g1.loc[idx, "t"], 1000) - np.minimum(b0.loc[idx, "t"], 1000)).to_frame("d")
            d["seed"] = [i[1] for i in idx]
            per_seed = d.groupby("seed")["d"].mean().to_numpy()
            boots = [per_seed[rng.integers(0, len(per_seed), len(per_seed))].mean() for _ in range(2000)]
            row.update(paired_rmst_diff_vs_none=float(per_seed.mean()), paired_seed_bootstrap_lo=float(np.percentile(boots, 2.5)),
                       paired_seed_bootstrap_hi=float(np.percentile(boots, 97.5)), paired_n_episodes=int(len(idx)), paired_n_seeds=int(len(per_seed)))
        res.append(row)
    out = pd.DataFrame(res).sort_values(["policy", "tag"])
    (Path(a.out) / "summary.csv").write_text(out.to_csv(index=False))
    print(out.to_string(index=False))


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--core-commit", required=True)
    r.add_argument("--core-repo", default="/data/worktrees/delphi-evolve/core")
    r.add_argument("--raw", default="/data/worktrees/delphi-evolve/core/data/raw")
    r.add_argument("--policy", required=True)
    r.add_argument("--tag", required=True)
    r.add_argument("--priors", default="/data/artifacts/delphi-evolve-scale/arrays")
    r.add_argument("--seeds", default="0-19")
    r.add_argument("--out", required=True)
    s = sub.add_parser("summarize")
    s.add_argument("--out", required=True)
    a = ap.parse_args()
    run(a) if a.cmd == "run" else summarize(a)


if __name__ == "__main__":
    main()
