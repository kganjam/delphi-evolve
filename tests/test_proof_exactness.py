"""Exactness, validity and independence tests for evolve.proof (no Lean needed).

Synthetic tables here are LOGIC fixtures for edge cases (NaN, rounding, unknown vertices); they are
never presented as measurements. Real-source facts are asserted against the committed certificates,
re-derived from raw source TEXT with fractions.Fraction (independent of the scaled-int conversion).
"""
import copy
import sys
from fractions import Fraction
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from evolve import proof as P  # noqa: E402

ART = ROOT / "artifacts" / "proof"
CERTS = {p.stem: P.read_json(p) for p in sorted(ART.glob("trpb_*.json"))}


# ---------------------------------------------------------------- strict parsing
@pytest.mark.parametrize("bad", ["nan", "NaN", "inf", "-inf", "", "  ", "1,5", "0x10", "1e", "abc", None, True, float("nan"),
                                 float("inf"), [1]])
def test_parse_exact_rejects_non_finite_or_non_decimal(bad):
    with pytest.raises(P.ProofInputError):
        P.parse_exact(bad)


def test_parse_exact_is_exact_not_binary_float():
    assert P.parse_exact("0.1") == Fraction(1, 10)
    assert P.parse_exact(0.1) == Fraction(1, 10)  # via shortest repr, not 0.1000000000000000055...
    assert P.parse_exact("1.5e-07") == Fraction(15, 10 ** 8)
    assert P.parse_exact("-0.009477917781581479") == Fraction(-9477917781581479, 10 ** 18)


def test_scaled_exact_refuses_inexact_and_outward_rounds_correctly():
    with pytest.raises(P.ProofInputError):
        P.scaled_exact(Fraction(1, 3), 5)
    assert P.floor_scaled(Fraction(-1, 3), 3) == -334  # floor goes down for negatives
    assert P.ceil_scaled(Fraction(-1, 3), 3) == -333
    assert P.floor_scaled(Fraction(1, 3), 3) == 333 and P.ceil_scaled(Fraction(1, 3), 3) == 334


def test_instance_rejects_nan_missing_nondecimal_and_negative_delta():
    for bad in ("nan", "", "1/3"):
        with pytest.raises(P.ProofInputError):
            P.Instance({"VFVS": (bad, "0.1")}, "0")
    with pytest.raises(P.ProofInputError):
        P.Instance({"VFVS": ("0.1", "0.2")}, "-0.001")
    with pytest.raises(P.ProofInputError):
        P.Instance({"VF*S": ("0.1", "0.2")}, "0")  # stop symbol is outside the graph
    with pytest.raises(P.ProofInputError):
        P.Instance({"VFVS": (Fraction(1, 3), "0.2")}, "0")  # non-decimal without outward mode


def test_outward_rounding_only_widens():
    inst = P.Instance({"VFVS": (Fraction(1, 3), Fraction(2, 3))}, "0", scale_exponent=3, outward=True)
    lo, hi = inst.bounds("VFVS")
    assert Fraction(lo, 1000) <= Fraction(1, 3) and Fraction(2, 3) <= Fraction(hi, 1000)
    assert (lo, hi) == (333, 667) and inst.rounded == 1


def test_float_equality_would_give_a_false_certificate_but_exact_comparison_does_not():
    # two decimal texts that collapse to the SAME double; exact comparison must still see u > v.
    u_text, v_text = "0.1000000000000000055511151231257827", "0.1"
    assert float(u_text) == float(v_text)  # the hazard
    inst = P.Instance({"VFVS": (u_text, u_text), "VFMS": (v_text, v_text)}, "0")
    assert not inst.dominates("VFVS", "VFMS")      # exact: hi(u) > lo(v)
    assert inst.dominates("VFMS", "VFVS")
    with pytest.raises(P.CannotCertify):
        P.find_route(inst, "VFVS", "VFMS")


# ---------------------------------------------------------------- graph scope
def test_neighbors_are_the_full_76_single_substitutions_and_symmetric():
    ns = P.neighbors("GCLS")
    assert len(ns) == 76 and len(set(ns)) == 76 and "GCLS" not in ns
    assert all(P.adjacent("GCLS", n) and "GCLS" in P.neighbors(n) for n in ns[:10])
    assert not P.adjacent("GCLS", "ACLT")  # two substitutions
    with pytest.raises(P.ProofInputError):
        P.neighbors("GC*S")


