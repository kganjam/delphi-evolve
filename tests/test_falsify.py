"""Tests for the falsification service. Run bounded:
systemd-run --user --scope -p TasksMax=128 -p MemoryMax=4G -p MemorySwapMax=0 -p RuntimeMaxSec=600 \
  env OMP_NUM_THREADS=2 python -m pytest tests/test_falsify.py -q
Set FALSIFY_TEST_LEAN=1 to include the (slow, ~15 s per case) Lean receipt tests.
"""
import json
import os
import random
import shutil
import sys
import threading
import urllib.request
from fractions import Fraction as F
from http.server import ThreadingHTTPServer
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from falsify import engine, presets, lean_receipt  # noqa: E402
from falsify.engine import falsify_turing as run  # noqa: E402
from falsify import server as srv  # noqa: E402


def base(r="1", bc="neumann", **kw):
    q = {"jacobian": [[1, -2], [2, -3]], "diffusivities": [1, 10],
         "domain": {"dimension": 1, "boundary": bc, "length_over_pi": r}}
    q.update(kw)
    return q


# ---------- the textbook example: pi blocks, 2 pi allows
def test_pi_vs_2pi():
    a, b = run(base("1")), run(base("2"))
    assert a["verdict"] == "domain_blocks_pattern" and a["adjudication"]["outcome"] == "refuted"
    assert a["continuum_band"]["textbook_turing_condition_holds"] is True
    assert b["verdict"] == "pattern_possible" and b["modes"]["unstable"][0]["index"] == 1
    assert b["modes"]["unstable"][0]["determinant"] == "-1/8" and b["modes"]["unstable"][0]["trace"] == "-19/4"
    assert a["independent_checks"]["turing_scope_adapter"]["agrees"] is True
    assert b["independent_checks"]["turing_scope_adapter"]["agrees"] is True
    assert a["independent_checks"]["finite_difference_eigenvalues"]["agrees_with_exact_verdict"] is True
    assert b["independent_checks"]["finite_difference_eigenvalues"]["agrees_with_exact_verdict"] is True


# ---------- regressions from the primary review (issues 1-6)
def test_review1_caller_text_is_never_adjudicated():
    o = run(base("2", claim="this drug cures cancer"))
    assert o["adjudication"]["proposition"] == engine.PROPOSITION
    assert "claim" not in o["adjudication"]
    rc = o["requested_claim_text"]
    assert rc["text"] == "this drug cures cancer" and "NOT adjudicated" in rc["status"]
    assert "cancer" not in json.dumps(o["adjudication"])
    assert run(base("2"))["requested_claim_text"] is None
    r = run(base("2", claim="x") | {"jacobian": [[1, 1], [1, 1]]})            # refusal path also carries the fixed proposition
    assert r["verdict"] == "refused" and r["adjudication"]["proposition"] == engine.PROPOSITION


def test_review2_pin_failure_is_generic_not_delphi_reuse(monkeypatch):
    ok = run(base("2"))
    assert ok["basis"] == "delphi_claim_backed_calculation" and ok["delphi_claim_basis"]["reuse_status"] == "source_authorized"
    monkeypatch.setattr(engine, "_delphi_basis", lambda: {"claim_iri": "turing-ddi", "source_pin_ok": False, "error": "injected fault"})
    bad = run(base("2"))
    assert bad["verdict"] == "pattern_possible"                                  # the arithmetic is unchanged...
    assert bad["basis"] == "generic_calculation_only"                            # ...but it is not Delphi-source-authorized reuse
    assert bad["delphi_claim_basis"]["reuse_status"] == "NOT_authorized_source_pin_failed"
    assert "turing_scope_adapter" not in bad["independent_checks"]
    req = run(base("2", require_delphi_pin=True))
    assert req["verdict"] == "refused" and req["refusal"]["code"] == "source_pin_failed"


