"""TEST-ONLY synthetic replay builder.  Used to exercise validation and the final-render path.
Nothing built from this module may be committed as a deck or quoted as a result."""
import csv
import json
import random
import shutil
from pathlib import Path

POLS = ["random", "greedy", "uncertainty", "directed", "q2c", "collective_shared", "collective_isolated"]
BUDGETS = (100, 250, 500, 1000)
PROB = {"random": .1, "greedy": .1, "uncertainty": .12, "directed": .3, "q2c": .7, "collective_shared": .7, "collective_isolated": .75, "collective_shared_rr": .72}


def make_root(src_root: Path, dst: Path, seeds=20, empty_shards=0, drop_episode=False, followup_partial=False, with_followup=False):
    for rel in ["artifacts/demo.json", "artifacts/proof/receipt.json", "artifacts/integration/core_kappa2_route_lean.json",
                "artifacts/core/protocol.json", "site/data/landscape.js", "artifacts/evidence/route_summary.json"]:
        s = src_root / rel
        if s.exists():
            (dst / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(s, dst / rel)
    proto = json.loads((dst / "artifacts/core/protocol.json").read_text())
    proto["seeds"] = seeds
    (dst / "artifacts/core/protocol.json").write_text(json.dumps(proto))
    rd = dst / "artifacts/core/replay"
    (rd / "shards").mkdir(parents=True, exist_ok=True)
    rng = random.Random(1)
    pols = POLS + (["collective_shared_rr"] if with_followup else [])
    rows = []
    n_empty = 0
    for p in pols:
        for sd in range(seeds):
            sr = []
            for k in range(5):
                certd = rng.random() < PROB[p]
                a = rng.randint(30, 900)
                sr.append({"family": "A" if k == 0 else "B", "seed": sd, "start": "S", "target": f"T{k}", "policy": p, "truth_open": True,
                           "status": "open" if certd else "unresolved", "assays": a if certd else 1000, "censored": not certd,
                           "certificate": "open" if certd else "", "correct": True if certd else "", "verified_by_full_data": True if certd else ""})
            if p == "collective_shared_rr" and followup_partial and sd >= 10:
                continue
            if drop_episode and p == "q2c" and sd == 3:
                sr = sr[:-1]
            if n_empty < empty_shards and p == "greedy":
                n_empty += 1
                (rd / "shards" / f"{p}__seed{sd:02d}.json").write_text(json.dumps({"rows": [], "qlogs": {}}))
                rows += sr
                continue
            (rd / "shards" / f"{p}__seed{sd:02d}.json").write_text(json.dumps({"rows": sr, "qlogs": {}}))
            rows += sr
    keys = list(rows[0])
    with open(rd / "episodes.csv", "w", newline="") as f:
        w = csv.DictWriter(f, keys); w.writeheader(); w.writerows(rows)
    (rd / "summary.json").write_text(json.dumps({"episodes": len(rows), "seeds": seeds, "policies": pols}))
    tp = []
    for p in pols:
        s = [r for r in rows if r["policy"] == p]
        for b in BUDGETS:
            c = sum(1 for r in s if r["certificate"] and r["assays"] <= b)
            tp.append({"family": "all", "policy": p, "budget": b, "episodes": len(s), "certified": c, "cert_rate": c / len(s), "abstain_censored": len(s) - c,
                       "false_certificates": 0, "full_data_verification_failures": 0, "rmst_assays": 500.0})
    with open(rd / "table_primary.csv", "w", newline="") as f:
        w = csv.DictWriter(f, list(tp[0])); w.writeheader(); w.writerows(tp)
    pr = []
    for a, b in [("q2c", "random"), ("collective_shared", "q2c"), ("collective_shared", "collective_isolated"), ("directed", "random")]:
        pr.append({"a": a, "b": b, "family": "all", "budget": 1000, "metric": "cert_rate_diff(a-b)", "mean_diff": .1, "seed_cluster_bootstrap_2.5": -.05,
                   "seed_cluster_bootstrap_97.5": .25, "episodes": seeds * 5, "a_better": 1, "b_better": 1, "tied": 1})
    with open(rd / "table_paired.csv", "w", newline="") as f:
        w = csv.DictWriter(f, list(pr[0])); w.writeheader(); w.writerows(pr)
    return dst
