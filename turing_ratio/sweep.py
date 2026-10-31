"""CPU sweeps. A: named kinetics -> minimum d_c over their parameter space and Turing-region area vs d.
B: generic 2x2 Jacobian ensembles -> distribution of d_c and fine-tuning (robustness to 5% entry perturbations).
Usage: python -m turing_ratio.sweep OUT.json   (numpy only; ~seconds)"""
import json, sys, time
import numpy as np
from .core import d_crit, turing_unstable, stable

DS = [1.1, 1.5, 2, 3, 5, 10, 20, 50]


def jac(model, p, q):
    if model == "schnakenberg":      # a=p,b=q: u*=a+b, v*=b/(a+b)^2
        s = p + q; return (q - p) / s, s ** 2, -2 * q / s, -s ** 2
    if model == "brusselator":       # A=p,B=q
        return q - 1, p ** 2, -q, -p ** 2
    if model == "gierer_meinhardt":  # a=p,b=q: u*=(a+1)/b
        us = (p + 1) / q; return -q + 2 / us, -1 / us ** 2, 2 * us, -np.ones_like(us)
    raise ValueError(model)


def named(n=1000):
    out = {}
    g = np.logspace(-2, 1, n)        # parameters on log grid [0.01, 10]^2 (a CHOICE; area is relative to this box)
    P, Q = np.meshgrid(g, g, indexing="ij")
    for m in ("schnakenberg", "brusselator", "gierer_meinhardt"):
        a, b, c, e = jac(m, P, Q); dc = d_crit(a, b, c, e)
        okmask = np.isfinite(dc); i = np.nanargmin(np.where(okmask, dc, np.nan)) if okmask.any() else None
        o = {"grid": f"{n}x{n} log-spaced in [0.01,10]^2", "stable_activator_inhibitor_fraction": float(okmask.mean()),
             "d_c_min": float(np.nanmin(dc)) if okmask.any() else None,
             "d_c_at_min_params": [float(P.flat[i]), float(Q.flat[i])] if i is not None else None,
             "d_c_quantiles_over_stable_region": {k: float(np.nanquantile(dc, k)) for k in (0.05, 0.5, 0.95)} if okmask.any() else None,
             "turing_area_fraction_of_box_vs_d": {str(d): float(turing_unstable(a, b, c, e, d).mean()) for d in DS}}
        out[m] = o
    return out


def generic(N=2_000_000, seed=0, nperturb=32, delta=0.05):
    rng = np.random.default_rng(seed)
    res = {}
    for ens in ("E1_a11=1_s,p_loguniform", "E2_all_entries_loguniform_signed"):
        if ens.startswith("E1"):
            a = np.ones(N); s = 1 + 10 ** rng.uniform(-2, 1, N); e = -s
            p = s * (1 + 10 ** rng.uniform(-3, 1, N)); b = -np.sqrt(p) * 10 ** rng.uniform(-.5, .5, N); c = p / b * -1 * -1
            c = -p / b            # b*c = -p
        else:
            a = 10 ** rng.uniform(-1, 1, N); e = -10 ** rng.uniform(-1, 1, N)
            b = 10 ** rng.uniform(-1, 1, N) * rng.choice([-1, 1], N); c = 10 ** rng.uniform(-1, 1, N) * rng.choice([-1, 1], N)
        dc = d_crit(a, b, c, e); ok = np.isfinite(dc)
        o = {"N": N, "fraction_stable_activator_inhibitor": float(ok.mean()),
             "d_c_quantiles": {str(k): float(np.nanquantile(dc, k)) for k in (0.01, 0.1, 0.5, 0.9)},
             "fraction_d_c_below": {str(d): float((dc[ok] < d).mean()) for d in (1.1, 1.5, 2, 3, 10)}}
        # fine-tuning: among systems that are Turing at d_test, fraction of 5% multiplicative entry perturbations that stay Turing
        rob = {}
        for dtest in (1.5, 10.0):
            idx = np.where(ok & (dc < dtest))[0][:200_000]
            if len(idx) == 0: continue
            A, B, C, E = (x[idx] for x in (a, b, c, e))
            keep = np.zeros(len(idx)); keep_stable = np.zeros(len(idx))
            for _ in range(nperturb):
                f = lambda x: x * (1 + delta * rng.uniform(-1, 1, len(idx)))
                A2, B2, C2, E2 = f(A), f(B), f(C), f(E)
                keep += turing_unstable(A2, B2, C2, E2, dtest); keep_stable += stable(A2, B2, C2, E2)
            keep /= nperturb; keep_stable /= nperturb; margin = dc[idx] / dtest
            cond = np.divide(keep, keep_stable, out=np.full_like(keep, np.nan), where=keep_stable > 0)   # P(Turing | still stable)
            bins = [(0, .25), (.25, .5), (.5, .75), (.75, .9), (.9, 1.0)]
            rob[str(dtest)] = {"n_systems": int(len(idx)), "median_survival_fraction": float(np.median(keep)), "median_stability_survival_fraction": float(np.median(keep_stable)),
                "median_turing_given_still_stable": float(np.nanmedian(cond)),
                "turing_given_stable_by_dc_over_d_bin": {f"{lo}-{hi}": (float(np.nanmedian(cond[(margin >= lo) & (margin < hi)])) if ((margin >= lo) & (margin < hi)).any() else None) for lo, hi in [(0, .25), (.25, .5), (.5, .75), (.75, .9), (.9, 1.0)]},
                "survival_by_dc_over_d_bin": {f"{lo}-{hi}": (float(np.median(keep[(margin >= lo) & (margin < hi)])) if ((margin >= lo) & (margin < hi)).any() else None) for lo, hi in bins}}
        o["robustness_5pct_entry_perturbation"] = rob
        res[ens] = o
    return res


if __name__ == "__main__":
    t = time.time(); out = {"named_kinetics": named(), "generic": generic()}; out["wall_s"] = round(time.time() - t, 1)
    out["notes"] = ["linear continuum criterion only (infinite domain); finite-domain mode admissibility needs L and is Lean's job",
                    "ensembles and parameter box are MY arbitrary choices; fractions describe the ensemble, not biology",
                    "Gray-Scott omitted: its standard patterns do not come from a Turing-unstable uniform state"]
    json.dump(out, open(sys.argv[1], "w"), indent=1); print(json.dumps(out, indent=1)[:6000])
