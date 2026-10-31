"""Exact / resampling statistics used by the desk evaluation. No invented numbers: every interval below is a
documented computation on the supplied data.

clopper_pearson   exact binomial interval for k/n. Treats items as independent, so it is NOT cluster-aware; reported
                  next to, never instead of, the family-clustered bootstrap.
cluster_ratio_ci  percentile bootstrap of a ratio-of-sums estimator sum(num)/sum(den), resampling whole FAMILIES with
                  replacement (instances in a family share generator and structure, so the family is the unit of
                  independence). Few families => wide intervals; that is the honest answer.
mcnemar_exact     exact two-sided binomial test on the discordant pairs of a paired binary outcome (item-level).
auc               Mann-Whitney AUC with ties = 0.5.
"""
from __future__ import annotations

import numpy as np
from scipy import stats as sps


def clopper_pearson(k: int, n: int, alpha: float = 0.05):
    if n == 0:
        return (None, None)
    lo = 0.0 if k == 0 else float(sps.beta.ppf(alpha / 2, k, n - k + 1))
    hi = 1.0 if k == n else float(sps.beta.ppf(1 - alpha / 2, k + 1, n - k))
    return (lo, hi)


def rate(k: int, n: int):
    lo, hi = clopper_pearson(k, n)
    return {"k": int(k), "n": int(n), "rate": (k / n) if n else None, "cp_lo": lo, "cp_hi": hi}


def cluster_ratio_ci(num, den, fam, B: int, seed: int, ci: float = 0.95):
    """num, den: per-item arrays (NaN items must be removed by the caller); fam: per-item family labels.
    Returns point estimate sum(num)/sum(den) and a family-cluster percentile bootstrap interval."""
    num = np.asarray(num, float)
    den = np.asarray(den, float)
    fam = np.asarray(fam)
    if den.sum() == 0:
        return {"estimate": None, "lo": None, "hi": None, "n_families": 0, "n_boot_valid": 0}
    fams = sorted(set(fam.tolist()))
    F = len(fams)
    fn = np.array([num[fam == f].sum() for f in fams])
    fd = np.array([den[fam == f].sum() for f in fams])
    rng = np.random.default_rng(seed)
    draws = rng.integers(0, F, (B, F))
    counts = np.zeros((B, F))
    for j in range(F):
        counts[:, j] = (draws == j).sum(axis=1)
    N, D = counts @ fn, counts @ fd
    ok = D > 0
    vals = N[ok] / D[ok]
    a = (1 - ci) / 2
    lo, hi = (np.quantile(vals, [a, 1 - a]) if len(vals) else (np.nan, np.nan))
    return {"estimate": float(num.sum() / den.sum()), "lo": float(lo), "hi": float(hi), "n_families": F, "n_boot_valid": int(ok.sum())}


def mcnemar_exact(x_right, y_right):
    x_right = np.asarray(x_right, bool)
    y_right = np.asarray(y_right, bool)
    b = int(np.sum(x_right & ~y_right))
    c = int(np.sum(~x_right & y_right))
    p = 1.0 if b + c == 0 else float(sps.binomtest(b, b + c, 0.5).pvalue)
    return {"x_only_right": b, "y_only_right": c, "both_right": int(np.sum(x_right & y_right)),
            "both_wrong": int(np.sum(~x_right & ~y_right)), "p_two_sided_exact": p,
            "note": "item-level, ignores family clustering; the family-cluster interval governs the verdict"}


def auc(scores_pos, scores_neg):
    """P(score_pos > score_neg) + 0.5 P(tie). Returns None if either class is empty."""
    sp, sn = np.asarray(scores_pos, float), np.asarray(scores_neg, float)
    if len(sp) == 0 or len(sn) == 0:
        return None
    gt = (sp[:, None] > sn[None, :]).sum()
    eq = (sp[:, None] == sn[None, :]).sum()
    return float((gt + 0.5 * eq) / (len(sp) * len(sn)))
