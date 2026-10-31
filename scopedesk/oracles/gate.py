"""Delphi-scoped gate: decide(structured, records=..., pins=..., record_removed|record_hash_changed|continuum_only).

Reuses `turing_scope.source` (pinned, hash-checked Delphi records `turing-ddi`, `turing-wavelength`) and, for 1-D Neumann with a
rational Jacobian, cross-checks the committed `turing_scope.adapter.analyze` (no arithmetic is forked: this layer extends it to
periodic/Dirichlet/2-D with its own exact lattice code in linear.py and records the cross-check).

Decision modes
  full                  records accepted -> exact linear check with admissible modes -> applies | out_of_scope | underdetermined
  record_removed        no Delphi record available -> only the plain textbook formula (C0) can be applied; scope_known=False
  record_hash_changed   pinned content hash altered -> every computation is refused (compute -> refuse). Shows PROVENANCE dependence only.
  continuum_only        records accepted but the finite-domain / boundary / dimensionality conditions are ignored: continuum inequality only
                        (the 'misapplied claim' ablation)
The plain formula C0 is returned under `baseline_C0` in EVERY mode and in every audit so the comparison is never hidden.

Three kinds of assumption are kept apart in the output: `delphi_record_text` (what the pinned record states), `adapter_added`
(turing_scope's own additions) and `this_layer_added` (this layer's additions).
"""
from __future__ import annotations

import copy
import math
from fractions import Fraction as F

import numpy as np

from turing_scope.adapter import analyze as ts_analyze
from turing_scope.adapter import RECORDED_ASSUMPTIONS, ADAPTER_ADDED_ASSUMPTIONS
from turing_scope.source import SourceStore, load_pins

from . import linear

LAYER_ADDED = [
    "boundary-condition and rectangle mode sets beyond turing_scope's 1-D Neumann (periodic, Dirichlet, 2-D) are this layer's additions",
    "bc unstated is treated as unknown: Neumann and periodic are both evaluated and disagreement => underdetermined",
    "wavelength-formula licence uses the bench convention: licensed iff 2pi/k_c is within 10% of the fastest-growing ADMISSIBLE linear mode's wavelength (float, margin reported)",
]
REQUIRED = ("turing-ddi",)


def _tamper(pins):
    t = copy.deepcopy(pins)
    h = t["turing-ddi"]["content_sha256"]
    t["turing-ddi"]["content_sha256"] = ("0" if h[0] != "0" else "1") + h[1:]
    return t


def _ts_crosscheck(s, lin):
    """1-D Neumann, rational J: compare unstable mode set with turing_scope.analyze (committed, exact)."""
    try:
        if s.get("bc") != "neumann" or "r_over_pi" not in s or lin.get("verdict") not in ("linearly_unstable", "stable"):
            return None
        J = linear.jacobian_of(s)
        req = {"request_id": "xcheck", "system": {"kind": "two_species_reaction_diffusion_linearization",
               "jacobian": [[linear.fs(J[0]), linear.fs(J[1])], [linear.fs(J[2]), linear.fs(J[3])]],
               "diffusivities": ["1", linear.fs(F(s["Dv"]))],
               "fixed_point": {"declared": True, "description": "declared"}},
               "domain": {"dimension": 1, "boundary": "neumann_zero_flux", "length_over_pi": str(s["r_over_pi"])},
               "assumptions": {"linearization_about_homogeneous_steady_state": True, "fixed_domain_no_growth": True, "no_mechanical_coupling": True}}
        res = ts_analyze(req)
        if res["verdict"] == "refused":
            return {"turing_scope": "refused", "code": res.get("refusal", {}).get("code") if isinstance(res.get("refusal"), dict) else None}
        ts_modes = sorted(res.get("unstable_modes", []))
        mine = sorted(i["index"][0] for i in lin["admissible_unstable_modes"])
        if len(lin["admissible_unstable_modes"]) >= 50:
            mine = mine[:len(ts_modes)]
        return {"turing_scope_verdict": res["verdict"], "turing_scope_unstable_modes": ts_modes[:50], "agree": ts_modes[:50] == mine[:50]}
    except Exception as ex:   # cross-check must never break the decision
        return {"error": repr(ex)}