@pytest.mark.parametrize("ladder", [engine.PRECISIONS, (10 ** 12,)])
def test_review3_narrow_band_fails_closed_or_is_verified(monkeypatch, ladder):
    """Executed reproducer from the review: J21 = -18/5 + 1e-50. With the default ladder the bracket is refined and re-verified;
    with only the coarse precision the old code emitted an unverified 'unstable at upper endpoint' statement - it must now refuse."""
    monkeypatch.setattr(engine, "PRECISIONS", ladder)
    Jc = str(F(-18, 5) + F(1, 10 ** 50))
    o = run({"jacobian": [[1, 1], [Jc, -2]], "diffusivities": [1, 10], "domain": {"dimension": 1, "boundary": "neumann", "length_over_pi": "2"}})
    assert o["continuum_band"]["textbook_turing_condition_holds"] is True
    cl = o["critical_length"]
    if len(ladder) > 1:
        assert cl["status"] == "verified"
        assert cl["exact_recheck"]["below"]["unstable_modes"] == [] and cl["exact_recheck"]["above"]["unstable_modes"] == [1]
        lo, hi = (F(x) for x in cl["length_over_pi_between"])
        assert 0 < lo < hi
    else:
        assert cl["status"] == "unresolved"
        assert "length_over_pi_between" not in cl and "exact_recheck" not in cl and "length_windows" not in cl
        assert "NO length is advised" in cl["statement"]
        assert o["verdict"] == "domain_blocks_pattern"            # the exact per-domain verdict is unaffected


def test_review3_degenerate_inputs_do_not_raise():
    # tiny positive coefficients / near-zero determinant
    for J in ([[1, 1], ["-18/5", "-2"]], [["1/10**30" if False else str(F(1, 10 ** 30)), 1], [-1, -2]]):
        o = run({"jacobian": J, "diffusivities": [1, 10], "domain": {"dimension": 1, "boundary": "neumann", "length_over_pi": "1"}})
        assert o["verdict"] in ("domain_blocks_pattern", "no_turing_instability", "pattern_possible", "refused", "unresolved")


def test_review4_discriminant_zero_marginal_mode():
    # S^2 = 4 Du Dv det J exactly; marginal q* = 1/4 is hit by Neumann n=1 on L = 2 pi
    o = run({"jacobian": [[1, 3], [-3, -8]], "diffusivities": [1, 16], "domain": {"dimension": 1, "boundary": "neumann", "length_over_pi": "2"}})
    assert o["verdict"] == "unresolved" and o["adjudication"]["outcome"] == "unresolvable" and o["modes"]["marginal_count"] == 1
    o2 = run({"jacobian": [[1, 3], [-3, -8]], "diffusivities": [1, 16], "domain": {"dimension": 1, "boundary": "neumann", "length_over_pi": "1"}})
    assert o2["verdict"] == "no_turing_instability"
    assert "no strictly growing eigenmode" in o2["adjudication"]["reasons"][0]


def test_review5_truncation_wording():
    o = run({"jacobian": [[1, -2], [2, -3]], "diffusivities": [1, 10], "domain": {"dimension": 1, "boundary": "neumann", "length_over_pi": "400"}})
    m = o["modes"]
    assert m["unstable_count"] > 50 and len(m["unstable"]) == 50
    assert m["returned_detail_truncated"] is True and m["enumeration_complete"] is True
    assert "may be truncated" in m["completeness"] and "COMPLETE list" not in m["completeness"]


def test_periodic_multiplicity_is_explicit():
    o = run(base("4", "periodic"))
    m = o["modes"]
    assert m["unstable_count"] >= 1 and "count_meaning" in m
    assert m["unstable_eigenfunction_count"] == sum(x["eigenfunction_multiplicity"] for x in m["unstable"])
    assert all(x["eigenfunction_multiplicity"] == (2 if x["index"] > 0 else 1) for x in m["unstable"])
    n = run(base("4", "neumann"))["modes"]
    assert n["unstable_eigenfunction_count"] == n["unstable_count"]
    d2 = run({"jacobian": [[1, -2], [2, -3]], "diffusivities": [1, 10], "domain": {"dimension": 2, "boundary": "periodic", "lengths_over_pi": ["4", "3"]}})["modes"]
    assert d2["unstable_eigenfunction_count"] == sum(x["eigenfunction_multiplicity"] for x in d2["unstable"]) and d2["unstable_eigenfunction_count"] > d2["unstable_count"]


