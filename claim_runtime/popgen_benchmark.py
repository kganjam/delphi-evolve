"""SIMULATED benchmark: Kimura diffusion formula vs exact finite Markov chains (<200 states).

This tests the numerical formula and its model assumptions in a bounded grid of HYPOTHETICAL
populations. It is not an empirical result about any organism and uses no biological data.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

from . import exact_chains as X
from .kimura import fixation_probability as u

N_GRID = [10, 25, 50, 90]                 # diploid N -> 2N+1 <= 181 states
S_GRID = [-0.05, -0.01, 0.0, 0.001, 0.01, 0.05, 0.2]
MAX_STATES = 199


def diploid_rows():
    rows = []
    for N in N_GRID:
        assert 2 * N + 1 <= MAX_STATES
        for s in S_GRID:
            P, ab = X.diploid_wf_genic(N, s)
            for label, i in (("new_mutant_1_copy", 1), ("half_frequency", N)):
                p = i / (2 * N)
                ex, kim = ab[i], u(p, N, s)
                rows.append({"model": "diploid_wf_genic", "N": N, "states": 2 * N + 1, "s": s, "start_copies": i, "p": p, "case": label,
                             "exact": ex, "kimura": kim, "abs_err": kim - ex, "rel_err": (kim - ex) / ex if ex > 0 else None,
                             "neutral_p": p})
    return rows


def haploid_rows():
    """Haploid WF (E. coli-like reproduction, 1 copy/individual). Shows why the diploid
    formula must not be applied with Ne = N: the exponent is 2Ns, not 4Ns."""
    rows = []
    for N in (20, 50, 150):
        assert N + 1 <= MAX_STATES
        for s in (-0.02, 0.005, 0.02, 0.05):
            P, ab = X.haploid_wf(N, s)
            ex = ab[1]
            rows.append({"model": "haploid_wf", "N": N, "states": N + 1, "s": s, "p": 1 / N, "exact": ex,
                         "diploid_formula_Ne_equals_N": u(1 / N, N, s),
                         "diploid_formula_Ne_equals_N_over_2": u(1 / N, N / 2, s),
                         "rel_err_naive": (u(1 / N, N, s) - ex) / ex,
                         "rel_err_variance_mapping_Ne_N_over_2": (u(1 / N, N / 2, s) - ex) / ex})
    return rows


def checks():
    out = {}
    # 1. neutral exactness (martingale): u_i = i/2N exactly for every i
    P, ab = X.diploid_wf_genic(30, 0.0)
    out["neutral_martingale_max_abs_dev"] = max(abs(ab[i] - i / 60) for i in range(61))
    # 2. exact rational solve vs float solve (tiny chain)
    from fractions import Fraction
    fr = X.diploid_exact_fraction(3, Fraction(1, 10))
    P3, ab3 = X.diploid_wf_genic(3, 0.1)
    out["fraction_vs_float_max_abs_dev_N3"] = max(abs(float(a) - b) for a, b in zip(fr, ab3))
    # 3. forward iteration vs linear solve
    P20, ab20 = X.diploid_wf_genic(20, 0.02)
    it, steps = X.absorption_by_iteration(P20, 1)
    out["iteration_vs_solve_abs_dev_N20"] = abs(it - ab20[1])
    out["iteration_steps_N20"] = steps
    # 4. Moran closed form vs chain
    Pm = X.moran_matrix(40, 1.03)
    am = X.absorption_probabilities(Pm)
    out["moran_chain_vs_closed_form_max_abs_dev"] = max(abs(am[i] - X.moran_closed_form(40, 1.03, i)) for i in range(41))
    return out


def main(out: Path):
    t = time.time()
    d, h = diploid_rows(), haploid_rows()
    ok = [r for r in d if r["rel_err"] is not None]
    summ = {}
    for s in S_GRID:
        e = [abs(r["rel_err"]) for r in ok if r["s"] == s and r["case"] == "new_mutant_1_copy"]
        summ[str(s)] = {"max_abs_rel_err_new_mutant": max(e), "min_abs_rel_err_new_mutant": min(e)} if e else None
    res = {"kind": "popgen-benchmark/v1", "label": "SIMULATED hypothetical populations; exact finite Markov chains; no biological data; not an empirical result",
           "grids": {"diploid_N": N_GRID, "s": S_GRID, "max_states": max(r["states"] for r in d)},
           "independent_reference_checks": checks(), "diploid_vs_diffusion": d, "haploid_conflation_demo": h,
           "diploid_new_mutant_rel_err_by_s": summ, "wall_seconds": round(time.time() - t, 2),
           "model_definitions": {"diploid": "2N copies; genotype fitness 1:1+s:1+2s; random mating; p'=p(1+s(1+p))/(1+2sp); binomial(2N,p')",
                                 "haploid": "N copies; fitness 1:1+s; p'=p(1+s)/(1+sp); binomial(N,p')"}}
    out.write_text(json.dumps(res, indent=1, sort_keys=True))
    return res


if __name__ == "__main__":
    main(Path(sys.argv[1]))
