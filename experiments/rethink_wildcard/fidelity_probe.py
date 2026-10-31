"""Smallest decisive probe for candidate E (operationalization-fidelity audit), critic 2026-10-31.

Three exactly-computable families. Each family has a BASE operational test (verdict function over in-scope
instances) that the critic wrote from the Delphi record's math and standard model statements -- NOT yet verified
faithful by a second reader (kill condition 1 in planning/rethink/critic-E-redteam.md). Mutants are produced by
fixed edits. A mutant is labelled CONSEQUENTIAL only if a differential search finds an in-scope instance where the
verdicts disagree (the witness is stored and re-verified); EQUIVALENT if none is found in the search AND an
analytic reason is recorded. Equivalent labels from search alone are 'unrefuted', not proven.
Also reports the deterministic baseline: how often *uniform random* in-scope instances expose each mutant.
Usage: python3 -I fidelity_probe.py OUT.json
"""
import json, math, sys
import numpy as np

# ---------------- family 1: Turing finite-domain instability (Delphi turing-ddi, finite Neumann domain) -------------
def t_inst(rng):
    a, b, c, e = rng.standard_normal(4)
    return {"J": (a, b, c, e), "d": 10 ** rng.uniform(0, 2), "L": math.pi * rng.choice([1, 2, 3, 5, 10]) }
def _det_q(J, d, q):  # det(J - qD), Du=1, Dv=d
    a, b, c, e = J
    return (a - q) * (e - d * q) - b * c
def _stable(J):
    a, b, c, e = J
    return (a + e) < 0 and (a * e - b * c) > 0
def turing_base(x):          # Turing instability on a Neumann interval: stable HSS, some admissible mode n>=1 with det<0
    if not _stable(x["J"]): return False
    return any(_det_q(x["J"], x["d"], (n * math.pi / x["L"]) ** 2) < 0 for n in range(1, 400))
def turing_continuum(x):     # drops admissible-mode restriction: any real q
    if not _stable(x["J"]): return False
    a, b, c, e = x["J"]; d = x["d"]
    B = -(d * a + e); C = a * e - b * c
    return B < 0 and B * B - 4 * d * C > 0
def turing_no_stability(x):  # drops stable-HSS precondition
    return any(_det_q(x["J"], x["d"], (n * math.pi / x["L"]) ** 2) < 0 for n in range(1, 400))
def turing_includes_n0(x):   # adds n=0 (constant mode); equivalent GIVEN stability since det(J)>0
    if not _stable(x["J"]): return False
    return any(_det_q(x["J"], x["d"], (n * math.pi / x["L"]) ** 2) < 0 for n in range(0, 400))
def turing_expanded(x):      # same condition, quadratic expanded: d q^2 - (d a + e) q + det J < 0
    if not _stable(x["J"]): return False
    a, b, c, e = x["J"]; d = x["d"]
    return any(d * q * q - (d * a + e) * q + (a * e - b * c) < 0 for q in [(n * math.pi / x["L"]) ** 2 for n in range(1, 400)])

# ---------------- family 2: Kimura fixation probability, neutral approximation (kimura-fixation-probability) -------
def k_inst(rng):
    return {"Ne": 10 ** rng.uniform(1, 4), "s": rng.choice([-1, 1]) * 10 ** rng.uniform(-5, -0.5)}
def _u(Ne, s, p):
    x = 4 * Ne * s
    if abs(x) < 1e-12: return p
    if x > 0: return -math.expm1(-x * p) / -math.expm1(-x)          # stable for large x>0
    return (math.exp(x) - math.exp(x * (1 - p))) / math.expm1(x)     # x<0: multiply num/den by e^x (stable)
def kimura_base(x):          # in scope |4 Ne s|<=1: is the neutral approximation u~p good to 10% at p=1/(2N)?  (N=Ne)
    if abs(4 * x["Ne"] * x["s"]) > 1: return None  # out of scope -> instance excluded from comparison
    p = 1 / (2 * x["Ne"]); return abs(_u(x["Ne"], x["s"], p) - p) / p < 0.1
def kimura_no_scope(x):      # drops the |4Ne s|<=1 scope guard
    p = 1 / (2 * x["Ne"]); return abs(_u(x["Ne"], x["s"], p) - p) / p < 0.1
def kimura_tol_changed(x):   # tolerance 10% -> 1%
    if abs(4 * x["Ne"] * x["s"]) > 1: return None
    p = 1 / (2 * x["Ne"]); return abs(_u(x["Ne"], x["s"], p) - p) / p < 0.01
