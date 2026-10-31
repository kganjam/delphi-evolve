"""LazySP-style policy for the TrpB query-to-certify benchmark (node-query adaptation).

Reference: Dellin & Srinivasa, "A Unifying Formulation for the Lazy Shortest-Path family of
algorithms" (LazySP), ICAPS 2016 [https://www.ri.cmu.edu/pub_files/2016/3/paper-lazysp.pdf];
related decision-region work: Choudhury et al., IJCAI 2018 [https://ijcai.org/proceedings/2018/679].

What is faithful
  * Optimistic graph: every single-substitution edge u->v of the declared 20^4 graph has estimated
    weight w_est = 1 until evaluated; an evaluated edge has weight 1 if ADMISSIBLE
    (Lo[v] >= Hi[u], the core ledger's rule) and +inf otherwise.
  * Loop (LazySP Algorithm 1): shortest candidate path under w_lazy from `start` to `target`;
    if every edge on it is evaluated (and admissible) the path is returned (here: the shared
    ledger reports `open`, and the replay loop stops); otherwise an edge selector picks edges to
    evaluate, they are evaluated through the SAME paid-query oracle, and the search repeats.
  * Selectors Forward / Reverse / Alternate with the paper's definitions (Algorithm 2).
  * The shortest-path step is exact (A*, Hamming lower bound); no pruning, no beam, no cap.

Node-query adaptation (NOT in the source papers)
  The prior art prices EDGE evaluations.  Here the only paid action is a genotype assay, which
  reveals a vertex interval; an edge becomes evaluated when BOTH of its endpoints are revealed
  (free once the second endpoint arrives).  Because the path starts at a revealed vertex (start)
  and ends at one (target), the first unevaluated edge of a path always has a revealed tail and an
  unrevealed head, and the last unevaluated edge has an unrevealed tail and a revealed head, so:
      Forward  -> assay the FIRST unrevealed vertex on the candidate path,
      Reverse  -> assay the LAST unrevealed vertex on the candidate path,
      Alternate-> Forward on odd LazySP iterations, Reverse on even ones.
  One assay may evaluate two edges at once (both neighbours on the path).  An assay that returns
  "outside the measured scope" (absent) removes that vertex from the graph and costs one assay,
  exactly like every other policy.  Unrevealed vertices are always optimistic: the baseline has NO
  access to the declared measured mask, only to what assays have revealed.

Caching note (equivalence with re-planning every iteration)
  The optimistic edge set only ever SHRINKS as vertices are revealed.  A candidate path that is
  still fully optimistic therefore remains a shortest path (its length is unchanged and it is
  still in the feasible set), so we keep it and only re-run the search when an observation
  invalidates it.  LazySP permits arbitrary tie-breaking among shortest paths, and keeping the
  incumbent is one admissible tie-break.  The iteration counter that drives Alternate still
  advances once per assay (= one LazySP iteration).

Objective semantics
  Certificates are the core ledger's: `open` (a route of conservative admissible edges among
  revealed vertices) or `blocked` (the revealed admissible closure of start is closed and omits
  target).  `blocked` means NO CONSERVATIVELY-ADMISSIBLE ROUTE in the declared measured graph; it
  does NOT mean biological impossibility, nor that no ascending route exists for every assignment
  inside the intervals (specs/CONTRACT.md; tasks/semantics-review.md).

Native infeasibility
  If the optimistic graph itself disconnects start from target while the ledger is still
  unresolved (possible when the target side is sealed off first), the optimistic search has PROVED
  there is no admissible route.  The ledger would still need its own closed set, so the policy
  records `native_infeasible_at` and then spends assays only on the ledger's unknown frontier
  (ordered by Hamming distance to target, then index) until the ledger certifies.  Those queries
  are labelled `fallback_after_native_infeasible`.
"""
from __future__ import annotations

import time

import numpy as np

from evolve.policies import Base

SELECTORS = ("forward", "reverse", "alternate")
_POW = (8000, 400, 20, 1)


