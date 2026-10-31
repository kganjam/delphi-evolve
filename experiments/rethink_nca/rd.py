"""Schnakenberg reaction-diffusion on a 1-D Neumann interval: two independent solvers and pattern metrics.

Model (declared, not measured; evidence kind = SIMULATED everywhere in this package):
    u_t = Du u_xx + g (a - u + u^2 v),   v_t = Dv v_xx + g (b - u^2 v),   a = 1/10, b = 9/10,  Du = 1, Dv = d.
Homogeneous steady state u* = a + b = 1, v* = b/(a+b)^2 = 9/10.  Linearization J = g * J1 with
J1 = [[4/5, 1], [-9/5, -1]] (tr J1 = -1/5, det J1 = 1).  In "tau" units (tau = g t) the diffusivities are
(1/g, d/g) and the kinetics have no free parameter, so one array solver covers many (g, d) at once.

Two solvers that share no stepping or discretisation code:
  * `euler_fd`     : explicit Euler, second-order finite differences, cell-centred, zero-flux ghost cells.
                     This is the *training / design-time* solver (what an NCA is fitted to).
  * `spectral_strang`: Strang splitting with EXACT cosine-mode diffusion (DCT-II) + RK4 reaction substeps.
                     This is the *independent evaluator*.  Its Laplacian eigenvalues are the continuum
                     (n pi / L)^2, not the finite-difference ones.
Both use N cells over length L = r*pi with dx = pi/4 (so N = 4 r; r integer).
"""
from __future__ import annotations

import numpy as np
from scipy.fft import dct, idct

A, B = 0.1, 0.9
U0, V0 = A + B, B / (A + B) ** 2
J1 = np.array([[0.8, 1.0], [-1.8, -1.0]])
DX = np.pi / 4.0
REACTION_DT_MAX = 0.02   # tau units; reaction-stiffness cap for explicit Euler (see euler_dt)


def n_cells(r: float) -> int:
    n = r * 4.0
    if abs(n - round(n)) > 1e-9:
        raise ValueError(f"r={r} gives non-integer N={n}")
    return int(round(n))


def react(u, v):
    w = u * u * v
    return A - u + w, B - w


def initial_state(S, N, seeds, eps=1e-2):
    """Steady state + eps * N(0,1) noise; one independent noise field per (sample, seed)."""
    out = np.empty((S, 2, N))
    for i in range(S):
        rng = np.random.default_rng(int(seeds[i]))
        out[i, 0] = U0 + eps * rng.standard_normal(N)
        out[i, 1] = V0 + eps * rng.standard_normal(N)
    return out


def lap_fd(x):
    """Cell-centred second difference with zero-flux (replicated) ghost cells; x[..., N]."""
    xl = np.concatenate([x[..., :1], x[..., :-1]], axis=-1)
    xr = np.concatenate([x[..., 1:], x[..., -1:]], axis=-1)
    return (xl - 2 * x + xr) / DX ** 2


def euler_dt(gamma, d, safety=0.9):
    """Largest stable explicit-Euler step in tau units for the batch (diffusion limit; reaction is milder here)."""
    dmax = float(np.max(np.maximum(1.0, np.asarray(d)) / np.asarray(gamma)))
    # NOTE (critic audit, 2026-10-31): the diffusion-only bound alone lets dt_tau grow without limit when d/gamma is small
    # (large gamma), which is far above the reaction-stiffness limit and flipped Euler verdicts at gamma>=32. Cap added after
    # the scored probe; the scored probe always passed dt=0.005 explicitly, so its results are unaffected.
    return min(safety * DX ** 2 / (2 * dmax), REACTION_DT_MAX)