def kimura_equiv_form(x):    # same u via (e^x - e^{x(1-p)})/(e^x - 1) computed with expm1 differently
    if abs(4 * x["Ne"] * x["s"]) > 1: return None
    p = 1 / (2 * x["Ne"]); X = 4 * x["Ne"] * x["s"]
    try:
        u = p if abs(X) < 1e-12 else (math.expm1(X) - math.expm1(X * (1 - p))) / math.expm1(X)
    except OverflowError:   # |X|>~709: same expression, evaluated through the stable branch
        u = _u(x["Ne"], x["s"], p)
    return abs(u - p) / p < 0.1
def kimura_abs_err(x):       # relative -> absolute error criterion (absolute error is ~always tiny): consequential
    if abs(4 * x["Ne"] * x["s"]) > 1: return None
    p = 1 / (2 * x["Ne"]); return abs(_u(x["Ne"], x["s"], p) - p) < 0.1

# ---------------- family 3: Hawk-Dove ESS (maynardsmith-hawk-dove) ----------------------------------------------
def h_inst(rng):
    V = 10 ** rng.uniform(-1, 1); return {"V": V, "C": V * 10 ** rng.uniform(-0.7, 0.7)}
def _hd(V, C, p, q):         # expected payoff to mixed strategy p against q (p,q = prob Hawk)
    return p*q*(V-C)/2 + p*(1-q)*V + (1-p)*q*0 + (1-p)*(1-q)*V/2
def hd_base(x):              # in scope C>V: p*=V/C is an ESS (checked on a grid of invaders)
    V, C = x["V"], x["C"]
    if C <= V: return None
    ps = V / C
    return all(_hd(V, C, ps, ps) >= _hd(V, C, q, ps) - 1e-12 and (abs(q - ps) < 1e-9 or _hd(V, C, ps, q) > _hd(V, C, q, q)) for q in np.linspace(0, 1, 101))
def hd_no_scope(x):          # drops C>V guard, still claims p*=V/C ESS
    V, C = x["V"], x["C"]; ps = min(max(V / C, 0.0), 1.0) if C > 0 else 1.0
    ps_claim = V / C
    if ps_claim > 1: return False   # not a probability -> test fails
    return all(_hd(V, C, ps_claim, ps_claim) >= _hd(V, C, q, ps_claim) - 1e-12 and (abs(q - ps_claim) < 1e-9 or _hd(V, C, ps_claim, q) > _hd(V, C, q, q)) for q in np.linspace(0, 1, 101))
def hd_wrong_payoff(x):      # E(H,H)=(V-C)/2 replaced by V-C
    V, C = x["V"], x["C"]
    if C <= V: return None
    def hd2(p, q): return p*q*(V-C) + p*(1-q)*V + (1-p)*(1-q)*V/2
    ps = V / C
    return all(hd2(ps, ps) >= hd2(q, ps) - 1e-12 and (abs(q - ps) < 1e-9 or hd2(ps, q) > hd2(q, q)) for q in np.linspace(0, 1, 101))
def hd_equiv_ps(x):          # p*=V/C rewritten as 1-(C-V)/C
    V, C = x["V"], x["C"]
    if C <= V: return None
    ps = 1 - (C - V) / C
    return all(_hd(V, C, ps, ps) >= _hd(V, C, q, ps) - 1e-12 and (abs(q - ps) < 1e-9 or _hd(V, C, ps, q) > _hd(V, C, q, q)) for q in np.linspace(0, 1, 101))
def hd_weak_ess(x):          # drops the stability (second) ESS clause; keeps only Nash condition
    V, C = x["V"], x["C"]
    if C <= V: return None
    ps = V / C
    return all(_hd(V, C, ps, ps) >= _hd(V, C, q, ps) - 1e-12 for q in np.linspace(0, 1, 101))

FAMILIES = {
 "turing_finite_domain": (t_inst, turing_base, {
    "continuum_instead_of_admissible_modes": (turing_continuum, None),
    "drop_stable_hss_precondition": (turing_no_stability, None),
    "include_constant_mode_n0": (turing_includes_n0, "equivalent given stability: det(J)>0 so q=0 cannot give det<0"),
    "expanded_quadratic_form": (turing_expanded, "algebraic expansion of det(J-qD)")}),
 "kimura_neutral_limit": (k_inst, kimura_base, {
    "drop_scope_guard": (kimura_no_scope, None),
    "tolerance_10pct_to_1pct": (kimura_tol_changed, None),
    "relative_to_absolute_error": (kimura_abs_err, None),
    "rewrite_u_with_expm1_difference": (kimura_equiv_form, "algebraically identical expression for u(p)")}),
 "hawk_dove_ess": (h_inst, hd_base, {
    "drop_C_gt_V_scope": (hd_no_scope, None),
    "payoff_HH_V_minus_C": (hd_wrong_payoff, None),
    "drop_stability_clause": (hd_weak_ess, None),
    "pstar_rewritten_1_minus_C_minus_V_over_C": (hd_equiv_ps, "algebraic rewrite of V/C")}),
}

