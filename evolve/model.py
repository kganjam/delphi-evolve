"""Small surrogate models used only to decide WHICH genotype to assay next.
They never discharge an empirical premise: certificates use revealed labels only.

GPModel   : GP regression on sequence with additive + pairwise-site + Hamming
            kernels (hyperparameters fixed a priori, no tuning on hidden labels).
LocalModel: Hamming-neighbourhood smoother (different inductive bias).
Both return (mean, sd) in score units (micro-units/1e6) and cache per fit.
"""
from __future__ import annotations

import numpy as np
from scipy.linalg import cho_factor, cho_solve, solve_triangular

from .data import UNITS, digits

PAIRS = [(0, 1), (0, 2), (0, 3), (1, 2), (1, 3), (2, 3)]


def _eq(A, B):  # (m,4),(n,4) -> (m,n,4)
    return A[:, None, :] == B[None, :, :]


def kernel(A, B, w_add=0.35, w_pair=0.25, w_ham=0.40, rho=0.45):
    eq = _eq(A, B)
    k_add = eq.sum(-1) / 4.0
    k_pair = sum((eq[..., i] & eq[..., j]) for i, j in PAIRS) / 6.0
    k_ham = rho ** (4 - eq.sum(-1))
    return w_add * k_add + w_pair * k_pair + w_ham * k_ham


class GPModel:
    name = "gp"

    def __init__(self, noise=0.15, prior=None):
        self.noise, self.prior = noise, prior  # prior: optional (160000,) float array of external prior means (score units)
        self.n = 0; self.cache = {}

    def fit(self, nodes, scores):
        X = digits(np.asarray(nodes)); y = np.asarray(scores, float) / UNITS
        self.X = X
        pm = self._pm(nodes)
        self.mean0 = float(np.mean(y - pm)) if len(y) else 0.0
        self.sf2 = max(float(np.var(y)), 1e-4)
        K = self.sf2 * kernel(X, X) + self.noise * self.sf2 * np.eye(len(y))
        self.c = cho_factor(K, lower=True)
        self.alpha = cho_solve(self.c, y - pm - self.mean0)
        self.cache = {}; self.n = len(y)

    def _pm(self, nodes):
        return 0.0 if self.prior is None else np.asarray(self.prior)[np.asarray(nodes)].astype(float)

    def predict(self, nodes):
        nodes = np.asarray(nodes, np.int64)
        miss = [int(v) for v in nodes if int(v) not in self.cache]
        if miss:
            m = np.array(miss)
            Ks = self.sf2 * kernel(digits(m), self.X)
            mu = Ks @ self.alpha + self.mean0 + self._pm(m)
            V = solve_triangular(self.c[0], Ks.T, lower=True)
            var = np.maximum(self.sf2 * 1.0 - (V ** 2).sum(0), 1e-8) + self.noise * self.sf2
            for v, a, b in zip(miss, mu, np.sqrt(var)):
                self.cache[v] = (float(a), float(b))
        r = np.array([self.cache[int(v)] for v in nodes])
        return r[:, 0], r[:, 1]


class LocalModel:
    name = "local"

    def __init__(self, shrink=1.0, prior=None):
        self.shrink, self.prior = shrink, prior
        self.cache = {}

    def fit(self, nodes, scores):
        self.X = digits(np.asarray(nodes)); self.y = np.asarray(scores, float) / UNITS
        self.m0 = float(np.median(self.y)) if len(self.y) else 0.0
        self.sd0 = max(float(np.std(self.y)), 1e-3)
        self.cache = {}

    def predict(self, nodes):
        nodes = np.asarray(nodes, np.int64)
        miss = [int(v) for v in nodes if int(v) not in self.cache]
        if miss:
            m = np.array(miss)
            d = (digits(m)[:, None, :] != self.X[None, :, :]).sum(-1)      # (m,n)
            w = np.where(d == 1, 1.0, np.where(d == 2, 0.25, 0.0))
            sw = w.sum(1)
            base = self.m0 if self.prior is None else np.asarray(self.prior)[m]
            mu = (w @ self.y + self.shrink * base) / (sw + self.shrink)
            var = (self.sd0 ** 2) / (sw + self.shrink)
            sd = np.sqrt(var + 0.25 * self.sd0 ** 2 * (sw > 0) * 0)  # shrinks with local evidence
            for v, a, b in zip(miss, np.atleast_1d(mu), sd):
                self.cache[v] = (float(a), float(b))
        r = np.array([self.cache[int(v)] for v in nodes])
        return r[:, 0], r[:, 1]


class ConstModel:
    """Ablation: no learned surrogate.  Every unrevealed genotype is predicted with the pooled
    mean/sd of the revealed scores, so the planner can only use revealed facts and route/cut
    structure (number of unknown nodes, Hamming geometry)."""
    name = "const"

    def __init__(self, prior=None):
        self.prior = prior
        self.m, self.sd = 0.0, 0.02

    def fit(self, nodes, scores):
        y = np.asarray(scores, float) / UNITS
        self.m, self.sd = float(np.median(y)), max(float(np.std(y)), 1e-3)

    def predict(self, nodes):
        n = len(np.atleast_1d(nodes))
        return np.full(n, self.m), np.full(n, self.sd)
