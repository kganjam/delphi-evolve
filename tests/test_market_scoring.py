"""Hand-computed checks for scoring, aggregation, diversity decomposition, calibration, exact stats.
All arrays here are arithmetic fixtures chosen so the expected values can be worked by hand; none is data."""
import math

import numpy as np
import pytest

from market import aggregate as AG
from market import calibration as CAL
from market import diversity as DIV
from market import scoring as SC
from market import stats as ST


def test_brier_and_log_hand():
    assert SC.brier(0.7, 1) == pytest.approx(0.09)
    assert SC.brier(0.7, 0) == pytest.approx(0.49)
    assert SC.log_loss(0.8, 1) == pytest.approx(-math.log(0.8))
    assert SC.log_loss(0.8, 0) == pytest.approx(-math.log(0.2))
    assert SC.log_loss(0.5, 1) == pytest.approx(math.log(2))


def test_log_loss_clips_and_counts():
    assert SC.log_loss(0.0, 1) == pytest.approx(-math.log(SC.LOG_EPS))  # finite, not inf
    assert SC.n_clipped([0.0, 1.0, 0.5, 1e-7]) == 3


def test_reference_scores():
    r = SC.constant_reference([1, 0, 0, 0])
    assert r["brier_p0.5"] == pytest.approx(0.25) and r["base_rate"] == 0.25
    assert r["brier_base_rate_hindsight"] == pytest.approx(0.25 * 0.75)


def test_aggregators_hand():
    P = np.array([[0.8], [0.5]])
    assert AG.agg_mean(P)[0] == pytest.approx(0.65)
    assert AG.agg_median(P)[0] == pytest.approx(0.65)
    # log pool: sqrt(.8*.5)/(sqrt(.8*.5)+sqrt(.2*.5)) = 2/3
    assert AG.agg_log_pool(P)[0] == pytest.approx(2 / 3)
    # extremise with a=2 on mean logit ln4/2 -> sigmoid(ln 4) = 0.8
    assert AG.agg_extremised(P, 2.0)[0] == pytest.approx(0.8)
    assert AG.agg_median(np.array([[0.1], [0.2], [0.9]]))[0] == pytest.approx(0.2)


def test_recalibration_is_out_of_fold_and_finite():
    rng = np.random.default_rng(1)
    o = (np.arange(40) % 2).astype(float)
    P = np.vstack([np.where(o == 1, 0.7, 0.3), np.where(o == 1, 0.6, 0.4)])
    out, fits = AG.agg_recalibrated_cv(P, o, folds=5)
    assert out.shape == (40,) and np.all((out > 0) & (out < 1)) and len(fits) == 5
    # one training class only still returns finite values thanks to the ridge
    out2, _ = AG.agg_recalibrated_cv(P, np.ones(40), folds=5)
    assert np.all(np.isfinite(out2))


def test_diversity_hand_example():
    P = np.array([[0.9, 0.2], [0.5, 0.6]])
    o = np.array([1.0, 0.0])
    d = DIV.decompose(P, o)
    assert d["crowd_brier"] == pytest.approx(0.125)
    assert d["mean_individual_brier"] == pytest.approx(0.165)
    assert d["diversity"] == pytest.approx(0.04)
    assert d["crowd_brier"] == pytest.approx(d["mean_individual_brier"] - d["diversity"], abs=1e-15)
    assert d["log_loss_jensen_gap"] >= 0


def test_diversity_identity_random_and_selftest():
    rng = np.random.default_rng(7)
    for n, m in [(2, 3), (10, 50), (26, 300)]:
        P = rng.uniform(0, 1, (n, m))
        o = (rng.uniform(size=m) < 0.5).astype(float)
        assert DIV.decompose(P, o)["identity_max_abs_residual"] < 1e-12
    assert DIV.self_test()["hand_example"] == "pass"


def test_identity_is_only_for_the_mean_crowd():
    # With a MEDIAN crowd the same subtraction does not close: guards against using it for other aggregators.
    P = np.array([[0.9], [0.5], [0.2]])  # asymmetric: [.9,.5,.1] closes by coincidence
    o = np.array([1.0])
    med = np.median(P, axis=0)
    lhs = ((med - o) ** 2).mean()
    rhs = ((P - o) ** 2).mean() - ((P - med) ** 2).mean()
    assert abs(lhs - rhs) > 1e-3


def test_identical_forecasters_have_zero_diversity_and_crowd_equals_individual():
    p = np.array([0.9, 0.2, 0.6])
    o = np.array([1.0, 0.0, 1.0])
    d = DIV.decompose(np.vstack([p, p, p]), o)
    assert d["diversity"] == pytest.approx(0.0, abs=1e-30) and d["crowd_brier"] == pytest.approx(d["mean_individual_brier"])


