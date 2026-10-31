"""Converged nonlinear PDE oracle (evidence kind: simulated, declared model; nothing observed).

Solver: Strang splitting with EXACT spectral diffusion (Neumann: cosine modes via DCT-II on cell centres; periodic: FFT) and RK4
reaction substeps, 1-D intervals and 2-D rectangles, two declared kinetics (kinetics.py). In tau = gamma*t units the
diffusivities are (1/gamma, Dv/gamma) and the kinetics are gamma-free.

Convergence is a CATEGORY, not a hope. Each solve runs three times from the SAME initial condition function:
  base (dt, N)   refined dt (dt/2, N)   refined grid (dt, 2N)
The initial perturbation is a band-limited modal series (cos(k pi x/L) or Fourier modes up to the coarse grid's Nyquist/2), evaluated at
cell centres, so the doubled grid sees the identical function. (My earlier probe drew white noise per grid, which made 'grid doubled'
disagree for realisation reasons; that is fixed here.) Declared converged iff all three runs agree on: patterned flag, dominant
mode index, and final amplitude within 10%. Otherwise category = 'nonconverged' and the result is never scored as success.
'settled' additionally requires the dominant mode and amplitude to be unchanged between 90% and 100% of the horizon; slow growth near
onset yields category 'not_settled'.

EXPLICIT VALIDITY LIMITS (also returned in `validity`):
  * Not valid, and never used here: explicit Euler finite differences with a diffusion-only step bound. The critic found it flips the verdict
    at large gamma because the reaction time scale is ignored (rd.euler_dt now caps dt, scored probe unaffected).
  * dt_tau * (largest pointwise reaction-Jacobian 1-norm sampled along the base run) <= 0.5; if violated dt is reduced ONCE (0.25/rho, floor 0.004) and all three runs repeat; still violated => nonconverged ('dt_cfl'). (v1 of this check used a crude amplitude bound and wrongly rejected 17 of 82 sweep configs whose three runs agreed.)
  * >= 16 cells per wavelength of the largest unstable wavenumber (grid refined automatically; refuses above 256 cells per side / 2-D 128x128).
  * Horizon T_tau = clip(30 / sigma_max, 300, T_max); if 30/sigma_max > T_max the run is flagged horizon_limited.
  * Positivity is NOT enforced; non-finite or |u|>1e3 => category 'diverged'.
  * Finite-amplitude (nonlinear) instability of a linearly stable state is NOT probed: initial perturbations are small (eps=1e-2).
Pure-Jacobian instances (no `model`) are refused: there is no nonlinear equation to solve.
"""
from __future__ import annotations

import math
from fractions import Fraction as F

import numpy as np
from scipy.fft import dctn, fft, fft2, idctn

from . import kinetics, linear

EVIDENCE = "simulated"
AMP_REL = 0.1          # pattern threshold: std(u) >= 0.1 * |u*|
DT = 0.02
T_MIN, T_MAX = 300.0, 3000.0
DT_MIN = 0.004          # below this the adaptive step is refused as too costly (category nonconverged, why dt_cfl)
MAX_CELLS_1D, MAX_CELLS_2D = 256, 128
EPS = 1e-2


class PdeRefuse(Exception):
    def __init__(self, code, detail):
        super().__init__(code)
        self.code, self.detail = code, detail


def _cells(L, lam_min):
    """cells along a side of length L: dx <= min(pi/4, lam_min/16)."""
    dx = min(math.pi / 4, lam_min / 16)
    return max(8, int(math.ceil(L / dx)))


