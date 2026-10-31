"""Named ensemble for the preregistered nonlinear sweep ('where does linear theory mispredict the nonlinear outcome').
Everything here is deterministic given SEED_ENSEMBLE. See PREREG.md for the declared design and its limits."""
from __future__ import annotations

import itertools
import math
import random
from fractions import Fraction as F

import numpy as np

from .. import kinetics, linear

SEED_ENSEMBLE = 20261031
RHOS = [0.7, 0.9, 0.97, 1.03, 1.1, 1.5, 3.0]          # Dv/Du as a multiple of the onset ratio d_c of the drawn kinetics
XS = [2, 4, 8]                                        # domain length in units of the onset critical wavelength lambda_c
EPS = [0.01, 0.1, 0.3]                                # initial perturbation std as a fraction of the steady-state value (each species)
PAIRED_SEEDS = [101, 102]                             # modal-coefficient seeds, paired across amplitudes, rho, x and solvers


def draw_params(model, n, rng):
    """Stated priors (NOT published ranges): see PREREG.md. Rejection: well-mixed stable and finite onset ratio."""
    out = []
    while len(out) < n:
        if model == "schnakenberg":
            a = math.exp(rng.uniform(math.log(0.05), math.log(0.4)))
            b = math.exp(rng.uniform(math.log(0.4), math.log(1.6)))
            p = {"a": F(a).limit_denominator(100), "b": F(b).limit_denominator(100)}
        else:
            A = rng.uniform(0.8, 2.5)
            u = rng.uniform(0.15, 0.85)
            Af = F(A).limit_denominator(20)
            Bf = F(1) + F(u).limit_denominator(20) * Af * Af
            p = {"A": Af, "B": Bf}
        dc = onset_ratio(model, p)
        if dc is not None and 1.5 < dc < 400:
            out.append(p)
    return out


def jac(model, p):
    return [[float(x) for x in row] for row in kinetics.jacobian(model, kinetics.params(model, {k: str(v) for k, v in p.items()}))]


def onset_ratio(model, p):
    """d_c: smallest Dv/Du (Du=1, gamma=1) for which the well-mixed-stable state has a continuum Turing band (turing-ddi inequality), else None."""
    (fu, fv), (gu, gv) = jac(model, p)
    tr, det = fu + gv, fu * gv - fv * gu
    if not (tr < 0 and det > 0) or fu <= 0:
        return None
    # (fu d + gv)^2 > 4 d det with fu d + gv > 0  =>  d > larger root of fu^2 d^2 + (2 fu gv - 4 det) d + gv^2
    Bq, disc = 2 * fu * gv - 4 * det, (2 * fu * gv - 4 * det) ** 2 - 4 * fu * fu * gv * gv
    if disc <= 0:
        return None
    d = (-Bq + math.sqrt(disc)) / (2 * fu * fu)
    return d if fu * d + gv > 0 and d > 1 else None


def lambda_c(model, p):
    """Onset critical wavelength with the record's notation k_c^2 = sqrt(det J/(Du Dv)) evaluated AT the onset ratio (Du=1, gamma=1)."""
    (fu, fv), (gu, gv) = jac(model, p)
    det = fu * gv - fv * gu
    dc = onset_ratio(model, p)
    kc = math.sqrt(math.sqrt(det / dc))
    return 2 * math.pi / kc


def build(n_draws, models=("schnakenberg", "brusselator"), seed=SEED_ENSEMBLE):
    rng = random.Random(seed)
    cells, cid = [], 0
    for model in models:
        for di, p in enumerate(draw_params(model, n_draws, rng)):
            dc, lc = onset_ratio(model, p), lambda_c(model, p)
            for rho, x, eps, sd in itertools.product(RHOS, XS, EPS, PAIRED_SEEDS):
                Dv = F(rho * dc).limit_denominator(1000)
                r = F(x * lc / math.pi).limit_denominator(50)
                cells.append({"id": cid, "model": model, "draw": di, "params": {k: str(v) for k, v in p.items()}, "d_c": dc, "lambda_c": lc,
                              "rho": rho, "x": x, "eps": eps, "seed": sd, "Dv": str(Dv), "r_over_pi": str(r)})
                cid += 1
    return cells


def linear_structured(c):
    return {"model": c["model"], "params": c["params"], "gamma": "1", "Dv": c["Dv"], "r_over_pi": c["r_over_pi"], "bc": "neumann"}


def permutation(n, seed=SEED_ENSEMBLE + 1):
    idx = list(range(n))
    random.Random(seed).shuffle(idx)
    return idx
