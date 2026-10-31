"""Fuller audit (critic) of scopedesk/oracles (rethink-nca): (1) repair.enumerate validity + relative_change field; (2) gate.decide and its three ablations on the Turing items;
(3) pde.solve vs an independently derived exact linear key for the two declared kinetics. Independent derivations: Jacobians by sympy differentiation of the model
equations (not oracles.kinetics), exact Fractions for modes. Disagreements are findings. Usage: python3 -I audit_oracle_full.py ORACLE_CHECKOUT BENCH_DIR OUT.json [N_PDE]"""
import json, random, sys, time
from fractions import Fraction as F
import sympy as sp
root, bench, out = sys.argv[1:4]; NPDE = int(sys.argv[4]) if len(sys.argv) > 4 else 12
sys.path.insert(0, root); sys.path.insert(0, bench)
from scopedesk.oracles import repair, gate, pde, linear
import fam_turing as T, fam_turing2d as T2
full = [json.loads(l) for l in open(f"{bench}/instances_full.jsonl")]; key = {json.loads(l)["id"]: json.loads(l) for l in open(f"{bench}/key.jsonl")}
res = {}
# ---- (1) repairs. Oracle semantics (verified from outputs): `value` is a SCALE FACTOR s applied to all sides; relative_change = |s-1|.
bad, tot, rc_bad, empty, notmin, unsorted = [], 0, [], 0, [], 0
for it in full:
    if it["family"] not in ("turing_finite_domain", "turing_2d_rectangle"): continue
    k = key[it["id"]]
    if k["verdict"] != "out_of_scope" or k["condition_ids"] != ["DOMAIN_ADMISSIBLE_MODE"]: continue
    s = it["hidden"]["structured"]; J = tuple(F(x) for x in s["J"]); d = F(s["Dv"]); bc = s["bc"] or "neumann"; bcx = "periodic" if bc == "periodic" else "neumann"
    def ok_scale(sc):
        if it["family"] == "turing_finite_domain": return T.key_for(J, d, F(s["r_over_pi"]) * sc, bc if bc != "dirichlet" else "neumann")[0] == "applies"
        return bool(T2.unstable(J, d, F(s["a_over_pi"]) * sc, F(s["b_over_pi"]) * sc, bcx))
    r = repair.enumerate(s); reps = [x for x in r.get("repairs", []) if x["knob"] == "domain_length"]
    if not reps: empty += 1
    vals = [F(x["value"]) for x in reps]
    if [abs(x - 1) for x in vals] != sorted(abs(x - 1) for x in vals): unsorted += 1
    for rp in reps:
        tot += 1; sc = F(rp["value"])
        if not ok_scale(sc): bad.append({"id": it["id"], "scale": rp["value"]})
        if abs(rp["relative_change"] - float(abs(sc - 1))) > 1e-9: rc_bad.append({"id": it["id"], "value": rp["value"], "reported": rp["relative_change"]})
    grid = [F(kk, 4) for kk in range(1, 41)]; valid = [x for x in grid if ok_scale(x)]
    if valid and reps and min(abs(x - 1) for x in valid) < min(abs(x - 1) for x in vals): notmin.append({"id": it["id"], "oracle_first": str(vals[0]), "closer_valid_scale_on_k/4_grid": str(min(valid, key=lambda x: abs(x - 1)))})
res["repair"] = {"repairs_checked": tot, "invalid_by_independent_check": bad, "items_with_no_repair": empty, "relative_change_mismatches": rc_bad, "not_sorted_by_relative_change": unsorted, "closer_valid_scale_missed_on_k/4_grid": notmin,
                 "semantics_note": "value = scale factor on all sides; an earlier run of this audit misread it as a new length (my error, corrected here)"}
