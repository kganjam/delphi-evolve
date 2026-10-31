"""Policy-level tests on SYNTHETIC logic-fixture landscapes (hand-set scores on the real 20^4 index space).

These fixtures are NOT measurements and make no biological statement; they exercise the algorithmic
semantics of the LazySP baseline through the real core Oracle / Ledger / replay.run_episode path.
Scores are in micro-units; with count_min=1000 and kappa=2 the half-width is eps=2992, so a step is
admissible iff the score rises by >= 5984."""
import dataclasses

import numpy as np
import pytest

from baselines.lazysp import run as lrun
from baselines.lazysp.policy import neighbors_py
from evolve import data, replay
from evolve.graph import truth_bfs, verify_route, verify_cut

DEAD = -10 ** 9
STEP = 10_000
E = lambda g: data.encode(g)


def make_land(score_fn=None, scores=None, unmeasured=(), default=DEAD):
    N = data.N_GENO
    s = np.full(N, default, np.int64)
    if score_fn is not None:
        s = np.array([score_fn(i) for i in range(N)], np.int64)
    for k, v in (scores or {}).items():
        s[E(k) if isinstance(k, str) else k] = v
    meas = np.ones(N, bool)
    for g in unmeasured:
        meas[E(g)] = False
    cm = np.where(meas, 1000, 0).astype(np.int32)
    s = np.where(meas, s, 0)
    nan = np.full(N, np.nan)
    return data.Landscape(meas, s.copy(), s.copy(), s, cm, nan, nan, (0.0, 0.0), {}, {}, 2.0)


def potential(target):
    h = np.array([int(data.hamming(i, target)) for i in range(data.N_GENO)]) if False else None
    from baselines.lazysp.policy import hamming_table
    H = hamming_table(target)
    return lambda i: STEP * (4 - H[i])


def run(land, start, target, selector="alternate", init=(), bmax=3000, cap=None):
    replay._truth_cache.clear()          # core caches truth by (start, kappa): never share across fixtures
    ep = {"family": "T", "seed": 0, "start": E(start), "target": E(target), "init": [E(g) if isinstance(g, str) else g for g in init]}
    out, qlog = lrun.run_task(land, selector, 0, 0, cap, bmax, ep=ep)
    replay._truth_cache.clear()
    return out, qlog, lrun._LAST["log"], lrun._LAST["pol"]


def route_of(out):
    return [data.encode(g) for g in out["route"]]


def test_indirect_route_requires_step_away_from_target():
    """Direct Hamming-monotone steps are dead; the only route goes AAAA->AAAC->CAAC->CCAC->CCAA (moves away first)."""
    sc = {"CAAA": DEAD, "ACAA": DEAD, "AAAC": 30000, "CAAC": 40000, "CCAC": 60000, "CCAA": 80000}
    land = make_land(potential(E("CCAA")), sc)
    for sel in ("forward", "reverse", "alternate"):
        out, q, log, pol = run(land, "AAAA", "CCAA", sel)
        assert out["status"] == "open" and out["correct"] and out["verified_by_full_data"], sel
        assert out["route_len"] == 4 > int(data.hamming(E("AAAA"), E("CCAA")))
        assert verify_route(land.measured, *land.intervals(), route_of(out))
        assert out["truth_open"] and out["assays"] == len(q) and out["assays"] > 2


def test_overlapping_intervals_are_not_admissible():
    """start [-2992,2992] -> target score 2000 gives [-992,4992]: intervals overlap, Lo[t] < Hi[s]: NOT admissible
    under the core rule, so a 1-step route is not certified and the baseline must run to a ledger cut."""
    land = make_land(None, {"AAAA": 0, "AAAC": 2000})
    out, q, log, pol = run(land, "AAAA", "AAAC")
    assert out["status"] == "blocked" and out["truth_open"] is False and out["correct"] and out["verified_by_full_data"]
    assert out["assays"] >= 75           # all other 75 out-neighbours of start must be assayed to close the cut (target is revealed free)
    # separated intervals: certified immediately with zero paid assays
    land2 = make_land(None, {"AAAA": 0, "AAAC": 7000})
    out2, q2, *_ = run(land2, "AAAA", "AAAC")
    assert out2["status"] == "open" and out2["assays"] == 0 and q2 == []


def test_unavailable_genotypes_cost_assays_and_are_excluded_only_after_revelation():
    tgt = "CCCC"
    # the lexicographically early shortest path goes through unmeasured genotypes; they must be assayed (paid) then excluded
    land = make_land(potential(E(tgt)), unmeasured=["AAAC", "AACA", "ACCA"])
    out, q, log, pol = run(land, "AAAA", tgt)
    assert out["truth_open"] and out["status"] == "open" and out["correct"] and out["verified_by_full_data"]
    absent_events = [e for e in log.events if e["type"] == "reveal" and e["cost"] == 1 and e["rec"] is None]
    assert absent_events, "an unmeasured vertex on a candidate path must be assayed (and reveal absent) before exclusion"
    assert all(e["n_queries"] >= 1 for e in absent_events)
    assert not any(not land.measured[v] for v in route_of(out))
    # assays include the absent reveals
    assert out["assays"] == len(q) >= len(absent_events) + 3
    assert q[0][2] == E("AAAC") and q[0][3] is None      # first candidate path's first vertex is unmeasured: paid for, then excluded


