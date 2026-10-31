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


def test_finite_domain_band_matches_known_interval():
    # J with q-band (1/5, 1/2): mode n unstable iff L in (n*pi*sqrt2, n*pi*sqrt5) <=> rho=L/pi in (n*1.4142, n*2.2361)
    from turing_ratio.mispredict_map import has_mode, exact_has_mode
    qlo, qhi = np.array([0.2]), np.array([0.5])
    assert not has_mode(qlo, qhi, 1.0)[0]                       # rho=1: no n with sqrt(.2)<n<sqrt(.5)
    assert has_mode(qlo, qhi, 2.0)[0]                           # 0.894<n/rho.. n=1 -> q=.25 in band
    assert not has_mode(qlo, qhi, 1.4)[0] and has_mode(qlo, qhi, 1.5)[0]
    # exact rational decision on the codex-style Jacobian: ratio 1.1, L=5*pi -> n=1 admissible (det -21/25000 < 0)
    J = (1, -1, Fraction(1011, 1000), Fraction(-101, 100))
    assert exact_has_mode(J, Fraction(11, 10), 5) and not exact_has_mode(J, Fraction(11, 10), 1)