def test_unknown_vertices_block_certificates():
    # route cannot pass through a vertex without an interval
    inst = P.Instance({"VFVS": ("0.1", "0.1"), "AFVS": ("0.2", "0.2")}, "0")
    assert P.find_route(inst, "VFVS", "AFVS") == ["VFVS", "AFVS"]
    with pytest.raises(P.CannotCertify):
        P.find_route(inst, "VFVS", "CFVS")           # CFVS undeclared
    # blocked: unknown neighbours are pulled into S; with a tiny cap the closure cannot be finished
    with pytest.raises(P.CannotCertify):
        P.find_blocked_set(inst, "VFVS", "WWWW", cap=5)


# ---------------------------------------------------------------- committed real-source certificates
@pytest.mark.parametrize("label", sorted(CERTS))
def test_certificate_digest_and_mirror(label):
    c = CERTS[label]
    assert P.certificate_digest(c) == c["certificate_sha256"]
    assert P.check_certificate_python(c) == (True, f"{c['kind']} accepted")
    t = copy.deepcopy(c)
    t["table"][0]["r1"] += 1
    assert P.certificate_digest(t) != c["certificate_sha256"]  # tampering is detectable


def _exact_bounds(c, g):
    e = next(r for r in c["table"] if r["genotype"] == g)
    a, b = P.parse_exact(e["r1_text"]), P.parse_exact(e["r2_text"])
    d = P.parse_exact(c["delta_decimal"])
    return min(a, b) - d, max(a, b) + d


@pytest.mark.parametrize("label", [k for k in sorted(CERTS) if CERTS[k]["kind"] == "route"])
def test_route_dominance_rederived_from_raw_source_text(label):
    c = CERTS[label]
    r = c["route"]
    assert r[0] == c["start"] and r[-1] == c["target"] and len(r) >= 3
    for u, v in zip(r, r[1:]):
        assert P.adjacent(u, v)
        assert _exact_bounds(c, u)[1] <= _exact_bounds(c, v)[0], (u, v)
    assert c["delta_status"].startswith("ASSUMED")


@pytest.mark.parametrize("label", ["trpb_blocked_delta005", "trpb_blocked_multi_delta005"])
def test_blocked_cut_rederived_from_raw_source_text_and_scope_is_full_graph(label):
    c = CERTS[label]
    S = c["closed_set"]
    assert c["start"] in S and c["target"] not in S
    checked = 0
    for u in S:
        for v in P.neighbors(u):
            if v in S:
                continue
            assert _exact_bounds(c, v)[1] < _exact_bounds(c, u)[0], (u, v)  # strictly below, both measured
            checked += 1
    assert c["crossing_edges_checked"] == 76 * len(S)
    assert checked == 76 * len(S) - sum(1 for u in S for v in S if P.adjacent(u, v))
    assert c["graph_scope"]["name"] == "four-site-20^4-single-substitution"
    assert "not_claimed" in c["graph_scope"]


def test_scaled_integers_match_source_text_exactly():
    for c in CERTS.values():
        assert c["outward_rounded_values"] == 0
        for e in c["table"]:
            assert Fraction(e["r1"], 10 ** c["scale_exponent"]) == P.parse_exact(e["r1_text"])
            assert Fraction(e["r2"], 10 ** c["scale_exponent"]) == P.parse_exact(e["r2_text"])


def test_every_data_mutant_has_matching_python_verdict():
    for c in CERTS.values():
        ms = P.data_mutants(c)
        assert any(m["expect"] == "accept" for m in ms) and any(m["expect"] == "reject" for m in ms)
        for m in ms:
            acc, why = P.check_certificate_python(m["cert"])
            assert acc == (m["expect"] == "accept"), (m["name"], why)


def test_cannot_certify_is_an_honest_negative_at_large_delta():
    import json
    sweep = P.read_json(ART / "sensitivity_sweep.json")
    by = {(r["kind"], r["delta"]): r for r in sweep["rows"]}
    assert by[("route", "0.005")]["status"] == "certified"
    assert by[("route", "0.01")]["status"] == "cannot_certify"
    assert all(r["delta_status"] == "assumed" for r in sweep["rows"])


def test_source_tie_when_csv_available():
    try:
        csv = P.find_source_csv()
    except FileNotFoundError:
        pytest.skip("summary_AA.csv not present on this machine; source hash tie NOT verified here")
    obs = P.load_trpb_observations(csv)[0]
    for c in CERTS.values():
        assert P.verify_against_source(c, csv, observations=obs)["rows_checked"] == len(c["table"])
    t = copy.deepcopy(CERTS["trpb_route_delta005"])
    t["table"][1]["r1_text"] = "0.0"
    with pytest.raises(P.ProofInputError):
        P.verify_against_source(t, csv, observations=obs)


