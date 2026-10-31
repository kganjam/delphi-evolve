"""Scoring for the probabilities the factor graph emits for simulated nodes.

P(M,L) is a Beta-Binomial posterior over basin volume built from k pattern outcomes in n (seed x amplitude) runs where the
two independently discretized solvers agreed. This module scores those probabilities the only honest way: as a predictive
distribution for HELD-OUT runs (different seeds/amplitudes), with the log score of the Beta-Binomial pmf and the Brier score
of the predictive mean. It builds no graph and sets no prior: a and b are arguments and are reported.

A Lean-clamped node (hard 0/1) carries no probability to score; it is checked, not forecast. If a clamped-0 node shows
held-out pattern outcomes, that is a re-indexing event (subcritical finite-amplitude instability), counted, never averaged away.
"""
from __future__ import annotations

from math import lgamma, log

import numpy as np


def predictive_mean(k: int, n: int, a: float = 1.0, b: float = 1.0) -> float:
    return (a + k) / (a + b + n)


def _lbeta(x, y):
    return lgamma(x) + lgamma(y) - lgamma(x + y)


def beta_binomial_logpmf(h: int, m: int, k: int, n: int, a: float = 1.0, b: float = 1.0) -> float:
    """log P(h of m held-out runs show a pattern | k of n training runs did), Beta(a,b) prior."""
    from math import comb
    return log(comb(m, h)) + _lbeta(a + k + h, b + n - k + m - h) - _lbeta(a + k, b + n - k)


def score_nodes(nodes: list[dict], a: float = 1.0, b: float = 1.0) -> dict:
    """nodes: {"id","k","n","held_out_k","held_out_m"[, "lean_clamped_zero": bool]}. Clamped nodes are counted separately."""
    scored, reindexed, ll, br = 0, [], [], []
    for r in nodes:
        if r.get("lean_clamped_zero"):
            if r["held_out_k"] > 0 or r["k"] > 0:
                reindexed.append(r["id"])
            continue
        p = predictive_mean(r["k"], r["n"], a, b)
        ll.append(-beta_binomial_logpmf(r["held_out_k"], r["held_out_m"], r["k"], r["n"], a, b) / r["held_out_m"])
        # Brier of the predictive mean against each held-out run, averaged
        h, m = r["held_out_k"], r["held_out_m"]
        br.append((h * (1 - p) ** 2 + (m - h) * p ** 2) / m)
        scored += 1
    return {"prior": [a, b], "n_scored_nodes": scored,
            "mean_log_loss_per_heldout_run": float(np.mean(ll)) if ll else None,
            "mean_brier_per_heldout_run": float(np.mean(br)) if br else None,
            "n_reindexed_subcritical_finite_amplitude": len(reindexed), "reindexed_ids": reindexed,
            "note": "log loss per run = -log BetaBinomial pmf / m (ordered-sequence normalisation not applied; comparable across nodes with equal m only)"}
