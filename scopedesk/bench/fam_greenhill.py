"""Family 8/8: greenhill_buckling. Claim (thompson1917-ch02-02 + Greenhill): self-weight buckling height of a UNIFORM solid circular column,
H_cr = (7.8373 E I / q)^(1/3) = 0.788 (E/(rho g))^(1/3) D^(2/3) (D diameter), clamped base. Scope condition UNIFORM_COLUMN.
Truth for tapered columns (linear taper of radius from base to top/base ratio t): Rayleigh-Ritz minimisation (polynomial basis, Gauss-Legendre)
  H^3 = (E r0^2 /(4 rho g)) * Lambda_t,  Lambda_t = min  int f^4 y''^2 / int F y'^2,  f=1-(1-t) xi,  F(xi)=int_xi^1 f^2.
Checked: Lambda_1 = 7.8373 (Greenhill) to 1e-3 (see verify). Units SI. Verdict: formula's predicted outcome (buckles iff H > H_u) vs true outcome.
Missing E or rho => underdetermined (MECH_INPUTS_MISSING). Items within 3% of either critical height excluded."""
import math
import numpy as np
from scipy.linalg import eigh
from fractions import Fraction as F
from common import item, exclude, ftxt
FAMILY = "greenhill_buckling"
G = 9.81
_xi, _w = np.polynomial.legendre.leggauss(40); _xi = (_xi + 1) / 2; _w = _w / 2

def Lambda(t, K=9):
    f = 1 - (1 - t) * _xi
    # F(xi) = int_xi^1 f^2 dsigma, exact for linear f: f^3 / (3 (1-t)) form; use quadrature of antiderivative
    if abs(1 - t) < 1e-12: Fx = 1 - _xi
    else: Fx = (f ** 3 - t ** 3) / (3 * (1 - t))
    ks = np.arange(2, K + 1)
    Y1 = np.array([k * _xi ** (k - 1) for k in ks]); Y2 = np.array([k * (k - 1) * _xi ** (k - 2) for k in ks])
    A = (Y2 * (f ** 4 * _w)) @ Y2.T; B = (Y1 * (Fx * _w)) @ Y1.T
    return float(eigh(A, B, eigvals_only=True)[0])

def Hcr(E, rho, D, t):
    r0 = D / 2
    return (E * r0 ** 2 / (4 * rho * G) * Lambda(t)) ** (1 / 3)

def Hform(E, rho, D):
    return 0.788 * (E / (rho * G)) ** (1 / 3) * D ** (2 / 3)

def decide(E, rho, D, H, t):
    if E is None or rho is None: return "underdetermined", ["MECH_INPUTS_MISSING"], {"missing": [k for k, v in (("E", E), ("rho", rho)) if v is None]}, 1.0
    Hu = (E * (D / 2) ** 2 / (4 * rho * G) * Lambda(1.0)) ** (1 / 3); Ht = Hcr(E, rho, D, t)
    margin = min(abs(H / Hu - 1), abs(H / Ht - 1))
    pred = H > Hu; true = H > Ht
    w = {"H_formula_uniform": round(Hu, 3), "H_cr_true": round(Ht, 3), "H": H, "Lambda_t": round(Lambda(t), 4), "t": t}
    if pred == true: return "applies", [], w, margin
    return "out_of_scope", ["UNIFORM_COLUMN"], w, margin

def render(rng, E, rho, D, H, t, tset):
    shape = "a uniform solid circular column" if t == 1 else f"a solid circular column that tapers linearly so its top diameter is {ftxt(F(t).limit_denominator(100))} of its base diameter"
    mech = ""
    if E is not None: mech += f" Young's modulus E = {E/1e9:g} GPa"
    if rho is not None: mech += f"{',' if mech else ''} density {rho:g} kg/m^3"
    mech = mech.strip() + "." if mech else "Material properties are not given."
    if tset == "A":
        return (f"A tree-like column: {shape}, base diameter {D:g} m, height {H:g} m, clamped at the base. {mech} Greenhill's formula H_cr = 0.788 (E/(rho g))^(1/3) D^(2/3) "
                f"is Thompson's limiting height. Will it buckle under its own weight?")
    return (f"Consider {shape} (base diameter {D:g} m) standing {H:g} m tall with a fixed base. {mech} Using Thompson/Greenhill's limiting-height formula, should I expect self-weight buckling?")

def make(rng, n, start_id):
    out, seen = [], set()
    want = ["applies_u", "oos", "oos", "undet", "applies_t", "applies_u", "oos", "undet"]
    while len(out) < n:
        k = want[len(out) % len(want)]
        E = rng.choice([4e9, 6e9, 10e9, 15e9]); rho = rng.choice([600.0, 800.0, 1000.0]); D = rng.choice([0.2, 0.4, 0.8, 1.5])
        t = 1.0 if k in ("applies_u",) else rng.choice([0.25, 0.4, 0.5, 0.7]) if k in ("oos", "applies_t") else rng.choice([1.0, 0.5])
        Hu = (E * (D / 2) ** 2 / (4 * rho * G) * Lambda(1.0)) ** (1 / 3)
        H = round(Hu * rng.choice([0.5, 0.8, 0.9, 1.1, 1.2, 1.4, 1.6, 2.0]), 1)
        Ei, rhoi = (None, rho) if k == "undet" and rng.random() < .5 else (E, None) if k == "undet" else (E, rho)
        v, c, w, m = decide(Ei, rhoi, D, H, t)
        if k != "undet" and m < 0.03: exclude(FAMILY, "within 3% of a critical height", {"E": E, "rho": rho, "D": D, "H": H, "t": t}); continue
        if {"applies_u": v == "applies", "applies_t": v == "applies", "oos": v == "out_of_scope", "undet": v == "underdetermined"}[k] is False or (Ei, rhoi, D, H, t) in seen: continue
        seen.add((Ei, rhoi, D, H, t)); tset = "A" if len(out) % 2 == 0 else "B"
        rep = {"knob": "use_tapered_buckling_formula", "valid_grid": ["Rayleigh-Ritz tapered column"]} if v == "out_of_scope" else {}
        out.append(item(f"gh-{start_id+len(out):04d}", FAMILY, "formal", render(rng, Ei, rhoi, D, H, t, tset), {"E": Ei, "rho": rhoi, "D": D, "H": H, "t": t}, v, c, w, rep, tset, k))
    return out
