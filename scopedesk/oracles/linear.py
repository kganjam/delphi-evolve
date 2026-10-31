"""Exact linear-instability oracle (evidence kind: formal). Fractions throughout; no floating point decides a verdict.

Question answered (same convention as the Scope Desk bench v1.1): does the declared homogeneous state, stable without
diffusion, have a linearly unstable diffusion-driven mode among the ADMISSIBLE modes of the stated finite domain?
It does NOT say a stable macroscopic pattern follows (see pde.solve) and says nothing about any real tissue.

Input `structured` (dict, strings or numbers that are exact rationals; floats are refused):
  J: [fu, fv, gu, gv]   OR  model: 'schnakenberg'|'brusselator' [+ params {..}, gamma]  -> J = gamma * J1(model)
  Dv (Du defaults to 1), bc in {'neumann','dirichlet','periodic',None}
  domain: 1-D  r_over_pi          (length r*pi)
          2-D  a_over_pi, b_over_pi (rectangle a*pi by b*pi)
Admissible q: Neumann (m*pi/L)^2 (m>=1; 2-D: (m/a)^2+(n/b)^2, m,n>=0 not both 0); Dirichlet 1-D same as Neumann (m>=1),
Dirichlet 2-D m,n>=1; periodic (2m/r)^2 (2-D (2m/a)^2+(2n/b)^2). bc=None: Neumann and periodic are both evaluated; if they
disagree the answer is `underdetermined` with condition BC_UNSTATED (the Delphi turing-ddi record states no boundary condition).
Added assumptions beyond the Delphi record text are listed in ASSUMPTIONS and never hidden.

Return: verdict in {linearly_unstable, stable, wellmixed_unstable, underdetermined, refused};
scope_verdict in the bench vocabulary {applies, out_of_scope, underdetermined, refused}.
"""
from __future__ import annotations

import math
from fractions import Fraction as F

from . import kinetics

ASSUMPTIONS = [
    "two species; linearization about a DECLARED homogeneous steady state (the state/Jacobian is not measured)",
    "fixed domain without growth or mechanics (Delphi turing-ddi context)",
    "boundary conditions and rectangle/1-D mode sets are adapter/oracle additions, not text of the Delphi record",
    "stable/unstable by exact Routh-Hurwitz sign test on each admissible mode matrix",
]
MAX_MODES = 400_000
EVIDENCE = "formal"


class Refuse(Exception):
    def __init__(self, code, detail):
        super().__init__(code)
        self.code, self.detail = code, detail


def rat(name, v):
    if isinstance(v, (bool, float)) or v is None:
        raise Refuse("invalid_input", f"{name}: floats/bools/null refused; give an exact rational (got {v!r})")
    try:
        return F(v)
    except (ValueError, ZeroDivisionError, TypeError):
        raise Refuse("invalid_input", f"{name}: not an exact rational: {v!r}")


def fs(x):
    return str(x.numerator) if x.denominator == 1 else f"{x.numerator}/{x.denominator}"


def jacobian_of(s):
    """-> (fu, fv, gu, gv) exact Fractions."""
    if "J" in s and s["J"] is not None:
        J = [rat(f"J[{i}]", x) for i, x in enumerate(s["J"])]
        if len(J) != 4:
            raise Refuse("invalid_input", "J must be [fu, fv, gu, gv]")
        return tuple(J)
    model = s.get("model")
    if model not in kinetics.DEFAULTS:
        raise Refuse("unsupported_system", f"give J or model in {list(kinetics.DEFAULTS)}")
    p = kinetics.params(model, s.get("params"))
    g = rat("gamma", s.get("gamma", 1))
    (a, b), (c, d) = kinetics.jacobian(model, p)
    return (g * a, g * b, g * c, g * d)


def well_mixed_stable(J):
    a, b, c, e = J
    return (a + e) < 0 and (a * e - b * c) > 0


def band(J, d, Du=F(1)):
    """Continuum band exists (turing-ddi inequality): S>0 and S^2 > 4 Du Dv detJ."""
    a, b, c, e = J
    S = a * d + e * Du
    return S > 0 and S * S > 4 * Du * d * (a * e - b * c)


def det_q(J, Du, Dv, q):
    a, b, c, e = J
    return (a - Du * q) * (e - Dv * q) - b * c


def _lattice(dim, r1, r2, bc, qcut):
    """All admissible q < qcut as sorted list of (q, index) with exact Fractions; refuses above MAX_MODES."""
    mult = 2 if bc == "periodic" else 1
    out = []
    if dim == 1:
        n = 1
        while True:
            q = (F(mult * n) / r1) ** 2
            if q >= qcut:
                break
            out.append((q, (n,)))
            n += 1
            if n > MAX_MODES:
                raise Refuse("too_many_modes", f"more than {MAX_MODES} admissible modes below the tail cutoff")
        return out
    lo = 1 if bc == "dirichlet" else 0
    m = lo
    while (F(mult * m) / r1) ** 2 < qcut:
        n = lo
        while (F(mult * m) / r1) ** 2 + (F(mult * n) / r2) ** 2 < qcut:
            if not (m == 0 and n == 0):
                out.append(((F(mult * m) / r1) ** 2 + (F(mult * n) / r2) ** 2, (m, n)))
                if len(out) > MAX_MODES:
                    raise Refuse("too_many_modes", f"more than {MAX_MODES} admissible modes below the tail cutoff")
            n += 1
        m += 1
    out.sort()
    return out


