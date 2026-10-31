"""Two integrations of the same declared equations, both written by the same author (rethink-nca):
 A  spectral Strang splitting (exact cosine-mode diffusion, RK4 reaction), scopedesk.oracles.pde._run
 B  scipy BDF method of lines: cell-centred second-order finite differences with zero-flux ends, adaptive implicit time stepping,
    different grid (1.5x cells) and no shared stepping or discretisation code with A.
Both start from the SAME continuous initial perturbation (grid-independent modal series) so they are paired."""
from __future__ import annotations

import math
from fractions import Fraction as F

import numpy as np
from scipy.integrate import solve_ivp
from scipy.sparse import lil_matrix

from .. import kinetics, linear, pde

AMP_REL = 0.1
SETTLE_AMP = 0.05


def ic_modal(seed, K, L, N, amp_u, amp_v):
    """Perturbation = sum_{k=1..K} c_k cos(k pi x/L) on cell centres; coefficients scaled so the ANALYTIC std over the domain is amp (grid independent)."""
    rng = np.random.default_rng(seed)
    cu, cv = rng.standard_normal(K), rng.standard_normal(K)
    x = (np.arange(N) + 0.5) * L / N
    M = np.cos(np.outer(x, np.arange(1, K + 1)) * math.pi / L)
    out = []
    for c, amp in ((cu, amp_u), (cv, amp_v)):
        std = math.sqrt(0.5 * float(np.sum(c * c)))
        out.append(amp * (M @ c) / std)
    return out


def dominant_cos_mode(u):
    from scipy.fft import dct
    c = np.abs(dct(u - u.mean(), type=2, norm="ortho"))
    c[0] = 0
    return int(c.argmax())


def metrics(u_final, u_snap, ust):
    sd, sd0 = float(u_final.std()), float(u_snap.std())
    pattern = sd >= AMP_REL * abs(ust)
    m, m0 = dominant_cos_mode(u_final), dominant_cos_mode(u_snap)
    settled = (m == m0 and abs(sd - sd0) <= SETTLE_AMP * max(sd, 1e-12)) if pattern else (sd <= 0.02 * abs(ust) or sd <= 1.05 * sd0)
    return {"pattern": bool(pattern), "mode": m, "amp": sd, "settled": bool(settled)}


def run_cell_a(model, pp, Dv, L, N, T, amp_u, amp_v, seed, K, dt=0.02):
    pu, pv = ic_modal(seed, K, L, N, amp_u, amp_v)
    res = pde._run(model, pp, F(1), Dv, 1, "neumann", [L], [N], [K], T, dt, seed, ic=(pu, pv))
    if res["diverged"]:
        return {"diverged": True}
    ust = res["ust"]
    out = metrics(res["u"], res["snap"], ust)
    out["diverged"] = False
    out["cfl"] = dt * res["rho"]
    return out


def run_cell_b(model, pp, Dv, L, N, T, amp_u, amp_v, seed, K, rtol=1e-6, atol=1e-9):
    ust, vst = (float(z) for z in kinetics.steady(model, pp))
    pu, pv = ic_modal(seed, K, L, N, amp_u, amp_v)
    dx, dv = L / N, float(Dv)
    y0 = np.concatenate([ust + pu, vst + pv])
    dx2 = dx * dx

    def lap(x):
        xl = np.concatenate([x[:1], x[:-1]])
        xr = np.concatenate([x[1:], x[-1:]])
        return (xl - 2 * x + xr) / dx2

    def rhs(t, y):
        u, v = y[:N], y[N:]
        fu, fv = kinetics.react(model, pp, u, v)
        return np.concatenate([lap(u) + fu, dv * lap(v) + fv])

    S = lil_matrix((2 * N, 2 * N))
    for i in range(N):
        for sp in (0, N):
            for j in (i - 1, i, i + 1):
                if 0 <= j < N:
                    S[sp + i, sp + j] = 1
        S[i, N + i] = 1
        S[N + i, i] = 1
    sol = solve_ivp(rhs, (0, T), y0, method="BDF", t_eval=[0.9 * T, T], jac_sparsity=S.tocsc(), rtol=rtol, atol=atol)
    if not sol.success or sol.y.shape[1] < 2 or not np.isfinite(sol.y).all() or np.abs(sol.y).max() > 1e3:
        return {"diverged": True, "message": str(sol.message)[:80]}
    out = metrics(sol.y[:N, 1], sol.y[:N, 0], ust)
    out["diverged"] = False
    out["nfev"] = int(sol.nfev)
    return out
