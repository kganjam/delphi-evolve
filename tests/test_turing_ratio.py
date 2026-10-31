import numpy as np
from fractions import Fraction
from turing_ratio.core import codex_counterexample, d_crit, stable, turing_unstable, band


def test_codex_counterexample_exact():
    r = codex_counterexample()
    assert r["det_at_mode1"] == Fraction(-21, 25000) and r["stable_without_diffusion"] and r["matches"]


def test_schnakenberg_threshold_hand_value():
    assert abs(float(d_crit(0.8, 1.0, -1.8, -1.0)) - 8.567627) < 1e-5
    assert not turing_unstable(0.8, 1.0, -1.8, -1.0, 8.5) and turing_unstable(0.8, 1.0, -1.8, -1.0, 8.6)


def test_brusselator_closed_form():
    for A, B in [(3, 5), (10, 50), (100, 9000)]:
        assert abs(float(d_crit(B - 1, A * A, -B, -A * A)) - A * A / (np.sqrt(B) - 1) ** 2) < 1e-9


def test_marginal_and_equal_diffusion_excluded():
    assert np.isnan(d_crit(1, 1, -2, -1))                      # trace 0: not stable
    assert np.isnan(d_crit(1, 1, 1, -3))                       # b*c>0: no activator-inhibitor cross-structure
    q1, q2 = band(0.8, 1.0, -1.8, -1.0, 10.0); assert q1 < q2