def test_oracle_query_accounting_and_immediate_stop():
    land = make_land(potential(E("CCCC")))
    out, q, log, pol = run(land, "AAAA", "CCCC", "forward")
    assert out["status"] == "open" and out["assays"] == 3 == len(q)           # 3 interior vertices, nothing wasted
    costs = [e for e in log.events if e["type"] == "reveal" and e["cost"] == 1]
    assert len(costs) == 3 and len({e["node"] for e in log.events if e["type"] == "reveal"}) == len(log.events)  # no duplicate reveals
    # stop as soon as the ledger certifies: with one fewer assay the episode is still unresolved
    out2, q2, *_ = run(land, "AAAA", "CCCC", "forward", bmax=2)
    assert out2["status"] == "unresolved" and out2["censored"] and out2["abstain_reason"] == "assay_budget" and out2["assays"] == 2
    assert out["lazysp"]["replans"] == 1 and out["event_chain_valid"] and out2["certificate"] is None


def test_selector_definitions_forward_reverse_alternate():
    land = make_land(potential(E("CCCC")))
    orders = {}
    for sel in ("forward", "reverse", "alternate"):
        out, q, *_ = run(land, "AAAA", "CCCC", sel)
        orders[sel] = [x[2] for x in q]
        route = route_of(out)
        assert out["status"] == "open" and len(route) == 5
        v1, v2, v3 = route[1:4]
        assert orders[sel] == {"forward": [v1, v2, v3], "reverse": [v3, v2, v1], "alternate": [v1, v3, v2]}[sel]


def test_unobserved_label_canary():
    """Scramble EVERY label the policy never saw; the full query sequence must be identical."""
    sc = {"CAAA": DEAD, "ACAA": DEAD, "AAAC": 30000, "CAAC": 40000, "CCAC": 60000, "CCAA": 80000}
    land = make_land(potential(E("CCAA")), sc)
    out, q, log, pol = run(land, "AAAA", "CCAA", "alternate")
    seen = {x[2] for x in q} | {E("AAAA"), E("CCAA")}
    rng = np.random.default_rng(3)
    s2 = land.s.copy()
    unseen = np.array([i for i in range(data.N_GENO) if i not in seen])
    s2[unseen] = rng.integers(-10 ** 6, 10 ** 6, unseen.size)
    land2 = dataclasses.replace(land, s=s2, s1=s2.copy(), s2=s2.copy())
    out2, q2, *_ = run(land2, "AAAA", "CCAA", "alternate")
    assert q == q2 and out["assays"] == out2["assays"] and len(q) > 2
    # sanity: the scrambled world really is a different world
    assert not np.array_equal(land.s, land2.s)


def test_blocked_certificate_is_the_ledger_cut_and_exact():
    land = make_land(potential(E("CCAA")), {"CAAA": DEAD, "ACAA": DEAD})
    out, q, log, pol = run(land, "AAAA", "CCAA")
    assert out["status"] == "blocked" and out["truth_open"] is False and out["correct"] and out["verified_by_full_data"]
    assert out["cut_size"] == 1 and out["cut_boundary_edges"] == 76


def test_budget_and_runtime_abstentions_are_never_blocked():
    land = make_land(potential(E("CCAA")), {"CAAA": DEAD, "ACAA": DEAD})
    out, q, log, pol = run(land, "AAAA", "CCAA", bmax=10)
    assert out["status"] == "unresolved" and out["censored"] and out["certificate"] is None and out["correct"] is None
    assert out["abstain_reason"] == "assay_budget" and out["assays"] == 10
    out, q, log, pol = run(land, "AAAA", "CCAA", cap=0.0)
    assert out["status"] == "unresolved" and out["abstain_reason"] == "runtime_bound" and out["certificate"] is None and out["assays"] == 0


def test_native_infeasibility_then_ledger_fallback():
    """All 76 in-neighbours of target revealed up front, each scoring above target: the optimistic graph has no route at 0 assays,
    yet the ledger is not blocked until start's frontier is closed; fallback queries are labelled."""
    tgt = E("CCAA")
    nb = neighbors_py(tgt)
    land = make_land(potential(tgt), {v: 10 ** 9 for v in nb})      # every in-neighbour scores ABOVE target: x->target is inadmissible
    out, q, log, pol = run(land, "AAAA", "CCAA", init=nb)
    assert pol.native_infeasible_at == 0
    assert out["status"] == "blocked" and out["correct"] and out["verified_by_full_data"] and out["truth_open"] is False
    assert all(x[4] == "fallback_after_native_infeasible" for x in q) and len(q) == pol.stats["fallback_queries"] > 0
