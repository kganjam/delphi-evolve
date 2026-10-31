"""Recompute dataset counts, hashes and the assumed noise model from the raw CSVs."""
from __future__ import annotations

import json
import platform

import numpy as np
import pandas as pd

from . import data


def run(out_path):
    L = data.load()
    d = pd.read_csv(data.RAW / "summary_AA.csv")
    ok = d[d["# Stop"] == 0]
    s1 = ok.mu_1 - L.bg[0]; s2 = ok.mu_2 - L.bg[1]
    mc = ok[["InputCount_1", "InputCount_2"]].min(axis=1).to_numpy()
    b = np.searchsorted(data.COUNT_BIN_EDGES, mc, side="right")
    diff = (s1 - s2).to_numpy()
    sds = [float(np.std(diff[b == k], ddof=1)) for k in range(4)]
    check = {"recomputed_sd_by_bin": [round(x, 6) for x in sds], "frozen": list(data.REPLICATE_DIFF_SD),
             "ok": all(abs(x - y) < 1e-6 for x, y in zip(sds, data.REPLICATE_DIFF_SD)),
             "bin_counts": [int((b == k).sum()) for k in range(4)], "bin_edges_min_input_count": list(data.COUNT_BIN_EDGES)}
    man = json.loads(data.MANIFEST.read_text())
    rep = {
        "counts": L.counts,
        "sha256": L.sha, "manifest_license": man["license"], "manifest_doi": man["doi_url"],
        "stop_codon_background_mean_mu": {"replicate_1": L.bg[0], "replicate_2": L.bg[1]},
        "score_definition": "mean over 2 replicates of (raw growth rate mu_k minus per-replicate mean raw mu of the 34,041 stop-containing rows); integer micro-units; no /max normalisation, no authors' row-specific mu-bg, no KNN labels",
        "score_summary_micro": {"min": int(L.s[L.measured].min()), "median": float(np.median(L.s[L.measured])), "max": int(L.s[L.measured].max())},
        "replicate_pearson_scores": float(np.corrcoef(s1, s2)[0, 1]),
        "noise_model_check": check,
        "assumed_kappa": data.DEFAULT_KAPPA,
        "kappa_statement": "kappa is an ASSUMED sensitivity multiplier on replicate-difference SD/2; it is not a confidence level and carries no coverage claim",
        "parent": {"genotype": data.PARENT, "score_micro": int(L.s[data.encode(data.PARENT)])},
        "versions": {"python": platform.python_version(), "numpy": np.__version__, "pandas": pd.__version__},
    }
    with open(out_path, "w") as f:
        json.dump(rep, f, indent=1, default=int)
    return rep