# ---- (2) gate + ablations
ab = {"n": 0, "default_agree": 0, "default_disagree": [], "hash_changed_refused": 0, "removed_equals_textbook": 0, "continuum_only_equals_textbook": 0}
for it in full:
    if it["family"] != "turing_finite_domain": continue
    s = it["hidden"]["structured"]; J = tuple(F(x) for x in s["J"]); d = F(s["Dv"]); k = key[it["id"]]
    if s["bc"] is None: continue
    ab["n"] += 1
    g = gate.decide(s); ab["default_agree"] += int(g["decision"] == k["verdict"])
    if g["decision"] != k["verdict"]: ab["default_disagree"].append({"id": it["id"], "gate": g["decision"], "key": k["verdict"]})
    tb = "applies" if (T.stable(J) and T.band(J, d)) else "out_of_scope"      # textbook: stable + continuum band
    ab["hash_changed_refused"] += int(gate.decide(s, record_hash_changed=True)["decision"] == "refused_source")
    ab["removed_equals_textbook"] += int(gate.decide(s, record_removed=True)["decision"] == tb)
    ab["continuum_only_equals_textbook"] += int(gate.decide(s, continuum_only=True)["decision"] == tb)
res["gate_ablations_1d_with_bc"] = ab
# ---- (3) pde vs independent exact linear key
u, v, g_ = sp.symbols("u v g")
def jac(model, pr):
    if model == "schnakenberg":
        a, b = pr["a"], pr["b"]; f = a - u + u**2*v; gg = b - u**2*v; us, vs = a + b, b/(a + b)**2
    else:
        A, B = pr["A"], pr["B"]; f = A - (B + 1)*u + u**2*v; gg = B*u - u**2*v; us, vs = A, B/A
    M = sp.Matrix([f, gg]).jacobian([u, v]).subs({u: us, v: vs}); return [[F(int(x.p), int(x.q)) for x in row] for row in M.tolist()]
def exact_unstable(model, pr, gamma, Dv, r):
    J = [[gamma*x for x in row] for row in jac(model, pr)]
    Jt = (J[0][0], J[0][1], J[1][0], J[1][1])
    if not T.stable(Jt): return None
    return bool(T.unstable(Jt, Dv, r, "neumann"))
rng = random.Random(5); cases = []
for model, pr in (("schnakenberg", {"a": F(1, 10), "b": F(9, 10)}), ("brusselator", {"A": F(3, 2), "B": F(2)})):
    for _ in range(NPDE // 2):
        cases.append((model, pr, F(rng.choice([1, 2, 4, 8])), F(rng.choice([5, 10, 16, 20, 40])), F(rng.choice([2, 4, 6]))))
pr_rows = []; t0 = time.time()
for model, pr, gamma, Dv, r in cases:
    ex = exact_unstable(model, pr, gamma, Dv, r)
    s = {"model": model, "gamma": str(gamma), "Dv": str(Dv), "r_over_pi": str(r), "bc": "neumann"}
    if model == "brusselator": s["params"] = {"A": str(pr["A"]), "B": str(pr["B"])}
    try: o = pde.solve(s, T_max=600.0)
    except Exception as e: o = {"category": "error:" + repr(e)[:60]}
    pr_rows.append({"model": model, "gamma": str(gamma), "Dv": str(Dv), "r": str(r), "exact_unstable": ex, "pde_category": o.get("category"), "pde_pattern": o.get("pattern"), "converged": o.get("converged"), "settled": o.get("settled")})
settled = [x for x in pr_rows if x["pde_category"] in ("pattern", "no_pattern")]
res["pde_vs_exact_linear"] = {"cases": len(pr_rows), "categories": {c: sum(x["pde_category"] == c for x in pr_rows) for c in sorted({x["pde_category"] for x in pr_rows})},
    "settled_agree_with_exact": sum((x["pde_category"] == "pattern") == bool(x["exact_unstable"]) for x in settled), "settled_n": len(settled),
    "disagreements": [x for x in settled if (x["pde_category"] == "pattern") != bool(x["exact_unstable"])], "seconds": round(time.time() - t0, 1), "rows": pr_rows,
    "caveat": "cases limited to the two declared kinetics; the exact key is LINEAR; nonlinear subcritical behaviour of linearly stable states is not probed (oracle declares this)"}
json.dump(res, open(out, "w"), indent=1)
print(json.dumps({k: ({a: b for a, b in v_.items() if a not in ("rows",)} if isinstance(v_, dict) else v_) for k, v_ in res.items()})[:3000])