def _core(J, Du, Dv, dim, r1, r2, bc):
    a, b, c, e = J
    S = a * Dv + e * Du
    P = Du * Dv
    detJ = a * e - b * c
    qcut = max(S, F(0)) / P          # tail rule: q >= S/(Du Dv) => det >= detJ > 0 and trace < 0 (all higher modes stable)
    modes = _lattice(dim, r1, r2, bc, qcut)
    unstable = [(q, idx, det_q(J, Du, Dv, q)) for q, idx in modes if det_q(J, Du, Dv, q) < 0]
    return unstable, modes, qcut


def marginal_modes(J, Du, Dv, modes):
    """Admissible modes with det(J - qD) == 0 exactly (a zero eigenvalue; trace < 0 here): linearization is inconclusive for them.
    The verdict convention (bench key, turing_scope) is STRICT growth, so these do not make a mode 'unstable'; they are reported."""
    return [(q, idx, det_q(J, Du, Dv, q)) for q, idx in modes if det_q(J, Du, Dv, q) == 0]


def _brief(rows, k=12):
    return [{"index": list(idx), "q": fs(q), "det": fs(dt), "q_float": float(q)} for q, idx, dt in rows[:k]]


def _eig_max(J, Du, Dv, q):
    a, b, c, e = J
    A, B, C, E = float(a - Du * q), float(b), float(c), float(e - Dv * q)
    tr, dt = A + E, A * E - B * C
    disc = tr * tr - 4 * dt
    return (tr + math.sqrt(disc)) / 2 if disc >= 0 else tr / 2


def _one_bc(J, Du, Dv, dim, r1, r2, bc):
    if not well_mixed_stable(J):
        return "wellmixed_unstable", None, None, None
    um, modes, qcut = _core(J, Du, Dv, dim, r1, r2, bc)
    return ("linearly_unstable" if um else "stable"), um, modes, qcut


def check(structured: dict) -> dict:
    """Exact linear check; never raises for bad input (returns verdict 'refused' with a code)."""
    sid = structured.get("id", "unnamed") if isinstance(structured, dict) else "unnamed"
    try:
        J = jacobian_of(structured)
        Dv = rat("Dv", structured.get("Dv"))
        Du = rat("Du", structured.get("Du", 1))
        if Du <= 0 or Dv <= 0:
            raise Refuse("invalid_input", "Du, Dv must be > 0")
        dom = structured.get("domain") or structured
        if "r_over_pi" in dom and dom["r_over_pi"] is not None:
            dim, r1, r2 = 1, rat("r_over_pi", dom["r_over_pi"]), None
        elif "a_over_pi" in dom and "b_over_pi" in dom:
            dim, r1, r2 = 2, rat("a_over_pi", dom["a_over_pi"]), rat("b_over_pi", dom["b_over_pi"])
        else:
            raise Refuse("invalid_input", "domain needs r_over_pi (1-D) or a_over_pi and b_over_pi (rectangle)")
        if r1 <= 0 or (r2 is not None and r2 <= 0):
            raise Refuse("invalid_input", "domain lengths must be > 0")
        bc = structured.get("bc")
        if bc not in ("neumann", "dirichlet", "periodic", None):
            raise Refuse("unsupported_boundary", f"bc {bc!r}: supported neumann, dirichlet, periodic, or None (unstated)")
    except Refuse as ex:
        return {"id": sid, "verdict": "refused", "scope_verdict": "refused", "refusal": {"code": ex.code, "detail": ex.detail},
                "condition_ids": [], "admissible_unstable_modes": [], "evidence": EVIDENCE}
    except (KeyError, TypeError, AttributeError) as ex:
        return {"id": sid, "verdict": "refused", "scope_verdict": "refused", "refusal": {"code": "invalid_input", "detail": repr(ex)},
                "condition_ids": [], "admissible_unstable_modes": [], "evidence": EVIDENCE}
    try:
        res = _decide(J, Du, Dv, dim, r1, r2, bc)
    except Refuse as ex:
        return {"id": sid, "verdict": "refused", "scope_verdict": "refused", "refusal": {"code": ex.code, "detail": ex.detail},
                "condition_ids": [], "admissible_unstable_modes": [], "evidence": EVIDENCE}
    res.update(id=sid, evidence=EVIDENCE, assumptions=ASSUMPTIONS,
               inputs={"J": [fs(x) for x in J], "Du": fs(Du), "Dv": fs(Dv), "dim": dim, "r1_over_pi": fs(r1),
                       "r2_over_pi": fs(r2) if r2 is not None else None, "bc": bc})
    return res


