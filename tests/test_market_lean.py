"""Lean-coverage evaluation and basin-probability scoring. Literal hand fixtures and test-only simulated power fixtures."""
import json
import math

import numpy as np
import pytest
from scipy import stats as sps

from market import basin as BA
from market import desk as D
from market import lean as L


def write(tmp, name, rows):
    p = tmp / name
    p.write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    return p


def setup(tmp, stm, proofs, ledger=None):
    """stm: list of (id, family). proofs: {arm: {id: (proved, axioms_clean, calls[, reuse])}}"""
    sp = write(tmp, "stm.jsonl", [{"statement_id": i, "family": f} for i, f in stm])
    rows = []
    for arm, d in proofs.items():
        for i, t in d.items():
            r = {"statement_id": i, "arm": arm, "proved": t[0], "axioms_clean": t[1], "compiler_calls": t[2]}
            if len(t) > 3:
                r["cross_family_lemma_uses"] = t[3]
            rows.append(r)
    rp = write(tmp, "res.jsonl", rows)
    lp = write(tmp, "ledger.jsonl", [{"arm": a, "compiler_calls": c} for a, c in ledger.items()]) if ledger else None
    return dict(statements_path=sp, results_path=rp, ledger_path=lp)


STM6 = [("s1", "f1"), ("s2", "f1"), ("s3", "f2"), ("s4", "f2"), ("s5", "f3"), ("s6", "f3")]


def arm(proved_ids, calls=10, clean=True):
    return {i: (i in proved_ids, clean, calls) for i, _ in STM6}


def test_hand_coverage_mcnemar_and_budget_gate(tmp_path):
    proofs = {"L1": arm({"s1", "s2", "s3"}), "L2": arm({"s1", "s3"}), "L3": arm({"s1", "s2", "s3", "s4", "s5"}), "L0": arm({"s1"})}
    rep = L.run_lean(**setup(tmp_path, STM6, proofs, ledger={"L1": 100, "L2": 103, "L3": 99, "L0": 12}))
    assert rep["arms"]["L3"]["coverage"]["k"] == 5 and rep["arms"]["L3"]["coverage"]["rate"] == pytest.approx(5 / 6)
    assert rep["arms"]["L2"]["coverage"]["cp_lo"] == pytest.approx(sps.beta.ppf(0.025, 2, 5))
    c = rep["comparisons"]["L3_vs_L2"]
    assert c["status"] == "COMPARED_MATCHED_BUDGET" and c["x_minus_y_coverage"] == pytest.approx(0.5)
    assert (c["mcnemar"]["x_only_right"], c["mcnemar"]["y_only_right"]) == (3, 0) and c["mcnemar"]["p_two_sided_exact"] == pytest.approx(0.25)
    # only 3 families: the bootstrap would be a zero-width interval; the guard refuses to issue a verdict
    assert c["verdict"].startswith("INSUFFICIENT FAMILIES") and rep["commons_benefit_supported"] is False
    assert rep["comparisons"]["L3_vs_L0"]["status"] == "COMPARED_UNMATCHED_BASELINE_EXEMPT_ARM"
    assert "Only 3 catalogue families" in rep["limitations"][0]


def test_budget_mismatch_refused_and_ledger_overrides_rows(tmp_path):
    proofs = {"L2": arm({"s1"}), "L3": arm({"s1", "s2"})}
    rep = L.run_lean(**setup(tmp_path, STM6, proofs, ledger={"L2": 100, "L3": 120}))
    assert rep["comparisons"]["L3_vs_L2"]["status"] == "REFUSED_BUDGET_MISMATCH" and "x_minus_y_coverage" not in rep["comparisons"]["L3_vs_L2"]
    assert rep["arms"]["L3"]["compiler_calls"] == 120 and rep["arms"]["L3"]["compiler_calls_source"] == "ledger"
    assert rep["arms"]["L3"]["compiler_calls_sum_of_rows"] == 60


def test_unclean_axioms_do_not_count_and_unattempted_are_uncovered(tmp_path):
    p = arm({"s1", "s2"})
    p["s2"] = (True, False, 10)   # proved but sorry/axiom not clean
    del p["s6"]                   # never attempted
    rep = L.run_lean(**setup(tmp_path, STM6, {"L3": p}))
    a = rep["arms"]["L3"]
    assert a["coverage"]["k"] == 1 and a["coverage"]["n"] == 6
    assert a["n_proved_but_axioms_not_clean_rejected"] == 1 and a["n_attempted"] == 5


def _catalogue(n_fam=12, per=5):
    return [(f"m{f}-{k}", f"m{f}") for f in range(n_fam) for k in range(per)]


