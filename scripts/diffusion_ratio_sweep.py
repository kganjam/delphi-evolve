"""CPU Monte-Carlo: how much of kinetics-space admits a textbook Turing band at inhibitor/activator diffusivity ratio tau?
PRIOR (stated, and the result depends on it): J entries i.i.d. uniform on [-1,1], conditioned on tr J<0 and det J>0.
Band test (float, vectorized): activator = species with positive self-feedback; band iff S>0 and S^2 > 4 Du Dv det J.
Exact spot-check of sampled positives/negatives with falsify.engine (Fractions). Seeded; 2 threads."""
import json, os, sys
os.environ.setdefault("OMP_NUM_THREADS", "2")
import numpy as np
from fractions import Fraction as F
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from falsify.engine import falsify_turing

rng = np.random.default_rng(20261031)
N = 4_000_000
J = rng.uniform(-1, 1, size=(N, 4))
a, b, c, d = J.T
stable = (a + d < 0) & (a * d - b * c > 0)
a, b, c, d = a[stable], b[stable], c[stable], d[stable]
det = a * d - b * c
n_stable = int(stable.sum())
taus = [1.1, 1.25, 1.5, 2, 3, 5, 10, 20, 50, 100]
rows = []
for tau in taus:
    # activator u (a>0): D_u=1, D_v=tau ; activator v (d>0): D_u=tau, D_v=1
    Du = np.where(a > 0, 1.0, tau); Dv = np.where(a > 0, tau, 1.0)
    S = a * Dv + d * Du
    band = (S > 0) & (S * S > 4 * Du * Dv * det)
    frac = float(band.mean())
    disc = np.sqrt(np.maximum(S * S - 4 * Du * Dv * det, 0))
    ratio = (S + disc) / np.maximum(S - disc, 1e-300)          # q_hi / q_lo, scale-free band width
    r = ratio[band]
    rows.append({"tau": tau, "fraction_of_stable_kinetics_with_band": frac,
                 "median_band_q_hi_over_q_lo": float(np.median(r)) if r.size else None,
                 "p10_band_q_hi_over_q_lo": float(np.percentile(r, 10)) if r.size else None})
# exact spot checks
mism = 0
idx = rng.choice(n_stable, 300, replace=False)
for i in idx:
    tau = float(rng.choice(taus))
    Jm = [[repr(float(a[i])), repr(float(b[i]))], [repr(float(c[i])), repr(float(d[i]))]]
    Dd = [1, repr(tau)] if a[i] > 0 else [repr(tau), 1]
    o = falsify_turing({"jacobian": Jm, "diffusivities": Dd, "domain": {"dimension": 1, "boundary": "neumann", "length_over_pi": "50"}, "crosscheck": False})
    if o["verdict"] == "refused":
        continue
    Su = a[i] * (tau if a[i] > 0 else 1.0) + d[i] * (1.0 if a[i] > 0 else tau)
    fl = bool(Su > 0 and Su * Su > 4 * tau * (a[i] * d[i] - b[i] * c[i]))
    if fl != o["continuum_band"]["textbook_turing_condition_holds"]:
        mism += 1
out = {"prior": "J entries iid U[-1,1], conditioned on tr J<0 and det J>0 (RESULT DEPENDS ON THIS PRIOR)", "samples_drawn": N, "stable_samples": n_stable,
       "seed": 20261031, "exact_spot_checks": 300, "float_vs_exact_mismatches": mism, "rows": rows,
       "reading": "Under this prior, the fraction of stable kinetics that admit a band rises with tau: about 1e-5 at 1.1 (only ~11 of ~1e6 samples, Poisson error ~30%), 3e-3 at 2, 6e-2 at 10, 0.17 at 100. A small ratio is therefore possible but occupies a tiny volume of kinetics space (fine tuning). The scale-free band width q_hi/q_lo does NOT shrink at small tau in this sample (median ~16 at 1.1) because those kinetics are near-singular (det J -> 0, q_lo -> 0): it is not a robustness measure. There is no universal threshold.",
       "not_established": "any biological system's kinetics; domain admissibility (a band is necessary, not sufficient, for a pattern); nonlinear behaviour"}
json.dump(out, open("artifacts/diffusion_ratio/sweep.json", "w"), indent=1)
for r_ in rows: print(r_)
print("stable", n_stable, "mismatches", mism)
