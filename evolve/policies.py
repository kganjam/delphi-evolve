"""Query policies for matched-budget retrospective replay.

All policies share ONE soundness path: certificates are computed from revealed
labels only (graph.Ledger).  Policies differ only in WHICH unrevealed genotype
they spend the next assay on.  None sees unqueried labels.

random      uniform over the unknown frontier (competent random: global random
            would almost never touch the closure)
greedy      measured-neighbour walk: assay unknown neighbours of the highest-scoring
            reachable genotype (target-agnostic hill climbing)
uncertainty GP predictive-sd acquisition over the frontier
directed    deterministic single policy, no learned model: best-first toward the
            target by Hamming distance (ties: parent score, then index)
q2c         single-brain query-to-certify: GP-predicted open-route vs cut cost
collective_shared / collective_isolated   see collective.py
"""
from __future__ import annotations

import itertools
import math

import numpy as np
from scipy.special import ndtr

from .data import UNITS, digits, hamming
from .model import ConstModel, GPModel, LocalModel

REFIT = 16
POOL = 400


def phi(z):
    return ndtr(z)


class Base:
    name = "base"

    def __init__(self, ctx, rng):
        self.ctx, self.rng = ctx, rng

    def step(self, oracle, ledger) -> bool:  # perform one query; False => no admissible query
        raise NotImplementedError

    def ask(self, oracle, ledger, v, why):
        rec = oracle.query(v, self.name, why)
        ledger.reveal(int(v), rec)
        return rec


def frontier_array(ledger):
    return np.fromiter(ledger.frontier.keys(), np.int64, len(ledger.frontier))


class RandomFrontier(Base):
    name = "random"

    def step(self, oracle, ledger):
        keys = list(ledger.frontier.keys())
        if not keys:
            return False
        self.ask(oracle, ledger, keys[int(self.rng.integers(len(keys)))], "uniform frontier")
        return True


class _Pooled(Base):
    """Pool of preferred frontier nodes refreshed every REFIT queries."""

    def __init__(self, ctx, rng):
        super().__init__(ctx, rng)
        self.pool, self.age = [], REFIT

    def rank(self, ledger, F):  # return ordered list of candidate nodes (best first)
        raise NotImplementedError

    def step(self, oracle, ledger):
        self.pool = [v for v in self.pool if v in ledger.frontier]
        if not self.pool or self.age >= REFIT:
            F = frontier_array(ledger)
            if F.size == 0:
                return False
            self.pool = list(self.rank(ledger, F))[:POOL]; self.age = 0
        if not self.pool:
            return False
        v = self.pool.pop(0); self.age += 1
        self.ask(oracle, ledger, v, self.why)
        return True

    why = ""


def _best_parent_hi(ledger, v):
    return max(ledger.obs[u][2] for u in ledger.frontier[v])


class Greedy(_Pooled):
    name = "greedy"; why = "neighbour of highest-scoring reachable genotype"

    def rank(self, ledger, F):
        sc = np.array([_best_parent_hi(ledger, int(v)) for v in F])
        order = np.lexsort((F, -sc))
        return F[order[:POOL]].tolist()


class Directed(_Pooled):
    name = "directed"; why = "Hamming-closest unknown neighbour to target"

    def rank(self, ledger, F):
        h = hamming(F, self.ctx.target)
        cut = np.argsort(h, kind="stable")[: 8 * POOL]
        Fc, hc = F[cut], h[cut]
        sc = np.array([_best_parent_hi(ledger, int(v)) for v in Fc])
        order = np.lexsort((Fc, -sc, hc))
        return Fc[order].tolist()


class Uncertainty(_Pooled):
    name = "uncertainty"; why = "max GP predictive sd on frontier"

    def __init__(self, ctx, rng):
        super().__init__(ctx, rng)
        self.gp = GPModel(prior=ctx.prior)

    def rank(self, ledger, F):
        if len(F) > 3 * POOL:
            F = self.rng.choice(F, 3 * POOL, replace=False)
        nodes = list(ledger.obs)
        self.gp.fit(nodes, [ledger.obs[v][2] for v in nodes])
        _, sd = self.gp.predict(F)
        order = np.lexsort((F, -sd))
        return F[order].tolist()


