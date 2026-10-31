"""Two declared two-species reaction models (dimensionless, tau = gamma * t; gamma multiplies the whole kinetics).

schnakenberg : f = a - u + u^2 v,        g = b - u^2 v;            steady (a+b, b/(a+b)^2)
brusselator  : f = A - (B+1) u + u^2 v,  g = B u - u^2 v;          steady (A, B/A)
Parameters are exact Fractions so the Jacobian at the steady state is exact. Nothing here is measured; these are textbook
model equations, chosen so the family is not one model. Defaults: Schnakenberg a=1/10,b=9/10 (J1=[[4/5,1],[-9/5,-1]]);
Brusselator A=3/2,B=2 (J=[[1,9/4],[-2,-9/4]], well-mixed stable, Turing band for Dv/Du=16).
Note: Brusselator A=1,B=9/5 has exactly the Schnakenberg default Jacobian, which isolates nonlinear differences from linear ones.
"""
from __future__ import annotations

from fractions import Fraction as F

import numpy as np

DEFAULTS = {"schnakenberg": {"a": F(1, 10), "b": F(9, 10)}, "brusselator": {"A": F(3, 2), "B": F(2)}}


def params(model, p=None):
    base = dict(DEFAULTS[model])
    for k, v in (p or {}).items():
        base[k] = F(v)
    unknown = set(base) - set(DEFAULTS[model])
    if unknown:
        raise ValueError(f"unknown parameters for {model}: {unknown}")
    return base


def steady(model, p):
    if model == "schnakenberg":
        a, b = p["a"], p["b"]
        return a + b, b / (a + b) ** 2
    A, B = p["A"], p["B"]
    return A, B / A


def jacobian(model, p):
    """Exact 2x2 Jacobian at the steady state for gamma=1: [[fu, fv],[gu, gv]]."""
    u, v = steady(model, p)
    if model == "schnakenberg":
        return [[-1 + 2 * u * v, u * u], [-2 * u * v, -u * u]]
    B = p["B"]
    return [[-(B + 1) + 2 * u * v, u * u], [B - 2 * u * v, -u * u]]


def react(model, p, u, v):
    """Reaction terms (gamma=1) on numpy arrays."""
    if model == "schnakenberg":
        a, b = float(p["a"]), float(p["b"])
        w = u * u * v
        return a - u + w, b - w
    A, B = float(p["A"]), float(p["B"])
    w = u * u * v
    return A - (B + 1) * u + w, B * u - w


def jac_norm(model, p, u, v):
    """Pointwise 1-norm of the reaction Jacobian (gamma=1) on numpy fields u, v: max column/row sum used as a stiffness bound."""
    if model == "schnakenberg":
        fu, fv, gu, gv = -1 + 2 * u * v, u * u, -2 * u * v, -u * u
    else:
        B = float(p["B"])
        fu, fv, gu, gv = -(B + 1) + 2 * u * v, u * u, B - 2 * u * v, -u * u
    return np.maximum(np.abs(fu) + np.abs(gu), np.abs(fv) + np.abs(gv))
