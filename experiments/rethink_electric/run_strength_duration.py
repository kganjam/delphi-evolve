"""Held-out stimulus-class test: predict the 3 ms short-square threshold current of each cell from long-square-only
measurements, and quantify the cost of a robust (covering) stimulus amplitude.

PROTOCOL (fixed before any prediction was computed; amendments listed in AMENDMENTS and in the memo):
  Calibration data per cell: Long Square sweeps only (rheobase, Vrest, spike threshold voltage, Rin, tau from
  non-spiking/hyperpolarising steps). Evaluation target: the Short Square 3 ms pulse threshold of the SAME cell (a
  different stimulus class; never used to build any feature). Cells are the unit of replication (n cells, not sweeps).
  Cross-cell predictors are fitted leave-one-cell-out. The released GLIF comparator was optimised by the Allen
  Institute on sweeps we cannot list, so it is reported but NOT called held-out.
  Observed: every measured number. Model-derived: every prediction. Nothing here is a field/extracellular result.
"""
from __future__ import annotations

import json, math
from pathlib import Path

import numpy as np

from .glif_baseline import glif_short_threshold_pA

HERE = Path(__file__).resolve().parent
RES = HERE / "results"
RNG = np.random.default_rng(20261031)
T_S = 3e-3
AMENDMENTS = [
    "A1 (before any prediction): sampling rate was hard-coded 50 kHz; 44 of the first 102 cells are 200 kHz. Now read per sweep.",
    "A2 (before any prediction, from the primary-session review): long-square rheobase counts only POSITIVE steps with a spike "
    "during the step (rebound after step end reported separately); short-square spike window = pulse + 20 ms.",
    "A3 (before any prediction): short-square bracket is repeat-aware: hi = lowest amplitude with >=1 spiking repeat, "
    "lo = highest lower amplitude with no spiking repeat; repeat disagreement, non-monotonicity and censoring are flagged.",
]


def load():
    cells = json.loads((RES / "cell_features.json").read_text())["cells"]
    glif = json.loads((RES / "glif_lif_configs.json").read_text())["models"]
    return cells, glif


def usable(c):
    why = []
    if not c.get("unit_ok"): why.append("unit_conversion")
    if c.get("short_pulse_ms") != [3.0]: why.append("pulse_not_3ms")
    if c.get("short_right_censored"): why.append("short_right_censored")
    if c.get("short_left_censored"): why.append("short_left_censored")
    if c.get("short_thr_lo_pA") is None or c.get("short_thr_hi_pA") is None: why.append("no_bracket")
    for k in ("rheobase_ls_pA", "tau_ms", "ri_MOhm", "vth_ls_mV", "vrest_mV"):
        if c.get(k) is None: why.append("missing_" + k)
    if not why:
        if c["tau_ms"] <= 0 or c["ri_MOhm"] <= 0 or c["rheobase_ls_pA"] <= 0: why.append("nonpositive_feature")
        if c["vth_ls_mV"] <= c["vrest_mV"]: why.append("threshold_below_rest")
        if (c.get("tau_fit_r2") or 0) < 0.9: why.append("tau_fit_poor")
    return why


def lapicque(irh, tau_ms, kappa=1.0):
    return irh / (1.0 - math.exp(-T_S * 1e3 / (kappa * tau_ms)))


def mae_log2(pred, true):
    e = np.log2(np.asarray(pred) / np.asarray(true))
    return e


def boot_ci(x, f, n=4000):
    x = np.asarray(x); idx = RNG.integers(0, len(x), (n, len(x)))
    v = np.array([f(x[i]) for i in idx])
    return [float(np.percentile(v, 2.5)), float(np.percentile(v, 97.5))]


def wilson(k, n, z=1.96):
    p = k / n; d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d; h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [c - h, c + h]


