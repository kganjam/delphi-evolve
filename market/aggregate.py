"""Aggregators over a forecast matrix P of shape (n_units, n_claims).

All aggregators are reported side by side; none is selected after seeing results (see prereg.json).

mean            unweighted linear pool. The ONLY aggregator for which the diversity-prediction identity is exact.
median          coordinate-wise median (mean of the two middle values when n_units is even).
log_pool        equal-weight logarithmic opinion pool = normalised geometric mean of probabilities
                = sigmoid(mean of logits). (p_i clipped to [eps,1-eps] before the logit.)
extremised      sigmoid(a * mean logit) with a FIXED a (preregistered, default 1.5). a>1 pushes away from 0.5.
                a is not fitted to outcomes, so this is an ex-ante rule.
recalibrated_cv sigmoid(alpha + beta * mean logit) with (alpha, beta) fitted by ridge-regularised logistic
                regression (ridge pulls toward the identity alpha=0, beta=1) on the OTHER folds. K-fold over
                claims, folds assigned by claim index mod K, so every score is out-of-fold. It uses outcomes of
                other claims, so it is a cross-validated evaluation, not an ex-ante forecast.
"""
from __future__ import annotations

import numpy as np

EPS = 1e-6


def logit(p, eps: float = EPS):
    q = np.clip(np.asarray(p, dtype=float), eps, 1.0 - eps)
    return np.log(q / (1.0 - q))


def expit(z):
    z = np.asarray(z, dtype=float)
    return 1.0 / (1.0 + np.exp(-z))


def agg_mean(P):
    return np.mean(P, axis=0)


def agg_median(P):
    return np.median(P, axis=0)


def agg_log_pool(P, eps: float = EPS):
    return expit(np.mean(logit(P, eps), axis=0))


def agg_extremised(P, a: float = 1.5, eps: float = EPS):
    return expit(a * np.mean(logit(P, eps), axis=0))


def _fit_platt(x, y, ridge: float, iters: int = 100):
    X = np.column_stack([np.ones_like(x), x])
    prior = np.array([0.0, 1.0])
    w = prior.copy()
    for _ in range(iters):
        p = expit(X @ w)
        g = X.T @ (p - y) + ridge * (w - prior)
        H = (X.T * (p * (1 - p))) @ X + ridge * np.eye(2)
        step = np.linalg.solve(H, g)
        step = np.clip(step, -5.0, 5.0)
        w = w - step
        if np.max(np.abs(step)) < 1e-10:
            break
    return w


def agg_recalibrated_cv(P, o, folds: int = 10, ridge: float = 1.0, eps: float = EPS):
    """Out-of-fold Platt recalibration of the log-pool logit. Returns (forecasts, fitted (alpha,beta) per fold)."""
    x = np.mean(logit(P, eps), axis=0)
    y = np.asarray(o, dtype=float)
    m = x.shape[0]
    folds = max(2, min(folds, m))
    idx = np.arange(m)
    out = np.empty(m)
    fits = []
    for k in range(folds):
        test = idx % folds == k
        train = ~test
        w = _fit_platt(x[train], y[train], ridge)
        out[test] = expit(w[0] + w[1] * x[test])
        fits.append([float(w[0]), float(w[1])])
    return out, fits


def all_aggregates(P, o=None, cfg: dict | None = None):
    """Return {name: forecast vector}, plus meta. `cfg` is the preregistered 'aggregators' block."""
    cfg = cfg or {}
    a = float(cfg.get("extremised", {}).get("a", 1.5))
    rc = cfg.get("recalibrated_cv", {})
    out = {
        "mean": agg_mean(P),
        "median": agg_median(P),
        "log_pool": agg_log_pool(P),
        f"extremised_a{a:g}": agg_extremised(P, a),
    }
    meta = {"extremised_a": a}
    if o is not None:
        pr, fits = agg_recalibrated_cv(P, o, int(rc.get("folds", 10)), float(rc.get("ridge", 1.0)))
        out["recalibrated_cv"] = pr
        meta["recalibrated_cv_fits_alpha_beta"] = fits
    return out, meta
