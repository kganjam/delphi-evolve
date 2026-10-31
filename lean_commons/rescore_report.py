"""Old-vs-new per run: registered certificates (original checker) vs strict certificates (repaired checker + mutant replay),
and regex 'uses' vs proof-term library dependencies. Reads only committed artifacts."""
import glob, json, statistics
from pathlib import Path

ROOT = Path("artifacts/commons/runs")
rows, per = [], {}
for f in sorted(glob.glob(str(ROOT / "AUDIT_*_rx.json"))):
    d = json.load(open(f)); per.update(d["per_run"]); rows += d["rows"]
runs = []
for r in sorted(per):
    s = json.load(open(ROOT / r / "summary.json"))
    deps = [x for x in rows if x["run"] == r]
    runs.append({"run": r, "registered_certified": s["n_proved"], "strict_certified": per[r]["strict"],
                 "unreconstructed": per[r]["unreconstructed"], "mutant_accepted": per[r]["mutant_accepted"],
                 "deps_extracted_all": all(x.get("deps_extracted", False) for x in deps if x["reconstructed_ok"]),
                 "regex_lemma_uses_original_summary": s["reuse"]["total_lemma_uses"],
                 "proof_term_library_deps_direct": per[r]["lib_dep_uses"], "proof_term_cross_agent_deps": per[r]["cross_agent_dep_uses"],
                 "targets_with_any_library_dep": sum(1 for x in deps if x.get("library_deps")),
                 "calls_used": s["calls_used"], "tokens": s["tokens_spent"], "wall_s": s["wall_s"]})
arms = {}
for r in runs:
    arms.setdefault(r["run"].split("_")[0], []).append(r)
agg = {a: {"runs": len(v), "registered": [x["registered_certified"] for x in v], "strict": [x["strict_certified"] for x in v],
           "calls": [x["calls_used"] for x in v], "tokens": [x["tokens"] for x in v], "wall_s": [x["wall_s"] for x in v],
           "proof_term_library_deps": [x["proof_term_library_deps_direct"] for x in v],
           "cross_agent_deps": [x["proof_term_cross_agent_deps"] for x in v],
           "regex_uses_original": [x["regex_lemma_uses_original_summary"] for x in v],
           "median_calls": statistics.median(x["calls_used"] for x in v), "median_tokens": statistics.median(x["tokens"] for x in v),
           "median_wall_s": statistics.median(x["wall_s"] for x in v)} for a, v in sorted(arms.items())}
out = {"proofs_rescored": len(rows), "strict": sum(x["strictly_certified"] for x in rows),
       "reconstruction_failures": sum(not x["reconstructed_ok"] for x in rows), "mutant_accepted": sum(not x["mutant_rejected"] for x in rows),
       "helper_structure_violations": sum(bool(x.get("helper_structure_error")) for x in rows), "per_run": runs, "by_arm": agg}
(ROOT / "RESCORE_SUMMARY.json").write_text(json.dumps(out, indent=1) + "\n")
print(json.dumps({k: v for k, v in out.items() if k != "per_run"}, indent=1))
