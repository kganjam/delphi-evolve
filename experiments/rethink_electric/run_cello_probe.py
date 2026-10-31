"""Feasibility probe for the 'cellular computation' arm using the open Cello UCF (BSD-2-Clause, CIDARLAB/cello, file
resources/UCF/Eco1C1G1T1.UCF.json): 20 NOR gates, each with flow-cytometry output histograms at 12 input levels.

Question: do gate transfer functions fitted on SOME input levels predict the measured output at HELD-OUT input levels
of the same gate (interleaved split), and does the authors' published Hill fit (fitted on ALL levels, so NOT held-out)
do better? Observed: cytometry histograms (geometric mean per input level). Model-derived: Hill predictions.
This probes gate-level transfer only; no circuit composition, no measured circuit outputs (those are in Nielsen et al.
2016 SI and were NOT retrieved), no new-condition (host/medium/temperature) data. Feasibility evidence, not validation.
"""
from __future__ import annotations

import json, sys
from pathlib import Path

import numpy as np
from scipy.optimize import curve_fit

HERE = Path(__file__).resolve().parent


def hill(x, ymin, ymax, K, n):
    return ymin + (ymax - ymin) / (1.0 + (x / K) ** n)


def geo_mean(bins, counts):
    b, c = np.asarray(bins, float), np.asarray(counts, float)
    return float(np.exp((np.log(b) * c).sum() / c.sum()))


def main(ucf_path):
    d = json.loads(Path(ucf_path).read_text())
    cyt = {x["gate_name"]: x for x in d if x.get("collection") == "gate_cytometry"}
    rf = {x["gate_name"]: {p["name"]: p["value"] for p in x["parameters"]} for x in d if x.get("collection") == "response_functions"}
    rows = []
    for g, x in sorted(cyt.items()):
        pts = sorted((c["input"], geo_mean(c["output_bins"], c["output_counts"])) for c in x["cytometry_data"])
        X, Y = np.array([p[0] for p in pts]), np.array([p[1] for p in pts])
        tr, te = np.arange(len(X)) % 2 == 0, np.arange(len(X)) % 2 == 1
        try:
            p, _ = curve_fit(lambda x_, a, b, K, n: np.log(hill(x_, a, b, K, n)), X[tr], np.log(Y[tr]),
                             p0=(Y.min(), Y.max(), float(np.median(X)), 1.5), bounds=([1e-4, 1e-3, 1e-4, 0.3], [10, 100, 10, 8]), maxfev=20000)
            err_fit = np.abs(np.log2(hill(X[te], *p) / Y[te]))
        except Exception as e:  # noqa: BLE001
            p, err_fit = None, np.full(te.sum(), np.nan)
        pub = rf[g]
        err_pub = np.abs(np.log2(hill(X[te], pub["ymin"], pub["ymax"], pub["K"], pub["n"]) / Y[te]))
        err_const = np.abs(np.log2(np.exp(np.log(Y[tr]).mean()) / Y[te]))   # constant (geo-mean of training outputs)
        rows.append({"gate": g, "n_levels": int(len(X)), "heldout_median_abs_log2_err": {
            "refit_on_even_levels": float(np.nanmedian(err_fit)), "published_hill_UNIT_MISMATCH_UNINTERPRETABLE": float(np.median(err_pub)),
            "constant_baseline": float(np.median(err_const))}, "refit_params": None if p is None else [float(v) for v in p]})
    med = {k: float(np.nanmedian([r["heldout_median_abs_log2_err"][k] for r in rows])) for k in rows[0]["heldout_median_abs_log2_err"]}
    out = {"source": "CIDARLAB/cello Eco1C1G1T1.UCF.json (BSD-2-Clause per GitHub API)", "n_gates": len(rows), "median_over_gates": med, "gates": rows,
           "limits": ["gate transfer only", "geometric-mean summary of histograms; population heterogeneity discarded",
                      "interleaved split of one input ladder: interpolation not extrapolation, not new conditions",
                      "the published Hill parameters (RPU-normalised in the UCF) give ~1.6 log2 error against the raw histogram geometric means; this almost certainly reflects a unit/normalisation mismatch that was NOT resolved, so that comparator is uninterpretable and is not used", "no measured circuit outputs used"]}
    (HERE / "results" / "cello_gate_probe.json").write_text(json.dumps(out, indent=1))
    print(json.dumps({"n_gates": len(rows), "median_over_gates": med}, indent=1))


if __name__ == "__main__":
    main(sys.argv[1])
