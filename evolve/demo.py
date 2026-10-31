"""Build artifacts/demo.json (CONTRACT schema) and integer-interval certificates.

Exploratory/descriptive layer: the demo pair VFVS -> AIKG uses FULL measured labels to
draw the landscape and compute the route/cut (like a lab notebook figure).  It is not
a prediction or a benchmark result.  The benchmark block is filled only from the saved
replay summary; proof/compute/claims stay "unavailable" unless another worker's
receipts are integrated by the coordinator.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import itertools
import json
import platform
from pathlib import Path

import numpy as np

from . import data, replay
from .graph import path_to, truth_bfs

ROOT = Path(__file__).resolve().parents[1]
CERT_DIR = ROOT / "artifacts" / "core" / "certificates"
SCOPE = {"name": "measured-subgraph-of-four-site-20^4-single-substitution",
         "vertices": "the 159,129 non-stop genotypes with a measurement in summary_AA.csv",
         "edges": "two genotypes differing at exactly one of the four positions",
         "outside_scope": "871 unmeasured library genotypes and all stop-containing genotypes; a certificate says NOTHING about paths through them",
         "not_claimed": "absence of a route here is not absence of an evolutionary route in biology or in full sequence space"}
ASSUME = [
    "A1 interval containment (ASSUMED, not proved): each genotype's true assay growth score lies in [lower, upper]",
    "A2 kappa is an assumed sensitivity multiplier on replicate-difference SD/2 by read-count bin; it is NOT a confidence level and gives no coverage claim",
    "A3 scores are cellular growth-selection proxies (E. coli Trp auxotrophy), not purified-enzyme kcat/KM",
    "A4 graph scope is the measured subgraph only (see graph_scope)",
]


def _node(L, i, Lo, Hi):
    g = data.decode(int(i)); d = data.digits(int(i))
    base = {"id": g, "genotype": g, "grid": [int(d[0] * 20 + d[1]), int(d[2] * 20 + d[3])]}
    if not L.measured[i]:
        return {**base, "observed_score": None, "replicate_1": None, "replicate_2": None, "lower": None, "upper": None, "evidence_kind": "unknown"}
    return {**base, "observed_score": L.s[i] / data.UNITS, "replicate_1": L.s1[i] / data.UNITS, "replicate_2": L.s2[i] / data.UNITS,
            "lower": Lo[i] / data.UNITS, "upper": Hi[i] / data.UNITS, "lower_micro": int(Lo[i]), "upper_micro": int(Hi[i]),
            "raw_mu_1": float(L.raw_mu1[i]), "raw_mu_2": float(L.raw_mu2[i]), "min_input_count": int(L.count_min[i]), "evidence_kind": "observed"}


def _cert(L, kind, start, target, route=None, S=None, Lo=None, Hi=None, label=""):
    body = {"schema": "delphi-evolve/core-certificate/v1", "kind": kind, "label": label,
            "graph_scope": SCOPE, "dataset": {"summary_AA_sha256": L.sha["summary_AA.csv"], "manifest": "data/manifest.json", "doi": "10.22002/h5rah-5z170", "license": "CC0 1.0"},
            "interval_model": {"rule": "lower=round(mean(r1,r2)*1e6)-eps, upper=round(mean(r1,r2)*1e6)+eps, eps=ceil(kappa*sd_bin/2*1e6); r_k = raw mu_k minus mean raw mu of stop-codon rows; all integers (1e-6 growth-rate units)",
                               "kappa": L.kappa, "sd_bin_edges_min_input_count": list(data.COUNT_BIN_EDGES), "sd_bin_values": list(data.REPLICATE_DIFF_SD), "units": "1e-6 growth-rate units, integers"},
            "edge_rule": "u->v admissible iff lower[v] >= upper[u]", "start": data.decode(start), "target": data.decode(target),
            "assumptions": ASSUME, "software": {"python": platform.python_version(), "numpy": np.__version__}}
    nodes = {}

    def add(i):
        nodes[data.decode(int(i))] = {"measured": bool(L.measured[i]), "lower": int(Lo[i]) if L.measured[i] else None, "upper": int(Hi[i]) if L.measured[i] else None}
    if kind == "route":
        body["route"] = [data.decode(v) for v in route]
        for v in route:
            add(v)
        body["edges"] = [{"from": data.decode(route[i]), "to": data.decode(route[i + 1]), "margin": int(Lo[route[i + 1]] - Hi[route[i]])} for i in range(len(route) - 1)]
    else:
        body["closed_set"] = sorted(data.decode(v) for v in S)
        bnd = []
        for u in sorted(S):
            add(u)
            for w in data.neighbors(np.int64(u)).tolist():
                if w in S:
                    continue
                add(w)
                bnd.append({"from": data.decode(u), "to": data.decode(w), "reason": "unmeasured-outside-scope" if not L.measured[w] else "inadmissible",
                            "margin": None if not L.measured[w] else int(Lo[w] - Hi[u])})
        body["boundary"] = bnd
    body["nodes"] = nodes
    body["body_sha256"] = hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()
    return body


def _dec_event(e):
    out = {}
    for k, x in e.items():
        if k in ("prev", "hash"):
            continue
        if k in ("route", "demoted", "preferred"):
            x = [data.decode(int(v)) for v in x]
        elif k in ("query", "node") and isinstance(x, (int, np.integer)):
            x = data.decode(int(x))
        out[k] = x
    return out


def build(output: Path, replay_dir: Path = ROOT / "artifacts" / "core" / "replay"):
    L = data.load(); Lo, Hi = L.intervals()
    start, target = data.encode("VFVS"), data.encode("AIKG")
    reached, parent, depth = truth_bfs(L.measured, Lo, Hi, start)
    route = path_to(parent, start, target) if reached[target] else None
    # --- all 24 direct (Hamming-monotone) orderings, shown with where they break
    ds, dt_ = data.digits(start), data.digits(target); direct = []
    for perm in itertools.permutations(range(4)):
        cur = ds.copy(); path = [start]
        for p in perm:
            cur[p] = dt_[p]; path.append(int(((cur[0] * 20 + cur[1]) * 20 + cur[2]) * 20 + cur[3]))
        bad = next((i for i in range(4) if not (L.measured[path[i + 1]] and Lo[path[i + 1]] >= Hi[path[i]])), None)
        direct.append({"order": [int(p) for p in perm], "nodes": path, "first_bad_edge": bad,
                       "min_point_score": int(min(L.s[v] for v in path if L.measured[v])), "admissible": bad is None})
    tempting = max(direct, key=lambda r: r["min_point_score"])
    # --- kappa sweep: route existence and closure size at each assumed bound
    sweep = []
    for k in (0.0, 0.5, 1.0, 1.5, 2.0, 3.0, 4.0, 6.0):
        lk, hk = L.intervals(k); r, p, d = truth_bfs(L.measured, lk, hk, start)
        rt = path_to(p, start, target) if r[target] else None
        sweep.append({"kappa": k, "open": bool(r[target]), "reachable_from_start": int(r.sum()), "shortest_route_edges": None if rt is None else len(rt) - 1})
    route_ok = lambda k, rt: all(L.intervals(k)[0][rt[i + 1]] >= L.intervals(k)[1][rt[i]] for i in range(len(rt) - 1))
    break_k = next((k for k in np.arange(0, 12.01, 0.05) if route and not route_ok(float(k), route)), None)
    # --- illustrative blocked pair: smallest closed set among panel pairs (chosen for illustration, flagged)
    panel = replay.make_episodes(L, 20); blocked = None
    for e in panel:
        r, p, d = truth_bfs(L.measured, Lo, Hi, e["start"])
        if not r[e["target"]] and (blocked is None or r.sum() < blocked[0]):
            blocked = (int(r.sum()), e, np.flatnonzero(r))
    CERT_DIR.mkdir(parents=True, exist_ok=True)
    certs = {}
    if route:
        c = _cert(L, "route", start, target, route=route, Lo=Lo, Hi=Hi, label="VFVS->AIKG shortest admissible route (full labels)")
        (CERT_DIR / "route_VFVS_AIKG_kappa2.json").write_text(json.dumps(c, indent=1)); certs["route"] = "artifacts/core/certificates/route_VFVS_AIKG_kappa2.json"
    if blocked:
        n, e, S = blocked
        c = _cert(L, "cut", e["start"], e["target"], S=set(int(x) for x in S), Lo=Lo, Hi=Hi, label="smallest blocked pair in panel (illustrative)")
        name = f"cut_{data.decode(e['start'])}_{data.decode(e['target'])}_kappa2.json"
        (CERT_DIR / name).write_text(json.dumps(c, indent=1)); certs["cut"] = "artifacts/core/certificates/" + name
    # --- nodes/edges for the figure: routes, subcube, neighbours of the weakest step
    keep = set(route or []) | {v for r in direct for v in r["nodes"]}
    weakest = None
    if route and len(route) > 1:
        m = [(Lo[route[i + 1]] - Hi[route[i]], i) for i in range(len(route) - 1)]
        weakest = min(m)[1]
        for v in (route[weakest], route[weakest + 1]):
            keep.update(data.neighbors(np.int64(v)).tolist())
    keep = sorted(keep)
    nodes = [_node(L, i, Lo, Hi) for i in keep]
    kset = set(keep); edges = []
    for u in keep:
        for w in data.neighbors(np.int64(u)).tolist():
            if w in kset:
                st = "unknown" if not (L.measured[u] and L.measured[w]) else ("admissible" if Lo[w] >= Hi[u] else "inadmissible")
                edges.append({"source": data.decode(u), "target": data.decode(w), "status": st})
    routes = []
    if route:
        steps = [{"from": data.decode(route[i]), "to": data.decode(route[i + 1]), "margin": float((Lo[route[i + 1]] - Hi[route[i]]) / data.UNITS),
                  "to_min_input_count": int(L.count_min[route[i + 1]])} for i in range(len(route) - 1)]
        routes.append({"id": "certified-shortest", "nodes": [data.decode(v) for v in route], "status": "open (certified in measured subgraph, kappa=2 assumed)",
                       "assumptions": ASSUME, "certificate_path": certs.get("route"), "steps": steps, "weakest_step_index": weakest,
                       "breaks_at_kappa": None if break_k is None else float(break_k), "lean_receipt": None})
    routes.append({"id": "tempting-direct", "nodes": [data.decode(v) for v in tempting["nodes"]],
                   "status": "open" if tempting["admissible"] else f"broken at step {tempting['first_bad_edge'] + 1}: upper bound of source exceeds lower bound of next",
                   "assumptions": ASSUME, "certificate_path": None,
                   "note": "highest minimum point score among the 24 direct orderings; point scores alone make it look usable"})
    if blocked:
        n, e, S = blocked
        routes.append({"id": "blocked-example", "nodes": [data.decode(e["start"]), data.decode(e["target"])], "status": f"blocked (closed set of {n} measured genotypes; all 76-neighbour boundary edges inadmissible or unmeasured)",
                       "assumptions": ASSUME, "certificate_path": certs.get("cut"), "note": "pair chosen for illustration as the smallest blocked pair in the frozen panel"})
    # --- worked specialist replay (shared evidence), pair B: VFVS -> VLKG, seed 0
    ep = next(e for e in panel if e["family"] == "B" and e["seed"] == 0 and e["target"] == data.encode("VLKG"))
    out, qlog, other, log = replay.run_episode(L, ep, "collective_shared", keep_events=True)
    spec_events = [e for e in log.events if e["type"] != "reveal"]
    ex = {"policy": "collective_shared", "pair": "VFVS->VLKG", "seed": 0, "outcome": {k: out[k] for k in ("status", "assays", "truth_open", "correct", "route", "verified_by_full_data") if k in out},
          "queries": [{"n": n, "actor": a, "genotype": data.decode(v), "lower": None if r is None else r[0] / data.UNITS, "upper": None if r is None else r[1] / data.UNITS,
                       "score": None if r is None else r[2] / data.UNITS, "why": w} for n, a, v, r, w in qlog],
          "specialist_events_first_60": [_dec_event(e) for e in spec_events[:60]],
          "event_chain_valid": log.verify(), "n_specialist_events": len(spec_events)}
    summ_path = replay_dir / "summary.json"
    bench = {"status": "unavailable", "protocol": "artifacts/core/protocol.json", "metrics": None, "limitations": ["replay not yet run in this checkout"]}
    if summ_path.exists():
        s = json.loads(summ_path.read_text())
        bench = {"status": "completed", "protocol": "artifacts/core/protocol.json", "metrics": s,
                 "tables": ["artifacts/core/replay/table_primary.csv", "artifacts/core/replay/table_paired.csv", "artifacts/core/replay/episodes.csv"],
                 "plots": ["artifacts/core/replay/cert_vs_assays.png", "artifacts/core/replay/outcomes_at_budget.png"],
                 "kind": "retrospective simulated assay-budget replay over observed labels; benchmark truth = finite measured-graph reachability under the declared assumed interval model",
                 "limitations": ["graph truth is under an ASSUMED noise model (kappa=2), not biological truth",
                                 "open certificates are sound by construction (only revealed labels), so false_certificates=0 is a check, not a finding",
                                 "family-B pairs reuse one start/4 targets across seeds; seeds vary only the 96 initial observations and tie-breaks",
                                 "isolated vs shared collective compares evidence boundaries inside one software process; scheduling is fixed code"]}
    if summ_path.exists():
        import pandas as pd
        pr = pd.read_csv(replay_dir / "table_primary.csv"); pa = pd.read_csv(replay_dir / "table_paired.csv")
        rate = lambda pol, b, fam="all": float(pr[(pr.policy == pol) & (pr.budget == b) & (pr.family == fam)].cert_rate.iloc[0])
        def pd_(a, b, bud):
            r = pa[(pa.a == a) & (pa.b == b) & (pa.budget == bud) & (pa.family == "all") & pa.metric.str.startswith("cert")].iloc[0]
            return {"mean_cert_rate_diff": float(r.mean_diff), "seed_cluster_bootstrap_95": [float(r["seed_cluster_bootstrap_2.5"]), float(r["seed_cluster_bootstrap_97.5"])], "a_better": int(r.a_better), "b_better": int(r.b_better), "tied": int(r.tied)}
        bench["key_numbers_derived_from_tables"] = {
            "episodes_per_policy": 100, "seeds": 20, "budget_assays": 1000,
            "cert_rate_at_1000": {k: rate(k, 1000) for k in ("random", "greedy", "uncertainty", "directed", "q2c", "q2c_nomodel", "collective_shared", "collective_isolated", "collective_shared_c", "collective_isolated_c")},
            "cert_rate_at_250": {k: rate(k, 250) for k in ("random", "directed", "q2c", "q2c_nomodel", "collective_shared", "collective_isolated")},
            "paired_q2c_vs_directed_at_1000": pd_("q2c", "directed", 1000),
            "paired_q2c_nomodel_vs_q2c_at_1000": pd_("q2c_nomodel", "q2c", 1000),
            "paired_collective_shared_vs_q2c_at_1000": pd_("collective_shared", "q2c", 1000),
            "paired_collective_shared_c_vs_isolated_c_at_1000": pd_("collective_shared_c", "collective_isolated_c", 1000),
            "false_certificates_all_policies": int(pr.false_certificates.sum()),
            "post_hoc_variants": ["q2c_nomodel", "collective_shared_rr", "collective_shared_c", "collective_isolated_c"]}
        bench["limitations"].append("q2c_nomodel, collective_shared_rr and the *_c collectives were added AFTER inspecting the 7-policy results (not in the frozen protocol); treat as exploratory")
    counts = dict(L.counts)
    demo = {
        "schema_version": "delphi-evolve/demo/1", "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "source": {"url": "https://data.caltech.edu/records/h5rah-5z170", "doi": "10.22002/h5rah-5z170", "paper_doi": "10.1073/pnas.2400439121",
                   "sha256": L.sha, "license": "CC0 1.0 (CaltechDATA record)", "retrieved_at": json.loads(data.MANIFEST.read_text())["retrieved_at"],
                   "assay": "E. coli tryptophan-auxotroph growth selection of TrpB (Tm9D8s*) variants at residues 183,184,227,228; two replicate flasks; score = raw growth rate mu minus mean stop-codon mu; a cellular proxy, not purified-enzyme catalysis",
                   "positions": list(data.POSITIONS), "parent": data.PARENT, "counts": counts,
                   "score_units": "growth-rate units (raw mu minus stop-codon background); not max-normalised; imputed KNN rows never used as observations"},
        "graph_scope": SCOPE, "interval_model": {"kappa": L.kappa, "meaning": "assumed sensitivity multiplier, not a confidence level", "sd_bins": dict(zip(["<20", "20-49", "50-199", ">=200"], data.REPLICATE_DIFF_SD))},
        "pair": {"start": "VFVS", "target": "AIKG", "basis": "parent and published top variant; exploratory full-label figure", "reachable_from_start_measured_graph": int(reached.sum())},
        "nodes": nodes, "edges": edges, "routes": routes, "kappa_sweep": sweep,
        "claims": [], "claims_status": "unavailable: Delphi claim import is not performed by the core worker; no claim IDs are asserted",
        "benchmark": bench,
        "proof": {"status": "unavailable", "theorem": None, "command": None, "exit_code": None, "mutation_exit_code": None, "receipt": None,
                  "note": "core worker emits integer-interval certificates (certificates/*.json) for the proof worker; nothing here has been Lean-checked"},
        "compute": {"status": "unavailable", "provider": None, "model": None, "job_id": None, "artifacts": []},
        "replay_example": ex,
        "limitations": [
            "Retrospective replay over already-assayed labels; no new wet-lab measurement and no newly discovered variant",
            "Scores are a growth-selection proxy; not kcat/KM and not a universal fitness",
            "Interval bounds are ASSUMED (kappa); two replicates give no rigorous simultaneous confidence bands over 159,129 variants",
            "Graph scope is the measured four-site subgraph; blocked means blocked there only, never impossible in biology or full sequence space",
            "Node grid coordinates are a projection of (AA1,AA2) x (AA3,AA4), not molecular geometry or an energy surface",
            "The demo figure uses full labels (descriptive); benchmark numbers come only from the saved replay"]}
    output = Path(output); output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(demo, indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o)))
    return demo
