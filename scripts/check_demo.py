#!/usr/bin/env python3
"""Integration check of artifacts/demo.json against specs/CONTRACT.md.

Independent of evolve/. Prints a JSON report; exit 0 only if every hard check
passes. Soft findings are reported but do not fail. Usage:
  python3 -I scripts/check_demo.py artifacts/demo.json
"""
import json, sys

TOP = ["schema_version", "generated_at", "source", "nodes", "edges", "routes",
       "claims", "benchmark", "proof", "compute", "limitations"]
SRC = ["url", "doi", "sha256", "license", "assay", "counts"]
NODE = ["id", "genotype", "observed_score", "replicate_1", "replicate_2",
        "lower", "upper", "evidence_kind"]
EDGE = ["source", "target", "status"]
ROUTE = ["id", "nodes", "status", "assumptions", "certificate_path"]
CLAIM = ["id", "source_uri", "statement", "relation_to_test", "status"]
BENCH = ["status", "protocol", "metrics", "limitations"]
PROOF = ["status", "theorem", "command", "exit_code", "mutation_exit_code", "receipt"]
COMP = ["status", "provider", "model", "job_id", "artifacts"]
KINDS_OK = {"observed", "predicted", "simulated", "unknown"}


def need(d, keys, where, fails):
    if not isinstance(d, dict):
        fails.append(f"{where}: not an object")
        return
    for k in keys:
        if k not in d:
            fails.append(f"{where}: missing '{k}'")


def main(path):
    d = json.load(open(path))
    fails, soft = [], []
    need(d, TOP, "top", fails)
    need(d.get("source"), SRC, "source", fails)
    for i, n in enumerate(d.get("nodes", [])[:5000]):
        need(n, NODE, f"nodes[{i}]", fails)
        if isinstance(n, dict):
            if n.get("evidence_kind") not in KINDS_OK:
                fails.append(f"nodes[{i}]: evidence_kind {n.get('evidence_kind')!r}")
            if n.get("evidence_kind") == "observed" and n.get("observed_score") is None:
                fails.append(f"nodes[{i}]: observed without score")
            if n.get("evidence_kind") != "observed" and n.get("observed_score") not in (None,):
                fails.append(f"nodes[{i}]: non-observed node carries observed_score")
    ids = {n.get("id") for n in d.get("nodes", []) if isinstance(n, dict)}
    for i, e in enumerate(d.get("edges", [])):
        need(e, EDGE, f"edges[{i}]", fails)
        if isinstance(e, dict) and ids and (e.get("source") not in ids or e.get("target") not in ids):
            fails.append(f"edges[{i}]: endpoint not in nodes")
            break
    for i, r in enumerate(d.get("routes", [])):
        need(r, ROUTE, f"routes[{i}]", fails)
        if isinstance(r, dict):
            missing = [x for x in r.get("nodes", []) if x not in ids]
            if missing:
                msg = f"routes[{i}]: nodes not in graph: {missing[:3]}"
                if str(r.get("status", "")).startswith("blocked") and r.get("lean_checked") is False:
                    soft.append(msg + " (blocked endpoint pair, labelled lean_checked=false)")
                else:
                    fails.append(msg)
            if not r.get("assumptions"):
                fails.append(f"routes[{i}]: no named assumptions")
    for i, c in enumerate(d.get("claims", [])):
        need(c, CLAIM, f"claims[{i}]", fails)
    need(d.get("benchmark"), BENCH, "benchmark", fails)
    need(d.get("proof"), PROOF, "proof", fails)
    need(d.get("compute"), COMP, "compute", fails)
    if not d.get("limitations"):
        fails.append("limitations empty")
    # Guardrails
    src = d.get("source", {}) if isinstance(d.get("source"), dict) else {}
    cnt = src.get("counts", {}) if isinstance(src.get("counts"), dict) else {}
    flat = json.dumps(cnt)
    for want in ("159129", "871"):
        if want not in flat:
            soft.append(f"source.counts does not mention {want}")
    p = d.get("proof", {}) if isinstance(d.get("proof"), dict) else {}
    if p.get("status") in ("passed", "verified", "ok", "compiled"):
        if p.get("exit_code") != 0:
            fails.append("proof status positive but exit_code != 0")
        if p.get("mutation_exit_code") in (None, 0):
            fails.append("proof status positive but mutation was not rejected (mutation_exit_code must be nonzero)")
        if not p.get("receipt"):
            fails.append("proof status positive but no receipt")
    c = d.get("compute", {}) if isinstance(d.get("compute"), dict) else {}
    if c.get("status") in ("completed", "passed", "ok") and not c.get("job_id"):
        fails.append("compute completed without job_id")
    b = d.get("benchmark", {}) if isinstance(d.get("benchmark"), dict) else {}
    if b.get("status") in ("completed", "passed", "ok") and not b.get("metrics"):
        fails.append("benchmark completed with empty metrics")
    imp = [n for n in d.get("nodes", []) if isinstance(n, dict) and n.get("evidence_kind") == "observed"
           and str(n.get("source_file", "")).lower().find("knn") >= 0]
    if imp:
        fails.append(f"{len(imp)} nodes flagged observed come from KNN file")
    rep = {"path": path, "n_nodes": len(d.get("nodes", [])), "n_edges": len(d.get("edges", [])),
           "n_routes": len(d.get("routes", [])), "n_claims": len(d.get("claims", [])),
           "proof_status": p.get("status"), "benchmark_status": b.get("status"),
           "compute_status": c.get("status"), "hard_failures": fails, "soft_findings": soft}
    print(json.dumps(rep, indent=2))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
