"""Finite-domain MISPREDICTION MAP (linear, Neumann 1-D interval of length L = rho*pi, modes q_n = (n pi / L)^2 = n^2/rho^2).

Among stable activator-inhibitor Jacobians that PASS the continuum Turing test at ratio d, what fraction has NO admissible mode
n>=1 with h(q_n) = d q^2 - (d a + e) q + det < 0 ?   (rho = L/pi.)  Float64 vectorised decision; exact Fraction cross-check on a subset
(for rational rho, q_n is rational, so the sign of h is decided EXACTLY, no square roots).
Ensembles / ratios are MY choices; the map describes the ensemble, not biology. Evidence kind: analytic/simulated.
"""
import json, sys, time
from fractions import Fraction
import numpy as np
from .core import d_crit, turing_unstable, band
from .robustness_tax_check import sample

RHOS = [1, 1.5, 2, 3, 4, 5, 7, 10, 15, 20]            # L/pi
RATIOS = {"d=2": 2.0, "d=5": 5.0, "d=10": 10.0, "d=1.2r*": None}


def has_mode(qlo, qhi, rho):
    """exists integer n>=1 with rho*sqrt(qlo) < n < rho*sqrt(qhi)."""
    lo, hi = rho * np.sqrt(qlo), rho * np.sqrt(qhi)
    n0 = np.maximum(np.floor(lo) + 1, 1)
    return n0 < hi


def exact_has_mode(J, d, rho):
    a, b, c, e = (Fraction(x) for x in J); d = Fraction(d); rho = Fraction(rho); det = a * e - b * c
    # n up to where q_n exceeds any root: q+ <= (d a+e)/d < a  => n < rho*sqrt(a); bound generously
    nmax = int(float(rho) * float(abs(a)) ** .5) + 3
    for n in range(1, max(nmax, 2) + 1):
        q = Fraction(n * n) / (rho * rho)
        if d * q * q - (d * a + e) * q + det < 0:
            return True
    return False


def main(out, N=5_000_000, M=20_000, seed=3):
    rng = np.random.default_rng(seed); res = {"N": N, "exact_check_M": M, "rhos_L_over_pi": RHOS}
    t_total = time.time()
    for kind in ("E1", "E2"):
        a, b, c, e = sample(kind, N, rng); rs = d_crit(a, b, c, e); ok = np.isfinite(rs)
        a, b, c, e, rs = a[ok], b[ok], c[ok], e[ok], rs[ok]
        res[kind] = {"n_stable_AI": int(ok.sum())}
        for name, dval in RATIOS.items():
            d = 1.2 * rs if dval is None else np.full_like(rs, dval)
            m = turing_unstable(a, b, c, e, d)                         # passes the textbook (continuum) test
            qlo, qhi = band(a[m], b[m], c[m], e[m], d[m])
            tab = {}
            for rho in RHOS:
                hm = has_mode(qlo, qhi, rho)
                tab[str(rho)] = round(100 * float(1 - hm.mean()), 2) if m.any() else None   # % that pass continuum test but have NO mode
            res[kind][name] = {"n_pass_continuum": int(m.sum()), "pct_pass_but_no_admissible_mode_by_L_over_pi": tab}
        # exact cross-check on a subset (rational rho in {1,2,3,7/2,10,20}); d = 1.2 r* rounded to a rational
        idx = rng.choice(len(a), min(M, len(a)), replace=False); dis = 0; tested = 0
        for i in idx:
            d = Fraction(float(1.2 * rs[i])).limit_denominator(10**6)
            J = (Fraction(float(a[i])), Fraction(float(b[i])), Fraction(float(c[i])), Fraction(float(e[i])))
            if not (d * J[0] + J[3] > 0 and (d * J[0] + J[3]) ** 2 > 4 * d * (J[0] * J[3] - J[1] * J[2])):
                continue                                                # exact continuum test fails at rounded d: skip (counted)
            q = band(*[np.float64(float(x)) for x in J], float(d))
            for rho in (1, 2, 3, Fraction(7, 2), 10, 20):
                tested += 1
                if exact_has_mode(J, d, rho) != bool(has_mode(q[0], q[1], float(rho))):
                    dis += 1
        res[kind]["exact_vs_float_disagreements"] = {"decisions_tested": tested, "disagreements": dis}
    res["wall_s_total_incl_exact_check"] = round(time.time() - t_total, 1)
    json.dump(res, open(out, "w"), indent=1, allow_nan=False); print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main(sys.argv[1])