def test_loader_leaves_nan_rows_unknown_and_counts_them(tmp_path):
    f = tmp_path / "s.csv"
    f.write_text("AAs,# Stop,mu_1-bg,mu_2-bg\nVFVS,0.0,0.1,0.2\nVFMS,0.0,nan,0.2\nVFLS,0.0,,0.2\nV*VS,1.0,0.1,0.1\n")
    obs, counts = P.load_trpb_observations(f)
    assert list(obs) == ["VFVS"] and counts["non_decimal_unknown"] == 2 and counts["stop_containing"] == 1


# ---------------------------------------------------------------- core kappa-2 admissible cut (bridged)
CORE = P.read_json(ART / "core_kappa2_adm_cut_htgr_gtvn.json")


def test_core_cut_is_a_one_node_admissible_closure_with_exact_integer_intervals():
    c = CORE
    assert c["kind"] == "adm_blocked" and c["closed_set"] == ["HTGR"] and c["start"] == "HTGR" and c["target"] == "GTVN"
    assert c["delta_scaled"] == 0 and c["scale_exponent"] == 6 and len(c["table"]) == 77
    assert c["interval_origin"]["kind"] == "external-intervals"
    assert P.certificate_digest(c) == c["certificate_sha256"]
    u = next(e for e in c["table"] if e["genotype"] == "HTGR")
    for v in P.neighbors("HTGR"):
        e = next(r for r in c["table"] if r["genotype"] == v)
        assert min(e["r1"], e["r2"]) < max(u["r1"], u["r2"]), v     # hi(u) > lo(v): not certified dominating
    assert c["crossing_edges_checked"] == 76
    assert P.check_certificate_python(c) == (True, "adm_blocked accepted")
    assert "Does NOT exclude a true non-decreasing path" in c["semantics"]


def test_core_cut_not_overclaimed_as_blocked():
    # most outside neighbours are NOT certifiably lower, so the strong blocked statement would be false
    c = CORE
    hi_lo = {e["genotype"]: (max(e["r1"], e["r2"]), min(e["r1"], e["r2"])) for e in c["table"]}
    not_descending = [v for v in P.neighbors("HTGR") if not hi_lo[v][0] < hi_lo["HTGR"][1]]
    assert not_descending, "if every neighbour were strictly lower, a blocked certificate would be available"
    forged = copy.deepcopy(c)
    forged["kind"] = "blocked"
    assert P.check_certificate_python(forged)[0] is False


def test_core_cut_adversarial_edits_flip_python_verdict():
    for m in P.data_mutants(CORE):
        acc, why = P.check_certificate_python(m["cert"])
        assert acc == (m["expect"] == "accept"), (m["name"], why)


def test_overlapping_interval_example_is_adm_accepted_but_not_blocked():
    # A=[0,2], B=[1,3], delta 0: same counterexample as Distinction.lean, via the Python mirror
    inst = P.Instance({"AAAA": ("0", "2"), "CAAA": ("1", "3")}, "0")
    assert not inst.dominates("AAAA", "CAAA")                     # hi(A)=2 > lo(B)=1: not certified
    cert = P.build_adm_certificate(inst, "AAAA", "CAAA", {"sha256": "unit-test"}, label="ab_adm")
    assert cert["closed_set"] == ["AAAA"] and P.check_certificate_python(cert)[0] is True
    forged = copy.deepcopy(cert)
    forged["kind"] = "blocked"                                     # B is not certifiably below A
    assert P.check_certificate_python(forged)[0] is False


def test_core_origin_tie_when_csv_available():
    try:
        csv = P.find_source_csv()
    except FileNotFoundError:
        pytest.skip("summary_AA.csv not present on this machine; recomputation NOT verified here")
    r = P.verify_core_origin(CORE, csv)
    assert r["rows_checked"] == 77 and 0 <= r["exact_integer_matches"] <= 77   # the rest agree within 1e-6 (float order)
    t = copy.deepcopy(CORE)
    t["table"][0]["r2"] += 5
    t["certificate_sha256"] = P.certificate_digest(t)    # re-seal so only the recomputation can catch it
    with pytest.raises(P.ProofInputError):
        P.verify_core_origin(t, csv)
