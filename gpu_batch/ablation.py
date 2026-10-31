#!/usr/bin/env python3
"""Post-hoc DESCRIPTIVE check of label-free ESM2 priors against the measured TrpB assay.

  python -m gpu_batch.ablation --arrays DIR --core-commit SHA --out artifacts/scale/ablation_descriptive.json

y = core's bg-subtracted mean of two raw replicates on the 159,129 measured non-stop genotypes (never the KNN-imputed
rows).  Reported per (model, protocol): Spearman rho, top-1% overlap with the measured top-1%, and a variant-resampling
bootstrap interval (descriptive; variants are not independent draws, so it is NOT a coverage claim).
This is evaluation only: the priors were produced without any label.  It does not choose anything used in the replay
(the replay prior is predeclared as mm_ctx).
"""
import argparse
import json
import os
import sys
import tempfile
from pathlib import Path

import numpy as np
from scipy.stats import rankdata

from . import prior_replay as PR

SIZE_ORDER = ["te8m", "te35m", "te150m", "te650m", "te3b", "te15b"]
PROTOS = ["mm_wt", "mm_ctx", "unmasked", "allmask"]


def spearman(a, b):
    ra, rb = rankdata(a), rankdata(b)
    return float(np.corrcoef(ra, rb)[0, 1])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arrays", required=True)
    ap.add_argument("--core-commit", required=True)
    ap.add_argument("--core-repo", default="/data/worktrees/delphi-evolve/core")
    ap.add_argument("--raw", default="/data/worktrees/delphi-evolve/core/data/raw")
    ap.add_argument("--boot", type=int, default=200)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    root = PR.export_core(a.core_commit, a.core_repo, a.raw, tempfile.gettempdir() + "/scale_core_export")
    sys.path.insert(0, str(root))
    from evolve import data
    land = data.load()
    meas = land.measured
    y = land.s[meas].astype(float) / data.UNITS
    top = y >= np.quantile(y, 0.99)
    rng = np.random.default_rng(11)
    boots = [rng.integers(0, len(y), len(y)) for _ in range(a.boot)]
    res = {"core_commit": a.core_commit, "n_measured": int(meas.sum()), "y": "bg-subtracted mean of two raw replicates",
           "parent_score": float(land.s[data.encode("VFVS")] / data.UNITS), "rows": []}
    for m in SIZE_ORDER:
        p = Path(a.arrays) / f"{m}_library.npz"
        if not p.exists():
            continue
        lib = np.load(p)
        have = lib["have"]
        if not have[meas].all():
            res["rows"].append({"model": m, "note": "incomplete library coverage; skipped"})
            continue
        meta = json.loads(bytes(lib["meta_json"]).decode())
        for proto in PROTOS:
            z = lib[f"z_{proto}"][meas]
            rho = spearman(z, y)
            bs = [spearman(z[i], y[i]) for i in boots]
            topz = z >= np.quantile(z, 0.99)
            res["rows"].append({"model": m, "repo": meta["repo"], "revision": meta["revision"], "protocol": proto, "spearman": rho,
                                "boot_lo": float(np.percentile(bs, 2.5)), "boot_hi": float(np.percentile(bs, 97.5)),
                                "top1pct_overlap": float((top & topz).sum() / top.sum()), "chance_overlap": 0.01})
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(res, indent=1) + "\n")
    for r in res["rows"]:
        if "spearman" in r:
            print(f'{r["model"]:7s} {r["protocol"]:9s} rho={r["spearman"]:+.3f} [{r["boot_lo"]:+.3f},{r["boot_hi"]:+.3f}] top1%={r["top1pct_overlap"]:.3f}')


if __name__ == "__main__":
    main()
