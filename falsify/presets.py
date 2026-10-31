"""Exact-rational Jacobians of three textbook two-species kinetics at their (unique positive) homogeneous
fixed point. The fixed point is verified EXACTLY (f(u*,v*)=0, g(u*,v*)=0) by the engine; the Jacobian formulas are
hand-derived and cross-checked against symbolic differentiation in tests/test_falsify.py.

  brusselator:       u' = A - (B+1)u + u^2 v ;  v' = B u - u^2 v           u*=A, v*=B/A
  schnakenberg:      u' = a - u + u^2 v      ;  v' = b - u^2 v             u*=a+b, v*=b/(a+b)^2
  gierer_meinhardt:  u' = a - b u + u^2/v    ;  v' = u^2 - v               u*=(a+1)/b, v*=u*^2
"""
from __future__ import annotations

from fractions import Fraction


def _pos(name, x):
    if x <= 0:
        raise ValueError(f"parameter {name} must be > 0")
    return x


def brusselator(p):
    A, B = _pos("A", p["A"]), _pos("B", p["B"])
    u, v = A, B / A
    f = lambda u, v: A - (B + 1) * u + u * u * v
    g = lambda u, v: B * u - u * u * v
    J = [[B - 1, A * A], [-B, -A * A]]
    return (u, v), f, g, J


def schnakenberg(p):
    a, b = _pos("a", p["a"]), _pos("b", p["b"])
    u = a + b
    v = b / (u * u)
    f = lambda u, v: a - u + u * u * v
    g = lambda u, v: b - u * u * v
    J = [[(b - a) / (a + b), (a + b) ** 2], [-2 * b / (a + b), -((a + b) ** 2)]]
    return (u, v), f, g, J


def gierer_meinhardt(p):
    a, b = _pos("a", p["a"]), _pos("b", p["b"])
    u = (a + 1) / b
    v = u * u
    f = lambda u, v: a - b * u + u * u / v
    g = lambda u, v: u * u - v
    # f_u = -b + 2u/v ; f_v = -u^2/v^2 ; g_u = 2u ; g_v = -1
    J = [[-b + 2 * u / v, -(u * u) / (v * v)], [2 * u, Fraction(-1)]]
    return (u, v), f, g, J


PRESETS = {"brusselator": (brusselator, ("A", "B")),
           "schnakenberg": (schnakenberg, ("a", "b")),
           "gierer_meinhardt": (gierer_meinhardt, ("a", "b"))}


def build(name, params):
    """-> (fixed_point, J) with exact Fractions; raises ValueError if the fixed point is not an exact equilibrium."""
    if name not in PRESETS:
        raise ValueError(f"unknown model {name!r}; supported: {sorted(PRESETS)}")
    fn, keys = PRESETS[name]
    missing = [k for k in keys if k not in params]
    if missing:
        raise ValueError(f"model {name} needs params {list(keys)}; missing {missing}")
    fp, f, g, J = fn({k: params[k] for k in keys})
    if f(*fp) != 0 or g(*fp) != 0:
        raise ValueError("internal error: fixed point is not an exact equilibrium")
    return fp, [[Fraction(x) for x in row] for row in J]
