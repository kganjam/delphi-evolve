"""The diversity prediction theorem (Page), on binary outcomes with squared (Brier) error.

For one claim with outcome o, forecasts p_1..p_n and crowd forecast c = mean(p_i):

    (c - o)^2   =   mean_i (p_i - o)^2   -   mean_i (p_i - c)^2
    crowd error     mean individual error    DIVERSITY

This is an algebraic identity (not a statistical estimate) and holds only for the UNWEIGHTED MEAN crowd.
`decompose` re-checks it numerically on every call and raises IdentityError if the residual exceeds TOL, so a
wrong headline cannot be produced silently.

!! THE LIMIT, which must accompany every use of the number !!
   Diversity >= 0, so crowd error <= mean individual error, ALWAYS. That is guaranteed, and a crowd that is
   merely better than the average member is a weak result. The theorem says NOTHING about whether the crowd
   beats the BEST individual. That is an empirical question, measured in report.py, and the answer may be
   negative (e.g. one strong agent plus several weak, correlated ones).

Also reported, labelled as such (not part of the theorem): the Jensen gap for log loss,
    mean_i L(p_i) - L(mean p)  >= 0   because log loss is convex in p.
"""
from __future__ import annotations

import numpy as np

from .scoring import log_loss

TOL = 1e-12


class IdentityError(AssertionError):
    pass


def decompose(P, o, tol: float = TOL):
    """P: (n_units, n_claims) forecasts, o: (n_claims,) outcomes in {0,1}. Averages are over claims.

    Returns per-claim vectors and claim-averaged scalars. Raises IdentityError if the identity fails."""
    P = np.asarray(P, dtype=float)
    o = np.asarray(o, dtype=float)
    if P.ndim != 2 or o.shape != (P.shape[1],):
        raise ValueError(f"shape mismatch: P{P.shape} o{o.shape}")
    crowd = P.mean(axis=0)
    crowd_err = (crowd - o) ** 2
    indiv_err = ((P - o) ** 2).mean(axis=0)
    div = ((P - crowd) ** 2).mean(axis=0)
    resid = crowd_err - (indiv_err - div)
    max_resid = float(np.max(np.abs(resid))) if resid.size else 0.0
    if not max_resid <= tol:
        raise IdentityError(f"diversity identity violated: max |residual| = {max_resid:.3e} > {tol:.0e}")
    # claim-averaged identity must also close
    avg_resid = float(crowd_err.mean() - (indiv_err.mean() - div.mean()))
    if not abs(avg_resid) <= tol:
        raise IdentityError(f"claim-averaged identity violated: {avg_resid:.3e}")
    indiv_log = log_loss(P, o).mean(axis=0)
    crowd_log = log_loss(crowd, o)
    return {
        "n_units": int(P.shape[0]),
        "n_claims": int(P.shape[1]),
        "crowd_brier": float(crowd_err.mean()),
        "mean_individual_brier": float(indiv_err.mean()),
        "diversity": float(div.mean()),
        "identity_max_abs_residual": max_resid,
        "identity_claim_avg_residual": avg_resid,
        "diversity_share_of_mean_individual_error": float(div.mean() / indiv_err.mean()) if indiv_err.mean() > 0 else None,
        "mean_individual_log_loss": float(indiv_log.mean()),
        "crowd_mean_pool_log_loss": float(crowd_log.mean()),
        "log_loss_jensen_gap": float((indiv_log - crowd_log).mean()),
        "per_claim": {"crowd_err": crowd_err, "indiv_err": indiv_err, "diversity": div},
    }


def self_test() -> dict:
    """Hand-computed literal example plus exact-identity check on fixed numeric matrices.
    The matrices are arithmetic fixtures for the identity only; they are not data and are not reported as results."""
    P = np.array([[0.9, 0.2], [0.5, 0.6]])
    o = np.array([1.0, 0.0])
    d = decompose(P, o)
    expect = {"crowd_brier": 0.125, "mean_individual_brier": 0.165, "diversity": 0.04}
    for k, v in expect.items():
        if abs(d[k] - v) > 1e-12:
            raise IdentityError(f"hand example {k}: got {d[k]}, expected {v}")
    rng = np.random.default_rng(0)
    worst = 0.0
    for n, m in [(2, 5), (6, 40), (26, 300), (1, 7)]:
        Pr = rng.uniform(0, 1, (n, m))
        orr = (rng.uniform(0, 1, m) < 0.4).astype(float)
        worst = max(worst, decompose(Pr, orr)["identity_max_abs_residual"])
    return {"hand_example": "pass", "random_fixtures_max_abs_residual": worst, "tolerance": TOL}
