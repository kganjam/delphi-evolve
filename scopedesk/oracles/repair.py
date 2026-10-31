"""Repair enumerator: minimal declared changes that make an admissible linear instability available (exact), optionally checked
nonlinearly. Knobs: domain_length (all side lengths scaled by s), reaction_scale (gamma multiplies the Jacobian), diffusion_ratio (Dv).

A repair is only proposed when the exact linear oracle returns `linearly_unstable` for the changed configuration. Whether the
nonlinear system then forms the predicted pattern is a separate, simulated statement (`pde`, only when a kinetics model is given and
with_pde=True). Underdetermined requests (boundary unstated) get no repair: the missing input is the boundary condition, not a knob.
Repair values are exact rationals; ordering is by relative size of the change.
"""
from __future__ import annotations

from fractions import Fraction as F

from . import linear, pde

SCALES = sorted({F(k, 4) for k in range(2, 33)} | {F(k, 2) for k in range(1, 17)})          # 1/2 .. 8
GAMMAS = sorted({F(k, 4) for k in range(1, 129)})                                              # 1/4 .. 32
DVS = sorted({F(k, 2) for k in range(2, 241)})                                                 # 1 .. 120


def _with(s, knob, val):
    t = dict(s)
    dom = dict(t.get("domain") or {k: t[k] for k in t if k.endswith("_over_pi")})
    if knob == "domain_length":
        for k in [k for k in dom if k.endswith("_over_pi")]:
            dom[k] = str(F(s_dom(s)[k]) * val)
        if "domain" in t:
            t["domain"] = dom
        else:
            t.update(dom)
    elif knob == "reaction_scale":
        if "model" in t:
            t["gamma"] = str(val)
        else:
            t["J"] = [str(F(x) * val) for x in t["J"]]
    elif knob == "diffusion_ratio":
        t["Dv"] = str(val)
    return t


def s_dom(s):
    dom = s.get("domain") or {k: s[k] for k in s if k.endswith("_over_pi")}
    return {k: v for k, v in dom.items() if k.endswith("_over_pi")}


def _current(s, knob):
    if knob == "domain_length":
        return F(1)
    if knob == "reaction_scale":
        return F(s.get("gamma", 1)) if "model" in s else F(1)
    return F(s["Dv"])


def enumerate(structured: dict, with_pde=False, per_knob=3) -> dict:
    base = linear.check(structured)
    out = {"base_linear_verdict": base.get("verdict"), "base_scope_verdict": base.get("scope_verdict"), "repairs": [], "note": ""}
    if base.get("scope_verdict") != "out_of_scope":
        out["note"] = {"applies": "no repair needed", "underdetermined": "missing input is the boundary condition, not a knob",
                       "refused": "refused input"}.get(base.get("scope_verdict"), "")
        return out
    if base["condition_ids"] == ["WELLMIXED_STABLE"]:
        out["note"] = "the homogeneous state is unstable without diffusion; none of the three knobs is a diffusion-driven repair except reaction_scale cannot change sign of the trace; no repair offered"
        return out
    for knob, grid in (("domain_length", SCALES), ("reaction_scale", GAMMAS), ("diffusion_ratio", DVS)):
        cur = _current(structured, knob)
        cands = []
        for v in grid:
            val = v if knob == "domain_length" else v
            if val == cur or (knob == "domain_length" and val == 1):
                continue
            s2 = _with(structured, knob, val)
            r = linear.check(s2)
            if r.get("verdict") == "linearly_unstable":
                change = abs(val - cur) / cur
                cands.append((change, val, r))
        cands.sort(key=lambda t: (t[0], t[1]))
        for change, val, r in cands[:per_knob]:
            rec = {"knob": knob, "value": str(val), "relative_change": float(change), "linear_verdict": r["verdict"],
                   "admissible_unstable_modes": r["admissible_unstable_modes"][:5], "evidence": "formal"}
            if with_pde and structured.get("model") and structured.get("bc") in ("neumann", "periodic"):
                s2 = _with(structured, knob, val)
                rec["pde"] = pde.solve(s2)
            out["repairs"].append(rec)
        if not cands:
            out["repairs"].append({"knob": knob, "value": None, "linear_verdict": "no_repair_in_grid", "evidence": "formal"})
    return out
