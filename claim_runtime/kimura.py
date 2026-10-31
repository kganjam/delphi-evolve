"""Hand-authored adapter for the existing Delphi claim `kimura-fixation-probability`.

Claim (Delphi record, network source; math field verbatim):
    u(p) = (1 - exp(-4 Ne s p)) / (1 - exp(-4 Ne s));  neutral limit u(p) = p.
Recorded assumptions (delphi:context): diffusion approximation to the Wright-Fisher
model, genic (additive) selection with coefficient s, constant effective size Ne,
no linkage to other selected sites. The 4Ne form and the "1/(2N)" neutral statement
make the model DIPLOID (2N gene copies); we verified that reading against an exact
diploid Wright-Fisher chain (claim_runtime/exact_chains.py, tests, benchmark).

Nothing here parses or evals the claim's math string. The formula below is
hand-written and bound to a specific claim content hash by claim_runtime/pins.json.
"""
from __future__ import annotations

import math

ADAPTER_ID = "kimura-fixation-probability/diploid-genic-diffusion"
ADAPTER_VERSION = "1.0.0"
CLAIM_ID = "kimura-fixation-probability"

# Assumptions as recorded by Delphi (verbatim paraphrase of delphi:context) ...
RECORDED_ASSUMPTIONS = [
    "diffusion approximation to the Wright-Fisher model",
    "genic (additive) selection with coefficient s",
    "constant effective population size Ne",
    "no linkage to other selected sites",
]
# ... and the ones the adapter ADDS (labelled so nobody mistakes them for the record).
ADAPTER_ADDED_ASSUMPTIONS = [
    "diploid reading: 4Ne s p and the neutral value 1/(2N) imply 2N gene copies; genotype fitnesses 1 : 1+s : 1+2s (checked against an exact chain, not stated verbatim in the record)",
    "a single new or standing mutant at initial frequency p, no recurrent mutation",
    "s is a per-copy selection coefficient in the evolving population's own environment, NOT an assay score",
]
S_LARGE_WARNING = 0.1   # convention, not from the claim; see benchmark for exact-chain error


def _num(name, v):
    if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
        raise ValueError(f"{name} must be a finite number (no strings/expressions are evaluated); got {v!r}")
    return float(v)


def fixation_probability(p: float, Ne: float, s: float) -> float:
    """u(p) with stable expm1 evaluation. Domain: 0<=p<=1, Ne>0, any finite real s."""
    p, Ne, s = _num("p", p), _num("Ne", Ne), _num("s", s)
    if not 0.0 <= p <= 1.0:
        raise ValueError("p must be in [0,1]")
    if not Ne > 0.0:
        raise ValueError("Ne must be > 0")
    if p == 0.0:
        return 0.0
    if p == 1.0:
        return 1.0
    x = 4.0 * Ne * s
    if abs(x) < 1e-8:               # series: u = p (1 + x (1-p)/2 + O(x^2))
        return p * (1.0 + x * (1.0 - p) / 2.0)
    if x > 0.0:
        return math.expm1(-x * p) / math.expm1(-x)
    y = -x                          # y > 0; u = expm1(y p)/expm1(y), rewritten to avoid overflow
    return math.exp(-y * (1.0 - p)) * (-math.expm1(-y * p)) / (-math.expm1(-y))


def new_mutant_frequency(N_census: float) -> float:
    return 1.0 / (2.0 * N_census)


def sensitivity(p: float, Ne: float, s: float, rel_step: float = 1e-4) -> dict:
    """Elasticities d ln u / d ln s and d ln u / d ln Ne (equal, because u depends on Ne*s),
    by central difference of the stable function. Numerical, not analytic."""
    f = lambda sv, nv: fixation_probability(p, nv, sv)
    u0 = f(s, Ne)
    if s == 0.0 or u0 == 0.0:
        return {"elasticity_s": None, "elasticity_Ne": None,
                "note": "undefined at s=0 (use du/ds directly) or u=0"}
    hi, lo = s * (1 + rel_step), s * (1 - rel_step)
    el_s = (math.log(f(hi, Ne)) - math.log(f(lo, Ne))) / (math.log(1 + rel_step) - math.log(1 - rel_step)) \
        if (f(hi, Ne) > 0 and f(lo, Ne) > 0) else None
    nh, nl = Ne * (1 + rel_step), Ne * (1 - rel_step)
    el_n = (math.log(f(s, nh)) - math.log(f(s, nl))) / (math.log(1 + rel_step) - math.log(1 - rel_step)) \
        if (f(s, nh) > 0 and f(s, nl) > 0) else None
    return {"elasticity_s": el_s, "elasticity_Ne": el_n, "method": "central difference of ln u, rel_step=%g" % rel_step}


def neutral_fixation(p: float) -> float:
    return p
