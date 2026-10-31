"""Matched-budget retrospective query-to-certify replay.

Protocol (frozen before the first run; see PANEL below and artifacts/core/protocol.json):
* declared graph: measured subgraph G_meas (159,129 nodes), single substitutions;
* declared edge rule: Lo[v] >= Hi[u] with eps = KAPPA * sd_bin / 2 (assumed);
* truth: forward admissible closure under FULL measured labels (benchmark truth,
  not biological truth);
* every policy gets the same start, target, 96 random initial observations (+start,
  target) and assay budget BMAX; one run yields the whole certificate-vs-assays curve
  because no policy is told the budget;
* certificates are issued only from revealed labels; unresolved runs are RIGHT-CENSORED
  at BMAX and kept;
* pair families (no hidden-label cherry-picking):
    A "seeded-initial": target = best-scoring genotype among the seed's own 96
       initial observations, start = random other initial observation with lower score
       and Hamming >= 2.  Uses only admissible observations.
    B "published-parent": start = parent VFVS, target in the published top variants
       AIKG, CLKG, VLKG, ALKG (identified in the source paper / dataset).  Targets fixed
       by published biology, not by held-out ranking performed here.
"""
from __future__ import annotations

import gzip
import json
import time
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from . import data
from .collective import Collective
from .graph import Ledger, path_to, truth_bfs, verify_cut, verify_route
from .oracle import EventLog, Oracle
from .policies import Directed, Greedy, Q2C, RandomFrontier, Uncertainty

BMAX = 1000
N_INIT = 96
SEED_BASE = 20261031
PUBLISHED_START = "VFVS"
PUBLISHED_TARGETS = ("AIKG", "CLKG", "VLKG", "ALKG")
POLICIES = {
    "random": RandomFrontier, "greedy": Greedy, "uncertainty": Uncertainty,
    "directed": Directed, "q2c": Q2C,
    "collective_shared": lambda c, r: Collective(c, r, True),
    "collective_isolated": lambda c, r: Collective(c, r, False),
}


@dataclass
class Ctx:
    start: int
    target: int
    eps_typ: float
    prior: object = None


def eps_typical(land):
    return float(np.ceil(land.kappa * data.REPLICATE_DIFF_SD[2] / 2 * data.UNITS))


def make_episodes(land, seeds):
    """Deterministic pair + initial-set panel. Label use: only the seed's own initial observations."""
    meas_idx = np.flatnonzero(land.measured)
    eps = []
    for seed in range(seeds):
        rng = np.random.default_rng(SEED_BASE + seed)
        init = [int(x) for x in rng.choice(meas_idx, N_INIT, replace=False)]
        sc = land.s[init]
        tgt = init[int(np.argmax(sc))]
        cand = [x for x in init if x != tgt and land.s[x] <= land.s[tgt] and int(data.hamming(x, tgt)) >= 2]
        st = int(rng.choice(cand))
        eps.append({"family": "A", "seed": seed, "start": st, "target": tgt, "init": init})
        s0 = data.encode(PUBLISHED_START)
        for g in PUBLISHED_TARGETS:
            r2 = np.random.default_rng(SEED_BASE + 10_000 + seed)
            init2 = [int(x) for x in r2.choice(meas_idx, N_INIT, replace=False)]
            eps.append({"family": "B", "seed": seed, "start": s0, "target": data.encode(g), "init": init2})
    return eps


_truth_cache = {}


def truth(land, start, target):
    k = (start, land.kappa)
    if k not in _truth_cache:
        Lo, Hi = land.intervals()
        _truth_cache[k] = truth_bfs(land.measured, Lo, Hi, start)
    r, p, d = _truth_cache[k]
    return bool(r[target]), int(r.sum()), (path_to(p, start, target) if r[target] else None)


