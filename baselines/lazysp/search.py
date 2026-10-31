"""Exact optimistic shortest-path search used by the LazySP baseline.

This module is graph-agnostic on purpose so that it can be validated against an independent
exhaustive BFS on tiny graphs (tests/test_lazysp_search.py).  It never sees fitness labels: the
caller supplies `edge_ok` / `node_ok` predicates that encode ONLY what has been revealed.

Search = A* on unit edge weights (LazySP's `w_est(e) = 1` for every unevaluated edge) with a
caller-supplied heuristic that must be consistent (|h(u)-h(v)| <= 1 for every edge u->v and
h(target)=0).  For the TrpB graph h is the Hamming distance to the target, which is a true lower
bound because each edge changes exactly one position.  The search is exact: it either returns a
shortest path of the optimistic graph or proves none exists (heap exhaustion).  There is no
expansion cap; the only early exit is an optional wall-clock `deadline`, which is reported as an
`aborted` flag and must be treated as an abstention, never as "no path".

Deterministic tie-breaking: heap key = (f, h, node index); neighbours are expanded in ascending
index order; a node's parent only changes on a STRICT improvement of g.
"""
from __future__ import annotations

import heapq
import time
from typing import Callable, Iterable, Optional


def shortest_optimistic_path(
    start: int,
    target: int,
    neighbors: Callable[[int], Iterable[int]],
    heuristic: Callable[[int], int],
    edge_ok: Callable[[int, int], bool],
    node_ok: Callable[[int], bool],
    deadline: Optional[float] = None,
):
    """Return (path | None, stats, aborted).

    path is a list of nodes start..target; None with aborted=False is a PROOF that no path
    exists in the optimistic graph; aborted=True means the wall-clock deadline was hit (unknown).
    """
    stats = {"expansions": 0, "generated": 0}
    if not node_ok(start) or not node_ok(target):
        return None, stats, False
    if start == target:
        return [start], stats, False
    g = {start: 0}
    parent = {start: -1}
    heap = [(heuristic(start), heuristic(start), start)]
    closed = set()
    while heap:
        f, h, u = heapq.heappop(heap)
        if u in closed:
            continue
        if u == target:
            path = [u]
            while parent[path[-1]] != -1:
                path.append(parent[path[-1]])
            return path[::-1], stats, False
        closed.add(u)
        stats["expansions"] += 1
        if deadline is not None and (stats["expansions"] & 1023) == 0 and time.monotonic() > deadline:
            return None, stats, True
        gu = g[u] + 1
        for w in sorted(neighbors(u)):
            if w in closed or not node_ok(w) or not edge_ok(u, w):
                continue
            stats["generated"] += 1
            old = g.get(w)
            if old is None or gu < old:
                g[w] = gu
                parent[w] = u
                hw = heuristic(w)
                heapq.heappush(heap, (gu + hw, hw, w))
    return None, stats, False