def _decide(J, Du, Dv, dim, r1, r2, bc):
    cont = band(J, Dv, Du)
    if bc is None:
        vn = _one_bc(J, Du, Dv, dim, r1, r2, "neumann")
        vp = _one_bc(J, Du, Dv, dim, r1, r2, "periodic")
        if vn[0] == "wellmixed_unstable":
            return _wm(J)
        if vn[0] != vp[0]:
            return {"verdict": "underdetermined", "scope_verdict": "underdetermined", "condition_ids": ["BC_UNSTATED"],
                    "admissible_unstable_modes": [], "continuum_band": cont,
                    "witness": {"neumann": vn[0], "periodic": vp[0], "neumann_modes": _brief(vn[1] or []), "periodic_modes": _brief(vp[1] or [])}}
        bc_used, v = "neumann", vn
    else:
        bc_used, v = bc, _one_bc(J, Du, Dv, dim, r1, r2, bc)
        if v[0] == "wellmixed_unstable":
            return _wm(J)
    verdict, um, modes, qcut = v
    mg = marginal_modes(J, Du, Dv, modes)
    out = {"bc_used": bc_used, "continuum_band": cont, "tail_cutoff_q": fs(qcut), "n_modes_checked": len(modes),
           "n_marginal_modes": len(mg), "marginal_modes": _brief(mg, 5),
           "marginal_note": ("exactly marginal mode(s) present: strict-growth convention gives the verdict above, but linearization is "
                             "inconclusive for them (the reviewed falsification service labels such cases 'unresolved')") if mg else None}
    if verdict == "linearly_unstable":
        top = max(um, key=lambda t: _eig_max(J, Du, Dv, t[0]))
        out.update(verdict="linearly_unstable", scope_verdict="applies", condition_ids=[],
                   admissible_unstable_modes=_brief(um, 50), n_unstable_modes=len(um),
                   witness={"first_unstable": _brief(um, 1)[0], "fastest_growing_mode": {"index": list(top[1]), "q": fs(top[0]),
                            "max_eigenvalue_float": _eig_max(J, Du, Dv, top[0])}})
    else:
        mult = 2 if bc_used == "periodic" else 1
        lo = 1 if bc_used == "dirichlet" else 0
        if dim == 1:
            first = [((F(mult) / r1) ** 2, (1,))]
        else:   # smallest admissible nonzero q of the rectangle (not below the tail cutoff in general)
            cand = [(m, n) for m in range(lo, 3) for n in range(lo, 3) if (m, n) != (0, 0)]
            first = [((F(mult * m) / r1) ** 2 + (F(mult * n) / r2) ** 2, (m, n)) for m, n in cand]
        near = sorted(modes + first, key=lambda t: det_q(J, Du, Dv, t[0]))[:3]
        out.update(verdict="stable", scope_verdict="out_of_scope",
                   condition_ids=["DOMAIN_ADMISSIBLE_MODE"] if cont else ["DIFFUSION_RATIO"],
                   admissible_unstable_modes=[], n_unstable_modes=0,
                   witness={"reason": "continuum band exists but no admissible mode falls inside it" if cont else "turing-ddi inequality fails: no unstable band",
                            "closest_admissible_modes_by_det": _brief([(q, i, det_q(J, Du, Dv, q)) for q, i in near], 3)})
    if dim == 2 and verdict == "linearly_unstable":
        # DIMENSIONALITY witness: would a 1-D reduction along the longest side have said the opposite?
        L = max(r1, r2)
        one = _one_bc(J, Du, Dv, 1, L, None, "periodic" if bc_used == "periodic" else "neumann")
        out["witness"]["one_d_longest_side_would_say"] = one[0]
        if one[0] == "stable":
            out["condition_ids"] = []
            out["witness"]["trap"] = "reducing to 1-D along the longest side wrongly gives 'stable'"
    return out


def _wm(J):
    a, b, c, e = J
    return {"verdict": "wellmixed_unstable", "scope_verdict": "out_of_scope", "condition_ids": ["WELLMIXED_STABLE"],
            "admissible_unstable_modes": [], "continuum_band": False,
            "witness": {"trace": fs(a + e), "det": fs(a * e - b * c), "reason": "turing-ddi assumes a state stable without diffusion"}}


def plain_formula(structured: dict) -> dict:
    """C0, the plain textbook formula: the continuum diffusion-driven inequality, no domain, boundary or admissibility scoping.
    scope_verdict is 'applies' iff the well-mixed state is stable and the inequality D_v f_u + D_u g_v > 2 sqrt(Du Dv det J) holds."""
    try:
        J = jacobian_of(structured)
        Dv, Du = rat("Dv", structured.get("Dv")), rat("Du", structured.get("Du", 1))
    except Refuse as ex:
        return {"scope_verdict": "refused", "refusal": {"code": ex.code, "detail": ex.detail}}
    ok = well_mixed_stable(J) and band(J, Dv, Du)
    return {"scope_verdict": "applies" if ok else "out_of_scope", "baseline": "C0_plain_formula", "evidence": EVIDENCE}