def _eigs(N, L, bc):
    k = np.arange(N)
    if bc == "neumann":
        return (k * math.pi / L) ** 2
    kk = np.where(k <= N // 2, k, k - N)     # periodic: fft ordering
    return (2 * math.pi * kk / L) ** 2


def _ic(rng_seed, Ks, dim, bc, Ls, Ns, eps):
    """Band-limited IC evaluated on grid Ns: same coefficient draw regardless of Ns. Returns (u', v') perturbations."""
    rng = np.random.default_rng(rng_seed)
    shape = tuple(Ks)
    out = []
    for _ in range(2):
        if bc == "neumann":
            c = rng.standard_normal(shape) / math.sqrt(np.prod(shape))
            f = c
            for ax in range(dim):
                x = (np.arange(Ns[ax]) + 0.5) * Ls[ax] / Ns[ax]
                M = np.cos(np.outer(x, np.arange(Ks[ax])) * math.pi / Ls[ax])       # (N, K)
                f = np.moveaxis(np.tensordot(M, np.moveaxis(f, ax, 0), axes=(1, 0)), 0, ax)
            out.append(eps * f)
        else:
            ca = rng.standard_normal(shape) / math.sqrt(np.prod(shape))
            cb = rng.standard_normal(shape) / math.sqrt(np.prod(shape))
            # separable Fourier features phase-shifted per axis: use cos and sin of 2 pi k x / L product expansion (dim<=2)
            f = np.zeros(tuple(Ns))
            if dim == 1:
                x = (np.arange(Ns[0]) + 0.5) * Ls[0] / Ns[0]
                for k in range(Ks[0]):
                    f += ca[k] * np.cos(2 * math.pi * k * x / Ls[0]) + cb[k] * np.sin(2 * math.pi * k * x / Ls[0])
            else:
                x = (np.arange(Ns[0]) + 0.5) * Ls[0] / Ns[0]
                y = (np.arange(Ns[1]) + 0.5) * Ls[1] / Ns[1]
                for i in range(Ks[0]):
                    for j in range(Ks[1]):
                        f += ca[i, j] * np.outer(np.cos(2 * math.pi * i * x / Ls[0]), np.cos(2 * math.pi * j * y / Ls[1])) \
                             + cb[i, j] * np.outer(np.sin(2 * math.pi * i * x / Ls[0]), np.sin(2 * math.pi * j * y / Ls[1]))
            out.append(eps * f)
    return out


def _run(model, p, gamma, Dv, dim, bc, Ls, Ns, Ks, T, dt, seed, checkpoint_frac=0.9, ic=None):
    ust, vst = (float(z) for z in kinetics.steady(model, p))
    du, dv = [float(x) for x in (F(1) / gamma, Dv / gamma)]
    lam = None
    if dim == 1:
        q = _eigs(Ns[0], Ls[0], bc)
    else:
        q = _eigs(Ns[0], Ls[0], bc)[:, None] + _eigs(Ns[1], Ls[1], bc)[None, :]
    mu, mv = np.exp(-du * q * dt / 2), np.exp(-dv * q * dt / 2)
    pu, pv = ic if ic is not None else _ic(seed, Ks, dim, bc, Ls, Ns, EPS)   # ic: optional explicit perturbation arrays (sweep)
    u, v = ust + pu, vst + pv
    axes = tuple(range(dim))

    def fwd(x):
        return dctn(x, type=2, norm="ortho", axes=axes) if bc == "neumann" else (fft(x, axis=0) if dim == 1 else fft2(x))

    def inv(c):
        if bc == "neumann":
            return idctn(c, type=2, norm="ortho", axes=axes)
        return np.fft.ifft(c, axis=0).real if dim == 1 else np.fft.ifft2(c).real

    def diff(x, m):
        return inv(fwd(x) * m)

    def rk4(u, v):
        f = lambda a, b: kinetics.react(model, p, a, b)
        k1u, k1v = f(u, v)
        k2u, k2v = f(u + .5 * dt * k1u, v + .5 * dt * k1v)
        k3u, k3v = f(u + .5 * dt * k2u, v + .5 * dt * k2v)
        k4u, k4v = f(u + dt * k3u, v + dt * k3v)
        return u + dt / 6 * (k1u + 2 * k2u + 2 * k3u + k4u), v + dt / 6 * (k1v + 2 * k2v + 2 * k3v + k4v)

    n = int(round(T / dt))
    chk = int(round(checkpoint_frac * n))
    snap = None
    maxabs = 0.0
    rho = 0.0
    for k in range(n):
        u, v = diff(u, mu), diff(v, mv)
        u, v = rk4(u, v)
        u, v = diff(u, mu), diff(v, mv)
        if (k + 1) == chk:
            snap = u.copy()
        if k % 200 == 0:
            m = float(max(np.abs(u).max(), np.abs(v).max()))
            maxabs = max(maxabs, m)
            rho = max(rho, float(kinetics.jac_norm(model, p, u, v).max()))
            if not np.isfinite(m) or m > 1e3:
                return {"diverged": True}
    maxabs = max(maxabs, float(np.abs(u).max()), float(np.abs(v).max()))
    rho = max(rho, float(kinetics.jac_norm(model, p, u, v).max()))
    return {"diverged": False, "u": u, "snap": snap, "ust": ust, "maxabs": maxabs, "rho": rho}


def _mode(u, dim, bc):
    f = u - u.mean()
    if bc == "neumann":
        c = np.abs(dctn(f, type=2, norm="ortho", axes=tuple(range(dim))))
        if dim == 1:
            c[0] = 0
            return (int(c.argmax()),)
        c[0, 0] = 0
        return tuple(int(i) for i in np.unravel_index(c.argmax(), c.shape))
    c = np.abs(np.fft.fft(f) if dim == 1 else np.fft.fft2(f))
    if dim == 1:
        c[0] = 0
        k = int(c.argmax())
        return (min(k, len(c) - k),)
    c[0, 0] = 0
    kx, ky = np.unravel_index(c.argmax(), c.shape)
    return (int(min(kx, c.shape[0] - kx)), int(min(ky, c.shape[1] - ky)))


def structured_defaults(s):
    model = s.get("model")
    if model not in kinetics.DEFAULTS:
        raise PdeRefuse("no_nonlinear_model", "pde.solve needs `model` in %s; a bare Jacobian has no nonlinear equation" % list(kinetics.DEFAULTS))
    return model, kinetics.params(model, s.get("params"))


def solve(structured: dict, gamma=None, seed=11, T_max=T_MAX, quick=False) -> dict:
    return _jsonable(_solve(structured, gamma, seed, T_max, quick))


def _jsonable(x):
    if isinstance(x, dict):
        return {k: _jsonable(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_jsonable(v) for v in x]
    if isinstance(x, np.generic):
        return x.item()
    return x


def _solve(structured, gamma, seed, T_max, quick):
    """Converged nonlinear solve. quick=True skips the two refinement runs (category 'unchecked'; NEVER scored as converged)."""
    try:
        model, p = structured_defaults(structured)
        g = linear.rat("gamma", gamma if gamma is not None else structured.get("gamma", 1))
        Dv = linear.rat("Dv", structured["Dv"])
        bc = structured.get("bc")
        if bc not in ("neumann", "periodic"):
            raise PdeRefuse("unsupported_boundary", f"pde.solve supports neumann|periodic only (got {bc!r}); Dirichlet or unstated need a different base state/problem")
        dom = structured.get("domain") or structured
        if dom.get("r_over_pi") is not None:
            dim, rs = 1, [linear.rat("r_over_pi", dom["r_over_pi"])]
        elif dom.get("a_over_pi") is not None:
            dim, rs = 2, [linear.rat("a_over_pi", dom["a_over_pi"]), linear.rat("b_over_pi", dom["b_over_pi"])]
        else:
            raise PdeRefuse("invalid_input", "domain needs r_over_pi or a_over_pi,b_over_pi")
    except (PdeRefuse, linear.Refuse, KeyError) as ex:
        code = getattr(ex, "code", "invalid_input")
        return {"category": "refused", "refusal": {"code": code, "detail": getattr(ex, "detail", repr(ex))}, "evidence": EVIDENCE}
    Ls = [float(r) * math.pi for r in rs]
    lin = linear.check({"model": model, "params": {k: str(v) for k, v in p.items()}, "gamma": str(g), "Dv": str(Dv),
                        "domain": structured.get("domain") or {k: structured[k] for k in structured if k.endswith("_over_pi")}, "bc": bc})
    # horizon from the linear growth rate of the fastest admissible mode
    sig = 0.0
    qmax = 0.0
    J1 = [[float(z) for z in row] for row in kinetics.jacobian(model, p)]
    gf, Dvf = float(g), float(Dv)
    mult = 1 if bc == "neumann" else 2
    for idx in (lin.get("admissible_unstable_modes") or []):
        qq = idx["q_float"]
        Mx = np.array(J1) - qq * np.diag([1 / gf, Dvf / gf])
        sg = np.linalg.eigvals(Mx).real.max()
        if sg > sig:
            sig, qmax = sg, qq
    horizon_limited = False
    if sig > 0:
        T = min(T_max, max(T_MIN, 30.0 / sig))
        horizon_limited = 30.0 / sig > T_max
    else:
        T = T_MIN
    # grid: resolve the largest unstable wavenumber
    qtop = max([i["q_float"] for i in (lin.get("admissible_unstable_modes") or [])] + [1e-9])
    lam_min = 2 * math.pi / math.sqrt(qtop)
    Ns = [_cells(L, lam_min) for L in Ls]
    cap = MAX_CELLS_1D if dim == 1 else MAX_CELLS_2D
    if max(Ns) > cap:
        return {"category": "refused", "refusal": {"code": "too_large", "detail": f"needs {Ns} cells (cap {cap}); reduce domain or gamma"}, "evidence": EVIDENCE}
    Ks = [max(4, n // 4) for n in Ns]
    ust = float(kinetics.steady(model, p)[0])
    amp_min = AMP_REL * abs(ust)
    # CFL on reaction: bound by max Jacobian 1-norm at the largest state observed in the base run (checked after)
    res = {"model": model, "dim": dim, "bc": bc, "gamma": float(g), "Dv": float(Dv), "horizon_tau": T, "horizon_limited": horizon_limited,
           "grid_cells": Ns, "dt_tau": DT, "linear": {"verdict": lin["verdict"], "scope_verdict": lin["scope_verdict"],
           "fastest_unstable_sigma": sig}, "evidence": EVIDENCE}
    dt = DT
    base = _run(model, p, g, Dv, dim, bc, Ls, Ns, Ks, T, dt, seed)
    if not base["diverged"] and dt * base["rho"] > 0.5:
        dt_new = max(DT_MIN, 0.25 / base["rho"])           # one adaptation: the sampled reaction stiffness was too large for dt
        res["dt_adapted_from"] = dt
        dt = float(round(dt_new, 6))
        base = _run(model, p, g, Dv, dim, bc, Ls, Ns, Ks, T, dt, seed)
    res["dt_tau"] = dt
    if base["diverged"]:
        res.update(category="diverged", converged=False, pattern=None)
        return res
    runs = {"base": base}
    if not quick:
        runs["dt_half"] = _run(model, p, g, Dv, dim, bc, Ls, Ns, Ks, T, dt / 2, seed)
        runs["grid_double"] = _run(model, p, g, Dv, dim, bc, Ls, [2 * n for n in Ns], Ks, T, dt, seed)
    if any(r["diverged"] for r in runs.values()):
        res.update(category="diverged", converged=False, pattern=None)
        return res
    sumr = {}
    for nm, r in runs.items():
        u = r["u"]
        sumr[nm] = {"amp": float(u.std()), "mode": _mode(u, dim, bc), "pattern": bool(u.std() >= amp_min)}
    b = sumr["base"]
    mode_settled = _mode(base["snap"], dim, bc) == b["mode"]
    amp_settled = abs(float(base["snap"].std()) - b["amp"]) <= 0.05 * max(b["amp"], 1e-12)
    # reaction CFL on the base run's largest state
    rho = base["rho"]
    cfl = dt * rho
    res.update(runs=sumr, validity={"reaction_cfl": cfl, "reaction_cfl_ok": cfl <= 0.5, "cells_per_min_wavelength": min(
        lam_min / (L / n) for L, n in zip(Ls, Ns)), "T_max": T_max, "euler_fd_not_used": True,
        "amplitude_threshold": amp_min})
    if quick:
        res.update(category="unchecked", converged=False, pattern=b["pattern"], m_dom=list(b["mode"]), amp=b["amp"])
        return res
    agree_flag = len({r["pattern"] for r in sumr.values()}) == 1
    agree_mode = len({r["mode"] for r in sumr.values()}) == 1 or not b["pattern"]
    amps = [r["amp"] for r in sumr.values()]
    agree_amp = (max(amps) - min(amps)) <= AMP_REL * max(amps) or not b["pattern"] and max(amps) < amp_min
    converged = bool(agree_flag and agree_mode and agree_amp and cfl <= 0.5)
    res.update(converged=converged, pattern=b["pattern"], m_dom=list(b["mode"]), amp=b["amp"], settled=bool(mode_settled and amp_settled),
               agreement={"flag": agree_flag, "mode": agree_mode, "amp": bool(agree_amp)})
    if not converged:
        res["category"] = "nonconverged"
        res["why"] = [k for k, v in (("dt_cfl", cfl > 0.5), ("flag", not agree_flag), ("mode", not agree_mode), ("amp", not agree_amp)) if v]
    elif not res["settled"] or horizon_limited:
        res["category"] = "not_settled"
    else:
        res["category"] = "pattern" if b["pattern"] else "no_pattern"
    # linear-vs-nonlinear
    res["disagrees_with_linear"] = bool((lin["scope_verdict"] == "applies") != bool(b["pattern"])) if res["category"] in ("pattern", "no_pattern") else None
    return res


def kinetics_jac_norm(model, p, umax):
    """Crude upper bound on the 1-norm of the reaction Jacobian over |u|,|v|<=umax (gamma=1 units)."""
    if model == "schnakenberg":
        return max(1 + 2 * umax * umax, 2 * umax * umax + 2 * umax * umax) + 1
    B = float(p["B"])
    return max(B + 1 + 2 * umax * umax, B + 4 * umax * umax) + 1