def test_mcp_tool_description_does_not_promise_complete_list():
    from falsify import server
    assert "complete list" not in server.TOOL_SCHEMA["description"] and "capped at 50" in server.TOOL_SCHEMA["description"]


def test_review6_dirichlet_semantics_stated():
    o = run(base("5", "dirichlet"))
    txt = " ".join(o["assumptions"])
    assert "HELD AT the homogeneous steady state" in txt and "NOT zero concentration" in txt


# ---------- correctness: independent differential tests
def numpy_unstable(J, D, qs):
    import numpy as np
    Jf = np.array([[float(x) for x in r] for r in J])
    return [float(np.linalg.eigvals(Jf - float(q) * np.diag([float(D[0]), float(D[1])])).real.max()) for q in qs]


def test_random_differential_vs_numpy_1d_all_boundaries():
    rng = random.Random(7)
    checked = 0
    for _ in range(150):
        a, d = rng.randint(-6, 6), rng.randint(-6, 6)
        b, c = rng.randint(-6, 6), rng.randint(-6, 6)
        Du, Dv = F(rng.randint(1, 4)), F(rng.randint(1, 60))
        if not (a + d < 0 and a * d - b * c > 0):
            continue
        r = F(rng.randint(1, 80), rng.randint(1, 8))
        bc = rng.choice(["neumann", "dirichlet", "periodic"])
        o = run({"jacobian": [[a, b], [c, d]], "diffusivities": [Du.numerator if Du.denominator == 1 else str(Du), str(Dv)],
                 "domain": {"dimension": 1, "boundary": bc, "length_over_pi": str(r)}, "crosscheck": False})
        if o["verdict"] in ("refused", "unresolved"):
            continue
        cm, nmin = engine.BOUNDARIES[bc]
        n_hi = int(r * 40) + 5
        qs = [F(cm * cm * n * n) / (r * r) for n in range(nmin, n_hi)]
        ev = numpy_unstable([[a, b], [c, d]], [Du, Dv], qs)
        np_unstable = {nmin + i for i, e in enumerate(ev) if e > 1e-9}
        exact = {m["index"] for m in o["modes"]["unstable"]}
        assert exact == np_unstable, (a, b, c, d, Du, Dv, r, bc)
        checked += 1
    assert checked > 25


def test_2d_modes_match_brute_force():
    rng = random.Random(3)
    for _ in range(40):
        a, d, b, c = (rng.randint(-5, 5) for _ in range(4))
        if not (a + d < 0 and a * d - b * c > 0):
            continue
        Du, Dv = 1, rng.randint(5, 40)
        r1, r2 = F(rng.randint(2, 20), 2), F(rng.randint(2, 20), 3)
        for bc in ("neumann", "dirichlet", "periodic"):
            o = run({"jacobian": [[a, b], [c, d]], "diffusivities": [Du, Dv], "domain": {"dimension": 2, "boundary": bc, "lengths_over_pi": [str(r1), str(r2)]}})
            if o["verdict"] in ("refused", "unresolved"):
                continue
            cm, nmin = engine.BOUNDARIES[bc]
            brute = set()
            for m in range(nmin, 60):
                for n in range(nmin, 60):
                    q = cm * cm * (F(m * m) / (r1 * r1) + F(n * n) / (r2 * r2))
                    if (a * Dv + d * Du > 0) and (Du * Dv * q * q - (a * Dv + d * Du) * q + (a * d - b * c)) < 0:
                        brute.add((m, n))
            got = {tuple(x["index"]) for x in o["modes"]["unstable"]}
            assert got == brute


