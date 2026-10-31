"""Audit (critic) of oracles.pde.solve on 2-D rectangles vs an independently derived exact linear key (sympy Jacobian of the declared Schnakenberg kinetics, exact Neumann modes
q=(m/a)^2+(n/b)^2 via fam_turing2d). Small seeded sample; non-converged / not_settled results are reported, not scored. Usage: python3 -I audit_pde_2d.py ORACLE BENCH_DIR OUT.json [N]"""
import json, random, sys, time
from fractions import Fraction as F
import sympy as sp
root, bench, out = sys.argv[1:4]; N = int(sys.argv[4]) if len(sys.argv) > 4 else 8
sys.path.insert(0, root); sys.path.insert(0, bench)
from scopedesk.oracles import pde
import fam_turing as T, fam_turing2d as T2
u, v = sp.symbols("u v"); a_, b_ = F(1, 10), F(9, 10)
M = sp.Matrix([sp.Rational(1, 10) - u + u**2*v, sp.Rational(9, 10) - u**2*v]).jacobian([u, v]).subs({u: 1, v: sp.Rational(9, 10)})
J1 = [[F(int(x.p), int(x.q)) for x in row] for row in M.tolist()]
rng = random.Random(9); rows = []; t0 = time.time()
cases = [(F(rng.choice([1, 2, 4, 8])), F(rng.choice([5, 10, 20, 40])), F(rng.choice([2, 3, 4])), F(rng.choice([2, 3, 4]))) for _ in range(N)]
for g, Dv, a, b in cases:
    J = (g*J1[0][0], g*J1[0][1], g*J1[1][0], g*J1[1][1])
    ex = bool(T2.unstable(J, Dv, a, b, "neumann")) if T.stable(J) else None
    s = {"model": "schnakenberg", "gamma": str(g), "Dv": str(Dv), "a_over_pi": str(a), "b_over_pi": str(b), "bc": "neumann"}
    try: o = pde.solve(s, T_max=600.0)
    except Exception as e: o = {"category": "error:" + repr(e)[:80]}
    rows.append({"gamma": str(g), "Dv": str(Dv), "a": str(a), "b": str(b), "exact_unstable": ex, "category": o.get("category"), "converged": o.get("converged"), "settled": o.get("settled")})
settled = [r for r in rows if r["category"] in ("pattern", "no_pattern")]
res = {"cases": len(rows), "categories": {c: sum(r["category"] == c for r in rows) for c in sorted({r["category"] for r in rows})}, "settled_n": len(settled),
       "settled_agree": sum((r["category"] == "pattern") == bool(r["exact_unstable"]) for r in settled), "disagreements": [r for r in settled if (r["category"] == "pattern") != bool(r["exact_unstable"])],
       "seconds": round(time.time() - t0, 1), "rows": rows, "caveat": "tiny sample; declared kinetics; exact key is LINEAR; subcritical behaviour not probed"}
json.dump(res, open(out, "w"), indent=1); print({k: v_ for k, v_ in res.items() if k != "rows"})