def main():
    cells, glif = load()
    excl, keep = {}, []
    for c in cells:
        w = usable(c)
        if w:
            for x in w: excl[x] = excl.get(x, 0) + 1
        else:
            keep.append(c)
    n = len(keep)
    irh = np.array([c["rheobase_ls_pA"] for c in keep]); tau = np.array([c["tau_ms"] for c in keep])
    ri = np.array([c["ri_MOhm"] for c in keep]); vth = np.array([c["vth_ls_mV"] for c in keep]); vr = np.array([c["vrest_mV"] for c in keep])
    lo = np.array([c["short_thr_lo_pA"] for c in keep]); hi = np.array([c["short_thr_hi_pA"] for c in keep])
    mid = np.sqrt(lo * hi)                                   # geometric midpoint of the bracket (target)
    grid_floor = float(np.median(np.log2(hi / lo)) / 2)      # best-case |log2 error| from the amplitude grid alone

    preds = {}
    # P0: population ratio, leave-one-cell-out
    r = mid / irh
    preds["P0_ratio_to_rheobase(LOO)"] = np.array([irh[i] * np.median(np.delete(r, i)) for i in range(n)])
    preds["P1_lapicque_rheobase_tau(no fit)"] = np.array([lapicque(irh[i], tau[i]) for i in range(n)])
    # P2: one calibrated parameter kappa (effective tau multiplier), LOO, minimising median |log2 err|
    kg = np.exp(np.linspace(math.log(0.2), math.log(5), 121)); k_sel = []
    p2 = np.zeros(n)
    for i in range(n):
        m = np.arange(n) != i
        errs = [np.median(np.abs(np.log2(np.array([lapicque(a, t, k) for a, t in zip(irh[m], tau[m])]) / mid[m]))) for k in kg]
        k = kg[int(np.argmin(errs))]; k_sel.append(float(k)); p2[i] = lapicque(irh[i], tau[i], k)
    preds["P2_lapicque_kappa(LOO)"] = p2
    # P3: LIF from independently measured parts (Vth-Vrest)/(Ri (1-exp(-T/tau)))
    preds["P3_LIF_from_Vth_Ri_tau(no fit)"] = np.array(
        [((vth[i] - vr[i]) * 1e-3 / (ri[i] * 1e6) * 1e12) / (1 - math.exp(-T_S * 1e3 / tau[i])) for i in range(n)])
    # P4: LOO OLS  log2 y = a + b log2 irh + c log2 tau
    X = np.c_[np.ones(n), np.log2(irh), np.log2(tau)]; y = np.log2(mid)
    p4 = np.zeros(n)
    for i in range(n):
        m = np.arange(n) != i
        beta, *_ = np.linalg.lstsq(X[m], y[m], rcond=None); p4[i] = 2 ** (X[i] @ beta)
    preds["P4_LOO_regression(log irh, log tau)"] = p4
    # P5: released GLIF LIF (provenance of training sweeps unverified)
    have = np.array([glif.get(str(c["specimen__id"])) is not None for c in keep])
    p5 = np.full(n, np.nan)
    for i, c in enumerate(keep):
        g = glif.get(str(c["specimen__id"]))
        if g: p5[i] = glif_short_threshold_pA(g, T_S)
    preds["P5_released_GLIF_LIF(provenance unverified)"] = p5

    out = {"amendments": AMENDMENTS, "n_cells_selected": len(cells), "n_cells_used": n, "exclusions": excl,
           "grid_floor_median_abs_log2_err": grid_floor, "n_with_glif": int(have.sum()), "kappa_selected_range": [min(k_sel), max(k_sel)],
           "repeat_disagreement_cells_in_used": int(sum(1 for c in keep if c["short_mixed_amps"])),
           "nonmonotone_cells_in_used": int(sum(1 for c in keep if c["short_nonmonotone"])),
           "long_square_rebound_cells": int(sum(1 for c in cells if c["long_square_rebound_sweeps"])),
           "long_square_negative_spike_cells": int(sum(1 for c in cells if c["long_square_negative_onstep_spikes"])),
           "models": {}}
    base_err = None
    for name, p in preds.items():
        ok = ~np.isnan(p)
        e = mae_log2(p[ok], mid[ok]); a = np.abs(e)
        row = {"n": int(ok.sum()), "median_abs_log2_err": float(np.median(a)), "mean_abs_log2_err": float(a.mean()),
               "mean_abs_log2_err_ci95_cellboot": boot_ci(a, np.mean), "bias_median_log2": float(np.median(e)),
               "frac_within_1.5x": float((a <= math.log2(1.5)).mean()), "frac_within_2x": float((a <= 1).mean()),
               "pearson_log": float(np.corrcoef(np.log2(p[ok]), np.log2(mid[ok]))[0, 1])}
        out["models"][name] = row
    # paired differences vs P0 on the common cell set (cell bootstrap)
    common = have
    a0 = np.abs(mae_log2(preds["P0_ratio_to_rheobase(LOO)"][common], mid[common]))
    out["paired_vs_P0_common_cells"] = {"n": int(common.sum())}
    for name, p in preds.items():
        if name.startswith("P0"): continue
        d = np.abs(mae_log2(p[common], mid[common])) - a0   # negative = better than P0
        out["paired_vs_P0_common_cells"][name] = {"mean_diff_abs_log2": float(d.mean()), "ci95_cellboot": boot_ci(d, np.mean)}
    # paired differences vs P0 on ALL used cells (models P1-P4 need no GLIF model)
    allc = np.ones(n, bool); a0_all = np.abs(mae_log2(preds["P0_ratio_to_rheobase(LOO)"], mid))
    out["paired_vs_P0_all_cells"] = {"n": n}
    for name, p in preds.items():
        if name.startswith(("P0", "P5")): continue
        d = np.abs(mae_log2(p, mid)) - a0_all
        out["paired_vs_P0_all_cells"][name] = {"mean_diff_abs_log2": float(d.mean()), "ci95_cellboot": boot_ci(d, np.mean),
                                               "frac_cells_better_than_P0": float((d < 0).mean())}
    # sensitivity: cells with clean threshold ladders (no repeat disagreement, monotone)
    clean = np.array([not c["short_mixed_amps"] and not c["short_nonmonotone"] for c in keep])
    out["sensitivity_clean_ladders"] = {"n": int(clean.sum()), **{nm.split("(")[0]: float(np.median(np.abs(mae_log2(p[clean & ~np.isnan(p)], mid[clean & ~np.isnan(p)]))))
                                                                  for nm, p in preds.items()}}
    # within-cell repeat spread: lowest-all-repeat amplitude vs lowest-any-spike amplitude (ratio >1 = threshold is probabilistic)
    allrep = np.array([c["short_thr_all_repeat_pA"] if c["short_thr_all_repeat_pA"] else np.nan for c in keep])
    sp = np.log2(allrep / hi)
    out["repeat_spread_log2_all_over_any"] = {"median": float(np.nanmedian(sp)), "p90": float(np.nanpercentile(sp, 90)), "n_nan": int(np.isnan(sp).sum())}
    # ---- decision: cross-fit calibrated safety margin (amplitude that should fire), K=10 folds
    K, level = 10, 0.9

    def decide(p, rng):
        ok = ~np.isnan(p); idx = np.nonzero(ok)[0]
        f_of = {i: k for k, f in enumerate(np.array_split(rng.permutation(idx), K)) for i in f}
        cov, over = [], []
        for k in range(K):
            te = [i for i in idx if f_of[i] == k]; tr = [i for i in idx if f_of[i] != k]
            res = np.sort(np.log(hi[tr] / p[tr]))                 # >0 means prediction too LOW (would fail)
            q = res[min(len(res) - 1, math.ceil((len(res) + 1) * level) - 1)]
            for i in te:
                A = p[i] * math.exp(q); cov.append(A >= hi[i]); over.append(A / hi[i])
        return np.array(cov), np.array(over)

    dec, seed_sens = {}, {}
    for name, p in preds.items():
        cov, over = decide(p, np.random.default_rng(20261031))
        dec[name] = {"n": int(len(cov)), "coverage": float(cov.mean()), "coverage_wilson95": wilson(int(cov.sum()), len(cov)),
                     "median_amplitude_overshoot_x": float(np.median(over)), "median_energy_overshoot_x": float(np.median(over ** 2)),
                     "iqr_amplitude_overshoot": [float(np.percentile(over, 25)), float(np.percentile(over, 75))]}
        sw = [decide(p, np.random.default_rng(sd)) for sd in range(30)]
        e = [float(np.median(o ** 2)) for _, o in sw]; cv = [float(c.mean()) for c, _ in sw]
        seed_sens[name] = {"median_energy_overshoot_x_range_over_30_fold_splits": [min(e), max(e)], "coverage_range": [min(cv), max(cv)]}
    out["fold_split_sensitivity"] = seed_sens
    out["robust_amplitude_decision_target_coverage_0.9"] = dec
    out["decision_note"] = ("overshoot = chosen amplitude / lowest amplitude actually observed to fire (hi); energy ~ I^2*T so energy overshoot = amplitude overshoot squared; "
                            "cross-fit margin is the conformal-style quantile of train-fold log residuals, NOT a distribution-free guarantee on this heterogeneous panel")
    # group breakdown for P0 and P2 by dendrite type
    grp = {}
    for t in sorted({c["tag__dendrite_type"] for c in keep}):
        m = np.array([c["tag__dendrite_type"] == t for c in keep])
        grp[t] = {"n": int(m.sum()), **{nm.split("(")[0]: float(np.median(np.abs(mae_log2(preds[nm][m], mid[m])))) for nm in
                                          ["P0_ratio_to_rheobase(LOO)", "P1_lapicque_rheobase_tau(no fit)", "P2_lapicque_kappa(LOO)"]}}
    out["median_abs_log2_err_by_dendrite_type"] = grp
    out["table"] = [{"specimen_id": c["specimen__id"], "lo": float(lo[i]), "hi": float(hi[i]), "irh": float(irh[i]), "tau_ms": float(tau[i]),
                     "ri": float(ri[i]), "dendrite": c["tag__dendrite_type"], "layer": c["structure__layer"],
                     **{nm.split("(")[0]: (None if np.isnan(p[i]) else float(p[i])) for nm, p in preds.items()}} for i, c in enumerate(keep)]
    (RES / "strength_duration_results.json").write_text(json.dumps(out, indent=1))
    print(json.dumps({k: out[k] for k in ["n_cells_used", "exclusions", "grid_floor_median_abs_log2_err", "models"]}, indent=1))
    print(json.dumps(out["paired_vs_P0_common_cells"], indent=1)); print(json.dumps(dec, indent=1))


if __name__ == "__main__":
    main()