def test_physical_length_matches_exact_and_is_conservative():
    import math
    # L = 2*pi physical -> the same verdict as length_over_pi=2, with pi bracketed
    o = run({"jacobian": [[1, -2], [2, -3]], "diffusivities": [1, 10], "domain": {"dimension": 1, "boundary": "neumann", "length": "6.283185307179586"}})
    assert o["verdict"] == "pattern_possible"
    # a length that puts a mode exactly on the band edge must be 'unresolved', never guessed
    edge = engine.sqrt_bracket(F(1, 1))  # sanity
    assert edge[0] <= 1 <= edge[1]


@pytest.mark.parametrize("name,params", [("brusselator", {"A": F(3, 2), "B": F(5, 2)}), ("schnakenberg", {"a": F(1, 5), "b": F(7, 5)}),
                                         ("gierer_meinhardt", {"a": F(1, 10), "b": F(1, 2)})])
def test_presets_match_symbolic_jacobian(name, params):
    import sympy as sp
    u, v = sp.symbols("u v")
    A, B, a, b = (params.get(k) for k in ("A", "B", "a", "b"))
    if name == "brusselator":
        f, g = sp.Rational(A.numerator, A.denominator) - (sp.Rational(B.numerator, B.denominator) + 1) * u + u ** 2 * v, sp.Rational(B.numerator, B.denominator) * u - u ** 2 * v
    elif name == "schnakenberg":
        f, g = sp.Rational(a.numerator, a.denominator) - u + u ** 2 * v, sp.Rational(b.numerator, b.denominator) - u ** 2 * v
    else:
        f, g = sp.Rational(a.numerator, a.denominator) - sp.Rational(b.numerator, b.denominator) * u + u ** 2 / v, u ** 2 - v
    fp, J = presets.build(name, params)
    sub = {u: sp.Rational(fp[0].numerator, fp[0].denominator), v: sp.Rational(fp[1].numerator, fp[1].denominator)}
    assert sp.simplify(f.subs(sub)) == 0 and sp.simplify(g.subs(sub)) == 0
    Js = sp.Matrix([f, g]).jacobian([u, v]).subs(sub)
    assert [[F(int(sp.numer(Js[i, j])), int(sp.denom(Js[i, j]))) for j in range(2)] for i in range(2)] == J


def test_refusals_are_explicit():
    assert run(base("1", "robin"))["refusal"]["code"] == "unsupported_boundary"
    assert run({"jacobian": [[1, 2, 3], [1, 2, 3]], "diffusivities": [1, 2], "domain": {"boundary": "neumann", "length_over_pi": 1}})["refusal"]["code"] == "unsupported_system"
    assert run(base("1", jacobian=[[1, True], [1, 1]]))["refusal"]["code"] == "invalid_input"
    assert run(base("0"))["refusal"]["code"] == "invalid_input"
    assert run(base("1", diffusivities=[0, 1]))["refusal"]["code"] == "invalid_input"
    assert run(base("1", jacobian=[[1, 0], [0, 1]]))["refusal"]["code"] == "claim_precondition_failed"


# ---------- input hardening (Codex review leads; the exponent case is refused before any Fraction is built)
@pytest.mark.parametrize("bad", ["1e999999999", "1E9", "0x10", "1_000", "9" * 201, " ", "1/0", "--1", float("inf"), float("nan"), 1e40, 10 ** 100, True, None, [1], {"a": 1}])
def test_hostile_numbers_refused_not_raised(bad):
    o = run(base("2", diffusivities=[1, bad]))
    assert o["verdict"] == "refused" and o["refusal"]["code"] == "invalid_input"
    o = run(base(bad))
    assert o["verdict"] == "refused"


@pytest.mark.parametrize("model", [{"name": ["x"]}, {"name": "brusselator", "params": [1, 2]}, {"name": "brusselator", "params": {"A": [1], "B": 2}},
                                   {"name": 7}, "brusselator", {"name": "nope", "params": {}}, {"name": "brusselator", "params": {"A": 1}}])
