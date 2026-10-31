import json
from fractions import Fraction as F

import pytest

from scopedesk.oracles import gate, kinetics, linear, pde, repair


def test_linear_matches_turing_scope_known_example():
    # turing_scope short/long examples: J=[[1,-2],[2,-3]], Dv=10; L=pi stable, L=2pi unstable (mode 1)
    s = {"J": ["1", "-2", "2", "-3"], "Dv": "10", "bc": "neumann"}
    assert linear.check({**s, "r_over_pi": "1"})["scope_verdict"] == "out_of_scope"
    r = linear.check({**s, "r_over_pi": "2"})
    assert r["scope_verdict"] == "applies" and r["admissible_unstable_modes"][0]["index"] == [1]


def test_boundary_semantics():
    s = {"J": ["1", "-2", "2", "-3"], "Dv": "10", "r_over_pi": "2"}
    assert linear.check({**s, "bc": None})["verdict"] == "underdetermined"       # Neumann unstable, periodic not
    assert linear.check({**s, "bc": "periodic"})["scope_verdict"] == "out_of_scope"
    assert linear.check({**s, "bc": "neumann"})["scope_verdict"] == "applies"


def test_2d_rectangle_dimensionality_trap():
    # a 1-D reduction along the longest side can miss a mode available in the second direction
    for a, b in [("2", "3"), ("3", "2"), ("4", "5")]:
        r = linear.check({"model": "schnakenberg", "gamma": "1", "Dv": "20", "a_over_pi": a, "b_over_pi": b, "bc": "neumann"})
        assert r["verdict"] in ("linearly_unstable", "stable")
    r = linear.check({"J": ["1", "-2", "2", "-3"], "Dv": "10", "a_over_pi": "1", "b_over_pi": "2", "bc": "neumann"})
    assert r["scope_verdict"] == "applies"        # mode (0,1): q=1/4 inside band (1/5,1/2) although 1-D along side 1 is stable


def test_refuses_floats_and_unknown_bc():
    assert linear.check({"J": [1.0, "-2", "2", "-3"], "Dv": "10", "r_over_pi": "2", "bc": "neumann"})["verdict"] == "refused"
    assert linear.check({"J": ["1", "-2", "2", "-3"], "Dv": "10", "r_over_pi": "2", "bc": "robin"})["refusal"]["code"] == "unsupported_boundary"


def test_wellmixed_unstable_is_out_of_scope():
    r = linear.check({"J": ["1", "0", "0", "1"], "Dv": "10", "r_over_pi": "2", "bc": "neumann"})
    assert r["verdict"] == "wellmixed_unstable" and r["condition_ids"] == ["WELLMIXED_STABLE"]


def test_gate_ablations_and_baseline_always_present():
    s = {"J": ["1", "-2", "2", "-3"], "Dv": "10", "r_over_pi": "1", "bc": "neumann"}   # continuum band exists, no admissible mode
    full, rem, hc, co = (gate.decide(s), gate.decide(s, record_removed=True), gate.decide(s, record_hash_changed=True),
                         gate.decide(s, continuum_only=True))
    assert full["decision"] == "out_of_scope" and full["condition_ids"] == ["DOMAIN_ADMISSIBLE_MODE"]
    assert rem["decision"] == "applies" and co["decision"] == "applies"            # plain formula / misapplied claim: wrong here
    assert hc["decision"] == "refused_source"
    assert all(d["baseline_C0"] == "applies" for d in (full, rem, hc, co))
    assert full["turing_scope_crosscheck"]["agree"] is True


def test_repair_is_exactly_checked_and_ordered():
    s = {"J": ["1", "-2", "2", "-3"], "Dv": "10", "r_over_pi": "1", "bc": "neumann"}
    out = repair.enumerate(s)
    dl = [r for r in out["repairs"] if r["knob"] == "domain_length" and r["value"]]
    assert dl and F(dl[0]["value"]) == F(3, 2)         # smallest grid scale giving an admissible unstable mode (1.5 pi > ... exact check)
    for r in dl:
        s2 = dict(s, r_over_pi=str(F(s["r_over_pi"]) * F(r["value"])))
        assert linear.check(s2)["verdict"] == "linearly_unstable"


def test_pde_refuses_bare_jacobian():
    assert pde.solve({"J": ["1", "-2", "2", "-3"], "Dv": "10", "r_over_pi": "2", "bc": "neumann"})["refusal"]["code"] == "no_nonlinear_model"


@pytest.mark.slow_cpu
def test_pde_agrees_with_linear_on_two_models_quick():
    for model, Dv in (("schnakenberg", "20"), ("brusselator", "16")):
        s = {"model": model, "gamma": "1", "Dv": Dv, "r_over_pi": "4", "bc": "neumann"}
        lin = linear.check(s)
        res = pde.solve(s, T_max=600.0)
        assert lin["scope_verdict"] == "applies"
        assert res["category"] in ("pattern", "not_settled") and res["pattern"] is True and res["converged"] is True
    # no band: equal diffusivity -> decays
    res = pde.solve({"model": "schnakenberg", "gamma": "1", "Dv": "1", "r_over_pi": "4", "bc": "neumann"})
    assert res["category"] == "no_pattern"


def test_kinetics_shared_jacobian():
    sj = kinetics.jacobian("schnakenberg", kinetics.params("schnakenberg"))
    bj = kinetics.jacobian("brusselator", kinetics.params("brusselator", {"A": 1, "B": F(9, 5)}))
    assert sj == bj
