"""Proper scoring rules on binary claims. Both are LOSSES: lower is better.

brier(p, o)    = (p - o)^2                          range [0, 1]; 0.25 for the constant forecast 0.5
log_loss(p, o) = -[o ln p + (1-o) ln(1-p)]          range [0, inf); ln 2 = 0.6931 for the constant 0.5
                 (the logarithmic score is the negative of this; we report the loss form so that
                  "lower is better" holds for both columns)

Forecasts of exactly 0 or 1 are legal in the store. A confident wrong forecast has infinite log loss, so
log_loss clips p into [eps, 1-eps] (eps = LOG_EPS, preregistered) and callers report how many forecasts were
clipped (n_clipped) so the clipping is never silent. Brier needs no clipping.
"""
from __future__ import annotations

import numpy as np

LOG_EPS = 1e-6


def _arr(x):
    return np.asarray(x, dtype=float)


def brier(p, o):
    p, o = _arr(p), _arr(o)
    return (p - o) ** 2


def log_loss(p, o, eps: float = LOG_EPS):
    p, o = _arr(p), _arr(o)
    q = np.clip(p, eps, 1.0 - eps)
    return -(o * np.log(q) + (1.0 - o) * np.log(1.0 - q))


def n_clipped(p, eps: float = LOG_EPS) -> int:
    p = _arr(p)
    return int(np.sum((p < eps) | (p > 1.0 - eps)))


def constant_reference(o, eps: float = LOG_EPS):
    """Reference scores that need no model: the uninformative 0.5 forecast, and the in-sample base rate
    (the base-rate forecast uses the outcomes themselves, so it is a hindsight reference, not a competitor)."""
    o = _arr(o)
    rate = float(o.mean())
    return {
        "base_rate": rate,
        "brier_p0.5": float(brier(np.full_like(o, 0.5), o).mean()),
        "log_loss_p0.5": float(log_loss(np.full_like(o, 0.5), o, eps).mean()),
        "brier_base_rate_hindsight": float(brier(np.full_like(o, rate), o).mean()),
        "log_loss_base_rate_hindsight": float(log_loss(np.full_like(o, rate), o, eps).mean()),
    }