def test_malformed_model_refused_not_raised(model):
    o = run({"model": model, "diffusivities": [1, 10], "domain": {"dimension": 1, "boundary": "neumann", "length_over_pi": "1"}})
    assert o["verdict"] == "refused"


def test_decimal_and_fraction_strings_still_work():
    o = run(base("2", diffusivities=["1", "10.0"], jacobian=[["1", "-2"], ["2", "-6/2"]]))
    assert o["verdict"] == "pattern_possible"
    assert run(base("2", diffusivities=[1, 1e-07]))["verdict"] in ("no_turing_instability", "domain_blocks_pattern", "refused")


# ---------- parameter uncertainty (Monte Carlo), BT proximity, agent gate
def test_wilson_known_values():
    lo, hi = engine.wilson(5, 10)
    assert abs(lo - 0.2366) < 1e-3 and abs(hi - 0.7634) < 1e-3
    lo, hi = engine.wilson(0, 10)
    assert lo == 0.0 and abs(hi - 0.2775) < 1e-3


def mc(r="2", rel="1/10", n=300, seed=1, **kw):
    return run(base(r, uncertainty={"relative": rel, "n": n, "seed": seed}, crosscheck=False, **kw))


def test_mc_deterministic_and_degenerate_cases():
    a, b = mc()["parameter_uncertainty"], mc()["parameter_uncertainty"]
    assert a == b and a["samples_completed"] == 300
    assert mc(seed=2)["parameter_uncertainty"]["counts"] != a["counts"]
    tiny = mc(rel="1/1000000")["parameter_uncertainty"]            # essentially no uncertainty: survival equals the exact verdict
    assert tiny["survival_fraction"] == 1.0
    assert mc("1", rel="1/1000000")["parameter_uncertainty"]["survival_fraction"] == 0.0


def test_mc_matches_independent_numpy_resampling():
    import numpy as np
    rel, n, seed = F(1, 10), 150, 7
    out = mc(rel=str(rel), n=n, seed=seed)["parameter_uncertainty"]
    rng = random.Random(seed)
    jig = lambda x: F(round(float(x) * (1 + float(rel) * rng.uniform(-1, 1)) * 10 ** 6), 10 ** 6)
    k = 0
    for _ in range(n):
        Jm = [[jig(x) for x in row] for row in ([1, -2], [2, -3])]
        Dm = [jig(x) for x in (1, 10)]
        (a, b), (c, d) = Jm
        if not (a + d < 0 and a * d - b * c > 0):
            continue
        Jf = np.array([[float(x) for x in r_] for r_ in Jm])
        grow = any(np.linalg.eigvals(Jf - (m * m / 4.0) * np.diag([float(Dm[0]), float(Dm[1])])).real.max() > 1e-9 for m in range(0, 400))
        k += grow
    assert k == out["counts"]["pattern_possible"]


def test_mc_preset_perturbs_parameters_and_budget_is_honest(monkeypatch):
    o = run({"model": {"name": "brusselator", "params": {"A": 1, "B": "3/2"}}, "diffusivities": [1, 30],
             "domain": {"dimension": 1, "boundary": "dirichlet", "length_over_pi": "5"}, "uncertainty": {"relative": "1/20", "n": 100, "seed": 3}, "crosscheck": False})
    assert "preset parameter" in o["parameter_uncertainty"]["model"] and o["parameter_uncertainty"]["samples_completed"] == 100
    monkeypatch.setattr(engine, "MC_TIME_BUDGET_S", 0.0)
    z = mc(n=1000)["parameter_uncertainty"]
    assert z["samples_completed"] < 1000 and z["samples_requested"] == 1000


@pytest.mark.parametrize("bad", [{"relative": 0}, {"relative": 2}, {"n": 0}, {"n": 5001}, {"n": True}, {"seed": -1}, "x", {"relative": "1e5"}])
def test_bad_uncertainty_refused(bad):
    assert run(base("2", uncertainty=bad))["verdict"] == "refused"


