"""Executable reuse of EXISTING Delphi records `turing-ddi` and `turing-wavelength` as a design constraint.

This module does not re-implement the claims. It calls the committed, source-pinned `turing_scope.adapter.analyze`
(exact rational arithmetic; refuses when the pinned Delphi record content hash changes) and turns its verdict into:
  * a refusal when no admissible Neumann mode of the declared finite domain is linearly unstable (turing-ddi + the
    adapter's finite-domain assumption),
  * a set of admissible unstable modes m and the interval of reaction scale gamma for which mode m is unstable,
  * a licence flag for using the continuum wavelength formula (turing-wavelength: near onset, large domain).

Keeping three things separate (see the report): the Delphi record text (hash pinned in turing_scope/sources/pins.json),
the adapter's added assumptions (1-D Neumann, declared Jacobian), and THIS experiment's additional assumptions
(Schnakenberg kinetics with a=1/10,b=9/10 treated as exactly known; tolerance 15%; near-onset 1/2; domain >= 5 wavelengths).
All outputs are model-derived; nothing here is observed.
"""
from __future__ import annotations

import math
from fractions import Fraction

from turing_scope.adapter import analyze
from turing_scope.source import SourceStore, load_pins

J1_EXACT = [[Fraction(4, 5), Fraction(1)], [Fraction(-9, 5), Fraction(-1)]]
NEAR_ONSET_MAX_EXCESS = "1/2"      # requester-declared operationalisation (same value as turing_scope example)
MIN_DOMAIN_OVER_WAVELENGTH = "5"   # requester-declared operationalisation (same value as turing_scope example)
TOL = 0.15                         # this experiment's wavelength tolerance, frozen in protocol.json


def _fs(x: Fraction) -> str:
    return str(x.numerator) if x.denominator == 1 else f"{x.numerator}/{x.denominator}"


def request(gamma: Fraction, d: Fraction, r: int, rid="req") -> dict:
    J = [[_fs(gamma * e) for e in row] for row in J1_EXACT]
    return {
        "request_id": rid,
        "system": {"kind": "two_species_reaction_diffusion_linearization", "jacobian": J,
                   "diffusivities": ["1", _fs(d)],
                   "fixed_point": {"declared": True, "description": "Schnakenberg u*=1, v*=9/10 DECLARED; not checked here."}},
        "domain": {"dimension": 1, "boundary": "neumann_zero_flux", "length_over_pi": str(r)},
        "assumptions": {"linearization_about_homogeneous_steady_state": True, "fixed_domain_no_growth": True,
                        "no_mechanical_coupling": True},
        "wavelength": {"near_onset_max_excess": NEAR_ONSET_MAX_EXCESS,
                       "min_domain_over_wavelength": MIN_DOMAIN_OVER_WAVELENGTH},
    }


def check(gamma, d, r, store: SourceStore | None = None, pins: dict | None = None) -> dict:
    """Adapter call at exact rationals. gamma/d may be float (converted with limit_denominator) or Fraction."""
    g = gamma if isinstance(gamma, Fraction) else Fraction(gamma).limit_denominator(10 ** 6)
    dd = d if isinstance(d, Fraction) else Fraction(d).limit_denominator(10 ** 6)
    return analyze(request(g, dd, r), store, pins)


def band_in_q(d, store=None, pins=None):
    """Unstable band in q (gamma=1), exact Fractions from the adapter; None if no band (d too small)."""
    res = check(Fraction(1), Fraction(d), 1, store, pins)
    if res["verdict"] == "refused":
        return None, res
    b = res["band"]
    if not b.get("band_exists"):
        return None, res
    if b.get("exact"):
        return (Fraction(b["q_lower"]), Fraction(b["q_upper"])), res
    # irrational endpoints: use the INNER rational brackets (never overstate the unstable band)
    return (Fraction(b["q_lower_bracket"][1]), Fraction(b["q_upper_bracket"][0])), res


def candidate_modes(L_over_pi: int, lam_star: float, tol=TOL):
    L = L_over_pi * math.pi
    lo = math.ceil(2 * L / (lam_star * (1 + tol)))
    hi = math.floor(2 * L / (lam_star * (1 - tol)))
    return [m for m in range(max(1, lo), hi + 1)]


def gate_design(d, r, lam_star, store=None, pins=None, gamma_range=(0.5, 3.0)):
    """Claim-gated candidate set for a request (target wavelength lam_star, Dv/Du = d, domain length r*pi).

    Returns dict(verdict, reasons, intervals=[(m, g_lo, g_hi)], licensed, analytic_gamma, source_ok, modes_window).
    verdict in {refuse_source, refuse_no_band, refuse_no_mode, candidates}.
    """
    band, res0 = band_in_q(d, store, pins)
    sc = res0.get("source_checks", [])
    if res0["verdict"] == "refused":
        return {"verdict": "refuse_source", "reasons": [res0.get("reasons") or res0.get("refusal")], "intervals": [],
                "licensed": False, "source_checks": sc}
    if band is None:
        return {"verdict": "refuse_no_band", "reasons": ["turing-ddi inequality fails: no unstable band for this Dv/Du"],
                "intervals": [], "licensed": False, "source_checks": sc}
    ql, qu = band
    glo, ghi = gamma_range
    ivs = []
    for m in candidate_modes(r, lam_star):
        qm = Fraction(m * m, r * r)              # (m pi / L)^2 with L = r pi
        # unstable iff q/gamma in (ql, qu)  <=>  gamma in (qm/qu, qm/ql)
        lo, hi = float(qm / qu), float(qm / ql)
        lo, hi = max(lo, glo), min(hi, ghi)
        if lo < hi:
            ivs.append((m, lo, hi))
    if not ivs:
        return {"verdict": "refuse_no_mode", "reasons": ["no admissible Neumann mode within tolerance of the target wavelength is linearly unstable for any gamma in range"],
                "intervals": [], "licensed": False, "source_checks": sc, "band_q": [str(ql), str(qu)]}
    # near-onset licence for the continuum wavelength formula depends only on d here (excess = (0.8d-1)^2/(4d)-1)
    excess = (0.8 * d - 1) ** 2 / (4 * d) - 1
    licensed_onset = excess <= float(Fraction(NEAR_ONSET_MAX_EXCESS))
    return {"verdict": "candidates", "intervals": ivs, "licensed_onset": licensed_onset, "excess": excess,
            "source_checks": sc, "band_q": [str(ql), str(qu)]}


def formula_gamma(d, lam_star):
    """turing-wavelength notation: k_c^2 = sqrt(det J/(Du Dv)); here det J = gamma^2  =>  gamma = sqrt(d) * (2 pi / lam)^2."""
    return math.sqrt(d) * (2 * math.pi / lam_star) ** 2