def verdict(v):
    """Normalise a test output: None means 'refuse: outside declared scope' and is its own verdict."""
    return "refuse" if v is None else bool(v)


def differs(base, mut, x):
    return verdict(base(x)) != verdict(mut(x))


def verify_repair(base, repaired, instances):
    """A proposed repair is accepted only if it agrees with the base test (including refusals) on every
    supplied instance. Agreement on a finite set is NOT a proof of equivalence."""
    return all(not differs(base, repaired, x) for x in instances)

def run(n_search=20000, n_rate=2000, seed=0):
    out = {"seed": seed, "n_search": n_search, "families": {}}
    for fam, (gen, base, muts) in FAMILIES.items():
        rng = np.random.default_rng(seed)
        insts = [gen(rng) for _ in range(n_search)]
        fres = {"n_instances": n_search,
                "base_refuse_rate": float(np.mean([base(x) is None for x in insts])), "mutants": {}}
        for name, (mut, reason) in muts.items():
            wit = next((i for i, x in enumerate(insts) if differs(base, mut, x)), None)
            dis = sum(differs(base, mut, x) for x in insts)
            ok = (differs(base, mut, insts[wit]) if wit is not None else None)  # re-verify witness
            wit_in_scope = (base(insts[wit]) is not None) if wit is not None else None
            rate = float(np.mean([differs(base, mut, x) for x in insts[:n_rate]]))
            fres["mutants"][name] = {
                "label": "consequential" if wit is not None else "equivalent_unrefuted",
                "witness_instance": ({k: (list(v) if isinstance(v, tuple) else float(v)) for k, v in insts[wit].items()} if wit is not None else None),
                "witness_reverified": ok, "witness_inside_base_scope": wit_in_scope,
                "n_disagree_of_%d" % n_search: dis,
                "random_test_exposure_rate_first_%d" % n_rate: rate,
                "analytic_equivalence_reason": reason}
        out["families"][fam] = fres
    exp_equiv = {"include_constant_mode_n0", "expanded_quadratic_form", "rewrite_u_with_expm1_difference",
                 "pstar_rewritten_1_minus_C_minus_V_over_C", "drop_stability_clause"}
    out["label_audit"] = {
        "analytic_expectation_equivalent": sorted(exp_equiv),
        "mismatches": [n for f in out["families"].values() for n, r in f["mutants"].items()
                       if (r["label"] == "equivalent_unrefuted") != (n in exp_equiv)],
        "amendment_note": ("First run (scope-only comparison) mislabelled the two scope-drop mutants as equivalent: "
                           "a dropped scope guard can only differ OUTSIDE the declared scope, so refusal must be a "
                           "verdict. Also my initial expectation that drop_stability_clause is consequential was wrong: "
                           "for the fully mixed p*=V/C, E(p*,q)-E(q,q)=(C/2)(q-p*)^2>0, so the second ESS clause holds "
                           "automatically in scope. Both corrections were made after seeing the first output; the "
                           "first output is summarised in critic-E-redteam.md section 7 (it was not committed).")
        ,"caveat": ("Base tests authored by one reader, unverified by a second; 'equivalent_unrefuted' is a finite "
                   "search outcome plus an analytic argument, not a Lean proof (ShadowBench-style bidirectional "
                   "checking would be stronger); 12 mutants over 3 families = 3 independent families; this is a "
                   "harness check, not a result about LLM auditors.")}
    return out


if __name__ == "__main__":
    r = run(); json.dump(r, open(sys.argv[1], "w"), indent=1)
    for f, v in r["families"].items():
        print(f, "base_refuse_rate", round(v["base_refuse_rate"], 3))
        for n, m in v["mutants"].items():
            print("  ", n, m["label"], "witness_in_scope", m["witness_inside_base_scope"], "rand_exposure", m["random_test_exposure_rate_first_2000"])
    print("audit mismatches:", r["label_audit"]["mismatches"])