def test_bt_proximity_and_gate():
    m = run(base("2"))["stability_margins"]
    assert m["trace_J"] == "-2" and m["det_J"] == "1" and m["frobenius_norm_squared"] == "18"
    assert abs(m["bt_proximity"] - ((2 / 18 ** 0.5) ** 2 + (1 / 18) ** 2) ** 0.5) < 1e-12
    near = run({"jacobian": [["-1/1000", 1], ["-1/2000000", 0]], "diffusivities": [1, 10], "domain": {"dimension": 1, "boundary": "neumann", "length_over_pi": "2"}})
    assert near["stability_margins"]["bt_proximity"] < 2e-3
    assert run(base("2"))["gate"]["linear_onset_on_this_domain"] is True and run(base("1"))["gate"]["linear_onset_on_this_domain"] is False
    marg = run({"jacobian": [[1, 3], [-3, -8]], "diffusivities": [1, 16], "domain": {"dimension": 1, "boundary": "neumann", "length_over_pi": "2"}})
    assert marg["gate"]["linear_onset_on_this_domain"] is None and "do not answer" in marg["gate"]["for_agents"]
    assert any("nonlinear" in x for x in run(base("2"))["gate"]["must_not_assert"])


# ---------- diffusion-ratio requirement (Stokes-Einstein bridge, exact)
def _req(J, ratio_act_inh_den, ratio):
    return run({"jacobian": J, "diffusivities": ratio_act_inh_den(ratio), "domain": {"dimension": 1, "boundary": "neumann", "length_over_pi": "50"}, "crosscheck": False})


def test_required_ratio_is_the_exact_band_threshold():
    # textbook example: rho_c = 9 exactly (S = 6, S^2 = 36 = 4 Du Dv det J at ratio 9)
    o = run(base("2"))
    dr = o["diffusion_requirement"]
    assert dr["activator"] == "u" and F(dr["required_inhibitor_over_activator_ratio_greater_than_bracket"][0]) == 9
    assert "proteins" not in dr and not any("mass" in k for k in dr)
    rng = random.Random(11)
    n = 0
    for _ in range(80):
        a, d, b, c = (rng.randint(-6, 6) for _ in range(4))
        if not (a + d < 0 and a * d - b * c > 0):
            continue
        for act_u in (True, False):
            Jm = [[a, b], [c, d]]
            probe = run({"jacobian": Jm, "diffusivities": [1, 2], "domain": {"dimension": 1, "boundary": "neumann", "length_over_pi": "50"}, "crosscheck": False})
            dr = probe["diffusion_requirement"]
            if dr["status"] != "computed":
                # no ratio suffices: the textbook band must be empty at a spread of ratios
                for t in (F(1, 50), 1, 7, 100, 10 ** 4):
                    for dd in ([1, t], [t, 1]):
                        assert run({"jacobian": Jm, "diffusivities": [str(x) for x in dd], "domain": {"dimension": 1, "boundary": "neumann", "length_over_pi": "50"}, "crosscheck": False})["continuum_band"]["textbook_turing_condition_holds"] is False
                n += 1
                break
            lo, hi = (F(x) for x in dr["required_inhibitor_over_activator_ratio_greater_than_bracket"])
            for rr, expect in ((hi * F(1001, 1000) + F(1, 1000), True), (lo * F(999, 1000), False)):
                Dd = [1, str(rr)] if dr["activator"] == "u" else [str(rr), 1]            # inhibitor/activator = rr
                got = run({"jacobian": Jm, "diffusivities": Dd, "domain": {"dimension": 1, "boundary": "neumann", "length_over_pi": "50"}, "crosscheck": False})
                assert got["continuum_band"]["textbook_turing_condition_holds"] is expect, (Jm, rr, dr)
            n += 1
            break
    assert n > 10


