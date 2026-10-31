"""Closed-form continuum Turing threshold for a 2x2 Jacobian J=[[a,b],[c,e]] with Du=1, Dv=d.

Instability of the stable homogeneous state needs  d*a + e > 0  and  (d*a+e)^2 > 4 d det(J)  (a>0).
Solving the quadratic a^2 d^2 + 2(2bc - a e) d + e^2 = 0 gives  d_c = [(a e - 2bc) + 2 sqrt(bc (bc - a e))] / a^2.
"""
from __future__ import annotations
from fractions import Fraction
import numpy as np


def stable(a, b, c, e):
    return (a + e < 0) & (a * e - b * c > 0)


def d_crit(a, b, c, e):
    """Vectorised. NaN where the state is unstable, a<=0, or bc>=0 (no activator-inhibitor cross-structure)."""
    a, b, c, e = map(np.asarray, (a, b, c, e))
    bc = b * c
    ok = stable(a, b, c, e) & (a > 0) & (bc < 0)
    with np.errstate(invalid="ignore", divide="ignore"):
        d = ((a * e - 2 * bc) + 2 * np.sqrt(bc * (bc - a * e))) / a ** 2
    return np.where(ok, d, np.nan)


def turing_unstable(a, b, c, e, d):
    """Continuum criterion at ratio d (arrays broadcast)."""
    return stable(a, b, c, e) & (d * a + e > 0) & ((d * a + e) ** 2 > 4 * d * (a * e - b * c))


def band(a, b, c, e, d):
    """Unstable wavenumber band q in (q-, q+): roots of d q^2 - (d a + e) q + det = 0. NaN if not unstable."""
    det = a * e - b * c; s = d * a + e
    disc = s * s - 4 * d * det
    with np.errstate(invalid="ignore"):
        r = np.sqrt(np.where(disc > 0, disc, np.nan))
    return (s - r) / (2 * d), (s + r) / (2 * d)


def exact_mode_det(J, Du, Dv, q):
    """Exact rational det(J - q diag(Du,Dv)) for the Lean-checked counterexample reproduction."""
    (a, b), (c, e) = J
    return (a - Du * q) * (e - Dv * q) - b * c


def codex_counterexample():
    F = Fraction
    J = ((F(1), F(-1)), (F(1011, 1000), F(-101, 100)))
    q = F(1, 25)                                    # Neumann mode n=1 on L=5*pi: q=(n*pi/L)^2 -> (1/5)^2
    det_mode = exact_mode_det(J, F(1), F(11, 10), q)
    tr = J[0][0] + J[1][1]; det = J[0][0] * J[1][1] - J[0][1] * J[1][0]
    return {"trace": tr, "det_J": det, "det_at_mode1": det_mode, "expected": F(-21, 25000), "matches": det_mode == F(-21, 25000),
            "stable_without_diffusion": tr < 0 and det > 0}
