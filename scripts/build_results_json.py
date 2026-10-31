#!/usr/bin/env python3
"""Build site/data/results.json from core's saved replay tables (no recomputation, no new science).
Every number in the file is copied from table_primary.csv / table_paired.csv; protocol.json decides which policies were
frozen before the main run (the rest are labelled post-hoc)."""
import json, pathlib
import pandas as pd
R = pathlib.Path(__file__).resolve().parents[1]
prim = pd.read_csv(R / "artifacts/core/replay/table_primary.csv")
pair = pd.read_csv(R / "artifacts/core/replay/table_paired.csv")
proto = json.load(open(R / "artifacts/core/protocol.json"))
summ = json.load(open(R / "artifacts/core/replay/summary.json"))
frozen = set(proto["policies"])
LABEL = {"random": "random frontier", "greedy": "greedy walk", "uncertainty": "GP uncertainty", "directed": "directed best-first (single deterministic policy)",
         "q2c_nomodel": "query-to-certify, no learned model", "q2c": "query-to-certify (GP-priced)", "collective_shared": "collective, shared evidence",
         "collective_shared_rr": "collective, shared, round-robin control", "collective_isolated": "collective, isolated evidence",
         "collective_shared_c": "collective, shared, no GP", "collective_isolated_c": "collective, isolated, no GP"}
ORDER = ["random", "greedy", "uncertainty", "directed", "q2c", "collective_shared", "collective_isolated",
         "q2c_nomodel", "collective_shared_rr", "collective_shared_c", "collective_isolated_c"]
pol = []
for p in ORDER:
    row = {"id": p, "label": LABEL[p], "frozen_in_protocol": p in frozen, "by_family": {}}
    for fam in ("all", "A", "B"):
        row["by_family"][fam] = {}
        for b in (100, 250, 500, 1000):
            r = prim[(prim.policy == p) & (prim.family == fam) & (prim.budget == b)].iloc[0]
            row["by_family"][fam][str(b)] = {"episodes": int(r.episodes), "certified": int(r.certified), "cert_rate": float(r.cert_rate),
                                             "unresolved_censored": int(r.abstain_censored), "false_certificates": int(r.false_certificates),
                                             "rmst_assays": float(r.rmst_assays)}
    pol.append(row)
WANT = [("q2c", "directed"), ("q2c", "random"), ("q2c_nomodel", "q2c"), ("collective_shared", "q2c"), ("collective_shared", "collective_isolated"),
        ("collective_shared_rr", "collective_shared"), ("collective_shared_c", "collective_isolated_c")]
contr = []
for a, b in WANT:
    for bud in (250, 500, 1000):
        r = pair[(pair.a == a) & (pair.b == b) & (pair.family == "all") & (pair.budget == bud) & (pair.metric == "cert_rate_diff(a-b)")].iloc[0]
        contr.append({"a": a, "b": b, "a_label": LABEL[a], "b_label": LABEL[b], "budget": bud, "mean_diff": float(r.mean_diff),
                      "ci_low": float(r["seed_cluster_bootstrap_2.5"]), "ci_high": float(r["seed_cluster_bootstrap_97.5"]),
                      "a_better": int(r.a_better), "b_better": int(r.b_better), "tied": int(r.tied),
                      "a_posthoc": a not in frozen, "b_posthoc": b not in frozen})
out = {"source_tables": ["artifacts/core/replay/table_primary.csv", "artifacts/core/replay/table_paired.csv", "artifacts/core/protocol.json", "artifacts/core/replay/summary.json"],
       "kind": "retrospective simulated assay-budget replay over already-measured labels; benchmark truth = finite measured-graph reachability under the declared ASSUMED interval model (kappa=2)",
       "seeds": summ["seeds"], "episodes_per_policy": 100, "budgets": [100, 250, 500, 1000],
       "protocol_panel_sha256": proto.get("panel_sha256"), "frozen_policies": sorted(frozen), "policies": pol, "paired_contrasts": contr,
       "uncertainty_procedure": "paired differences on identical episodes; percentile bootstrap over the 20 seeds as clusters; descriptive, not a coverage claim",
       "caveats": ["20 seeds; family B repeats one start and four targets, so its 80 episodes are not independent pairs",
                   "every episode starts with the start and target labels revealed free, plus 96 random observations, identically for all policies; family B targets are the published top variants of this same table, fixed by published biology and not by this replay",
                   "family A has 8 blocked pairs; blocked certification is the same for all policies because a cut needs every neighbour assayed",
                   "false certificates are 0 by construction (certificates use only revealed labels), so that column is a check, not a finding",
                   "policies marked post-hoc were added after the first results and are exploratory; best-of-several selection is optimistic",
                   "no ALDE implementation and no foundation-model prior was run; comparisons are against this repository's own policies",
                   "'no route certifiable' (called blocked in the tables) means no chain of steps with lower(next) >= upper(current) exists in the measured subgraph; an actual ascending route may still exist",
                   "the noise bins are estimated over all 159,129 measured rows before the replay: a transductive sensitivity calibration, not an independently held-out replicate validation; kappa is an assumed multiplier, not a confidence level",
                   "query-efficient path finding is established (LazySP, Bayesian active edge evaluation); only the enzyme-assay setting, the replay and the certificates are ours"]}
dst = R / "site/data/results.json"
dst.write_text(json.dumps(out, indent=1))
print("wrote", dst, len(pol), "policies", len(contr), "contrasts")
