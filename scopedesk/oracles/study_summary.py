"""Post-process linear_vs_nonlinear.json: compare the exact gate and the plain formula C0 against the converged PDE outcome."""
import json
from collections import Counter
from pathlib import Path

from . import linear

P = Path("scopedesk/oracles/results/linear_vs_nonlinear.json")
d = json.loads(P.read_text())
rows = d["rows"]
tab = []
for r in rows:
    c = r["config"]
    base = linear.plain_formula(c)["scope_verdict"]
    r["C0_plain_formula"] = base
    if r["pde_category"] in ("pattern", "no_pattern"):
        truth = "applies" if r["pde_pattern"] else "out_of_scope"
        tab.append({"config": c, "truth_pde": truth, "gate": r["linear_scope_verdict"], "C0": base})
out = {"n_scored": len(tab),
       "gate_equals_pde": sum(t["gate"] == t["truth_pde"] for t in tab),
       "C0_equals_pde": sum(t["C0"] == t["truth_pde"] for t in tab),
       "gate_wrong": [t for t in tab if t["gate"] != t["truth_pde"]],
       "C0_wrong_not_gate_wrong": [t["config"] for t in tab if t["C0"] != t["truth_pde"] and t["gate"] == t["truth_pde"]],
       "category_counts": dict(Counter(r["pde_category"] for r in rows)),
       "nonconverged_or_unsettled": [{"config": r["config"], "category": r["pde_category"], "why": r.get("why_nonconverged"), "linear": r["linear_scope_verdict"]}
                                     for r in rows if r["pde_category"] not in ("pattern", "no_pattern")]}
d["gate_vs_C0_vs_pde"] = out
P.write_text(json.dumps(d, indent=1))
print(json.dumps({k: v for k, v in out.items() if k not in ("gate_wrong", "nonconverged_or_unsettled", "C0_wrong_not_gate_wrong")}, indent=1))
print("gate wrong:", [(t['config'], t['gate'], t['truth_pde']) for t in out["gate_wrong"]])
print("nonconv/unsettled:", len(out["nonconverged_or_unsettled"]))