def run_episode(land, ep, policy_name, bmax=BMAX, keep_events=False, prior=None):
    Lo, Hi = land.intervals()
    log = EventLog()
    oracle = Oracle(land, land.kappa, log)
    ledger = Ledger(ep["start"], ep["target"])
    ctx = Ctx(ep["start"], ep["target"], eps_typical(land), prior)
    # same admissible initial observations for every policy: start, target, then the 96 random
    order = [ep["start"], ep["target"]] + [v for v in ep["init"] if v not in (ep["start"], ep["target"])]
    for v in order:
        ledger.reveal(v, oracle.reveal_free(v))
    pol_seed = SEED_BASE + 77 * ep["seed"] + 5 * ep["target"] % 100003
    pol = POLICIES[policy_name](ctx, np.random.default_rng(pol_seed))
    t0 = time.time(); status = ledger.status(); stuck = False
    qlog = []
    while status == "unresolved" and oracle.n_queries < bmax:
        n0 = oracle.n_queries
        if not pol.step(oracle, ledger):
            stuck = True; break
        assert oracle.n_queries == n0 + 1
        status = ledger.status()
    wall = time.time() - t0
    truth_open, closure_size, truth_route = truth(land, ep["start"], ep["target"])
    out = {"family": ep["family"], "seed": ep["seed"], "start": data.decode(ep["start"]), "target": data.decode(ep["target"]),
           "policy": policy_name, "truth_open": truth_open, "truth_closure_size": closure_size,
           "truth_shortest_route_len": None if truth_route is None else len(truth_route) - 1,
           "status": status, "assays": oracle.n_queries, "censored": status == "unresolved", "stuck": stuck,
           "wall_s": round(wall, 3), "bmax": bmax,
           "observed_max_score": int(max(v[2] for v in ledger.obs.values())), "n_observed": len(ledger.obs)}
    out["certificate"] = None if status == "unresolved" else status
    out["correct"] = None if status == "unresolved" else (status == "open") == truth_open
    # independent re-verification against FULL data (audit only, never policy-visible)
    if status == "open":
        route = ledger.route()
        out["verified_by_full_data"] = bool(verify_route(land.measured, Lo, Hi, route))
        out["route"] = [data.decode(v) for v in route]
        out["route_len"] = len(route) - 1
        out["min_edge_margin"] = int(min(Lo[route[i + 1]] - Hi[route[i]] for i in range(len(route) - 1))) if len(route) > 1 else None
        out["replicate_sign_agree_frac"] = float(np.mean([(land.s1[route[i + 1]] >= land.s1[route[i]]) and (land.s2[route[i + 1]] >= land.s2[route[i]]) for i in range(len(route) - 1)])) if len(route) > 1 else None
    elif status == "blocked":
        S, bnd = ledger.cut()
        out["verified_by_full_data"] = bool(verify_cut(land.measured, Lo, Hi, S, ep["start"], ep["target"]))
        out["cut_size"] = len(S); out["cut_boundary_edges"] = len(bnd)
    events = [e for e in log.events if e["type"] == "reveal" and e["cost"] == 1]
    qlog = [(e["n_queries"], e["actor"], e["node"], e["rec"], e["why"]) for e in events]
    other = [e for e in log.events if e["type"] != "reveal"] if keep_events else []
    return out, qlog, other, log


def shard_path(outdir, policy, seed):
    return Path(outdir) / "shards" / f"{policy}__seed{seed:02d}.json"


def run_shard(args):
    outdir, policy, seed, kappa, bmax = args
    import os
    os.environ.setdefault("OMP_NUM_THREADS", "1")
    p = shard_path(outdir, policy, seed)
    if p.exists():
        return str(p), True
    land = data.load(kappa=kappa)
    rows, qlogs = [], {}
    for ep in [e for e in make_episodes(land, seed + 1) if e["seed"] == seed]:
        out, qlog, other, log = run_episode(land, ep, policy, bmax=bmax, keep_events=(seed == 0 and policy.startswith("collective")))
        rows.append(out)
        qlogs[f'{out["family"]}:{out["start"]}>{out["target"]}'] = qlog
        if seed == 0 and policy.startswith("collective"):
            d = Path(outdir) / "events"; d.mkdir(parents=True, exist_ok=True)
            with gzip.open(d / f'{policy}__{out["family"]}_{out["start"]}_{out["target"]}.jsonl.gz', "wt") as f:
                for e in log.events:
                    f.write(json.dumps(e, default=int) + "\n")
            out["event_chain_valid"] = log.verify()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"rows": rows, "qlogs": qlogs}, default=int))
    return str(p), False


def protocol(land, seeds=20):
    import hashlib
    panel = make_episodes(land, seeds)
    pairs = [{"family": e["family"], "seed": e["seed"], "start": data.decode(e["start"]), "target": data.decode(e["target"]),
              "initial_observations_sha256": hashlib.sha256(json.dumps(sorted(e["init"])).encode()).hexdigest()} for e in panel]
    return {
        "frozen_before_main_run": True,
        "graph_scope": "measured subgraph G_meas of 20^4 amino-acid library, single-substitution adjacency; 871 unmeasured genotypes are outside scope; stop-containing genotypes excluded",
        "edge_rule": "u->v admissible iff Lo[v] >= Hi[u]; Lo/Hi = round(mean of 2 replicates, micro-units) -/+ ceil(kappa*sd_bin/2*1e6)",
        "kappa_main": land.kappa, "kappa_meaning": "assumed sensitivity multiplier, not a confidence level",
        "noise_bins_min_input_count_edges": list(data.COUNT_BIN_EDGES), "replicate_diff_sd": list(data.REPLICATE_DIFF_SD),
        "truth": "forward admissible closure of start under full measured labels (benchmark truth under declared model, not biological truth)",
        "budget_assays_beyond_initial": BMAX, "n_initial_random_observations": N_INIT,
        "policies": list(POLICIES), "seeds": seeds,
        "pair_rules": {"A": "target = best-scoring of the seed's 96 initial observations; start = random other initial observation with lower score, Hamming>=2",
                       "B": f"start {PUBLISHED_START}; targets {list(PUBLISHED_TARGETS)} (published top variants); initial set seeded by seed"},
        "censoring": "unresolved or stuck at budget is right-censored and retained",
        "dataset_sha256": land.sha, "panel": pairs,
        "panel_sha256": hashlib.sha256(json.dumps(pairs, sort_keys=True).encode()).hexdigest(),
    }
