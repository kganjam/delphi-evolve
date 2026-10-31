"""Pattern-formation falsifier: exact-rational linear-instability adjudication on finite domains.

Question answered (and the only one): given a two-species reaction-diffusion linearization J, diffusivities
(Du, Dv) and a finite domain with a stated boundary condition, does ANY admissible Laplacian mode have a growing
linear perturbation?  The textbook Turing condition (continuum band non-empty) can hold while the answer is NO
because no admissible wavenumber lands in the band (turing_scope's L = pi example).

All decisions use fractions.Fraction.  Physical lengths (not multiples of pi) use rigorous rational bracketing of pi,
so a verdict is only issued when the sign of the mode determinant is the same across the whole bracket.

Evidence type of every output: model-derived (from inputs the caller declared).  Nothing is observed.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
from fractions import Fraction
from math import isqrt

from . import SERVICE_VERSION
from . import presets

PI_LO = Fraction("3.14159265358979323846264338327950")
PI_HI = Fraction("3.14159265358979323846264338327951")   # PI_LO <= pi <= PI_HI (true pi = 3.14159265358979323846264338327950288...)

PRECISIONS = (10 ** 12, 10 ** 24, 10 ** 48, 10 ** 96)
MAX_CANDIDATE_MODES = 250_000
MAX_DIGITS = 60
BOUNDARIES = {"neumann": (1, 0), "dirichlet": (1, 1), "periodic": (2, 0)}   # (wavenumber multiplier c, first mode index)

NOT_ESTABLISHED = [
    "nonlinear pattern existence, selection, amplitude or timescale (linear stability only)",
    "that the declared Jacobian / diffusivities / fixed point describe any real chemical or biological system",
    "behaviour under domain growth, advection, mechanics, noise, anisotropic diffusion, other boundaries or >2 species",
    "anything about a nonlinear model beyond its linearization at the stated homogeneous state",
]
ASSUMPTIONS = [
    "two species; smooth kinetics linearized about a HOMOGENEOUS steady state that the caller declares (Jacobian given or derived from a preset)",
    "diffusion is isotropic and constant: Du, Dv > 0; fixed domain without growth or mechanics",
    "boundaries: neumann (modes n >= 0), dirichlet (modes n >= 1), periodic (wavenumber 2 n pi / L), on an interval or rectangle",
    "boundary meaning is for the PERTURBATION w = u - u*: neumann = zero flux; dirichlet = w = 0 on the boundary, i.e. the boundary concentration is "
    "HELD AT the homogeneous steady state u* (NOT zero concentration, which is incompatible with a nonzero u*); periodic = ring / torus",
    "'unstable' = det(J - q D) < 0 at an admissible q (Routh-Hurwitz sign test for a real 2x2 matrix; trace < 0 is guaranteed when tr J < 0)",
]


PROPOSITION = ("Under the declared two-species linearization J, diffusivities D and domain/boundary, at least one admissible Laplacian mode "
               "has a strictly growing linear eigenvalue (det(J - qD) < 0).")


class Refuse(Exception):
    def __init__(self, code, detail, outcome="out_of_scope"):
        super().__init__(code)
        self.code, self.detail, self.outcome = code, detail, outcome


# ------------------------------------------------------------------ helpers
def fs(x: Fraction) -> str:
    x = Fraction(x)
    return str(x.numerator) if x.denominator == 1 else f"{x.numerator}/{x.denominator}"


_RX_DEC = re.compile(r"[+-]?\d+(\.\d+)?")
_RX_FRAC = re.compile(r"[+-]?\d+/\d+")
MAX_STR = 200


def rat(name, v, notes=None) -> Fraction:
    """Exact rational from int, plain decimal string, 'p/q' string, or a float (read as its decimal repr).
    Scientific notation and over-long strings are refused BEFORE any Fraction is built (a '1e999999999' string would
    otherwise allocate a gigantic integer)."""
    if isinstance(v, bool) or v is None:
        raise Refuse("invalid_input", f"{name}: expected a number, got {v!r}", "out_of_scope")
    try:
        if isinstance(v, float):
            if not math.isfinite(v) or abs(v) >= 1e30:
                raise Refuse("invalid_input", f"{name}: non-finite or |value| >= 1e30")
            x = Fraction(repr(v)) if "e" not in repr(v) else Fraction(v)    # tiny floats such as 1e-07 use the exact binary value
            if notes is not None:
                notes.append(f"{name}: float {v!r} read as {fs(x)}; send a string like '1/10' to avoid this")
        elif isinstance(v, int):
            if abs(v).bit_length() > 200:
                raise Refuse("invalid_input", f"{name}: integer too large")
            x = Fraction(v)
        elif isinstance(v, str):
            t = v.strip()
            if len(t) > MAX_STR or not (_RX_DEC.fullmatch(t) or _RX_FRAC.fullmatch(t)):
                raise Refuse("invalid_input", f"{name}: give an integer, a plain decimal like '0.35' or a fraction like '3/2' (no exponents, max {MAX_STR} chars)")
            x = Fraction(t)
        else:
            raise Refuse("invalid_input", f"{name}: expected number or string, got {type(v).__name__}")
    except (ValueError, ZeroDivisionError, OverflowError):
        raise Refuse("invalid_input", f"{name}: not an exact rational")
    if max(len(str(abs(x.numerator))), len(str(x.denominator))) > MAX_DIGITS:
        raise Refuse("invalid_input", f"{name}: more than {MAX_DIGITS} digits")
    return x


def sqrt_bracket(x: Fraction, scale=10 ** 12):
    n = isqrt(x.numerator * scale * scale // x.denominator)
    return Fraction(n, scale), Fraction(n + 1, scale)


def det_range_sign(P, S, dJ, qa, qb):
    """Sign of det(q)=P q^2 - S q + dJ over [qa,qb] (convex in q, P>0): +1, -1, 0 (exactly zero at a point), None (ambiguous)."""
    f = lambda q: P * q * q - S * q + dJ
    fa, fb = f(qa), f(qb)
    if qa == qb:
        return (fa > 0) - (fa < 0)
    qv = S / (2 * P)
    fmin = min(fa, fb, f(qv)) if qa < qv < qb else min(fa, fb)
    if fmin > 0:
        return 1
    if fa < 0 and fb < 0:      # convex: below the chord on the whole interval
        return -1
    return None


# ------------------------------------------------------------------ input normalization
def normalize(req: dict) -> dict:
    notes: list[str] = []
    if not isinstance(req, dict):
        raise Refuse("invalid_input", "request body must be a JSON object")
    out: dict = {"notes": notes}
    # kinetics
    if "model" in req and req["model"] is not None:
        m = req["model"]
        if not isinstance(m, dict) or not isinstance(m.get("name"), str) or not isinstance(m.get("params", {}), dict):
            raise Refuse("invalid_input", "model must be {'name': <string>, 'params': {<string>: <number>, ...}}")
        params = {str(k)[:40]: rat(f"model.params.{str(k)[:40]}", v, notes) for k, v in (m.get("params") or {}).items()}
        try:
            fp, J = presets.build(m["name"], params)
        except ValueError as e:
            raise Refuse("invalid_input", str(e))
        out["kinetics"] = {"source": f"preset:{m['name']}", "params": {k: fs(v) for k, v in params.items()},
                           "fixed_point": [fs(fp[0]), fs(fp[1])], "fixed_point_exactly_verified": True}
    else:
        try:
            Jr = req["jacobian"]
            if len(Jr) != 2 or any(len(r) != 2 for r in Jr):
                raise Refuse("unsupported_system", "jacobian must be 2x2 (two species); other sizes are out of scope")
            J = [[rat(f"jacobian[{i}][{j}]", Jr[i][j], notes) for j in range(2)] for i in range(2)]
        except KeyError:
            raise Refuse("invalid_input", "give either 'jacobian' ([[a,b],[c,d]]) or 'model' ({'name','params'})")
        except (TypeError, IndexError):
            raise Refuse("invalid_input", "jacobian must be a 2x2 array of numbers or exact strings")
        out["kinetics"] = {"source": "caller-declared jacobian", "fixed_point": "declared by caller, NOT verified by this service"}
    out["J"] = J
    try:
        D = [rat(f"diffusivities[{i}]", v, notes) for i, v in enumerate(req["diffusivities"])]
    except (KeyError, TypeError):
        raise Refuse("invalid_input", "'diffusivities': [Du, Dv] is required")
    if len(D) != 2 or D[0] <= 0 or D[1] <= 0:
        raise Refuse("invalid_input", "exactly two diffusivities, both > 0")
    out["D"] = D
    # domain
    dom = req.get("domain")
    if not isinstance(dom, dict):
        raise Refuse("invalid_input", "'domain' object is required")
    bc = str(dom.get("boundary", "")).lower()
    if bc not in BOUNDARIES:
        raise Refuse("unsupported_boundary", f"boundary {dom.get('boundary')!r} not supported; use one of {sorted(BOUNDARIES)}. "
                     "Robin/mixed/no-flux-with-growth etc. have different admissible spectra.")
    dim = dom.get("dimension", 1)
    if dim not in (1, 2):
        raise Refuse("unsupported_domain", "dimension must be 1 or 2 (rectangle)")
    exact_key, phys_key = ("length_over_pi", "length") if dim == 1 else ("lengths_over_pi", "lengths")
    raw = dom.get(exact_key, dom.get(phys_key))
    if raw is None:
        raise Refuse("invalid_input", f"domain needs '{exact_key}' (exact multiple of pi) or '{phys_key}' (physical length)")
    exact = exact_key in dom
    vals = raw if dim == 2 else [raw]
    if dim == 2 and (not isinstance(vals, list) or len(vals) != 2):
        raise Refuse("invalid_input", f"{exact_key} must be [L1, L2]")
    R = []
    for i, v in enumerate(vals):
        x = rat(f"domain.{exact_key if exact else phys_key}[{i}]", v, notes)
        if x <= 0:
            raise Refuse("invalid_input", "lengths must be > 0")
        R.append((x, x) if exact else (x / PI_HI, x / PI_LO))      # r = L/pi as an interval
    out["domain"] = {"dimension": dim, "boundary": bc, "exact": exact, "r": R,
                     "length_spec": [fs(x) for x in (vals)], "unit": "multiples of pi" if exact else "physical units (pi bracketed)"}
    out["claim"] = str(req.get("claim", ""))[:500]
    out["wants"] = {"lean": bool(req.get("lean", False)), "crosscheck": req.get("crosscheck", True) is not False}
    return out


# ------------------------------------------------------------------ core adjudication
def classify_modes(J, D, dom):
    (a, b), (c, d) = J
    Du, Dv = D
    trJ, dJ = a + d, a * d - b * c
    S, P = a * Dv + d * Du, Du * Dv
    cmul, nmin = BOUNDARIES[dom["boundary"]]
    c2 = cmul * cmul
    R = dom["r"]
    threshold = S / P if S > 0 else None   # q >= S/P  =>  det >= dJ > 0 (tail theorem); S <= 0: all modes stable
    unstable, ambiguous, marginal, examined = [], [], [], 0
    mult_total = 0
    periodic = dom["boundary"] == "periodic"

    def visit(idx):
        nonlocal examined
        examined += 1
        qa = c2 * sum(Fraction(n * n) / (r[1] * r[1]) for n, r in zip(idx, R))
        qb = c2 * sum(Fraction(n * n) / (r[0] * r[0]) for n, r in zip(idx, R))
        s = det_range_sign(P, S, dJ, qa, qb)
        row = {"index": list(idx) if len(idx) > 1 else idx[0], "q": fs(qa) if qa == qb else [fs(qa), fs(qb)]}
        mult = 1
        if periodic:                      # cos and sin eigenfunctions for each nonzero periodic index
            for n_ in idx:
                mult *= 2 if n_ > 0 else 1
        row["eigenfunction_multiplicity"] = mult
        if s == -1:
            nonlocal mult_total
            mult_total += mult
            if qa == qb:
                row.update(trace=fs(trJ - (Du + Dv) * qa), determinant=fs(P * qa * qa - S * qa + dJ))
            unstable.append(row)
        elif s is None:
            ambiguous.append(row)
        elif s == 0:
            marginal.append(row)
        return qa

    if threshold is not None:
        if len(R) == 1:
            n = nmin
            while True:
                qa = Fraction(c2 * n * n) / (R[0][1] * R[0][1])
                if qa >= threshold:
                    break
                if examined >= MAX_CANDIDATE_MODES:
                    raise Refuse("resource_limit", f"more than {MAX_CANDIDATE_MODES} candidate modes; domain too large for exact enumeration", "unresolvable")
                visit((n,))
                n += 1
        else:
            n1 = nmin
            while Fraction(c2 * n1 * n1) / (R[0][1] ** 2) + Fraction(c2 * nmin * nmin) / (R[1][1] ** 2) < threshold:
                n2 = nmin
                while True:
                    qa = Fraction(c2 * n1 * n1) / (R[0][1] ** 2) + Fraction(c2 * n2 * n2) / (R[1][1] ** 2)
                    if qa >= threshold:
                        break
                    if examined >= MAX_CANDIDATE_MODES:
                        raise Refuse("resource_limit", f"more than {MAX_CANDIDATE_MODES} candidate modes", "unresolvable")
                    visit((n1, n2))
                    n2 += 1
                n1 += 1
    return {"trJ": trJ, "detJ": dJ, "S": S, "P": P, "threshold": threshold, "unstable": unstable, "unstable_eigenfunctions": mult_total,
            "ambiguous": ambiguous, "marginal": marginal, "examined": examined}


def band_info(trJ, dJ, S, P):
    disc = S * S - 4 * P * dJ
    exists = bool(S > 0 and disc > 0)
    band = {"textbook_turing_condition_holds": exists,
            "condition": "S = a*Dv + d*Du > 0  and  S^2 > 4 Du Dv det J   (with tr J<0, det J>0)",
            "S": fs(S), "discriminant": fs(disc)}
    if exists:
        lo = sqrt_bracket(disc)
        band["q_lower_bracket"] = [fs((S - lo[1]) / (2 * P)), fs((S - lo[0]) / (2 * P))]
        band["q_upper_bracket"] = [fs((S + lo[0]) / (2 * P)), fs((S + lo[1]) / (2 * P))]
        band["meaning"] = "det(J - qD) < 0 exactly for q strictly between the endpoints (continuum band, in units of 1/length^2 with L in multiples of pi)"
    return band, disc


def length_analysis(J, D, boundary, n_show=4):
    """1-D only. Smallest domain length (multiples of pi) admitting any unstable mode, r_c = c/sqrt(q_hi), as a rational
    bracket [r_lo, r_hi] that is RE-VERIFIED by the exact mode test (no unstable mode at r_lo, an unstable mode at r_hi).
    Precision is refined (1e12, 1e24, 1e48, 1e96); if no verified bracket is reached the analysis is returned as
    status='unresolved' with NO length statement (fail closed: nothing is advised from an unchecked bracket)."""
    (a, b), (c, d) = J
    Du, Dv = D
    S, P, dJ = a * Dv + d * Du, Du * Dv, a * d - b * c
    disc = S * S - 4 * P * dJ
    if not (S > 0 and disc > 0):
        return None
    cm, _ = BOUNDARIES[boundary]
    last = "no precision level tried"
    for scale in PRECISIONS:
        try:
            slo, shi = sqrt_bracket(disc, scale)
            qhi_lo, qhi_hi = (S + slo) / (2 * P), (S + shi) / (2 * P)
            if qhi_lo <= 0:
                last = f"upper band edge not positive at precision {scale}"
                continue
            r_lo = cm * sqrt_bracket(1 / qhi_hi, scale)[0]
            r_hi = cm * sqrt_bracket(1 / qhi_lo, scale)[1]
            if r_lo <= 0 or r_hi <= r_lo:
                last = f"degenerate bracket at precision {scale}"
                continue
            chk = {}
            for tag, r in (("below", r_lo), ("above", r_hi)):
                res = classify_modes(J, D, {"boundary": boundary, "r": [(r, r)]})
                chk[tag] = {"length_over_pi": fs(r), "unstable_modes": [m["index"] for m in res["unstable"]],
                            "marginal_or_unresolved": len(res["marginal"]) + len(res["ambiguous"])}
            if chk["below"]["unstable_modes"] or chk["below"]["marginal_or_unresolved"] or not chk["above"]["unstable_modes"]:
                last = f"exact recheck did not confirm the bracket at precision {scale}"
                continue
            # windows for the first modes at the same verified precision
            ql_lo = (S - shi) / (2 * P)
            wins = []
            for n in range(max(BOUNDARIES[boundary][1], 1), max(BOUNDARIES[boundary][1], 1) + n_show):
                lo_ = cm * n * sqrt_bracket(1 / qhi_hi, scale)[0]
                hi_ = cm * n * sqrt_bracket(1 / ql_lo, scale)[1] if ql_lo > 0 else None
                wins.append({"mode": n, "unstable_for_length_over_pi_between": [float(lo_), float(hi_) if hi_ is not None else None],
                             "note": "reading aid only (floats of rational brackets); not separately re-verified"})
            return {"status": "verified", "precision_scale": scale,
                    "length_over_pi_between": [fs(r_lo), fs(r_hi)],
                    "length_over_pi_between_decimal": [float(r_lo), float(r_hi)],
                    "statement": "No admissible mode is linearly unstable for any domain length <= the lower value; "
                                 "an unstable mode exists at the upper value. Both facts are re-verified by the exact mode test.",
                    "exact_recheck": chk,
                    "why_valid_below": "for r <= r_c every admissible q >= q_1 = c^2/r^2 >= q_upper, outside the open band (monotone in r)",
                    "length_windows": wins}
        except (ZeroDivisionError, ValueError) as e:
            last = f"{type(e).__name__} at precision {scale}"
    return {"status": "unresolved", "detail": last,
            "statement": "No verified critical-length bracket was obtained; NO length is advised. The exact per-domain verdict above is unaffected."}


def diffusion_requirement(J, D):
    """Exact answer to: how much faster must the INHIBITOR diffuse than the ACTIVATOR for the textbook Turing band to exist at all,
    for THESE kinetics?  With alpha = activator self-feedback > 0, delta = inhibitor self-feedback, det J > 0, b*c < 0:

        band exists  <=>  D_inh / D_act  >  rho_c = (2 det J - alpha*delta + 2 sqrt(det J * (-b c))) / alpha^2

    (derived from S > 0 and S^2 > 4 Du Dv det J; rho_c is irrational in general -> rational bracket).  If neither species has
    positive self-feedback, or b*c >= 0, NO ratio suffices.

    There is NO universal threshold: rho_c is a property of THESE kinetics. It always exceeds |delta|/alpha (> 1) and tends to
    |delta|/alpha only as det J -> 0+, i.e. for near-singular, finely tuned kinetics (so a ratio barely above 1 can suffice;
    Lean-checked example: J=[[1,-1],[1011/1000,-101/100]], Du=1, Dv=1.1, L=5pi Neumann, mode 1 det=-21/25000).
    Proof of rho_c > |delta|/alpha: with s=alpha|delta|, beta=-bc>s, rho_c*alpha^2 = 2beta - s + 2 sqrt(beta(beta-s)) is increasing in beta
    and equals s at beta=s.  Figures like '7 to 10' are rules of thumb for particular kinetics.
    This is a kinetics-only calculator note. The service makes no claim about real proteins or tissue transport."""
    (a, b), (c, d) = J
    Du, Dv = D
    dJ = a * d - b * c
    out = {"model_derived_only": True}
    if a <= 0 and d <= 0:
        out.update(status="no_ratio_suffices", reason="neither species has positive self-feedback, so S = a Dv + d Du < 0 at every diffusivity ratio")
        return out
    if b * c >= 0:
        out.update(status="no_ratio_suffices", reason="b*c >= 0 (no activator-inhibitor cross-coupling of opposite sign): the discriminant condition fails at every ratio")
        return out
    if a > 0 and d > 0:                       # both positive self-feedback but tr J < 0 is impossible; guard anyway
        out.update(status="not_applicable", reason="tr J >= 0")
        return out
    # activator = the species with positive self-feedback
    if a > 0:
        alpha, delta, act_name, inh_name, ratio_supplied = a, d, "u", "v", Dv / Du
    else:
        alpha, delta, act_name, inh_name, ratio_supplied = d, a, "v", "u", Du / Dv
    disc = dJ * (-b * c)
    sl, sh = sqrt_bracket(disc, 10 ** 12)
    base = 2 * dJ - alpha * delta
    rho_lo, rho_hi = (base + 2 * sl) / (alpha * alpha), (base + 2 * sh) / (alpha * alpha)
    # exact test of the same condition for the supplied diffusivities, without using the bracket
    S = a * Dv + d * Du
    exceeds = bool(S > 0 and S * S > 4 * Du * Dv * dJ)
    out.update(status="computed", activator=act_name, inhibitor=inh_name,
               required_inhibitor_over_activator_ratio_greater_than_bracket=[fs(rho_lo), fs(rho_hi)],
               required_ratio_decimal=float(rho_lo),
               exact_form="(2 detJ - alpha*delta + 2*sqrt(detJ*(-b*c))) / alpha^2",
               supplied_inhibitor_over_activator_ratio=fs(ratio_supplied), supplied_ratio_meets_textbook_condition=exceeds,
               ratio_lower_bound_for_any_b_c=fs(abs(delta) / alpha),
               det_J=fs(dJ),
               no_universal_threshold="rho_c depends on these kinetics; it exceeds |delta|/alpha > 1 and approaches it only as det J -> 0+ (finely tuned). "
                                      "Numbers such as 7-10 are rules of thumb for particular kinetics, not a property of the mechanism.",
               background="well-known and already measured in vivo (reported by the director's scout, not independently checked here: Mueller et al. 2012 Science 336:721 by FRAP; Kuhn et al. 2022 Nat Commun at single-molecule resolution, where binding rather than molecular size gave the tissue-scale difference). A calculator note for YOUR kinetics, not a finding.")
    return out


# ------------------------------------------------------------------ independent numeric solver (not a proof)
def fd_crosscheck(J, D, dom, ncell=150):
    """Independent route: assemble the full finite-difference operator of the PDE linearization on ncell cells and ask
    numpy for the largest real eigenvalue. Shares no formula with the dispersion-relation test. Floating point,
    discretization error O(h^2): NOT a proof, and may disagree very close to a mode boundary."""
    try:
        import numpy as np
    except ImportError:
        return {"available": False, "reason": "numpy not installed"}
    if dom["dimension"] != 1:
        return {"available": False, "reason": "finite-difference check implemented for 1-D domains only"}
    r = dom["r"][0]
    L = float((r[0] + r[1]) / 2) * math.pi
    h = L / ncell
    Lap = np.zeros((ncell, ncell))
    for i in range(ncell):
        Lap[i, i] = -2.0
        if i > 0:
            Lap[i, i - 1] = 1.0
        if i < ncell - 1:
            Lap[i, i + 1] = 1.0
    bc = dom["boundary"]
    if bc == "neumann":
        Lap[0, 0] = Lap[-1, -1] = -1.0
    elif bc == "dirichlet":
        pass     # cell-centered with antisymmetric ghost: diag end = -3
        Lap[0, 0] = Lap[-1, -1] = -3.0
    else:
        Lap[0, -1] = Lap[-1, 0] = 1.0
    Lap /= h * h
    Jf = np.array([[float(x) for x in row] for row in J])
    A = np.kron(Jf, np.eye(ncell)) + np.kron(np.diag([float(D[0]), float(D[1])]), Lap)
    ev = np.linalg.eigvals(A)
    mx = float(ev.real.max())
    return {"available": True, "method": f"numpy.linalg.eigvals of the full {2 * ncell}x{2 * ncell} finite-difference operator ({bc}, {ncell} cells)",
            "max_real_eigenvalue": mx, "numerically_unstable": mx > 1e-6, "ambiguous": abs(mx) <= 1e-6,
            "limitation": "float, O(h^2) discretization error; independent of the dispersion-relation test but not a proof"}


# ------------------------------------------------------------------ public entry point
def _refusal(rid, e: Refuse, norm_notes=None):
    return {"service": "falsify-turing", "service_version": SERVICE_VERSION, "adjudication": {
                "proposition": PROPOSITION,
                "outcome": e.outcome, "verdict": "refused", "reason_code": e.code, "detail": e.detail},
            "verdict": "refused", "refusal": {"code": e.code, "detail": e.detail},
            "evidence_type": "model-derived", "observed": None, "not_established": NOT_ESTABLISHED,
            "notes": norm_notes or []}


def falsify_turing(req: dict) -> dict:
    try:
        n = normalize(req)
    except Refuse as e:
        return _refusal(None, e)
    J, D, dom = n["J"], n["D"], n["domain"]
    (a, b), (c, d) = J
    trJ, dJ = a + d, a * d - b * c
    if not (trJ < 0 and dJ > 0):
        e = Refuse("claim_precondition_failed",
                   f"Turing's mechanism presupposes a state that is stable WITHOUT diffusion (tr J<0, det J>0); got tr J={fs(trJ)}, det J={fs(dJ)}. "
                   "A diffusion-driven classification is not licensed here (the homogeneous state is already unstable or marginal).")
        r = _refusal(None, e, n["notes"])
        r["derived"] = {"trace_J": fs(trJ), "det_J": fs(dJ)}
        return r
    try:
        res = classify_modes(J, D, dom)
    except Refuse as e:
        return _refusal(None, e, n["notes"])
    band, _ = band_info(trJ, dJ, res["S"], res["P"])
    nu, na, nm = len(res["unstable"]), len(res["ambiguous"]), len(res["marginal"])
    if nu:
        outcome, verdict = "survived", "pattern_possible"
        why = [f"{nu} admissible {dom['boundary']} mode(s) have det(J - qD) < 0: linearly unstable"]
    elif na or nm:
        outcome, verdict = "unresolvable", "unresolved"
        why = [("pi-bracket too coarse to decide the sign for %d mode(s)" % na) if na else "",
               ("%d mode(s) exactly marginal: linearization inconclusive" % nm) if nm else ""]
        why = [w for w in why if w]
    elif band["textbook_turing_condition_holds"]:
        outcome, verdict = "refuted", "domain_blocks_pattern"
        why = ["the textbook Turing condition HOLDS (non-empty continuum band) but no admissible mode lies in the band on this domain: "
               "every admissible mode has trace<0 and det>0 (linearly asymptotically stable), so no strictly growing eigenmode exists here"]
    else:
        outcome, verdict = "refuted", "no_turing_instability"
        why = ["no strictly growing eigenmode: either no continuum band exists (S<=0 or S^2 < 4 Du Dv det J) or the band is a single marginal point (S^2 = 4 Du Dv det J) that no admissible mode hits; "
               "every admissible mode has trace<0 and det>0"]
    out = {
        "service": "falsify-turing", "service_version": SERVICE_VERSION, "verdict": verdict,
        "requested_claim_text": {"text": n["claim"], "status": "uninterpreted caller text; NOT adjudicated, NOT evaluated, not endorsed. "
                                 "The verdict below applies only to the formal proposition named in adjudication.proposition."} if n["claim"] else None,
        "adjudication": {"proposition": PROPOSITION,
                         "outcome": outcome, "verdict": verdict, "reasons": why,
                         "outcome_key": "survived = an unstable admissible mode exists; refuted = none does (stable, certified); "
                                        "out_of_scope = the request is outside what is adjudicated; unresolvable = bracket/marginal case"},
        "evidence_type": "model-derived", "observed": None,
        "kinetics": n["kinetics"],
        "inputs": {"jacobian": [[fs(x) for x in row] for row in J], "diffusivities": [fs(D[0]), fs(D[1])],
                   "domain": {"dimension": dom["dimension"], "boundary": dom["boundary"], "length_spec": dom["length_spec"],
                              "length_unit": dom["unit"]}},
        "derived": {"trace_J": fs(trJ), "det_J": fs(dJ), "S": fs(res["S"]), "DuDv": fs(res["P"])},
        "continuum_band": band,
        "diffusion_requirement": diffusion_requirement(J, D),
        "modes": {"unstable": res["unstable"][:50], "unstable_count": nu, "unstable_eigenfunction_count": res["unstable_eigenfunctions"],
                  "count_meaning": "unstable_count = distinct admissible wavenumber index tuples (canonical non-negative indices); unstable_eigenfunction_count = the same with periodic cos/sin multiplicity (2 per nonzero index)", "unresolved_count": na, "marginal_count": nm,
                  "candidate_modes_examined": res["examined"],
                  "completeness": ("every admissible mode with q < S/(Du Dv) was classified; every mode with q >= S/(Du Dv) has "
                                   "det >= det J > 0 and tr < 0, hence is stable (tail rule, Lean: TuringScope.neumann_tail_hurwitz). "
                                   "So the unstable-mode COUNT and the enumeration are complete; the returned list may be truncated to 50 entries (see returned_detail_truncated)." if res["threshold"] is not None else
                                   "S <= 0: det(q) >= det J > 0 for all q >= 0, so every mode is stable."),
                  "enumeration_complete": True, "returned_detail_truncated": nu > 50},
        "assumptions": ASSUMPTIONS, "not_established": NOT_ESTABLISHED,
        "notes": n["notes"],
        "epistemic_labels": {"observed": "none: no measurement is used", "model_derived": "every number here",
                             "simulated": "only the optional finite-difference cross-check (float)", "unknown": NOT_ESTABLISHED},
    }
    if dom["dimension"] == 1 and band["textbook_turing_condition_holds"]:
        cl = length_analysis(J, D, dom["boundary"])
        cl["applies_to"] = f"1-D {dom['boundary']} domain, length in multiples of pi" + ("; multiply by pi for physical length" if not dom["exact"] else "")
        out["critical_length"] = cl
    # independent implementation 1: turing_scope adapter (pinned Delphi claim turing-ddi) for the case it covers
    out["independent_checks"] = {}
    basis = _delphi_basis()
    out["delphi_claim_basis"] = basis
    if basis.get("source_pin_ok"):
        basis["reuse_status"] = "source_authorized"
        basis["scope"] = ("The turing-ddi record's continuum condition is evaluated here; the finite-domain applicability test is this service's "
                          "own addition (exact), not text from the record.")
    else:
        basis["reuse_status"] = "NOT_authorized_source_pin_failed"
        basis["scope"] = ("The pinned Delphi record could not be verified, so this response is a GENERIC mathematical calculation only. "
                          "It must not be cited as reuse of the Delphi claim turing-ddi.")
        if req.get("require_delphi_pin"):
            return _refusal(None, Refuse("source_pin_failed", "require_delphi_pin was set and the turing-ddi source pin failed", "unresolvable"), n["notes"])
    out["basis"] = "delphi_claim_backed_calculation" if basis.get("source_pin_ok") else "generic_calculation_only"
    if basis.get("source_pin_ok") and dom["dimension"] == 1 and dom["boundary"] == "neumann" and dom["exact"]:
        out["independent_checks"]["turing_scope_adapter"] = _adapter_check(J, D, dom, verdict)
    if n["wants"]["crosscheck"] and dom["dimension"] == 1:
        fd = fd_crosscheck(J, D, dom)
        if fd.get("available"):
            expect = verdict == "pattern_possible"
            fd["agrees_with_exact_verdict"] = None if fd["ambiguous"] else (fd["numerically_unstable"] == expect)
        out["independent_checks"]["finite_difference_eigenvalues"] = fd
    out["lean_wanted"] = n["wants"]["lean"]
    out["_lean_inputs"] = {"J": J, "D": D, "dom": dom, "unstable": res["unstable"], "threshold": res["threshold"]} if (
        dom["dimension"] == 1 and dom["exact"] and verdict in ("pattern_possible", "domain_blocks_pattern", "no_turing_instability")) else None
    return out


def _delphi_basis():
    try:
        from turing_scope.source import SourceStore, load_pins, claim_iri
        chk = SourceStore.bundled().check("turing-ddi", load_pins())
        return {"claim_iri": claim_iri("turing-ddi"), "source_pin_ok": bool(chk.ok), "source_check": chk.to_dict(),
                "role": "the turing-ddi record states the continuum condition this service evaluates; "
                        "applicability (finite domain, boundary) is what the service adds"}
    except Exception as e:                      # keep the service up if the claim snapshot is unavailable
        return {"claim_iri": "turing-ddi", "source_pin_ok": False, "error": f"{type(e).__name__}: {e}"}


def _adapter_check(J, D, dom, verdict):
    try:
        from turing_scope.adapter import analyze
        req = {"request_id": "falsify-crosscheck",
               "system": {"kind": "two_species_reaction_diffusion_linearization", "jacobian": [[fs(x) for x in r] for r in J],
                          "diffusivities": [fs(D[0]), fs(D[1])],
                          "fixed_point": {"declared": True, "description": "declared by the service caller"}},
               "domain": {"dimension": 1, "boundary": "neumann_zero_flux", "length_over_pi": fs(dom["r"][0][0])},
               "assumptions": {"linearization_about_homogeneous_steady_state": True, "fixed_domain_no_growth": True,
                               "no_mechanical_coupling": True}}
        res = analyze(req)
        mapped = {"linearly_unstable": "pattern_possible", "stable": None}.get(res["verdict"], "?")
        if res["verdict"] == "stable":
            agree = verdict in ("domain_blocks_pattern", "no_turing_instability")
        else:
            agree = mapped == verdict
        return {"implementation": "turing_scope.adapter (separately written, pinned to Delphi record turing-ddi)",
                "its_verdict": res["verdict"], "its_unstable_modes": res.get("unstable_modes"), "agrees": bool(agree)}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}", "agrees": None}


def canonical_request(req: dict) -> str:
    return json.dumps(req, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)


def request_hash(req: dict) -> str:
    return hashlib.sha256(canonical_request(req).encode()).hexdigest()