# ---------------------------------------------------------------- planners
class Planner:
    """Open-route and cut cost planning from a ledger and a surrogate model."""

    def __init__(self, ctx, ledger, model):
        self.ctx, self.ledger, self.model = ctx, ledger, model
        self.n_fit = -1

    def sync(self):
        n = len(self.ledger.obs)
        if self.n_fit < 0 or n - self.n_fit >= REFIT:
            nodes = list(self.ledger.obs)
            self.model.fit(nodes, [self.ledger.obs[v][2] for v in nodes])
            self.n_fit = n

    # --- edge probability under model
    def _stats(self, nodes, cache):
        need = [v for v in nodes if v not in self.ledger.obs and v not in cache and v not in self.ledger.absent]
        if need:
            mu, sd = self.model.predict(np.array(need))
            for v, a, b in zip(need, mu, sd):
                cache[v] = (a * UNITS, b * UNITS)

    def edge_p(self, u, w, cache):
        L = self.ledger
        if w in L.absent or u in L.absent:
            return 0.0
        eps = self.ctx.eps_typ
        ku, kw = u in L.obs, w in L.obs
        if ku and kw:
            return 1.0 if L.obs[w][0] >= L.obs[u][1] else 0.0
        if ku:
            mu, sd = cache[w]; return float(phi((mu - eps - L.obs[u][1]) / sd))
        if kw:
            mu, sd = cache[u]; return float(phi((L.obs[w][0] - mu - eps) / sd))
        (m1, s1), (m2, s2) = cache[u], cache[w]
        return float(phi((m2 - m1 - 2 * eps) / math.hypot(s1, s2)))

    # --- open-route candidates
    def open_routes(self, topk=5, members=40):
        L = self.ledger; t = self.ctx.target
        C = np.fromiter(L.closure.keys(), np.int64, len(L.closure))
        h = hamming(C, t)
        sc = np.array([L.obs[int(v)][2] for v in C])
        order = np.lexsort((C, -sc, h))[:members]
        routes, nodes = [], set()
        for ci in order:
            u = int(C[ci])
            du, dt = digits(u), digits(t)
            pos = [p for p in range(4) if du[p] != dt[p]]
            for perm in itertools.permutations(pos):
                cur = du.copy(); path = [u]
                for p in perm:
                    cur[p] = dt[p]
                    path.append(int(((cur[0] * 20 + cur[1]) * 20 + cur[2]) * 20 + cur[3]))
                if path[-1] != t or any(x in L.absent for x in path):
                    continue
                routes.append(path); nodes.update(path)
        cache = {}
        self._stats(nodes, cache)
        scored = []
        for path in routes:
            ps = [self.edge_p(path[i], path[i + 1], cache) for i in range(len(path) - 1)]
            P = float(np.prod(ps))
            if P <= 0:
                continue
            unk = [v for v in path if v not in L.obs]
            if not unk:
                continue
            scored.append({"nodes": path, "unknown": unk, "p_edges": ps, "p": P, "cost": len(unk), "score": len(unk) / P})
        scored.sort(key=lambda r: (r["score"], r["nodes"]))
        return scored[:topk], cache

    @staticmethod
    def next_on_route(route, ledger):
        """fail-fast: assay the unknown node adjacent to the weakest edge."""
        path, ps = route["nodes"], route["p_edges"]
        best = None
        for i, p in enumerate(ps):
            for v in (path[i], path[i + 1]):
                if v not in ledger.obs and (best is None or p < best[0]):
                    best = (p, v)
        return best[1] if best else None

    # --- cut planning
    def frontier_probs(self, k=POOL):
        L = self.ledger
        F = frontier_array(L)
        if F.size == 0:
            return F, np.array([]), 0.0
        h = hamming(F, self.ctx.target)
        sel = F[np.argsort(h, kind="stable")[:k]] if F.size > k else F
        cache = {}
        self._stats(sel.tolist(), cache)
        eps = self.ctx.eps_typ
        P = np.array([max(phi((cache[int(w)][0] - eps - L.obs[u][1]) / cache[int(w)][1]) for u in L.frontier[int(w)]) for w in sel])
        mean_p = float(P.mean())
        return sel, P, mean_p

    def block_cost(self):
        """Heuristic expected assays to close the cut: every frontier genotype must be
        assayed, and each admissible one (prob. ~ mean_p) opens up to 75 new neighbours."""
        F = len(self.ledger.frontier)
        sel, P, mp = self.frontier_probs()
        return F * (1.0 + 75.0 * mp), sel, P


class Q2C(Base):
    """Single-brain query-to-certify: choose the cheaper of open-route falsification
    and cut completion under one GP surrogate sharing all revealed evidence."""
    name = "q2c"

    def __init__(self, ctx, rng, model=None):
        super().__init__(ctx, rng)
        self.model = model or GPModel(prior=ctx.prior)
        self.pl = None

    def step(self, oracle, ledger):
        if self.pl is None:
            self.pl = Planner(self.ctx, ledger, self.model)
        pl = self.pl; pl.sync()
        if not ledger.frontier:
            return False
        routes, _ = pl.open_routes()
        bc, sel, P = pl.block_cost()
        use_open = bool(routes) and routes[0]["score"] <= bc
        if use_open:
            v = pl.next_on_route(routes[0], ledger); why = f"open route p={routes[0]['p']:.3g} unknown={routes[0]['cost']}"
        else:
            v = int(sel[int(np.argmax(P))]); why = f"cut completion frontier={len(ledger.frontier)}"
        if v is None or v in oracle.queried:
            v = int(sel[int(np.argmax(P))])
        self.ask(oracle, ledger, v, why)
        return True


class Q2CNoModel(Q2C):
    """Ablation of q2c: identical planner/arbitration, constant surrogate instead of the GP."""
    name = "q2c_nomodel"

    def __init__(self, ctx, rng):
        super().__init__(ctx, rng, model=ConstModel())
