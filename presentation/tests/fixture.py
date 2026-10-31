"""TEST-ONLY synthetic replay builder.  Used to exercise validation and the final-render path.
Nothing built from this module may be committed as a deck or quoted as a result."""
from __future__ import annotations

import csv
import json
import random
import shutil
from pathlib import Path

POLS = ["random", "greedy", "uncertainty", "directed", "q2c", "collective_shared", "collective_isolated"]
POST = ["q2c_nomodel", "collective_shared_c", "collective_isolated_c", "collective_shared_rr"]
BUDGETS = (100, 250, 500, 1000)
PROB = {"random": .1, "greedy": .1, "uncertainty": .12, "directed": .3, "q2c": .7, "collective_shared": .7, "collective_isolated": .75, "collective_shared_rr": .72, "q2c_nomodel": .9, "collective_shared_c": .9, "collective_isolated_c": .6}


def make_root(src_root: Path, dst: Path, seeds=20, with_lazysp=False, lazysp_tamper=None, turing_src: Path | None = None, demo_src: Path | None = None, empty_shards=0, drop_episode=False, followup_partial=False, with_followup=False, shards=True, queries=False, drop_query_row=False):
    if demo_src is not None:
        (dst / "artifacts").mkdir(parents=True, exist_ok=True)
        shutil.copy(demo_src, dst / "artifacts/demo.json")
    for rel in ["artifacts/demo.json", "artifacts/proof/receipt.json", "artifacts/integration/core_kappa2_route_lean.json",
                "artifacts/core/protocol.json", "site/data/landscape.js", "artifacts/evidence/route_summary.json",
                "artifacts/claim_reuse/demo_receipt.json", "artifacts/claim_reuse/reuse_benchmark.json", "artifacts/claim_reuse/verification_receipt.json"]:
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
    pols = POLS + (POST if with_followup else [])
    (rd / "queries").mkdir(parents=True, exist_ok=True)
    qrows: dict = {}
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
            for r_ in sr:
                qrows.setdefault(p, []).extend([(sd, f"{r_['family']}:{r_['start']}>{r_['target']}")] * int(r_["assays"]))
            if p == "collective_shared_rr" and followup_partial and sd >= 10:
                continue
            if drop_episode and p == "q2c" and sd == 3:
                sr = sr[:-1]
            if n_empty < empty_shards and p == "greedy":
                n_empty += 1
                if shards:
                    (rd / "shards" / f"{p}__seed{sd:02d}.json").write_text(json.dumps({"rows": [], "qlogs": {}}))
                rows += sr
                continue
            if shards:
                (rd / "shards" / f"{p}__seed{sd:02d}.json").write_text(json.dumps({"rows": sr, "qlogs": {}}))
            rows += sr
    if queries:
        import gzip
        for p, qs in qrows.items():
            # only episodes that exist in episodes.csv are kept (partial/dropped episodes were `continue`d or truncated above)
            have = {(r["seed"], f"{r['family']}:{r['start']}>{r['target']}") for r in rows if r["policy"] == p}
            qs = [q for q in qs if q in have]
            if drop_query_row and p == "q2c":
                qs = qs[:-1]
            with gzip.open(rd / "queries" / f"queries__{p}.tsv.gz", "wt") as g:
                g.write("seed\tpair\tn\n")
                g.writelines(f"{sd:02d}\t{pair}\t1\n".replace(f"{sd:02d}", str(sd), 1) for sd, pair in qs)
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
    pairs = [("q2c", "random"), ("collective_shared", "q2c"), ("collective_shared", "collective_isolated"), ("directed", "random"), ("q2c", "directed")] + ([("q2c_nomodel", "q2c")] if with_followup else [])
    for (a, b), bud in [(x, y) for x in pairs for y in (250, 1000)]:
        pr.append({"a": a, "b": b, "family": "all", "budget": bud, "metric": "cert_rate_diff(a-b)", "mean_diff": .1, "seed_cluster_bootstrap_2.5": -.05,
                   "seed_cluster_bootstrap_97.5": .25, "episodes": seeds * 5, "a_better": 1, "b_better": 1, "tied": 1})
    with open(rd / "table_paired.csv", "w", newline="") as f:
        w = csv.DictWriter(f, list(pr[0])); w.writeheader(); w.writerows(pr)
    if with_lazysp:
        make_lazysp(dst, rows, seeds, lazysp_tamper)
    if turing_src is not None:
        for rel in ("artifacts/turing_scope/results.json", "artifacts/turing_scope/lean_receipt.json"):
            if (turing_src / rel).exists():
                (dst / rel).parent.mkdir(parents=True, exist_ok=True)
                shutil.copy(turing_src / rel, dst / rel)
    return dst


