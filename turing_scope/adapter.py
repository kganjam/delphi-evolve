"""Hand-authored adapter: existing Delphi claims `turing-ddi` / `turing-wavelength` -> an executable
finite-domain linear applicability check.

Scope (deliberately narrow):
  * two species, Jacobian J=[[a,b],[c,d]] at a DECLARED homogeneous steady state (not computed here);
  * Du, Dv > 0; well-mixed state stable (tr J < 0, det J > 0), as the turing-ddi record assumes;
  * 1-D interval of length L = r*pi (r exact rational) with homogeneous Neumann (zero-flux) ends,
    so modes are cos(n*pi*x/L), n=0,1,2,..., with squared wavenumber q_n = n^2 / r^2 (exact rational);
  * linear stability only. No nonlinear pattern, growth, mechanics, noise or tissue claim.

All arithmetic is exact (fractions.Fraction). The statements are the dispersion relation
  det(J - q D) = Du*Dv*q^2 - S*q + det J,  tr(J - q D) = tr J - (Du+Dv) q,   S = a*Dv + d*Du
(S is the quantity D_v f_u + D_u g_v in the turing-ddi record) and the Routh-Hurwitz condition for a real 2x2
matrix (stable iff trace<0 and det>0). Lean (turing_scope/lean) proves the sign/identity/tail lemmas over the
integers; it does NOT prove the Routh-Hurwitz equivalence or any PDE statement.

Evidence typing: every number below is `model-derived` from the declared inputs. Nothing is observed.
"""
from __future__ import annotations

import math
from fractions import Fraction
from math import isqrt

from .source import SourceCheck, SourceStore, claim_iri, load_pins

ADAPTER_ID = "turing-scope/two-species-linear-neumann-1d"
ADAPTER_VERSION = "1.0.0"
SUPPORTED_BOUNDARY = "neumann_zero_flux"
MAX_EXHAUSTIVE_MODES = 200_000   # resource cap; larger cutoffs are refused, not silently truncated

RECORDED_ASSUMPTIONS = [   # from delphi:context of turing-ddi / turing-wavelength (paraphrase)
    "two species", "smooth kinetics, linearization about a homogeneous steady state",
    "fixed domain without growth or mechanics",
    "turing-wavelength: near onset of instability and domain large compared with the wavelength",
]
ADAPTER_ADDED_ASSUMPTIONS = [
    "1-D interval with homogeneous Neumann (zero-flux) ends; modes cos(n pi x / L); NOT Turing's ring (periodic) setting",
    "q_n = (n pi / L)^2 with L = r*pi, r an exact rational supplied by the requester",
    "stable/unstable means the Routh-Hurwitz sign test of the 2x2 mode matrix (trace<0 and det>0) at every admissible mode",
    "the homogeneous fixed point and its Jacobian are DECLARED by the requester; the adapter does not check f(u*,v*)=0 or the Jacobian's origin",
    "'near onset' and 'domain large' thresholds, when a wavelength question is asked, are REQUESTER-DECLARED operationalizations; the Delphi record gives no numbers",
]
EVIDENCE_TYPE = "model-derived"
NOT_ESTABLISHED = [
    "nonlinear pattern existence, selection or amplitude (linear analysis only)",
    "any biological, chemical or nanofabricated system realizing these parameters",
    "that the declared Jacobian/diffusivities describe any real tissue (no measurement is used)",
    "behaviour under domain growth, mechanics, noise, other boundary conditions or higher dimensions",
]


class Refuse(Exception):
    def __init__(self, code, detail):
        super().__init__(code)
        self.code, self.detail = code, detail


def rat(name, v) -> Fraction:
    if isinstance(v, bool) or isinstance(v, float) or v is None:
        raise Refuse("invalid_input", f"{name}: floats/bools/null refused; give an int or exact string like '3/2' (got {v!r})")
    try:
        return Fraction(v)
    except (ValueError, ZeroDivisionError, TypeError):
        raise Refuse("invalid_input", f"{name}: not an exact rational: {v!r}")


def fs(x: Fraction) -> str:
    return str(x.numerator) if x.denominator == 1 else f"{x.numerator}/{x.denominator}"


def frac_sqrt_exact(x: Fraction):
    if x < 0:
        return None
    n, d = isqrt(x.numerator), isqrt(x.denominator)
    return Fraction(n, d) if n * n == x.numerator and d * d == x.denominator else None