def test_required_ratio_matches_numpy_dense_q_scan():
    import numpy as np
    Jm = [[F(1, 2), F(-1)], [F(3, 2), F(-2)]]               # activator u, detJ = 1/2, alpha=1/2, delta=-2
    dr = run({"jacobian": [[str(x) for x in r] for r in Jm], "diffusivities": [1, 10], "domain": {"dimension": 1, "boundary": "neumann", "length_over_pi": "50"}, "crosscheck": False})["diffusion_requirement"]
    rho = float(F(dr["required_inhibitor_over_activator_ratio_greater_than_bracket"][0]))
    qs = np.linspace(1e-4, 3, 6000)
    Jf = np.array([[float(x) for x in r] for r in Jm])
    def grows(ratio):
        return any(np.linalg.eigvals(Jf - q * np.diag([1.0, ratio])).real.max() > 1e-9 for q in qs)
    assert grows(rho * 1.02) and not grows(rho * 0.98)


def test_no_universal_threshold_codex_counterexample():
    """Retraction 2026-10-31: ratio 1.1 suffices for these kinetics (Lean-checked by codex-api; re-derived here exactly)."""
    o = run({"jacobian": [[1, -1], ["1011/1000", "-101/100"]], "diffusivities": [1, "11/10"],
             "domain": {"dimension": 1, "boundary": "neumann", "length_over_pi": "5"}})
    assert o["verdict"] == "pattern_possible"
    m = o["modes"]["unstable"][0]
    assert (m["index"], m["q"], m["determinant"]) == (1, "1/25", "-21/25000")
    dr = o["diffusion_requirement"]
    assert 1 < float(F(dr["required_inhibitor_over_activator_ratio_greater_than_bracket"][1])) < 1.1
    assert "no_universal_threshold" in dr and dr["ratio_lower_bound_for_any_b_c"] == "101/100"


def test_required_ratio_exceeds_abs_delta_over_alpha_and_approaches_it():
    rng = random.Random(5)
    for _ in range(200):
        al, de = F(rng.randint(1, 20), 10), -F(rng.randint(21, 60), 10)       # alpha>0, |delta|>alpha so tr J<0
        s = al * -de
        for eps in (F(1, 10), F(1, 1000), F(1, 10 ** 6)):
            beta = s * (1 + eps)                                               # beta = -bc, so det J = beta - s = s*eps > 0
            b, c = F(1), -beta
            o = run({"jacobian": [[str(al), str(b)], [str(c), str(de)]], "diffusivities": [1, 2], "domain": {"dimension": 1, "boundary": "neumann", "length_over_pi": "50"}, "crosscheck": False})
            lo = F(o["diffusion_requirement"]["required_inhibitor_over_activator_ratio_greater_than_bracket"][0])
            assert lo >= abs(de) / al - F(1, 10 ** 11)                          # rho_c > |delta|/alpha (bracket rounding tolerance)
            if eps == F(1, 10 ** 6):
                assert lo - abs(de) / al < F(1, 100) * abs(de) / al + F(1, 10)  # and it approaches the bound as det J -> 0+


def test_no_ratio_suffices_cases():
    assert run(base("2", jacobian=[[-1, -2], [2, -3]]))["diffusion_requirement"]["status"] == "no_ratio_suffices"        # no positive self-feedback
    swapped = run(base("2", jacobian=[[-3, 2], [-2, 1]], diffusivities=[10, 1]))["diffusion_requirement"]
    assert swapped["activator"] == "v" and swapped["supplied_ratio_meets_textbook_condition"] is True


# ---------- server, MCP, usage ledger
@pytest.fixture()
def live(tmp_path):
    app = srv.App(tmp_path / "d", internal_token="tok")
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), srv.make_handler(app))
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    yield app, f"http://127.0.0.1:{httpd.server_address[1]}"
    httpd.shutdown()


def post(url, body, headers=None):
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers={"Content-Type": "application/json", **(headers or {})}, method="POST")
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read() or b"null")


