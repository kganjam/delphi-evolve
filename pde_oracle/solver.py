"""Batched periodic reaction-diffusion solver: Strang splitting, EXACT Fourier diffusion, RK4 reaction.

Same scheme as the independent evaluator `spectral_strang` in experiments/rethink_nca/rd.py (rethink-nca @ e7838b3),
but batched over parameter points, dimension-generic (1-D or 2-D) and device-agnostic. Neumann 1-D intervals are
reproduced exactly by the even periodic extension (see pde_validate.py). All output is SIMULATED (declared model).

State tensors: u, v with shape (B, *spatial). Per-sample parameters are (B,) tensors.
"""
from __future__ import annotations

import math
import torch

MODELS = ("schnakenberg", "gierer_meinhardt", "gray_scott", "brusselator")


def _b(p, nd):                       # (B,) -> (B,1,..,1)
    return p.reshape(-1, *([1] * nd))


def reaction(model, u, v, P, nd):
    if model == "schnakenberg":      # u_t = Du lap u + a - u + u^2 v ; v_t = Dv lap v + b - u^2 v
        a, b = _b(P["a"], nd), _b(P["b"], nd); w = u * u * v
        return a - u + w, b - w
    if model == "gierer_meinhardt":  # u_t = ... + a - b u + u^2/v ; v_t = ... + u^2 - v   (activator-inhibitor, sat.-free)
        a, b = _b(P["a"], nd), _b(P["b"], nd)
        return a - b * u + u * u / v, u * u - v
    if model == "gray_scott":        # u_t = ... - u v^2 + F(1-u) ; v_t = ... + u v^2 - (F+k) v
        F, k = _b(P["F"], nd), _b(P["k"], nd); w = u * v * v
        return -w + F * (1 - u), w - (F + k) * v
    if model == "brusselator":       # u_t = ... + A - (B+1) u + u^2 v ; v_t = ... + B u - u^2 v
        A, Bq = _b(P["A"], nd), _b(P["B"], nd); w = u * u * v
        return A - (Bq + 1) * u + w, Bq * u - w
    raise ValueError(model)


def steady_state(model, P):
    if model == "schnakenberg":
        s = P["a"] + P["b"]; return s, P["b"] / s ** 2
    if model == "gierer_meinhardt":
        u = (P["a"] + 1) / P["b"]; return u, u * u
    if model == "brusselator":
        return P["A"], P["B"] / P["A"]
    if model == "gray_scott":
        return torch.ones_like(P["F"]), torch.zeros_like(P["F"])
    raise ValueError(model)


def initial_state(model, P, spatial, seeds, eps=1e-2, device="cpu", dtype=torch.float64):
    """Steady state + eps*N(0,1) noise (one RNG stream per sample); Gray-Scott: u=1,v=0 with a noisy central seed."""
    B = len(seeds); nd = len(spatial)
    u0, v0 = steady_state(model, P)
    u = torch.empty(B, *spatial, dtype=dtype); v = torch.empty(B, *spatial, dtype=dtype)
    for i, s in enumerate(seeds):
        g = torch.Generator().manual_seed(int(s))
        nu = torch.randn(*spatial, generator=g, dtype=dtype); nv = torch.randn(*spatial, generator=g, dtype=dtype)
        if model == "gray_scott":
            u[i] = 1.0; v[i] = 0.0
            sl = tuple(slice(n // 2 - max(2, n // 16), n // 2 + max(2, n // 16)) for n in spatial)
            u[i][sl] = 0.5; v[i][sl] = 0.25
            u[i] += 0.01 * nu; v[i] += 0.01 * nv.abs()
        else:
            u[i] = float(u0[i]) + eps * nu; v[i] = float(v0[i]) + eps * nv
    return u.to(device), v.to(device)


class Solver:
    def __init__(self, model, P, spatial, lengths, device="cpu", dtype=torch.float64):
        self.model, self.nd, self.dtype, self.device = model, len(spatial), dtype, device
        self.P = {k: v.to(device=device, dtype=dtype) for k, v in P.items()}
        self.spatial = tuple(spatial)
        ks = []
        for ax, (n, L) in enumerate(zip(spatial, lengths)):
            if ax == len(spatial) - 1:
                k = torch.arange(n // 2 + 1, dtype=torch.float64) * 2 * math.pi / L
            else:
                k = torch.fft.fftfreq(n, d=1.0 / n).to(torch.float64) * 2 * math.pi / L
            ks.append(k)
        mesh = torch.meshgrid(*ks, indexing="ij") if self.nd > 1 else (ks[0],)
        self.q = sum(m ** 2 for m in mesh).to(device=device, dtype=dtype)          # |k|^2, (*spatial_rfft)
        self.dims = tuple(range(-self.nd, 0))

    def _mult(self, D, h):
        return torch.exp(-_b(self.P[D], self.nd) * self.q[None] * h)

    def _diffuse(self, u, v, mu, mv):
        fu = torch.fft.rfftn(u, dim=self.dims) * mu
        fv = torch.fft.rfftn(v, dim=self.dims) * mv
        return torch.fft.irfftn(fu, s=self.spatial, dim=self.dims), torch.fft.irfftn(fv, s=self.spatial, dim=self.dims)

    def _rk4(self, u, v, h):
        f = lambda a, b: reaction(self.model, a, b, self.P, self.nd)       # noqa: E731
        k1u, k1v = f(u, v)
        k2u, k2v = f(u + 0.5 * h * k1u, v + 0.5 * h * k1v)
        k3u, k3v = f(u + 0.5 * h * k2u, v + 0.5 * h * k2v)
        k4u, k4v = f(u + h * k3u, v + h * k3v)
        return u + h / 6 * (k1u + 2 * k2u + 2 * k3u + k4u), v + h / 6 * (k1v + 2 * k2v + 2 * k3v + k4v)

    @torch.no_grad()
    def run(self, u, v, T, dt, callback=None, every=0):
        """Advance to time T with `n=ceil(T/dt)` Strang steps; adjacent half-diffusions are merged (same maths)."""
        n = int(math.ceil(T / dt)); h = T / n
        mu_h, mv_h = self._mult("Du", h / 2), self._mult("Dv", h / 2)
        mu_f, mv_f = mu_h * mu_h, mv_h * mv_h
        u, v = self._diffuse(u, v, mu_h, mv_h)
        for k in range(n):
            u, v = self._rk4(u, v, h)
            last = k == n - 1
            u, v = self._diffuse(u, v, mu_h if last else mu_f, mv_h if last else mv_f)
            if callback and every and (k + 1) % every == 0 and not last:
                callback(k + 1, u, v)          # NOTE: mid-run states carry a half-step diffusion offset
        return u, v
