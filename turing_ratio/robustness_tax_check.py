"""Independent third implementation of primary's 'robustness tax' protocol (messages/2026-10-31-FINDING-robustness-tax.md).
Protocol as I read it: stable activator-inhibitor J; r* closed form; test ratio d = 1.2 r*; survival = fraction of noisy copies
(each entry x(1+noise), noise 10%) that remain stable AND Turing-unstable at that fixed d; bin systems by r*.
AMBIGUITIES I resolved by choice (both reported): noise uniform in [-10%,+10%] vs Gaussian sigma=10%. Sampling boxes are MY ensembles."""
import json, sys
import numpy as np
from .core import d_crit, turing_unstable

BINS = [(1.0, 1.5), (1.5, 2), (2, 3), (3, 5), (5, 10), (10, 30), (30, 1e9)]


def sample(kind, N, rng):
    if kind == "E1":
        a = np.ones(N); s = 1 + 10 ** rng.uniform(-2, 1, N); e = -s; p = s * (1 + 10 ** rng.uniform(-3, 1, N))
        b = -np.sqrt(p) * 10 ** rng.uniform(-.5, .5, N); c = -p / b
    else:
        a = 10 ** rng.uniform(-1, 1, N); e = -10 ** rng.uniform(-1, 1, N)
        b = 10 ** rng.uniform(-1, 1, N) * rng.choice([-1, 1], N); c = 10 ** rng.uniform(-1, 1, N) * rng.choice([-1, 1], N)
    return a, b, c, e


def main(out, N=3_000_000, K=32, seed=1):
    rng = np.random.default_rng(seed); res = {"N": N, "K": K, "margin": 1.2, "noise": 0.10}
    for kind in ("E1", "E2"):
        a, b, c, e = sample(kind, N, rng); r = d_crit(a, b, c, e); ok = np.isfinite(r)
        res[kind] = {"n_stable_AI": int(ok.sum()), "min_rstar": float(np.nanmin(r)), "rstar_le_1": int((r[ok] <= 1).sum())}
        idx = np.where(ok)[0][:400_000]; A, B, C, E, R = a[idx], b[idx], c[idx], e[idx], r[idx]
        for noise_kind in ("uniform", "gaussian"):
            keep = np.zeros(len(idx))
            for _ in range(K):
                f = (lambda x: x * (1 + 0.10 * rng.uniform(-1, 1, len(idx)))) if noise_kind == "uniform" else (lambda x: x * (1 + 0.10 * rng.standard_normal(len(idx))))
                keep += turing_unstable(f(A), f(B), f(C), f(E), 1.2 * R)
            keep /= K
            res[kind][noise_kind] = {f"{lo}-{hi if hi < 1e8 else 'inf'}": {"n": int(((R >= lo) & (R < hi)).sum()),
                "mean_survival_pct": (round(100 * float(keep[(R >= lo) & (R < hi)].mean()), 1) if ((R >= lo) & (R < hi)).any() else None)} for lo, hi in BINS}
    json.dump(res, open(out, "w"), indent=1, allow_nan=False); print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main(sys.argv[1])