def euler_fd(state, gamma, d, T_tau, dt=None, record_every_tau=None):
    """Advance `state` (S,2,N) to tau=T_tau with explicit Euler. gamma, d: (S,) arrays. Returns final (and frames)."""
    gamma = np.asarray(gamma, float)
    d = np.asarray(d, float)
    dt = dt or euler_dt(gamma, d)
    nsteps = int(np.ceil(T_tau / dt))
    dt = T_tau / nsteps
    Du = (1.0 / gamma)[:, None]
    Dv = (d / gamma)[:, None]
    x = state.copy()
    frames = []
    rec = int(round(record_every_tau / dt)) if record_every_tau else 0
    for k in range(nsteps):
        u, v = x[:, 0], x[:, 1]
        ru, rv = react(u, v)
        x[:, 0] = u + dt * (Du * lap_fd(u) + ru)
        x[:, 1] = v + dt * (Dv * lap_fd(v) + rv)
        if rec and (k + 1) % rec == 0:
            frames.append(x.copy())
    return (x, np.stack(frames, 1)) if rec else x


def _rk4_react(u, v, h):
    def f(u, v):
        return react(u, v)
    k1u, k1v = f(u, v)
    k2u, k2v = f(u + 0.5 * h * k1u, v + 0.5 * h * k1v)
    k3u, k3v = f(u + 0.5 * h * k2u, v + 0.5 * h * k2v)
    k4u, k4v = f(u + h * k3u, v + h * k3v)
    return u + h / 6 * (k1u + 2 * k2u + 2 * k3u + k4u), v + h / 6 * (k1v + 2 * k2v + 2 * k3v + k4v)


def spectral_strang(state, gamma, d, r, T_tau, dt=0.02, checkpoints=()):
    """Independent solver. Returns final state and {tau: state} for requested checkpoint times (nearest step)."""
    gamma = np.asarray(gamma, float)
    d = np.asarray(d, float)
    S, _, N = state.shape
    L = r * np.pi
    q = (np.arange(N) * np.pi / L) ** 2                      # exact Neumann eigenvalues
    nsteps = int(np.ceil(T_tau / dt))
    dt = T_tau / nsteps
    mu = np.exp(-(1.0 / gamma)[:, None] * q[None] * dt / 2)  # half-step diffusion multipliers
    mv = np.exp(-(d / gamma)[:, None] * q[None] * dt / 2)
    cps = {int(round(c / dt)): c for c in checkpoints}
    saved = {}
    u, v = state[:, 0].copy(), state[:, 1].copy()
    for k in range(nsteps):
        u = idct(dct(u, type=2, norm="ortho", axis=-1) * mu, type=2, norm="ortho", axis=-1)
        v = idct(dct(v, type=2, norm="ortho", axis=-1) * mv, type=2, norm="ortho", axis=-1)
        u, v = _rk4_react(u, v, dt)
        u = idct(dct(u, type=2, norm="ortho", axis=-1) * mu, type=2, norm="ortho", axis=-1)
        v = idct(dct(v, type=2, norm="ortho", axis=-1) * mv, type=2, norm="ortho", axis=-1)
        if (k + 1) in cps:
            saved[cps[k + 1]] = np.stack([u, v], 1)
    return np.stack([u, v], 1), saved


def pattern_metrics(u, r, amp_min=0.1):
    """u: (S,N) -> dict of arrays. m = dominant cosine mode of the final u; lam = 2L/m (length units)."""
    S, N = u.shape
    L = r * np.pi
    c = dct(u - u.mean(-1, keepdims=True), type=2, norm="ortho", axis=-1)
    mag = np.abs(c[:, 1:])
    m = mag.argmax(-1) + 1
    amp = u.std(-1)
    lam = 2 * L / m
    return {"m": m, "amp": amp, "lam": lam, "patterned": amp >= amp_min}


def linear_sigma(gamma, d, r, n_max=400):
    """Largest Re(eigenvalue) over admissible Neumann modes n>=1 (tau units) and the mode index attaining it."""
    q = (np.arange(1, n_max + 1) * np.pi / (r * np.pi)) ** 2
    best, arg = -1e9, 0
    for n, qq in enumerate(q, 1):
        M = J1 - qq * np.diag([1.0 / gamma, d / gamma])   # tau units: kinetics J1, diffusion (1/g, d/g) * q
        s = np.linalg.eigvals(M).real.max()
        if s > best:
            best, arg = s, n
    return best, arg
