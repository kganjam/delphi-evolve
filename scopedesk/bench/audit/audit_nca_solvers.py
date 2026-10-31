"""Audit (critic, 2026-10-31) of the NCA worker's frozen solver layer (experiments/rethink_nca/rd.py, read-only import from its checkout)
against an EXACT rational linear key for the same declared model (Schnakenberg, a=1/10, b=9/10, J = gamma*J1, J1=[[4/5,1],[-9/5,-1]], D=(1,d), Neumann 1-D, L=r*pi).
Exact key: linear instability iff some n>=1 has det(J - qD) < 0 with q=(n/r)^2 (Fractions). Compared:
  A) rd.linear_sigma sign vs exact key (floating eigenvalues),
  B) nonlinear spectral_strang 'patterned' (amp>=0.1 at T) vs the exact linear key  -> disagreements are findings (slow growth / subcritical),
  C) rd.euler_fd vs rd.spectral_strang patterned flags (solver agreement).
Cases whose exact |det| margin at the best mode is < 1e-9 relative are listed as excluded. Usage: python3 -I audit_nca_solvers.py NCA_CHECKOUT OUT.json"""
import json, sys, time
from fractions import Fraction as F
import numpy as np
nca, out = sys.argv[1], sys.argv[2]
sys.path.insert(0, nca)
from experiments.rethink_nca import rd

J1 = [[F(4, 5), F(1)], [F(-9, 5), F(-1)]]
def exact_unstable(g, d, r, nmax=400):
    best = None
    for n in range(1, nmax + 1):
        q = (F(n) / r) ** 2
        A = g * J1[0][0] - q * 1; B = g * J1[0][1]; C = g * J1[1][0]; E = g * J1[1][1] - q * d
        det = A * E - B * C
        if best is None or det < best[0]: best = (det, n)
        if det < 0: return True, n, det
    return False, best[1], best[0]

GS = [F(k, 4) for k in (1, 2, 3, 4, 6, 8, 12, 16, 24, 32, 48, 64, 96, 128, 160)]
DS = [F(5), F(10), F(20), F(40)]
RS = [2, 4, 8, 16]
cases = [(g, d, r) for r in RS for d in DS for g in GS]
rows, excluded = [], []
t0 = time.time()
for r in RS:
    sub = [(g, d) for (g, d, rr) in cases if rr == r]
    keys = [exact_unstable(g, d, F(r)) for g, d in sub]
    S = len(sub); N = rd.n_cells(r); T = 300.0
    gam = np.array([float(g) for g, _ in sub]); dd = np.array([float(d) for _, d in sub])
    st = rd.initial_state(S, N, seeds=np.arange(S) + 1000 * r)
    fin_s, _ = rd.spectral_strang(st, gam, dd, r, T)
    pm_s = rd.pattern_metrics(fin_s[:, 0], r)
    dt = rd.euler_dt(gam, dd)
    fin_e = rd.euler_fd(st, gam, dd, T, dt=dt)
    fin_e = fin_e[0] if isinstance(fin_e, tuple) else fin_e
    pm_e = rd.pattern_metrics(fin_e[:, 0], r)
    for i, ((g, d), (uns, n, det)) in enumerate(zip(sub, keys)):
        sig, arg = rd.linear_sigma(float(g), float(d), r)
        margin = abs(float(det))
        rows.append({"gamma": str(g), "d": str(d), "r": r, "exact_unstable": bool(uns), "exact_mode": n, "exact_det_best": float(det),
                     "linear_sigma": float(sig), "linear_sigma_mode": int(arg), "spectral_patterned": bool(pm_s["patterned"][i]), "euler_patterned": bool(pm_e["patterned"][i]),
                     "spectral_amp": float(pm_s["amp"][i]), "finite": bool(np.isfinite(fin_s[i]).all() and np.isfinite(fin_e[i]).all())})
A = [r for r in rows if abs(r["linear_sigma"]) > 1e-9]
agreeA = sum((r["linear_sigma"] > 0) == r["exact_unstable"] for r in A)
tab = {}
for r in rows:
    k = f"exact_unstable={r['exact_unstable']}|spectral_patterned={r['spectral_patterned']}"; tab[k] = tab.get(k, 0) + 1
agreeC = sum(r["spectral_patterned"] == r["euler_patterned"] for r in rows)
res = {"n_cases": len(rows), "T_tau": 300.0, "seconds": round(time.time() - t0, 1),
       "A_linear_sigma_vs_exact": {"agree": agreeA, "n": len(A), "excluded_|sigma|<=1e-9": len(rows) - len(A),
                                    "disagree": [r for r in A if (r["linear_sigma"] > 0) != r["exact_unstable"]]},
       "B_nonlinear_vs_exact_linear_table": tab,
       "B_findings": [r for r in rows if r["exact_unstable"] != r["spectral_patterned"]][:30],
       "C_euler_vs_spectral_patterned_agree": [agreeC, len(rows)],
       "nonfinite_cases": sum(not r["finite"] for r in rows), "rows": rows,
       "caveat": "declared Schnakenberg model on a pi-multiple grid; 'patterned' = u.std >= 0.1 at tau=300 from 1e-2 noise; not a convergence study; T may be too short for slow growth near threshold"}
json.dump(res, open(out, "w"), indent=1)
print({k: v for k, v in res.items() if k not in ("rows", "B_findings")} | {"A_linear_sigma_vs_exact": {k: (v if k != "disagree" else len(v)) for k, v in res["A_linear_sigma_vs_exact"].items()}})
