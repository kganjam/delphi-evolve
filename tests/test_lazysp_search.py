"""Search-level tests: A* optimistic shortest path vs an INDEPENDENT exhaustive BFS.

All graphs here are logic fixtures (random tiny digraphs / hand-set masks), never measurements."""
import itertools
import time
from collections import deque

import numpy as np

from baselines.lazysp.search import shortest_optimistic_path
from baselines.lazysp.policy import neighbors_py, hamming_table
from evolve import data


def test_identical_endpoint_must_still_be_available():
    for available in (False, True):
        path, stats, aborted = shortest_optimistic_path(
            7, 7, lambda _: [], lambda _: 0, lambda u, v: True, lambda _: available)
        assert path == ([7] if available else None)
        assert stats["expansions"] == 0 and not aborted


def tiny_graph(dims=(3, 3, 3)):
    nodes = list(itertools.product(*[range(d) for d in dims]))
    adj = {u: [v for v in nodes if sum(a != b for a, b in zip(u, v)) == 1] for u in nodes}
    return nodes, adj


def bfs_len(adj, blocked_edges, absent, s, t):
    """Independent exhaustive BFS (explicit adjacency, plain deque)."""
    if s in absent or t in absent:
        return None
    dist = {s: 0}; q = deque([s])
    while q:
        u = q.popleft()
        for v in adj[u]:
            if v in absent or (u, v) in blocked_edges or v in dist:
                continue
            dist[v] = dist[u] + 1; q.append(v)
    return dist.get(t)


def test_matches_exhaustive_bfs_on_random_tiny_graphs():
    nodes, adj = tiny_graph()
    rng = np.random.default_rng(7)
    idx = {n: i for i, n in enumerate(nodes)}
    n_none = n_path = n_detour = 0
    for trial in range(400):
        s, t = (nodes[i] for i in rng.choice(len(nodes), 2, replace=False))
        pe = rng.choice([0.0, 0.3, 0.6, 0.8])
        blocked = {(u, v) for u in nodes for v in adj[u] if rng.random() < pe}
        absent = {n for n in nodes if rng.random() < pe / 3} - {s, t}
        ham = lambda n: sum(a != b for a, b in zip(n, t))
        path, st, aborted = shortest_optimistic_path(
            s, t, lambda u: adj[u], ham, lambda u, v: (u, v) not in blocked, lambda v: v not in absent)
        ref = bfs_len(adj, blocked, absent, s, t)
        assert not aborted
        if ref is None:
            assert path is None; n_none += 1
        else:
            assert path is not None and len(path) - 1 == ref
            assert path[0] == s and path[-1] == t
            assert all(path[i + 1] in adj[path[i]] and (path[i], path[i + 1]) not in blocked and path[i + 1] not in absent for i in range(len(path) - 1))
            n_path += 1; n_detour += ref > ham(s)
    assert n_none > 10 and n_path > 100 and n_detour > 5     # all three regimes were actually exercised


def test_deterministic_tiebreak():
    nodes, adj = tiny_graph((3, 3, 3, 3))
    s, t = (0, 0, 0, 0), (2, 2, 2, 2)
    ham = lambda n: sum(a != b for a, b in zip(n, t))
    args = (s, t, lambda u: adj[u], ham, lambda u, v: True, lambda v: True)
    p1 = shortest_optimistic_path(*args)[0]; p2 = shortest_optimistic_path(*args)[0]
    assert p1 == p2 and len(p1) == 5


def test_detour_away_from_target_is_found():
    """Direct edges blocked: the only route first INCREASES Hamming distance to the target."""
    nodes, adj = tiny_graph((3, 3, 3))
    s, t = (0, 0, 0), (1, 0, 0)
    chain = [(0, 0, 0), (0, 0, 1), (1, 0, 1), (1, 0, 0)]
    allowed = set(zip(chain, chain[1:]))
    ham = lambda n: sum(a != b for a, b in zip(n, t))
    path, _, _ = shortest_optimistic_path(s, t, lambda u: adj[u], ham, lambda u, v: (u, v) in allowed, lambda v: True)
    assert path == chain and len(path) - 1 > ham(s)


def test_deadline_is_abstention_not_no_path():
    # no path exists, graph is the full 20^4 space (>1024 expansions needed to prove it)
    s, t = 0, 159999
    path, st, aborted = shortest_optimistic_path(s, t, neighbors_py, lambda v: 0, lambda u, v: False if u == s else True,
                                                 lambda v: True, deadline=time.monotonic() - 1)
    assert path is None and aborted is False   # start has no outgoing edge: exhausted legitimately (proof of no path)
    # now a start that can expand widely but a sealed target
    h = hamming_table(t)
    path, st, aborted = shortest_optimistic_path(s, t, neighbors_py, lambda v: 0, lambda u, v: v != t, lambda v: True,
                                                 deadline=time.monotonic() - 1)
    assert path is None and aborted is True and st["expansions"] >= 1024


def test_real_graph_matches_numpy_bfs_with_random_blocks():
    """20^4 graph, ~300 random 'revealed' vertices with random intervals; compare against an independent numpy layered BFS."""
    rng = np.random.default_rng(11)
    for trial in range(3):
        known = rng.choice(data.N_GENO, 300, replace=False)
        lo = {int(v): int(x) for v, x in zip(known, rng.integers(0, 1000, 300))}
        hi = {v: lo[v] + int(rng.integers(0, 600)) for v in lo}
        absent = set(int(x) for x in rng.choice(data.N_GENO, 200, replace=False)) - set(lo)
        s = int(known[0]); t = int(known[1])
        ok = lambda u, w: not (u in lo and w in lo) or lo[w] >= hi[u]
        path, _, _ = shortest_optimistic_path(s, t, neighbors_py, lambda v: int(data.hamming(v, t)), ok, lambda v: v not in absent)
        # independent layered BFS on the full index space
        alive = np.ones(data.N_GENO, bool); alive[list(absent)] = False
        dist = np.full(data.N_GENO, -1); dist[s] = 0; fr = np.array([s]); d = 0
        while fr.size and dist[t] < 0:
            d += 1
            nb = data.neighbors(fr)
            src = np.repeat(fr, 76); dst = nb.ravel()
            good = alive[dst] & (dist[dst] < 0)
            keep = np.array([ok(int(a), int(b)) if good[i] else False for i, (a, b) in enumerate(zip(src, dst))])
            dst = np.unique(dst[keep]); dist[dst] = d; fr = dst
        assert (path is None and dist[t] < 0) or (path is not None and len(path) - 1 == dist[t])
        assert path is not None