def neighbors_py(u: int):
    """76 single-substitution neighbours of genotype index u (pure python, same set as evolve.data.neighbors)."""
    out = []
    for pw in _POW:
        d = (u // pw) % 20
        base = u - d * pw
        out.extend(base + a * pw for a in range(20) if a != d)
    return out


def hamming_table(target: int) -> list:
    """Hamming distance of every genotype index to target (computed from indices only)."""
    idx = np.arange(20 ** 4)
    t = [(target // pw) % 20 for pw in _POW]
    h = np.zeros(idx.shape, np.int64)
    for pw, td in zip(_POW, t):
        h += ((idx // pw) % 20 != td)
    return h.tolist()


class LazySP(Base):
    name = "lazysp"

    def __init__(self, ctx, rng, selector="alternate", runtime_cap_s=None, neighbors=neighbors_py, heuristic=None):
        super().__init__(ctx, rng)
        if selector not in SELECTORS:
            raise ValueError(selector)
        self.selector = selector
        self.name = f"lazysp_{selector}"
        self.cap = runtime_cap_s
        self.t0 = time.monotonic()
        self.neighbors = neighbors
        self._h = None if heuristic is not None else hamming_table(ctx.target)
        self.heuristic = heuristic or (lambda v: self._h[v])
        self.path = None
        self.iteration = 0
        self.native_infeasible_at = None
        self.abort_reason = None
        self.stats = {"replans": 0, "expansions": 0, "search_wall_s": 0.0, "fallback_queries": 0,
                      "first_path_len": None, "max_path_len": 0}

    # ------------------------------------------------------------------ helpers
    def _path_valid(self, ledger):
        p = self.path
        if p is None:
            return False
        obs, absent = ledger.obs, ledger.absent
        for i, v in enumerate(p):
            if v in absent:
                return False
            if i and v in obs and p[i - 1] in obs and obs[v][0] < obs[p[i - 1]][1]:
                return False
        return True

    def _search(self, ledger):
        from .search import shortest_optimistic_path
        obs, absent = ledger.obs, ledger.absent

        def edge_ok(u, w):
            ou = obs.get(u)
            if ou is None:
                return True
            ow = obs.get(w)
            return ow is None or ow[0] >= ou[1]

        deadline = None if self.cap is None else self.t0 + self.cap
        t = time.monotonic()
        path, st, aborted = shortest_optimistic_path(
            self.ctx.start, self.ctx.target, self.neighbors, self.heuristic,
            edge_ok, lambda v: v not in absent, deadline)
        self.stats["search_wall_s"] += time.monotonic() - t
        self.stats["expansions"] += st["expansions"]
        self.stats["replans"] += 1
        return path, aborted

    def _pick(self, unknown):
        sel = self.selector
        if sel == "alternate":
            sel = "forward" if self.iteration % 2 == 1 else "reverse"
        return unknown[0] if sel == "forward" else unknown[-1]

    # ------------------------------------------------------------------ policy API
    def step(self, oracle, ledger):
        self.iteration += 1
        if self.cap is not None and time.monotonic() - self.t0 > self.cap:
            self.abort_reason = "runtime_bound"
            return False
        if self.native_infeasible_at is None and not self._path_valid(ledger):
            path, aborted = self._search(ledger)
            if aborted:
                self.abort_reason = "runtime_bound"
                return False
            self.path = path
            if path is None:
                self.native_infeasible_at = oracle.n_queries
            else:
                n = len(path) - 1
                if self.stats["first_path_len"] is None:
                    self.stats["first_path_len"] = n
                self.stats["max_path_len"] = max(self.stats["max_path_len"], n)
        if self.native_infeasible_at is not None:
            F = list(ledger.frontier)
            if not F:
                self.abort_reason = "no_frontier"
                return False
            v = min(F, key=lambda x: (self.heuristic(x), x))
            self.stats["fallback_queries"] += 1
            self.ask(oracle, ledger, v, "fallback_after_native_infeasible")
            return True
        unknown = [v for v in self.path if v not in ledger.obs]
        if not unknown:
            raise RuntimeError("fully evaluated admissible candidate path but ledger not open (invariant violated)")
        v = self._pick(unknown)
        self.ask(oracle, ledger, v, f"lazysp:{self.selector}:len={len(self.path) - 1}:unk={len(unknown)}")
        return True