def make_lazysp(dst: Path, core_rows: list, seeds: int, tamper=None):
    """TEST-ONLY synthetic artifacts/lazysp/results/ consistent with the synthetic core rows."""
    d = dst / "artifacts/lazysp/results"
    d.mkdir(parents=True, exist_ok=True)
    rng = random.Random(7)
    q = {(r["seed"], r["family"], r["start"], r["target"]): r for r in core_rows if r["policy"] == "q2c"}
    pb = {"alternate": .96, "forward": .96, "reverse": .5}
    ep, summ, audit, tp = [], {"variants": {}}, {}, []
    allrows = {}
    for v, pr in pb.items():
        rows = []
        for (sd, fam, st, tg), qr in q.items():
            ok = qr["certificate"] != "" or rng.random() < pr
            a = rng.randint(30, 900) if ok else 1000
            rows.append({"family": fam, "seed": sd, "start": st, "target": tg, "policy": f"lazysp_{v}", "status": "open" if ok else "unresolved", "assays": a,
                         "certificate": "open" if ok else "", "correct": "True" if ok else "", "verified_by_full_data": "True" if ok else "", "variant": v})
        if tamper == "drop" and v == "forward":
            rows = rows[:-1]
        ep += rows
        allrows[v] = rows
    def res(rows, b): return sum(1 for r in rows if r["certificate"] and r["assays"] <= b) / len(rows)
    def rmst(rows): return sum(r["assays"] if r["certificate"] else 1000 for r in rows) / len(rows)
    for v, rows in allrows.items():
        n = len(rows)
        op = sum(1 for r in rows if r["certificate"])
        sc = {"open": op, "unresolved": n - op}
        summ["variants"][v] = {"episodes_expected": n, "episodes_present": n, "complete_panel": True, "status": "COMPLETE_100", "status_counts": {k: c for k, c in sc.items() if c},
                               "resolved_at": {str(b): res(rows, b) for b in (100, 250, 500, 750, 1000)}, "rmst_assays": round(rmst(rows), 2)}
        audit[v] = {"shards_audited": n, "errors": ["synthetic error"] if tamper == "audit" and v == "reverse" else []}
        tp.append({"variant": v, "panel_status": "COMPLETE_100", "episodes": n, "open": op, "blocked": 0, "unresolved": n - op, "false_certificates": 0, "full_data_verification_failures": 0,
                   "resolved@1000": round(res(rows, 1000), 2), "rmst_assays": round(rmst(rows), 1)})
    alt = allrows["alternate"]
    okq = lambda r: r["certificate"] != "" and r["assays"] <= 1000
    ol = sum(1 for r in alt if r["certificate"] and not okq(q[(r["seed"], r["family"], r["start"], r["target"])]))
    oq = sum(1 for r in alt if not r["certificate"] and okq(q[(r["seed"], r["family"], r["start"], r["target"])]))
    both = sum(1 for r in alt if r["certificate"] and okq(q[(r["seed"], r["family"], r["start"], r["target"])]))
    if tamper == "paired":
        ol += 1
    qr_ = rmst(list(q.values()))
    summ["variants"]["alternate"]["paired"] = {"q2c": {"resolved_only_by_lazysp": ol, "resolved_only_by_comparator": oq, "both_resolved": both, "neither_resolved": len(alt) - ol - oq - both,
        "rmst_lazysp": summ["variants"]["alternate"]["rmst_assays"], "rmst_comparator": qr_, "resolved_diff_1000": {"diff": .1, "lo95": .05, "hi95": .15}, "rmst_diff": {"diff": -5.0, "lo95": -50.0, "hi95": 40.0}}}
    if tamper == "summary":
        summ["variants"]["alternate"]["resolved_at"]["1000"] = 0.5
    keys = list(ep[0])
    with open(d / "episodes.csv", "w", newline="") as f:
        w = csv.DictWriter(f, keys); w.writeheader(); w.writerows(ep)
    with open(d / "table_primary.csv", "w", newline="") as f:
        w = csv.DictWriter(f, list(tp[0])); w.writeheader(); w.writerows(tp)
    (d / "summary.json").write_text(json.dumps(summ)); (d / "audit.json").write_text(json.dumps(audit))
    cl = {"diff": .1, "lo95": 0.0, "hi95": .5}
    (d / "exploratory_post_hoc.json").write_text(json.dumps({"label": "POST HOC / exploratory; not preregistered", "problem_clusters": 24,
        "variants": {"alternate": {"problem_cluster_bootstrap_resolved_at_1000_diff": cl, "problem_cluster_bootstrap_rmst_diff": {"diff": -5.0, "lo95": -180.0, "hi95": 200.0}}}}))
