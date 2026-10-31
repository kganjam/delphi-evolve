"""Run the oracle layer against the critic's Scope Desk bench (v1.1 layout: instances_full.jsonl + key.jsonl) for the Turing
families, with the gate ablations and the plain-formula baseline C0 ALWAYS reported alongside.
Usage: python3 -m scopedesk.oracles.audit_v1_1 BENCHDIR OUT.json   (BENCHDIR contains instances_full.jsonl and key.jsonl)
Disagreements with the key are findings, listed row by row; nothing is tuned to the key."""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

from . import gate, linear

FAMS = ("turing_finite_domain", "turing_2d_rectangle", "wavelength_formula_licence")


def main(bench, out):
    full = [json.loads(l) for l in open(Path(bench) / "instances_full.jsonl")]
    key = {json.loads(l)["id"]: json.loads(l) for l in open(Path(bench) / "key.jsonl")}
    rows = []
    for it in full:
        if it["family"] not in FAMS:
            continue
        s, k = it["hidden"]["structured"], key[it["id"]]
        if it["family"] == "wavelength_formula_licence":
            r = gate.wavelength_licence(s)
            rows.append({"id": it["id"], "family": it["family"], "key": k["verdict"], "key_conditions": k["condition_ids"],
                         "oracle": r["scope_verdict"], "oracle_conditions": r.get("condition_ids"), "margin": r.get("margin_to_10pct"),
                         "agree": r["scope_verdict"] == k["verdict"], "conditions_agree": sorted(r.get("condition_ids") or []) == sorted(k["condition_ids"])})
            continue
        lin = linear.check(s)
        base = linear.plain_formula(s)
        d = {m: gate.decide(s, **fl) for m, fl in (("full", {}), ("record_removed", {"record_removed": True}),
                                                    ("record_hash_changed", {"record_hash_changed": True}),
                                                    ("continuum_only", {"continuum_only": True}))}
        rows.append({"id": it["id"], "family": it["family"], "key": k["verdict"], "key_conditions": k["condition_ids"],
                     "oracle": lin["scope_verdict"], "oracle_conditions": lin["condition_ids"], "agree": lin["scope_verdict"] == k["verdict"],
                     "conditions_agree": sorted(lin["condition_ids"]) == sorted(k["condition_ids"]), "refusal": lin.get("refusal"),
                     "C0_plain_formula": base["scope_verdict"], "C0_agree": base["scope_verdict"] == k["verdict"],
                     **{f"gate_{m}": d[m]["decision"] for m in d}, **{f"gate_{m}_agree": d[m]["decision"] == k["verdict"] for m in d}})
    res = {"n": len(rows), "by_family": {}, "rows": rows,
           "note": "key = critic's frozen bench; gate ablations: record_removed -> falls back to the plain formula (no scope), record_hash_changed -> refuses (provenance), continuum_only -> records valid but admissibility ignored"}
    for fam in FAMS:
        fr = [r for r in rows if r["family"] == fam]
        if not fr:
            continue
        e = {"n": len(fr), "oracle_agree": sum(r["agree"] for r in fr), "conditions_agree": sum(r["conditions_agree"] for r in fr)}
        if "C0_agree" in fr[0]:
            e["C0_plain_formula_agree"] = sum(r["C0_agree"] for r in fr)
            for m in ("full", "record_removed", "record_hash_changed", "continuum_only"):
                e[f"gate_{m}_agree"] = sum(r[f"gate_{m}_agree"] for r in fr)
            e["key_verdict_counts"] = dict(Counter(r["key"] for r in fr))
        res["by_family"][fam] = e
    res["disagreements"] = [r for r in rows if not r["agree"]]
    Path(out).write_text(json.dumps(res, indent=1))
    print(json.dumps(res["by_family"], indent=1))
    print("disagreements:", [(r["id"], r["key"], r["oracle"]) for r in res["disagreements"]])


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
