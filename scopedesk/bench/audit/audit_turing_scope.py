"""Audit of the EXISTING exact oracle turing_scope.adapter.analyze (authored by the turing-scope worker, a different session) against the
Scope Desk key for the turing_finite_domain family. Maps adapter output -> verdict: linearly_unstable -> applies; 'stable' -> out_of_scope;
any refusal -> recorded with its code. Neumann items are compared directly; Dirichlet shares the Neumann mode set (so the adapter's
Neumann refusal for Dirichlet is expected scope behaviour, but the verdict is still derivable); periodic / unstated BC items are
expected to be refused by the adapter (unsupported boundary) - reported, not scored as disagreements.
Usage: python3 -I audit_turing_scope.py BENCHDIR REPO_ROOT OUT.json"""
import json, sys
bench, root, out = sys.argv[1:4]
sys.path.insert(0, root)
from turing_scope.adapter import analyze
full = [json.loads(l) for l in open(f"{bench}/instances_full.jsonl")]
key = {json.loads(l)["id"]: json.loads(l) for l in open(f"{bench}/key.jsonl")}
rows, summ = [], {"neumann": [0, 0], "dirichlet_as_neumann": [0, 0]}
for it in full:
    if it["family"] != "turing_finite_domain": continue
    s = it["hidden"]["structured"]; k = key[it["id"]]
    bc = s["bc"]
    req_bc = "neumann_zero_flux" if bc in ("neumann", "dirichlet") else ("periodic" if bc == "periodic" else "unspecified")
    req = {"request_id": it["id"], "system": {"kind": "two_species_reaction_diffusion_linearization", "jacobian": [s["J"][:2], s["J"][2:]],
           "diffusivities": ["1", s["Dv"]], "fixed_point": {"declared": True, "description": "declared by requester"}},
           "domain": {"dimension": 1, "boundary": req_bc, "length_over_pi": s["r_over_pi"]},
           "assumptions": {"linearization_about_homogeneous_steady_state": True, "fixed_domain_no_growth": True, "no_mechanical_coupling": True}}
    res = analyze(req)
    v = res.get("verdict"); mapped = {"linearly_unstable": "applies", "stable": "out_of_scope"}.get(v, "refused:" + str(res.get("refusal", res.get("code", v))))
    row = {"id": it["id"], "bc": bc, "key": k["verdict"], "adapter_verdict": v, "mapped": mapped}
    if bc in ("neumann", "dirichlet"):
        ok = (mapped == k["verdict"]) or (mapped.startswith("refused") and k["condition_ids"] == ["WELLMIXED_STABLE"] and k["verdict"] == "out_of_scope")
        row["agree"] = ok; summ["neumann" if bc == "neumann" else "dirichlet_as_neumann"][0] += int(ok); summ["neumann" if bc == "neumann" else "dirichlet_as_neumann"][1] += 1
    rows.append(row)
refused_other = [r for r in rows if r["bc"] in ("periodic", None)]
res = {"agree_counts_[agree,n]": summ, "disagreements": [r for r in rows if r.get("agree") is False],
       "periodic_or_unstated_bc_items": {"n": len(refused_other), "adapter_mapped_counts": {m: sum(r["mapped"] == m for r in refused_other) for m in sorted({r["mapped"] for r in refused_other})}},
       "note": "adapter refusals on periodic/unstated BC are its documented scope; they are not oracle errors but show the oracle alone cannot label BC-variant items",
       "rows": rows}
json.dump(res, open(out, "w"), indent=1)
print(summ, "disagreements:", len(res["disagreements"]), res["periodic_or_unstated_bc_items"])
for r in res["disagreements"]: print(r)
