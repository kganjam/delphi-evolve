"""Actual reuse of the existing Delphi claim `turing-ddi` (via the committed, source-pinned turing_scope adapter) as a
DECISION GATE for the bioelectric-patterning arm: can a gap-junction-coupled voltage field plus ONE further variable show
diffusion-driven (Turing) instability at the resting state of real cells?

Inputs that are MEASURED: the resting membrane time constant tau_m of each used Allen Institute cell (a = -1/tau_m is the
voltage self-derivative of the linearised membrane at rest). Inputs that are DECLARED (not measured, swept over a grid):
the partner variable's relaxation time, the cross-coupling product, and the diffusivity ratio (gap-junction diffusion
of V versus the partner). Output: adapter verdicts (exact rational arithmetic; model-derived, nothing observed).

Claim-driven decision: turing-ddi needs  D_v f_u + D_u g_v > 2 sqrt(D_u D_v det J)  which requires S = a D_w + d D_V > 0.
With a < 0 (measured stable rest) the band can exist only if the partner is self-activating (d > 0)... which the adapter
checks exactly. ABLATIONS: (i) 'fault' request with a hypothetical regenerative a > 0 (NOT measured) flips the verdict;
(ii) with the claim's precondition removed the adapter would not classify at all (refused: both D > 0 and stable state).
Scope: linear, 1-D, Neumann, declared fixed point; says nothing about nonlinear excitable pattern formation, ionic
(electrodiffusive) coupling, or any tissue. A claim-removed pipeline would simply simulate and could mislabel
initial-condition-dependent standing patterns as Turing patterns; that counterfactual is NOT measured here.
"""
from __future__ import annotations

import json
from fractions import Fraction
from pathlib import Path

from turing_scope.adapter import analyze

from .run_strength_duration import usable

HERE = Path(__file__).resolve().parent
RES = HERE / "results"


def fr(x):  # exact rational of a value rounded to 0.01 (documented rounding of the measurement)
    return str(Fraction(round(x * 100), 100))


def req(rid, a, d, k, dw, L="50"):
    return {"request_id": rid,
            "system": {"kind": "two_species_reaction_diffusion_linearization", "jacobian": [[a, "1"], [k, d]],
                       "diffusivities": ["1", dw],
                       "fixed_point": {"declared": True, "description": "resting state; a=-1/tau_m measured (Allen Cell Types), other entries declared"}},
            "domain": {"dimension": 1, "boundary": "neumann_zero_flux", "length_over_pi": L},
            "assumptions": {"linearization_about_homogeneous_steady_state": True, "fixed_domain_no_growth": True, "no_mechanical_coupling": True}}


def main():
    cells = [c for c in json.loads((RES / "cell_features.json").read_text())["cells"] if not usable(c)]
    verdicts, n_req, refused = {}, 0, {}
    sample = None
    for c in cells:
        tau = Fraction(fr(c["tau_ms"]))                     # ms; a = -1/tau (per ms)
        a = -1 / tau
        for rho in (Fraction(1), Fraction(10), Fraction(100)):
            d = -1 / (rho * tau)
            for kk in (Fraction(0), Fraction(1), Fraction(4)):
                k = -kk / (tau * rho * tau)   # c = -kk/(tau*tau_w) with b=1 => b*c<=0, det = (1+kk)/(tau*tau_w) > 0
                for dw in ("1/1000", "1", "1000"):
                    r = analyze(req(f"c{c['specimen__id']}-rho{rho}-k{kk}-dw{dw}", str(a), str(d), str(k), dw))
                    n_req += 1
                    verdicts[r["verdict"]] = verdicts.get(r["verdict"], 0) + 1
                    if r["verdict"] == "refused": refused[r["refusal"]["code"]] = refused.get(r["refusal"]["code"], 0) + 1
        # ABLATION: hypothetical regenerative voltage (a>0, NOT measured), fast inhibitor-like partner
        af = 1 / (2 * tau); df = -2 / tau; kf = -4 / (tau * tau)
        rf = analyze(req(f"fault-{c['specimen__id']}", str(af), str(df), str(kf), "100"))
        n_req += 1
        verdicts["ablation_regenerative_" + rf["verdict"]] = verdicts.get("ablation_regenerative_" + rf["verdict"], 0) + 1
        if sample is None: sample = {"measured_rest_request": r, "ablation_request": rf}
    # precondition ablation: a strictly voltage-only coupling (gating variable does not diffuse, D_w = 0) is outside the record
    c0 = cells[0]; t0 = Fraction(fr(c0["tau_ms"]))
    r0 = analyze(req("dw-zero", str(-1 / t0), str(-1 / t0), "0", "0"))
    out_dw0 = {"verdict": r0["verdict"], "refusal": r0.get("refusal")}
    out = {"claim": "turing-ddi (Delphi record pinned in turing_scope/sources/pins.json)", "adapter": "turing_scope.adapter.analyze",
           "n_cells": len(cells), "n_requests": n_req, "verdict_counts": verdicts, "refusals": refused,
           "reading": ("If every measured-rest request is 'stable', the claim+measurement excludes Turing-type voltage patterning from a "
                       "passive-at-rest voltage variable for all swept partner/ coupling/ diffusivity choices on these cells; the regenerative "
                       "ablation shows the verdict changes only when the declared (unmeasured) self-activation sign is changed."),
           "voltage_only_D_w_zero_request": out_dw0, "sample_pair": {k: {kk: v[kk] for kk in ("request_id", "verdict", "reasons", "unstable_modes") if kk in v} for k, v in sample.items()},
           "not_established": ["any biological pattern", "nonlinear/excitable dynamics", "gap-junction conductance of any tissue",
                               "the counterfactual that a claim-free pipeline would have mislabeled patterns"]}
    (RES / "turing_gate.json").write_text(json.dumps(out, indent=1))
    print(json.dumps({k: out[k] for k in ("n_cells", "n_requests", "verdict_counts", "refusals")}, indent=1))


if __name__ == "__main__":
    main()