def sqrt_bracket(x: Fraction, scale=10**15):
    """Rational lo<=sqrt(x)<=hi with width 1/scale (exact integer arithmetic)."""
    n = isqrt(x.numerator * scale * scale // x.denominator)
    return Fraction(n, scale), Fraction(n + 1, scale)


def _ceil_div(a, b):
    return -((-a) // b)


def first_tail_mode(S: Fraction, P: Fraction, r: Fraction) -> int:
    """Smallest n>=1 with S*p^2 <= P*n^2*s^2, i.e. n^2 >= max(S,0)/P * r^2 (r=p/s).
    From that n on, det >= det J > 0 (mirrors Lean `neumann_tail_hurwitz`)."""
    R = max(S, Fraction(0)) / P * r * r
    need = _ceil_div(R.numerator, R.denominator)       # n^2 >= R  <=>  n^2 >= ceil(R)
    return max(1, isqrt(need - 1) + 1 if need >= 1 else 1)


def mode_row(n, J, D, r):
    (a, b), (c, d) = J
    Du, Dv = D
    q = Fraction(n * n) / (r * r)
    tr = (a - q * Du) + (d - q * Dv)
    det = (a - q * Du) * (d - q * Dv) - b * c
    if det < 0 or tr > 0:
        cls = "unstable"
    elif det == 0 or tr == 0:
        cls = "marginal"
    else:
        cls = "stable"
    row = {"n": n, "q": fs(q), "trace": fs(tr), "determinant": fs(det), "class": cls,
           "wavelength_over_pi": fs(2 * r / n) if n else None}   # cos(n pi x/L) has wavelength 2L/n = 2 r pi / n
    if cls == "unstable":
        disc = tr * tr - 4 * det
        row["eigenvalue_discriminant"] = fs(disc)
        if disc >= 0:   # real eigenvalues; float value is APPROXIMATE (sqrt)
            row["max_eigenvalue_approx"] = (float(tr) + math.sqrt(float(disc))) / 2
            row["eigenvalues_real"] = True
        else:
            row["eigenvalues_real"] = False
    return row


def _refused(req_id, code, detail, checks=None, extra=None):
    out = {"adapter": ADAPTER_ID, "adapter_version": ADAPTER_VERSION, "request_id": req_id, "verdict": "refused",
           "refusal": {"code": code, "detail": detail}, "evidence_type": EVIDENCE_TYPE,
           "source_checks": [c.to_dict() for c in (checks or [])],
           "observed": None, "not_established": NOT_ESTABLISHED}
    if extra:
        out.update(extra)
    return out


def analyze(request: dict, store: SourceStore | None = None, pins: dict | None = None) -> dict:
    store = store or SourceStore.bundled()
    pins = pins or load_pins()
    rid = request.get("request_id", "unnamed")
    # ---- 1. source identity: turing-ddi is always required
    ddi = store.check("turing-ddi", pins)
    checks = [ddi]
    if not ddi.ok:
        return _refused(rid, ddi.reason, f"turing-ddi: {ddi.detail}", checks)
    try:
        sysm, dom = request["system"], request["domain"]
        # ---- 2. declarations the claim's context requires
        decl = request.get("assumptions") or {}
        for key in ("linearization_about_homogeneous_steady_state", "fixed_domain_no_growth", "no_mechanical_coupling"):
            if decl.get(key) is not True:
                raise Refuse("assumption_not_declared", f"assumptions.{key} must be declared true (turing-ddi context)")
        if sysm.get("kind") != "two_species_reaction_diffusion_linearization":
            raise Refuse("unsupported_system", "only two_species_reaction_diffusion_linearization is supported")
        fp = sysm.get("fixed_point") or {}
        if fp.get("declared") is not True or not fp.get("description"):
            raise Refuse("fixed_point_not_declared", "system.fixed_point must have declared=true and a description")
        if dom.get("dimension") != 1:
            raise Refuse("unsupported_domain", "only dimension 1 is supported")
        if dom.get("boundary") != SUPPORTED_BOUNDARY:
            raise Refuse("unsupported_boundary", f"boundary {dom.get('boundary')!r} refused; supported: {SUPPORTED_BOUNDARY!r}. "
                         "Dirichlet, periodic/ring, mixed or unspecified boundaries have different admissible q-spectra.")
        r = rat("domain.length_over_pi", dom.get("length_over_pi"))
        if r <= 0:
            raise Refuse("invalid_input", "domain.length_over_pi must be > 0")
        Jraw = sysm["jacobian"]
        if len(Jraw) != 2 or any(len(row) != 2 for row in Jraw):
            raise Refuse("unsupported_system", "jacobian must be 2x2")
        J = [[rat(f"jacobian[{i}][{j}]", Jraw[i][j]) for j in range(2)] for i in range(2)]
        D = [rat(f"diffusivities[{i}]", v) for i, v in enumerate(sysm["diffusivities"])]
        if len(D) != 2 or D[0] <= 0 or D[1] <= 0:
            raise Refuse("invalid_input", "two diffusivities, both > 0 required")
    except Refuse as e:
        return _refused(rid, e.code, e.detail, checks)
    except (KeyError, TypeError) as e:
        return _refused(rid, "invalid_input", f"missing or malformed field: {e!r}", checks)

    (a, b), (c, d) = J
    Du, Dv = D
    trJ, detJ = a + d, a * d - b * c
    S, P = a * Dv + d * Du, Du * Dv
    if not (trJ < 0 and detJ > 0):
        return _refused(rid, "claim_precondition_failed",
                        f"turing-ddi assumes a state stable without diffusion (tr J<0, det J>0); got tr J={fs(trJ)}, det J={fs(detJ)}. "
                        "The record does not license a diffusion-driven classification here.", checks)

    # ---- 3. exact continuum band (turing-ddi)
    disc = S * S - 4 * P * detJ
    band = {"record_inequality": "D_v f_u + D_u g_v > 2 sqrt(D_u D_v det J)  <=>  S>0 and S^2 > 4 Du Dv det J",
            "S": fs(S), "discriminant_S2_minus_4DuDv_detJ": fs(disc), "band_exists": bool(S > 0 and disc > 0)}
    if band["band_exists"]:
        sq = frac_sqrt_exact(disc)
        lo_hi = [(S - sq) / (2 * P), (S + sq) / (2 * P)] if sq is not None else None
        if lo_hi:
            band.update(exact=True, q_lower=fs(lo_hi[0]), q_upper=fs(lo_hi[1]))
        else:
            slo, shi = sqrt_bracket(disc)
            band.update(exact=False, q_lower_bracket=[fs((S - shi) / (2 * P)), fs((S - slo) / (2 * P))],
                        q_upper_bracket=[fs((S + slo) / (2 * P)), fs((S + shi) / (2 * P))],
                        note="irrational endpoints; exact rational brackets of width ~1e-15")
        band["unstable_when"] = "q strictly between the endpoints (det J - q D < 0)"
    band["det_polynomial"] = f"{fs(P)} q^2 - {fs(S)} q + {fs(detJ)}"
    band["trace_polynomial"] = f"{fs(trJ)} - {fs(Du + Dv)} q"

    # ---- 4. discrete spectrum: exhaustive below the cutoff + analytic tail
    n_cut = first_tail_mode(S, P, r)
    if n_cut > MAX_EXHAUSTIVE_MODES:
        return _refused(rid, "resource_limit", f"first tail mode n={n_cut} exceeds the exhaustive cap {MAX_EXHAUSTIVE_MODES}", checks)
    show_to = max(n_cut + 1, 4)
    rows = [mode_row(n, J, D, r) for n in range(0, show_to + 1)]
    for row in rows:
        row["covered_by_tail_theorem"] = row["n"] >= n_cut
    # exact classification of all n < n_cut; n >= n_cut proved stable by the tail bound
    unstable = [x for x in rows if x["n"] < n_cut and x["class"] == "unstable"]
    marginal = [x for x in rows if x["n"] < n_cut and x["class"] == "marginal"]
    assert all(x["class"] == "stable" for x in rows if x["n"] >= n_cut)  # the tail theorem, re-checked on displayed rows
    tail = {"first_tail_mode_n": n_cut,
            "rule": "for q >= max(S,0)/(Du Dv): det = q(DuDv q - S) + det J >= det J > 0 and tr = tr J - (Du+Dv)q < 0",
            "scope": f"modes n=0..{n_cut - 1} classified exactly one by one; every n>={n_cut} (infinitely many) covered by the rule above",
            "lean": "TuringScope.neumann_tail_hurwitz (parameterized in J, Du, Dv, p, s, n0)"}
    L_label = f"{fs(r)}*pi"
    if unstable:
        verdict, reasons = "linearly_unstable", [
            f"{len(unstable)} admissible Neumann mode(s) have det(J - q D) < 0: n = {[x['n'] for x in unstable]}"]
    elif marginal:
        return _refused(rid, "marginal_non_hyperbolic",
                        f"modes {[x['n'] for x in marginal]} have zero determinant/trace: linearization is inconclusive", checks,
                        {"band": band})
    else:
        verdict, reasons = "stable", [
            "every admissible Neumann mode (n=0 and all n>=1) has trace<0 and det>0: linearly stable"]
        if band["band_exists"]:
            reasons.append("the continuum instability band is non-empty but contains no admissible q_n on this domain")

    # ---- 5. optional wavelength question (turing-wavelength), gated
    wl = _wavelength_section(request.get("wavelength"), store, pins, checks, S, P, detJ, r, unstable)
    out = {
        "adapter": ADAPTER_ID, "adapter_version": ADAPTER_VERSION, "request_id": rid, "verdict": verdict,
        "reasons": reasons, "evidence_type": EVIDENCE_TYPE, "observed": None,
        "inputs": {"jacobian": [[fs(x) for x in row] for row in J], "diffusivities": [fs(Du), fs(Dv)],
                   "fixed_point": fp, "domain": {"dimension": 1, "boundary": SUPPORTED_BOUNDARY, "length_over_pi": fs(r),
                                                  "length": L_label}},
        "derived": {"trace_J": fs(trJ), "det_J": fs(detJ), "S": fs(S), "DuDv": fs(P)},
        "band": band, "modes": rows, "unstable_modes": [x["n"] for x in unstable], "tail": tail,
        "wavelength": wl,
        "source_checks": [c.to_dict() for c in checks],
        "claim_iris": [claim_iri("turing-ddi")] + ([claim_iri("turing-wavelength")] if wl["status"] != "not_requested" else []),
        "assumptions": {"recorded_by_delphi": RECORDED_ASSUMPTIONS, "added_by_adapter": ADAPTER_ADDED_ASSUMPTIONS},
        "not_established": NOT_ESTABLISHED,
        "epistemic_labels": {"observed": "none: no measurement is used", "model_derived": "all numbers in this object",
                             "simulated": "none", "unknown": NOT_ESTABLISHED},
    }
    return out


def _wavelength_section(wreq, store, pins, checks, S, P, detJ, r, unstable_rows):
    if wreq is None:
        return {"status": "not_requested"}
    chk = store.check("turing-wavelength", pins)
    checks.append(chk)
    if not chk.ok:
        return {"status": "refused", "code": chk.reason, "detail": f"turing-wavelength: {chk.detail}"}
    try:
        tol = rat("wavelength.near_onset_max_excess", wreq.get("near_onset_max_excess"))
        m = rat("wavelength.min_domain_over_wavelength", wreq.get("min_domain_over_wavelength"))
    except Refuse as e:
        return {"status": "refused", "code": e.code, "detail": e.detail + " (the Delphi record gives no numeric threshold; the requester must declare one)"}
    if tol < 0 or m <= 0:
        return {"status": "refused", "code": "invalid_input", "detail": "near_onset_max_excess >= 0 and min_domain_over_wavelength > 0 required"}
    ratio = S * S / (4 * P * detJ) if S > 0 else None      # =1 exactly at onset, >1 once a band exists
    # onset wavenumber from the record: k_c^2 = sqrt(det J/(DuDv)); L/lambda_c = r*k_c/2
    kc2 = math.sqrt(float(detJ / P))
    kc = math.sqrt(kc2)
    lam_over_pi = 2.0 / kc            # lambda_c = 2 pi / k_c, in units of pi (approx)
    conds = []
    near = ratio is not None and ratio >= 1 and ratio - 1 <= tol
    conds.append({"condition": "near onset (declared tolerance)", "passed": bool(near),
                  "measure": "S^2/(4 Du Dv det J) - 1 (0 at onset, >0 supercritical)", "value": None if ratio is None else fs(ratio - 1),
                  "declared_max": fs(tol)})
    big = r ** 4 * detJ / P >= (4 * m * m) ** 2           # exact form of  L/lambda_c >= m
    conds.append({"condition": "domain large compared with lambda_c (declared multiple)", "passed": bool(big),
                  "measure": "L/lambda_c = r k_c / 2 (k_c approx; the pass test uses the exact inequality r^4 det J/(DuDv) >= (4 m^2)^2)",
                  "value_approx": r * kc / 2, "declared_min": fs(m)})
    ok = all(cn["passed"] for cn in conds)
    return {"status": "licensed" if ok else "not_licensed",
            "meaning": "licensed = the record's stated applicability conditions hold under the declared thresholds; "
                       "not_licensed = do NOT use lambda_c = 2 pi/k_c as the pattern wavelength",
            "conditions": conds,
            "infinite_domain_wavelength_over_pi_approx": lam_over_pi,
            "formula": "k_c^2 = sqrt(det J/(Du Dv)); lambda_c = 2 pi/k_c (turing-wavelength record notation; evaluated in float)",
            "discrete_unstable_mode_wavelengths_over_pi": [x["wavelength_over_pi"] for x in unstable_rows],
            "note": "On a finite domain only the mode wavelengths 2L/n are available (cf. Turing 1952: wavelengths on a ring must divide the circumference)."}
