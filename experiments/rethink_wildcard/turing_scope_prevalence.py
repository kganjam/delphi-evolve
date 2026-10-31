"""Cheap-compute check of the 'GPU counterexample search' claim. 2x2 Turing screen on N random Jacobians.
For each stable J (tr<0, det>0) and diffusion ratio d=Dv/Du, the continuum instability band is the interval of
q=k^2 where det(J - qD)<0. On a 1-D Neumann domain of length L admissible q=(n*pi/L)^2, n=1,2,...
We count 'textbook-pass but no admissible mode'. The sampling prior (J~N(0,1) entries, log10 d~U(0,2), Du=1) is
ARBITRARY and the prevalence depends on it and on length units; this measures compute cost and illustrates scope
dependence, not how often real models are misapplied. Usage: python3 -I turing_scope_prevalence.py N OUT.json"""
import json, sys, time
import numpy as np
N = int(sys.argv[1]); out = sys.argv[2]
t0 = time.time(); rng = np.random.default_rng(0)
a, b, c, e = (rng.standard_normal(N) for _ in range(4))     # J = [[a,b],[c,e]]
d = 10 ** rng.uniform(0, 2, N); Du = 1.0; Dv = d
tr = a + e; det = a * e - b * c
stable = (tr < 0) & (det > 0)
# det(J - qD) = Du*Dv q^2 - (Dv*a + Du*e) q + det
A = Du * Dv; B = -(Dv * a + Du * e); C = det
disc = B * B - 4 * A * C
turing = stable & (B < 0) & (disc > 0)                      # B<0 means (Dv a+Du e)>0 ; positive roots exist
sq = np.sqrt(np.where(disc > 0, disc, 0))
qlo = (-B - sq) / (2 * A); qhi = (-B + sq) / (2 * A)
res = {"N": N, "n_stable": int(stable.sum()), "n_continuum_turing": int(turing.sum())}
for name, L in [("pi", np.pi), ("2pi", 2 * np.pi), ("5pi", 5 * np.pi), ("20pi", 20 * np.pi)]:
    # smallest admissible n with q=(n pi/L)^2 >= qlo; admissible iff that q < qhi
    n = np.maximum(1, np.ceil(np.sqrt(np.maximum(qlo, 0)) * L / np.pi))
    q = (n * np.pi / L) ** 2
    ok = turing & (q > qlo) & (q < qhi)
    res[f"L={name}"] = {"admissible_mode": int(ok.sum()), "continuum_pass_but_no_mode": int((turing & ~ok).sum()),
                        "frac_of_continuum_pass_without_mode": float((turing & ~ok).sum() / max(1, turing.sum()))}
res["seconds_cpu_single_thread"] = round(time.time() - t0, 2)
json.dump(res, open(out, "w"), indent=1); print(json.dumps(res, indent=1))
