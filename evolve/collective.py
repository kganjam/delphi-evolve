"""Runtime specialist collective for query-to-certify.

Specialists (separate objects, each with its own surrogate and view of evidence):
  data     gatekeeper: sole holder of the oracle, budget and the certificate ledger;
           reveals only observed labels; refuses duplicate assays.
  route    proposes the next assay to confirm/falsify the best open route (GP model A).
  cut      proposes the next assay to complete a closed set (local model B).
  critic   (shared mode only) re-prices the route specialist's candidate routes with the
           cut specialist's model; a route that survives only under one model is
           demoted ("challenge").  Its output changes which assay is bought.
  arbiter  data specialist; compares open-route and cut cost estimates.

shared   : every specialist reads the one global ledger (all reveals) and posts
           proposals/challenges visible to all.
isolated : route and cut specialists keep PRIVATE ledgers + models fed only by assays
           they themselves caused; they alternate turns; no cross-reading.  The data
           specialist still pools all reveals for certification (a certificate needs the
           union of facts), and a duplicate request is answered from that ledger for
           free (logged) -- the only leak in the isolated arm.

This is a runtime decision protocol inside one Python process: the decisions are made
by distinct specialist objects, but scheduling/arbitration is fixed software, not an
independent-agent market.  See artifacts/core/README.md for what this does and does not show.
"""
from __future__ import annotations

import numpy as np

from .graph import Ledger
from .model import GPModel, LocalModel
from .policies import Base, Planner


class Collective(Base):
    def __init__(self, ctx, rng, shared=True):
        super().__init__(ctx, rng)
        self.shared = shared
        self.name = "collective_shared" if shared else "collective_isolated"
        self.pl = {}
        self.turn = 0
        self.priv = None

    # -- helpers
    def _planner(self, role, ledger, model):
        if role not in self.pl:
            self.pl[role] = Planner(self.ctx, ledger, model)
        return self.pl[role]

    def _post(self, oracle, type_, actor, visible_to, **kw):
        oracle.log.emit(type_, actor, visible_to=visible_to, **kw)

    def _init_private(self, ledger):
        if self.priv is None:
            self.priv = {}
            for role in ("route", "cut"):
                L = Ledger(self.ctx.start, self.ctx.target)
                for v, rec in ledger.obs.items():
                    L.reveal(v, rec)
                self.priv[role] = L

    # -- main
    def step(self, oracle, ledger):
        if not ledger.frontier:
            return False
        return self._shared_step(oracle, ledger) if self.shared else self._isolated_step(oracle, ledger)

    def _shared_step(self, oracle, ledger):
        plA = self._planner("route", ledger, GPModel(prior=self.ctx.prior))
        plB = self._planner("cut", ledger, LocalModel(prior=self.ctx.prior))
        plA.sync(); plB.sync()
        routes, _ = plA.open_routes()
        bcA, selA, PA = plA.block_cost()
        bcB, selB, PB = plB.block_cost()
        bc = 0.5 * (bcA + bcB)
        route_pick = None
        if routes:
            r0 = routes[0]
            self._post(oracle, "proposal", "route", "all", hyp="open", route=r0["nodes"], p=r0["p"], score=r0["score"])
            cacheB = {}
            plB._stats({v for r in routes for v in r["nodes"]}, cacheB)
            best = None
            for r in routes:
                pB = float(np.prod([plB.edge_p(r["nodes"][i], r["nodes"][i + 1], cacheB) for i in range(len(r["nodes"]) - 1)]))
                pess = min(r["p"], pB)
                sc = r["cost"] / pess if pess > 0 else float("inf")
                if best is None or sc < best[0]:
                    best = (sc, r, pB)
            route_pick = best
            if best[1]["nodes"] != r0["nodes"]:
                self._post(oracle, "challenge", "critic", "all", target="route", reason="route survives only under one model; demoted by pessimistic (min over models) probability",
                           demoted=r0["nodes"], preferred=best[1]["nodes"], p_route_model=r0["p"], p_cut_model=best[2])
        self._post(oracle, "proposal", "cut", "all", hyp="blocked", frontier=len(ledger.frontier), cost=bcB, query=int(selB[int(np.argmax(PB))]))
        use_open = route_pick is not None and route_pick[0] <= bc
        if use_open:
            v = plA.next_on_route(route_pick[1], ledger)
        else:
            v = None
        if v is None or v in oracle.queried:
            comb = PA[: len(selA)]
            v = int(selA[int(np.argmax(comb))]) if selA.size else int(selB[int(np.argmax(PB))])
            use_open = False
        self._post(oracle, "decision", "arbiter", "all", chose="open-route" if use_open else "cut", open_score=None if route_pick is None else route_pick[0], cut_cost=bc, query=int(v))
        self.ask(oracle, ledger, v, "shared: " + ("open route" if use_open else "cut completion"))
        return True

    def _isolated_step(self, oracle, ledger):
        self._init_private(ledger)
        role = "route" if self.turn % 2 == 0 else "cut"
        self.turn += 1
        mine = self.priv[role]
        if not mine.frontier:
            role = "cut" if role == "route" else "route"; mine = self.priv[role]
            if not mine.frontier:
                return False
        model = GPModel(prior=self.ctx.prior) if role == "route" else LocalModel(prior=self.ctx.prior)
        pl = self._planner(role, mine, model); pl.sync()
        v = None
        if role == "route":
            routes, _ = pl.open_routes()
            if routes:
                v = pl.next_on_route(routes[0], mine)
                self._post(oracle, "proposal", "route", ["route"], hyp="open", route=routes[0]["nodes"], p=routes[0]["p"], query=v)
        if v is None:
            _, sel, P = pl.block_cost()
            v = int(sel[int(np.argmax(P))])
            self._post(oracle, "proposal", role, [role], hyp="blocked" if role == "cut" else "fallback-cut", query=v)
        if v in oracle.queried:   # already revealed to the other specialist: gatekeeper answers from ledger, free
            rec = ledger.obs[v] if v in ledger.obs else None
            self._post(oracle, "duplicate_request", "data", [role], node=int(v), cost=0)
            mine.reveal(v, rec)
            # forced progress: avoid stalling when the proposer asks only for known nodes
            self.stall = getattr(self, "stall", 0) + 1
            if self.stall > 50:
                keys = [w for w in ledger.frontier]
                v = keys[int(self.rng.integers(len(keys)))]
            else:
                return self._isolated_step(oracle, ledger)
        self._post(oracle, "decision", "arbiter", "all", chose=role, query=int(v), rule="round-robin (no cost comparison across isolated models)")
        rec = oracle.query(v, self.name + ":" + role, "isolated " + role)
        ledger.reveal(int(v), rec); mine.reveal(int(v), rec)
        return True
