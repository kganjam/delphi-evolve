"""Audit (critic) of oracles.repair.enumerate knobs reaction_scale and diffusion_ratio on the turing_finite_domain out_of_scope items of bench v1.2 (completes the knob coverage begun in audit_oracle_full.py).
Semantics inferred from outputs and then CHECKED: reaction_scale value s = multiplier on J (relative_change=|s-1|); diffusion_ratio value = new Dv (relative_change=|Dv'-Dv|/Dv).
Independent check: exact Fractions via fam_turing.key_for with the changed J or Dv. Also checks ordering and, on grids, whether a closer valid value was missed.
Usage: python3 -I audit_repair_knobs.py ORACLE_CHECKOUT BENCH_DIR OUT.json"""
import json, sys
from fractions import Fraction as F
root, bench, out = sys.argv[1:4]
sys.path.insert(0, root); sys.path.insert(0, bench)
from scopedesk.oracles import repair
import fam_turing as T
full = [json.loads(l) for l in open(f"{bench}/instances_full.jsonl")]; key = {json.loads(l)["id"]: json.loads(l) for l in open(f"{bench}/key.jsonl")}
res = {"reaction_scale": {"checked": 0, "invalid": [], "relative_change_mismatch": [], "unsorted_items": 0, "closer_valid_missed": []},
       "diffusion_ratio": {"checked": 0, "invalid": [], "relative_change_mismatch": [], "unsorted_items": 0, "closer_valid_missed": []}, "items": 0, "items_with_no_repair_for_knob": {"reaction_scale": 0, "diffusion_ratio": 0}}
for it in full:
    if it["family"] != "turing_finite_domain" or key[it["id"]]["verdict"] != "out_of_scope": continue
    s = it["hidden"]["structured"]; J = tuple(F(x) for x in s["J"]); d = F(s["Dv"]); r = F(s["r_over_pi"]); bc = s["bc"] or "neumann"; bcx = "dirichlet" if bc == "dirichlet" else bc
    res["items"] += 1
    reps = repair.enumerate(s).get("repairs", [])
    def ok(Jx, dx): return T.key_for(Jx, dx, r, "neumann" if bcx == "dirichlet" else bcx)[0] == "applies"
    for knob in ("reaction_scale", "diffusion_ratio"):
        kr_all = [x for x in reps if x["knob"] == knob]; kr = [x for x in kr_all if x.get("value") is not None]; R = res[knob]
        if kr_all and not kr: R.setdefault("oracle_says_no_repair_in_grid", []).append(it["id"])
        if not kr: res["items_with_no_repair_for_knob"][knob] += 1
        vals = [F(x["value"]) for x in kr]
        rc = [abs(v - 1) if knob == "reaction_scale" else abs(v - d) / d for v in vals]
        if rc != sorted(rc): R["unsorted_items"] += 1
        for x, v in zip(kr, vals):
            R["checked"] += 1
            valid = ok(tuple(v * e for e in J), d) if knob == "reaction_scale" else ok(J, v)
            if not valid: R["invalid"].append({"id": it["id"], "value": x["value"]})
            exp = float(abs(v - 1) if knob == "reaction_scale" else abs(v - d) / d)
            if abs(x["relative_change"] - exp) > 1e-9: R["relative_change_mismatch"].append({"id": it["id"], "value": x["value"], "reported": x["relative_change"], "expected": exp})
        grid = [F(k, 4) for k in range(1, 61)] if knob == "reaction_scale" else [F(k, 2) for k in range(1, 400)]
        valid_grid = [g for g in grid if (ok(tuple(g * e for e in J), d) if knob == "reaction_scale" else ok(J, g))]
        dist = (lambda g: abs(g - 1)) if knob == "reaction_scale" else (lambda g: abs(g - d) / d)
        if valid_grid and kr and min(dist(g) for g in valid_grid) < min(rc): R["closer_valid_missed"].append({"id": it["id"], "oracle_first": str(vals[0]), "closer": str(min(valid_grid, key=dist))})
        if valid_grid and not kr: R.setdefault("no_repair_reported_but_valid_value_on_my_grid", []).append({"id": it["id"], "my_grid_value": str(min(valid_grid, key=dist))})
json.dump(res, open(out, "w"), indent=1)
print(json.dumps({k: ({a: (b if not isinstance(b, list) else len(b)) for a, b in v.items()} if isinstance(v, dict) else v) for k, v in res.items()}))
for knob in ("reaction_scale", "diffusion_ratio"):
    for m in res[knob]["closer_valid_missed"][:5] + res[knob]["invalid"][:5] + res[knob]["relative_change_mismatch"][:5]: print(knob, m)