def _proofs(stm, rng, rate, calls=10, reuse=None):
    d = {}
    for i, f in stm:
        ok = rng.uniform() < rate
        d[i] = (ok, True, calls) + ((reuse,) if reuse is not None and ok else ())
    return d


def test_engine_can_report_support_and_can_report_a_null(tmp_path):
    """SIMULATED power fixture. Support requires L3 to beat BOTH L2 and L1."""
    rng = np.random.default_rng(11)
    stm = _catalogue()
    l3 = {i: (True, True, 10, 2) for i, _ in stm}
    t1 = tmp_path / "sup"; t1.mkdir()
    proofs = {"L3": l3, "L2": _proofs(stm, rng, 0.35), "L1": _proofs(stm, rng, 0.35)}
    rep = L.run_lean(**setup(t1, stm, proofs, ledger={"L3": 600, "L2": 600, "L1": 600}))
    assert rep["commons_benefit_supported"] is True and "consistent with" in rep["mechanism_note"]
    assert "Sharing benefit SUPPORTED" in rep["slide_markdown"]
    # beats L2 but NOT L1 (a sequential persistent agent is as good): sharing not established
    t2 = tmp_path / "half"; t2.mkdir()
    proofs = {"L3": _proofs(stm, rng, 0.9), "L2": _proofs(stm, rng, 0.2), "L1": _proofs(stm, rng, 0.9)}
    rep2 = L.run_lean(**setup(t2, stm, proofs, ledger={"L3": 600, "L2": 600, "L1": 600}))
    assert rep2["comparisons"]["L3_vs_L2"]["verdict"] == "arm L3 BETTER than arm L2"
    assert not rep2["comparisons"]["L3_vs_L1"]["verdict"].startswith("arm L3 BETTER")
    assert rep2["commons_benefit_supported"] is False and "NOT established" in rep2["slide_markdown"]
    # gain without reuse is flagged as unattributed
    t3 = tmp_path / "noreuse"; t3.mkdir()
    proofs = {"L3": {i: (True, True, 10, 0) for i, _ in stm}, "L2": _proofs(stm, rng, 0.3), "L1": _proofs(stm, rng, 0.3)}
    rep3 = L.run_lean(**setup(t3, stm, proofs, ledger={"L3": 600, "L2": 600, "L1": 600}))
    assert rep3["commons_benefit_supported"] is True and "NOT attributed to reuse" in rep3["mechanism_note"]


def test_frozen_catalogue_hash_and_excluded_claims(tmp_path):
    args = setup(tmp_path, STM6, {"L3": arm({"s1"})})
    sha = tmp_path / "stm.sha256"
    sha.write_text("0" * 64 + "\n")
    with pytest.raises(D.DeskError, match="altered after freezing"):
        L.run_lean(**args, sha_path=sha)
    rows = [json.loads(l) for l in args["statements_path"].read_text().splitlines()]
    rows[0]["source_claim_id"] = "turing-morphogen-hypothesis"
    args["statements_path"].write_text("\n".join(json.dumps(r) for r in rows))
    with pytest.raises(D.DeskError, match="excluded source claim"):
        L.run_lean(**args)


def test_basin_predictive_scoring_hand_values():
    assert BA.predictive_mean(3, 10) == pytest.approx(4 / 12)
    assert math.exp(BA.beta_binomial_logpmf(1, 1, 0, 0)) == pytest.approx(0.5)  # uniform prior, one run
    assert math.exp(BA.beta_binomial_logpmf(2, 4, 3, 10)) == pytest.approx(sps.betabinom.pmf(2, 4, 1 + 3, 1 + 7))  # independent implementation
    r = BA.score_nodes([{"id": "n1", "k": 3, "n": 10, "held_out_k": 2, "held_out_m": 4}])
    assert r["mean_brier_per_heldout_run"] == pytest.approx(10 / 36)
    assert r["mean_log_loss_per_heldout_run"] == pytest.approx(-math.log(sps.betabinom.pmf(2, 4, 4, 8)) / 4)


def test_basin_counts_reindexing_instead_of_averaging_it_away():
    r = BA.score_nodes([{"id": "z", "k": 0, "n": 80, "held_out_k": 3, "held_out_m": 10, "lean_clamped_zero": True},
                        {"id": "ok", "k": 0, "n": 80, "held_out_k": 0, "held_out_m": 10, "lean_clamped_zero": True},
                        {"id": "p", "k": 40, "n": 80, "held_out_k": 5, "held_out_m": 10}])
    assert r["n_reindexed_subcritical_finite_amplitude"] == 1 and r["reindexed_ids"] == ["z"] and r["n_scored_nodes"] == 1
