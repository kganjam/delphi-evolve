"""Frozen sweep (grid fixed in this file before running): where does exact linear theory disagree with the converged nonlinear oracle?
Both kinetics models, 1-D Neumann/periodic and 2-D rectangles. Categories are reported as they come; nonconverged / not_settled
results are listed and never counted as agreement or disagreement."""
from __future__ import annotations

import itertools
import json
import sys
import time
from collections import Counter
from pathlib import Path

from . import linear, pde

OUT = Path("scopedesk/oracles/results/linear_vs_nonlinear.json")


def configs():
    cs = []
    for g, d, r in itertools.product(["1/2", "1", "2"], ["5", "10", "20"], ["4", "8", "16"]):
        cs.append({"model": "schnakenberg", "gamma": g, "Dv": d, "r_over_pi": r, "bc": "neumann"})
    for g, d, r in itertools.product(["1/2", "1", "2"], ["10", "16", "30"], ["4", "8", "16"]):
        cs.append({"model": "brusselator", "gamma": g, "Dv": d, "r_over_pi": r, "bc": "neumann"})
    for model, d in (("schnakenberg", "20"), ("brusselator", "16")):
        for g, r in itertools.product(["1", "2"], ["4", "8", "16"]):
            cs.append({"model": model, "gamma": g, "Dv": d, "r_over_pi": r, "bc": "periodic"})
    for model, d in (("schnakenberg", "20"), ("brusselator", "16")):
        for (a, b), g in itertools.product([("2", "3"), ("4", "4"), ("6", "3")], ["1"]):
            cs.append({"model": model, "gamma": g, "Dv": d, "a_over_pi": a, "b_over_pi": b, "bc": "neumann"})
    # same linear problem, different nonlinearity: Brusselator A=1,B=9/5 has the Schnakenberg default Jacobian
    for r in ("4", "8", "16"):
        cs.append({"model": "brusselator", "params": {"A": "1", "B": "9/5"}, "gamma": "1", "Dv": "20", "r_over_pi": r, "bc": "neumann", "tag": "same_J_as_schnakenberg"})
        cs.append({"model": "schnakenberg", "gamma": "1", "Dv": "20", "r_over_pi": r, "bc": "neumann", "tag": "same_J_as_schnakenberg"})
    # near-onset: Dv just above the critical ratio
    for model, d in (("schnakenberg", "9"), ("schnakenberg", "10"), ("brusselator", "13"), ("brusselator", "14")):
        cs.append({"model": model, "gamma": "1", "Dv": d, "r_over_pi": "16", "bc": "neumann", "tag": "near_onset"})
    return cs


def main(rerun_unscored=False):
    rows, t0 = [], time.time()
    prev = json.loads(OUT.read_text())["rows"] if rerun_unscored else None
    for i, c in enumerate(configs()):
        lin = linear.check(c)
        if prev is not None and prev[i]["pde_category"] in ("pattern", "no_pattern"):
            rows.append(prev[i])      # unchanged by the CFL fix (those runs had CFL <= 0.5 under the cruder bound)
            continue
        res = pde.solve(c)
        row = {"config": c, "linear_scope_verdict": lin["scope_verdict"], "linear_condition_ids": lin["condition_ids"],
               "linear_fastest_mode": (lin.get("witness") or {}).get("fastest_growing_mode", {}).get("index"),
               "pde_category": res["category"], "pde_pattern": res.get("pattern"), "pde_m_dom": res.get("m_dom"), "pde_amp": res.get("amp"),
               "converged": res.get("converged"), "settled": res.get("settled"), "horizon_tau": res.get("horizon_tau"),
               "disagrees_with_linear": res.get("disagrees_with_linear"), "refusal": res.get("refusal"), "why_nonconverged": res.get("why")}
        if row["linear_fastest_mode"] and row["pde_m_dom"] and len(row["linear_fastest_mode"]) == len(row["pde_m_dom"]):
            row["mode_matches_fastest_linear"] = list(row["linear_fastest_mode"]) == list(row["pde_m_dom"])
        if prev is not None:
            row["previous_category"] = prev[i]["pde_category"]
            row["previous_why_nonconverged"] = prev[i].get("why_nonconverged")
        rows.append(row)
        print(i, c.get("model"), c["Dv"], res["category"], row.get("mode_matches_fastest_linear"), round(time.time() - t0), flush=True)
    cats = Counter(r["pde_category"] for r in rows)
    scored = [r for r in rows if r["pde_category"] in ("pattern", "no_pattern")]
    dis = [r for r in scored if r["disagrees_with_linear"]]
    modes = [r for r in scored if "mode_matches_fastest_linear" in r and r["pde_pattern"]]
    summ = {"n_configs": len(rows), "pde_categories": dict(cats), "scored_for_linear_agreement": len(scored),
            "linear_nonlinear_disagreements": len(dis), "disagreement_ids": [r["config"] for r in dis],
            "dominant_mode_equals_fastest_linear_mode": f"{sum(r['mode_matches_fastest_linear'] for r in modes)}/{len(modes)}",
            "wall_s": time.time() - t0}
    OUT.write_text(json.dumps({"summary": summ, "rows": rows}, indent=1))
    print(json.dumps(summ, indent=1))


if __name__ == "__main__":
    sys.exit(main(rerun_unscored="--rerun-unscored" in sys.argv))
