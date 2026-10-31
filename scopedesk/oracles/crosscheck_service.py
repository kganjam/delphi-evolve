"""READ-ONLY cross-check of dx-collab's reviewed falsification service (`falsify.engine.falsify_turing`) against this oracle layer.
The service is NOT forked, edited or re-implemented: a snapshot of its source (`git archive origin/work/collab falsify turing_scope`) is
extracted to a separate directory and run in a SUBPROCESS (its own `turing_scope` copy must not mix with ours). Items: bench Turing 1-D
and 2-D items. Mapping: pattern_possible -> applies; domain_blocks_pattern | no_turing_instability -> out_of_scope; refusal
claim_precondition_failed -> out_of_scope (well-mixed unstable); boundary unstated: the service has no such input, so two calls
(neumann, periodic) are composed: differing outcomes -> underdetermined (same rule as the bench; reported separately from the raw refusal).
Every disagreement is listed row by row; scope differences (service refuses where we give a scope verdict) are classified, not hidden.
Usage: python3 -m scopedesk.oracles.crosscheck_service SERVICE_SNAPSHOT_DIR BENCHDIR OUT.json"""
from __future__ import annotations

import json
import subprocess
import sys
from collections import Counter
from pathlib import Path

from . import linear

WORKER = r'''
import json, sys
sys.path.insert(0, sys.argv[1])
from falsify.engine import falsify_turing
reqs = json.load(sys.stdin)
out = []
for r in reqs:
    res = falsify_turing(r)
    out.append({"verdict": res.get("verdict"), "refusal": (res.get("refusal") or {}).get("code"),
                "unstable_count": (res.get("modes") or {}).get("unstable_count"),
                "unstable_first": [m for m in ((res.get("modes") or {}).get("unstable") or [])[:3]],
                "basis": res.get("basis"), "service_version": res.get("service_version")})
json.dump(out, sys.stdout)
'''


def request(s, bc):
    J = s["J"]
    req = {"jacobian": [[J[0], J[1]], [J[2], J[3]]], "diffusivities": ["1", s["Dv"]], "crosscheck": False}
    if "r_over_pi" in s:
        req["domain"] = {"dimension": 1, "boundary": bc, "length_over_pi": s["r_over_pi"]}
    else:
        req["domain"] = {"dimension": 2, "boundary": bc, "lengths_over_pi": [s["a_over_pi"], s["b_over_pi"]]}
    return req


def to_scope(r):
    v = r["verdict"]
    if v == "pattern_possible":
        return "applies"
    if v in ("domain_blocks_pattern", "no_turing_instability"):
        return "out_of_scope"
    if v == "refused" and r["refusal"] == "claim_precondition_failed":
        return "out_of_scope"
    return "refused:" + str(r.get("refusal") or v)


def main(snap, bench, out):
    full = [json.loads(l) for l in open(Path(bench) / "instances_full.jsonl")]
    key = {json.loads(l)["id"]: json.loads(l) for l in open(Path(bench) / "key.jsonl")}
    items = [it for it in full if it["family"] in ("turing_finite_domain", "turing_2d_rectangle")]
    reqs, idx = [], []
    for it in items:
        s = it["hidden"]["structured"]
        bcs = [s["bc"]] if s["bc"] else ["neumann", "periodic"]
        for bc in bcs:
            reqs.append(request(s, bc))
            idx.append((it["id"], bc))
    p = subprocess.run([sys.executable, "-c", WORKER, str(snap)], input=json.dumps(reqs), capture_output=True, text=True, timeout=600)
    if p.returncode != 0:
        raise SystemExit("service subprocess failed: " + p.stderr[-800:])
    res = json.loads(p.stdout)
    by = {}
    for (iid, bc), r in zip(idx, res):
        by.setdefault(iid, {})[bc] = r
    rows = []
    for it in items:
        s, k = it["hidden"]["structured"], key[it["id"]]
        mine = linear.check(s)
        sv = by[it["id"]]
        if s["bc"]:
            r = sv[s["bc"]]
            svc_scope, svc_raw, compose = to_scope(r), r["verdict"], None
            count_svc = r.get("unstable_count")
        else:
            a, b = to_scope(sv["neumann"]), to_scope(sv["periodic"])
            svc_raw = f"neumann:{sv['neumann']['verdict']}|periodic:{sv['periodic']['verdict']}"
            compose = "underdetermined" if a != b else a
            svc_scope, count_svc = compose, None
        row = {"id": it["id"], "family": it["family"], "bc": s["bc"], "key": k["verdict"], "oracle": mine["scope_verdict"],
               "service": svc_scope, "service_raw": svc_raw, "oracle_agrees_key": mine["scope_verdict"] == k["verdict"],
               "service_agrees_key": svc_scope == k["verdict"], "oracle_equals_service": mine["scope_verdict"] == svc_scope,
               "oracle_marginal_modes": mine.get("n_marginal_modes")}
        if mine["scope_verdict"] != svc_scope:
            row["explained_by"] = ("marginal_mode_convention: service labels an exactly marginal mode 'unresolved'; oracle uses strict growth and now reports it"
                                   if (mine.get("n_marginal_modes") and "unresolved" in svc_raw) else "UNEXPLAINED")
        if count_svc is not None and mine.get("n_unstable_modes") is not None and svc_scope == "applies":
            row["unstable_count_oracle"], row["unstable_count_service"] = mine["n_unstable_modes"], count_svc
            row["unstable_count_equal"] = mine["n_unstable_modes"] == count_svc
        rows.append(row)
    dis = [r for r in rows if not r["oracle_equals_service"]]
    summ = {"n": len(rows), "oracle_equals_service": sum(r["oracle_equals_service"] for r in rows),
            "oracle_agrees_key": sum(r["oracle_agrees_key"] for r in rows), "service_agrees_key": sum(r["service_agrees_key"] for r in rows),
            "unstable_count_compared": sum("unstable_count_equal" in r for r in rows),
            "unstable_count_equal": sum(bool(r.get("unstable_count_equal")) for r in rows),
            "disagreements": len(dis), "unexplained_disagreements": sum(r.get("explained_by") == "UNEXPLAINED" for r in dis), "service_versions": sorted({r["service_version"] for r in res if r.get("service_version")}),
            "bc_unstated_composition": "two service calls (neumann, periodic) composed by the bench rule" }
    Path(out).write_text(json.dumps({"summary": summ, "disagreements": dis, "rows": rows,
                                     "note": "read-only; service snapshot from git archive, run in a subprocess; no service code modified"}, indent=1))
    print(json.dumps(summ, indent=1))
    for r in dis:
        print("DISAGREE", r["id"], r["bc"], "key", r["key"], "oracle", r["oracle"], "service", r["service"], r["service_raw"])


if __name__ == "__main__":
    main(*sys.argv[1:4])