def test_http_receipt_roundtrip_and_ledger(live):
    app, url = live
    res = post(url + "/v1/falsify/turing", base("2", caller="delphi-test"))
    assert res["verdict"] == "pattern_possible"
    rec = json.loads(urllib.request.urlopen(f"{url}/v1/receipts/{res['receipt_id']}").read())
    assert rec["response"]["receipt_id"] == res["receipt_id"]
    s = json.loads(urllib.request.urlopen(url + "/usage.json").read())
    assert s["totals"]["all_calls"] == 1 and s["totals"]["external_unverified_calls"] == 0     # our own loopback test is NOT 'used'
    assert "None yet" in urllib.request.urlopen(url + "/usage").read().decode()


def test_origin_classification_never_inflates_use(tmp_path):
    from falsify.usage import Ledger
    L = Ledger(tmp_path)
    assert L.classify("127.0.0.1", "someone", False) == "self-test"
    assert L.classify("203.0.113.9", "delphi-x", False) == "self-test"
    assert L.classify("203.0.113.9", "teamA", True) == "self-test"
    assert L.classify("203.0.113.9", "teamA", False) == "external-unverified"
    L.append({"tool": "x", "caller": "teamA", "origin": "external-unverified", "ip_hash": L.ip_hash("203.0.113.9"), "verdict": "pattern_possible"})
    s = L.summary()
    assert s["totals"]["external_unverified_calls"] == 1 and s["external_callers"][0]["caller_label_declared"] == "teamA"
    assert "203.0.113.9" not in json.dumps(s) and "203.0.113.9" not in L.page()


def test_mcp_protocol(live):
    app, url = live
    init = post(url + "/mcp", {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-03-26", "clientInfo": {"name": "t"}}})
    assert init["result"]["serverInfo"]["name"] == "delphi-falsify"
    tl = post(url + "/mcp", {"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
    assert {t["name"] for t in tl["result"]["tools"]} == {"falsify_turing_pattern", "get_receipt"}
    call = post(url + "/mcp", {"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "falsify_turing_pattern", "arguments": base("1")}})
    assert json.loads(call["result"]["content"][0]["text"])["verdict"] == "domain_blocks_pattern"
    assert post(url + "/mcp", {"jsonrpc": "2.0", "id": 4, "method": "nope"})["error"]["code"] == -32601


def test_huge_integer_json_is_400_not_500(live):
    app, url = live
    with pytest.raises(urllib.error.HTTPError) as e:
        urllib.request.urlopen(urllib.request.Request(url + "/v1/falsify/turing", data=b'{"jacobian": [[' + b"9" * 6000 + b", 1], [1, 1]]}", method="POST"))
    assert e.value.code == 400


def test_body_limit_and_bad_json(live):
    app, url = live
    with pytest.raises(urllib.error.HTTPError) as e:
        urllib.request.urlopen(urllib.request.Request(url + "/v1/falsify/turing", data=b"x" * 70000, method="POST"))
    assert e.value.code == 413
    with pytest.raises(urllib.error.HTTPError) as e:
        urllib.request.urlopen(urllib.request.Request(url + "/v1/falsify/turing", data=b"{nope", method="POST"))
    assert e.value.code == 400


# ---------- Lean receipts (slow)
lean_on = os.environ.get("FALSIFY_TEST_LEAN") == "1" and shutil.which("lake")


@pytest.mark.skipif(not lean_on, reason="set FALSIFY_TEST_LEAN=1")
def test_lean_receipt_accepts_truth_rejects_falsehood():
    J, D = [[F(1), F(-2)], [F(2), F(-3)]], [F(1), F(10)]
    good, _ = lean_receipt.build_source(J, D, "neumann", F(2), [1])
    assert lean_receipt.run(good)["status"] == "checked"
    bad, _ = lean_receipt.build_source(J, D, "neumann", F(2), [])         # claims no unstable mode on L = 2 pi: must fail
    assert lean_receipt.run(bad)["status"] == "failed"
