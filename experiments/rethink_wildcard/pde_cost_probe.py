"""Cost probe for the proposed 'dynamical tier' (100 nonlinear reaction-diffusion solves to T=1000).
Batched IMEX (implicit diffusion in cosine basis, explicit reaction) Schnakenberg on a 1-D Neumann domain,
100 instances (L in {pi,2pi,5pi,10pi,20pi}, small random ICs), N=128 modes, dt=0.02, T=1000, ONE CPU thread.
Measures wall time and whether a final pattern amplitude exceeds a (arbitrary) threshold. Numerics are NOT converged-
validated here (no dt/N refinement) -- this only bounds the compute cost and shows the claim 'stable pattern at T=1000'
needs an operational definition (threshold, IC, discretisation) before any oracle can settle it."""
import json, sys, time
import numpy as np
from scipy.fft import dct, idct
B, N, T, dt = 100, 128, 1000.0, 0.02
rng = np.random.default_rng(0)
Ls = np.pi * rng.choice([1, 2, 5, 10, 20], B)
gam, a, b, Du, Dv = 1.0, 0.1, 0.9, 1.0, 20.0
us, vs = a + b, b / (a + b) ** 2
k2 = (np.arange(N)[None, :] * np.pi / Ls[:, None]) ** 2           # (B,N) Neumann cosine eigenvalues
u = us + 1e-3 * rng.standard_normal((B, N)); v = vs + 1e-3 * rng.standard_normal((B, N))
den_u = 1 + dt * Du * k2; den_v = 1 + dt * Dv * k2
t0 = time.time()
for _ in range(int(T / dt)):
    f = gam * (a - u + u * u * v); g = gam * (b - u * u * v)
    uh = dct(u + dt * f, type=2, norm="ortho", axis=1) / den_u
    vh = dct(v + dt * g, type=2, norm="ortho", axis=1) / den_v
    u = idct(uh, type=2, norm="ortho", axis=1); v = idct(vh, type=2, norm="ortho", axis=1)
    if not np.isfinite(u).all(): break
el = time.time() - t0
amp = u.max(1) - u.min(1)
res = {"instances": B, "N": N, "T": T, "dt": dt, "wall_seconds_one_cpu_thread": round(el, 1),
       "finite": bool(np.isfinite(u).all()),
       "frac_amp_gt_0.1": float((amp > 0.1).mean()),
       "by_L_over_pi": {int(round(L / np.pi)): float((amp[Ls == L] > 0.1).mean()) for L in sorted(set(Ls))},
       "caveat": "no refinement study; threshold 0.1 arbitrary; illustrates cost, not a settled oracle"}
json.dump(res, open(sys.argv[1], "w"), indent=1); print(json.dumps(res, indent=1))