def test_identity_error_raised_on_shape_and_tolerance():
    with pytest.raises(ValueError):
        DIV.decompose(np.zeros((2, 3)), np.zeros(4))
    with pytest.raises(DIV.IdentityError):
        DIV.decompose(np.array([[0.9, 0.2], [0.5, 0.6]]), np.array([1.0, 0.0]), tol=-1.0)


def test_calibration_table_hand():
    p = [0.05, 0.05, 0.95, 0.95, 1.0]
    o = [0, 0, 1, 0, 1]
    t = CAL.calibration_table(p, o, bins=10)
    b0, b9 = t["bins"][0], t["bins"][9]
    assert b0["n"] == 2 and b0["observed_frequency"] == 0.0 and b0["mean_forecast"] == pytest.approx(0.05)
    assert b9["n"] == 3 and b9["observed_frequency"] == pytest.approx(2 / 3)  # 1.0 lands in last bin
    assert t["ece"] == pytest.approx(2 / 5 * 0.05 + 3 / 5 * abs(2 / 3 - (0.95 + 0.95 + 1.0) / 3))
    assert all(r["observed_frequency"] is None for r in t["bins"][1:9])


def test_error_correlation_hand():
    o = np.array([1, 0, 1, 0, 1, 0.0])
    a = np.array([0.9, 0.2, 0.7, 0.1, 0.6, 0.4])
    ec = CAL.error_correlation({"a": a, "b": a.copy(), "c": o + 0.1}, o)
    assert ec["raw"]["a"]["b"] == pytest.approx(1.0)
    assert ec["raw"]["a"]["c"] is None  # constant ERROR series (p = o + 0.1) is undefined, never reported as 0
    # within-outcome correlation removes structure shared only through the outcome
    ec2 = CAL.error_correlation({"a": a, "b": 1 - a}, o)
    assert ec2["within_outcome"]["a"]["b"] == pytest.approx(-1.0)


def test_stats_exact_values():
    lo, hi = ST.clopper_pearson(3, 10)
    assert (lo, hi) == (pytest.approx(0.0667395, abs=1e-6), pytest.approx(0.6524529, abs=1e-6))
    assert ST.clopper_pearson(0, 10)[0] == 0.0 and ST.clopper_pearson(0, 10)[1] == pytest.approx(0.3084971, abs=1e-6)
    assert ST.clopper_pearson(10, 10)[1] == 1.0
    assert ST.mcnemar_exact([1] * 5, [0] * 5)["p_two_sided_exact"] == pytest.approx(0.0625)
    assert ST.mcnemar_exact([1, 0], [1, 0])["p_two_sided_exact"] == 1.0
    assert ST.auc([0.9, 0.8], [0.1, 0.8]) == pytest.approx((1 + 1 + 1 + 0.5) / 4)
    assert ST.auc([], [0.1]) is None


def test_cluster_bootstrap_degenerate_and_bounds():
    fam = np.repeat(["a", "b", "c", "d"], 3)
    r = ST.cluster_ratio_ci(np.ones(12), np.ones(12), fam, 500, 1)
    assert r["estimate"] == 1.0 and r["lo"] == 1.0 and r["hi"] == 1.0
    num = np.array([1, 0, 0, 1, 1, 1, 0, 0, 0, 0, 1, 0.0])
    r = ST.cluster_ratio_ci(num, np.ones(12), fam, 2000, 1)
    assert r["estimate"] == pytest.approx(5 / 12) and 0 <= r["lo"] <= r["estimate"] <= r["hi"] <= 1
    assert ST.cluster_ratio_ci([], [], [], 10, 1)["estimate"] is None


def test_log_pool_three_forecasters_is_mean_of_logits_not_median():
    P = np.array([[0.9], [0.5], [0.5]])
    expect = 1 / (1 + math.exp(-(math.log(9) + 0 + 0) / 3))
    assert AG.agg_log_pool(P)[0] == pytest.approx(expect)
    assert abs(AG.agg_log_pool(P)[0] - 0.5) > 0.05  # a median-of-logits pool would return exactly 0.5


def test_budget_gate_boundary_is_relative_to_the_smaller_arm():
    from market import arms
    ok = lambda hi: arms.check_budgets({"x": {"total_tokens": 1000}, "y": {"total_tokens": hi}}, ["x", "y"], 0.05)["ok"]
    assert ok(1049) and ok(1050)        # 4.9% and exactly 5.0% of the smaller arm
    assert not ok(1051)                 # 5.1% of the smaller arm (4.85% of the larger would wrongly pass)
    assert not arms.check_budgets({"x": {"total_tokens": 0}, "y": {"total_tokens": 5}}, ["x", "y"], 0.05)["ok"]
    with pytest.raises(arms.BudgetMismatch):
        arms.require_matched({"x": {"total_tokens": 1000}, "y": {"total_tokens": 1300}}, ["x", "y"], 0.05)
