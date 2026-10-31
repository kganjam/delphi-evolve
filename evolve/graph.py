"""Admissible-edge reachability over the declared measured graph.

Edge rule (CONTRACT / PLAN 6): u -> v (single substitution) is ADMISSIBLE iff
Lo[v] >= Hi[u], all integer micro-units.  Under interval containment this implies
score(v) >= score(u).  Graph scope: the measured subgraph G_meas of the 20^4
library (159,129 of 160,000 genotypes).  Unmeasured genotypes are outside the
declared scope; certificates say nothing about paths through them.
"""
from __future__ import annotations

import numpy as np

from .data import N_GENO, neighbors


def truth_bfs(meas, Lo, Hi, start: int):
    """Full-information forward admissible closure of `start`. Returns (reached bool,
    parent int32, depth int16)."""
    reached = np.zeros(N_GENO, bool); parent = np.full(N_GENO, -1, np.int32); depth = np.full(N_GENO, -1, np.int16)
    reached[start] = True; depth[start] = 0
    frontier = np.array([start]); d = 0
    while frontier.size:
        d += 1
        nb = neighbors(frontier)                       # (F,76)
        src = np.repeat(frontier, 76); dst = nb.ravel()
        ok = meas[dst] & ~reached[dst] & (Lo[dst] >= Hi[src])
        src, dst = src[ok], dst[ok]
        if not dst.size:
            break
        uniq, first = np.unique(dst, return_index=True)
        reached[uniq] = True; parent[uniq] = src[first]; depth[uniq] = d
        frontier = uniq
    return reached, parent, depth


def path_to(parent, start, target):
    p = [int(target)]
    while p[-1] != start:
        p.append(int(parent[p[-1]]))
        if p[-1] < 0:
            return None
    return p[::-1]


def edge_status(meas, Lo, Hi, u, v):
    if not meas[u] or not meas[v]:
        return "unknown"
    return "admissible" if Lo[v] >= Hi[u] else "inadmissible"


class Ledger:
    """Policy-visible state: revealed observations only, plus an incrementally
    maintained forward closure and its unknown frontier.

    obs: idx -> (lo, hi, s)  for measured nodes;  absent: idx set revealed as outside scope.
    closure: nodes reachable from `start` via admissible edges between revealed nodes.
    frontier: UNREVEALED neighbours of closure members (their status is unknown);
        frontier_parents[w] = closure members adjacent to w.
    status(): 'open' if target in closure; 'blocked' if frontier empty (closed set,
    target outside); else 'unresolved'.
    """

    def __init__(self, start: int, target: int):
        self.start, self.target = start, target
        self.obs: dict[int, tuple[int, int, int]] = {}
        self.absent: set[int] = set()
        self.closure: dict[int, int] = {}   # node -> parent (for route reconstruction)
        self.frontier: dict[int, set[int]] = {}
        self._nb: dict[int, list[int]] = {}

    def nbrs(self, u):
        r = self._nb.get(u)
        if r is None:
            r = self._nb[u] = neighbors(np.int64(u)).tolist()
        return r

    def known(self, v):
        return v in self.obs or v in self.absent

    def reveal(self, v, rec):
        """rec = (lo, hi, s) or None (absent from scope)."""
        if rec is None:
            self.absent.add(v)
            self.frontier.pop(v, None)
            return
        self.obs[v] = rec
        parents = self.frontier.pop(v, None)
        if v == self.start and not self.closure:
            self._join(v, -1)
            return
        if self.closure and parents:
            for u in parents:
                if rec[0] >= self.obs[u][1]:
                    self._join(v, u)
                    break
        elif self.closure:
            # v may be adjacent to closure members only via frontier, which we popped; nothing
            pass

    def _join(self, v, parent):
        stack = [(v, parent)]
        while stack:
            x, p = stack.pop()
            if x in self.closure:
                continue
            self.closure[x] = p
            hi = self.obs[x][1]
            for w in self.nbrs(x):
                if w in self.closure or w in self.absent:
                    continue
                if w in self.obs:
                    if self.obs[w][0] >= hi:
                        stack.append((w, x))
                else:
                    self.frontier.setdefault(w, set()).add(x)

    def status(self):
        if self.target in self.closure:
            return "open"
        if self.closure and not self.frontier:
            return "blocked"
        return "unresolved"

    def route(self):
        if self.target not in self.closure:
            return None
        p = [self.target]
        while self.closure[p[-1]] != -1:
            p.append(self.closure[p[-1]])
        return p[::-1]

    def cut(self):
        """Closed set (closure) and boundary edges justifying a blocked status."""
        assert self.status() == "blocked"
        S = set(self.closure)
        out = []
        for u in S:
            for w in self.nbrs(u):
                if w in S:
                    continue
                out.append((u, w, "absent" if w in self.absent else "inadmissible"))
        return S, out


def verify_route(meas, Lo, Hi, route) -> bool:
    from .data import hamming
    if len(route) < 1 or any(not meas[v] for v in route):
        return False
    return all(int(hamming(route[i], route[i + 1])) == 1 and Lo[route[i + 1]] >= Hi[route[i]] for i in range(len(route) - 1))


def verify_cut(meas, Lo, Hi, S, start, target) -> bool:
    """Independent re-check of a closed set against FULL data (used by tests/audits only)."""
    if start not in S or target in S:
        return False
    for u in S:
        if not meas[u]:
            return False
        for w in neighbors(np.int64(u)).tolist():
            if w in S or not meas[w]:
                continue
            if Lo[w] >= Hi[u]:
                return False
    return True