def decide(structured, records: SourceStore | None = None, pins: dict | None = None, record_removed=False,
           record_hash_changed=False, continuum_only=False) -> dict:
    base = linear.plain_formula(structured)
    out = {"baseline_C0": base["scope_verdict"], "flags": {"record_removed": record_removed, "record_hash_changed": record_hash_changed,
           "continuum_only": continuum_only}, "evidence": "formal",
           "assumptions": {"delphi_record_text": RECORDED_ASSUMPTIONS, "adapter_added": ADAPTER_ADDED_ASSUMPTIONS, "this_layer_added": LAYER_ADDED}}
    if record_removed:
        out.update(decision=base["scope_verdict"], condition_ids=[], scope_known=False, source_checks=[],
                   note="no Delphi record: the plain formula is the only rule available; boundary, domain and dimensionality are unscoped")
        return out
    store = records or SourceStore.bundled()
    pins = pins or load_pins()
    if record_hash_changed:
        pins = _tamper(pins)
    checks = [store.check(c, pins).to_dict() for c in REQUIRED]
    out["source_checks"] = [{k: c[k] for k in ("claim", "ok", "reason", "content_sha256", "pinned_content_sha256")} for c in checks]
    if not all(c["ok"] for c in checks):
        out.update(decision="refused_source", condition_ids=[], scope_known=True,
                   note="pinned record content differs from the reviewed record: computation refused (provenance dependence only; not evidence that the science depends on the record)")
        return out
    if continuum_only:
        out.update(decision=base["scope_verdict"], condition_ids=[], scope_known=False,
                   note="records valid but the finite-domain / boundary / dimensionality conditions are ignored (claim misapplied)")
        return out
    lin = linear.check(structured)
    out.update(decision=lin["scope_verdict"], condition_ids=lin["condition_ids"], scope_known=True, linear=_trim(lin))
    if lin.get("refusal"):
        out["refusal"] = lin["refusal"]
    x = _ts_crosscheck(structured, lin)
    if x is not None:
        out["turing_scope_crosscheck"] = x
    return out


def _trim(lin):
    return {k: lin.get(k) for k in ("verdict", "bc_used", "n_unstable_modes", "witness", "continuum_band", "admissible_unstable_modes")}


# ---- wavelength-formula licence (turing-wavelength record), bench convention --------------------------------------------
def wavelength_licence(structured, tol=0.10) -> dict:
    """licensed iff lambda_c = 2 pi/k_c, k_c^2 = sqrt(det J/(Du Dv)), is within `tol` of the wavelength of the fastest-growing
    ADMISSIBLE no-flux mode (q = (n pi/L)^2, n>=1). Floats decide (sqrt); the margin to the threshold is reported and a margin < 2% is
    flagged `near_threshold`. Linear analysis only. Records are source-checked first (turing-wavelength pin)."""
    try:
        J = linear.jacobian_of(structured)
        Dv, Du = linear.rat("Dv", structured["Dv"]), linear.rat("Du", structured.get("Du", 1))
        r = linear.rat("r_over_pi", structured["r_over_pi"])
    except (linear.Refuse, KeyError) as ex:
        return {"scope_verdict": "refused", "condition_ids": [], "refusal": repr(ex)}
    store, pins = SourceStore.bundled(), load_pins()
    chk = store.check("turing-wavelength", pins)
    if not chk.ok:
        return {"scope_verdict": "refused", "decision": "refused_source", "condition_ids": [], "source_check": chk.to_dict()}
    a, b, c, e = [float(x) for x in J]
    du, dv = float(Du), float(Dv)
    det = a * e - b * c
    if not (a + e < 0 and det > 0):
        return {"scope_verdict": "out_of_scope", "condition_ids": ["WELLMIXED_STABLE"]}
    lam_c = 2 * math.pi / math.sqrt(math.sqrt(det / (du * dv)))
    qs = np.linspace(1e-4, 4.0, 40000)

    def grow(q):
        A, E = a - du * q, e - dv * q
        tr, dt = A + E, A * E - b * c
        disc = tr * tr / 4 - dt
        return tr / 2 + np.sqrt(np.where(disc > 0, disc, 0.0))
    g = grow(qs)
    if g.max() <= 1e-9:
        return {"scope_verdict": "out_of_scope", "condition_ids": ["DIFFUSION_RATIO"]}
    lam_cont = 2 * math.pi / math.sqrt(qs[int(g.argmax())])
    L = float(r) * math.pi
    nn = np.arange(1, 600)
    qa = (nn * math.pi / L) ** 2
    ga = grow(qa)
    if ga.max() <= 1e-9:
        return {"scope_verdict": "out_of_scope", "condition_ids": ["DOMAIN_ADMISSIBLE_MODE"], "margin_to_10pct": 1.0,
                "lambda_c": lam_c, "lambda_cont": lam_cont}
    lam_adm = 2 * math.pi / math.sqrt(qa[int(ga.argmax())])
    dev_a, dev_c = abs(lam_adm - lam_c) / lam_c, abs(lam_cont - lam_c) / lam_c
    res = {"lambda_c": lam_c, "lambda_continuum_fastest": lam_cont, "lambda_admissible_fastest": lam_adm, "dev_admissible": dev_a,
           "dev_continuum": dev_c, "margin_to_10pct": abs(dev_a - tol), "near_threshold": abs(dev_a - tol) < 0.02,
           "source_check": {"claim": "turing-wavelength", "ok": True, "content_sha256": chk.content_sha256}, "evidence": "formal-float"}
    if dev_a <= tol:
        res.update(scope_verdict="applies", condition_ids=[])
    else:
        res.update(scope_verdict="out_of_scope", condition_ids=["NEAR_ONSET"] if dev_c > tol else ["LARGE_DOMAIN"])
    return res
