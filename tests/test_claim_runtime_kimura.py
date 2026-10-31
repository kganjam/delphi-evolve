"""Kimura adapter numerics: boundaries, neutral limit, stability, sensitivity, and an
INDEPENDENT exact finite-chain reference. All populations are hypothetical (SIMULATED)."""
import math
from decimal import Decimal, getcontext
from fractions import Fraction

import pytest

from claim_runtime import exact_chains as X
from claim_runtime.kimura import fixation_probability as u, sensitivity

getcontext().prec = 60


def u_decimal(p, Ne, s):
    """Independent high-precision evaluation of the textbook formula."""
    x = Decimal(4) * Decimal(Ne) * Decimal(s)
    p = Decimal(p)
    return (1 - (-x * p).exp()) / (1 - (-x).exp())


def test_boundaries_and_neutral():
    for Ne in (1, 10, 1e4):
        for s in (-0.3, -1e-3, 0.0, 1e-3, 0.3):
            assert u(0.0, Ne, s) == 0.0
            assert u(1.0, Ne, s) == 1.0
    for p in (1e-6, 0.01, 0.5, 0.99):
        assert u(p, 100, 0.0) == p
        assert abs(u(p, 100, 1e-12) - p) < 1e-9          # continuity through the series branch
        assert abs(u(p, 100, -1e-12) - p) < 1e-9


def test_matches_high_precision_reference():
    for p in (1e-5, 1e-3, 0.2, 0.7):
        for Ne in (5, 100, 5000):
            for s in (-0.02, -1e-4, 1e-7, 1e-4, 0.01, 0.2):
                ref = float(u_decimal(p, Ne, s))
                assert u(p, Ne, s) == pytest.approx(ref, rel=1e-9, abs=1e-300)


def test_series_branch_boundary_is_smooth():
    # |x| = 1e-8 is the switch between the series and the expm1 branch
    a, b = u(0.3, 1.0, 0.99e-8 / 4), u(0.3, 1.0, 1.01e-8 / 4)
    assert abs(a - b) < 1e-9


def test_no_overflow_and_monotone():
    assert u(0.5, 1e9, -1.0) == 0.0                       # deep negative: underflows, no OverflowError
    assert 0.0 < u(1e-3, 1e4, 0.5) <= 1.0
    ps = [i / 50 for i in range(51)]
    vals = [u(p, 200, 0.01) for p in ps]
    assert all(b >= a for a, b in zip(vals, vals[1:]))
    ss = [-0.05, -0.01, 0.0, 0.01, 0.05]
    v2 = [u(0.01, 200, s) for s in ss]
    assert all(b > a for a, b in zip(v2, v2[1:]))
    assert u(0.01, 400, 0.01) > u(0.01, 200, 0.01)


@pytest.mark.parametrize("bad", ["500*2", None, True, float("nan"), float("inf"), [1]])
def test_rejects_non_numeric(bad):
    with pytest.raises(ValueError):
        u(0.1, bad, 0.01)
    with pytest.raises(ValueError):
        u(0.1, 100, bad)


def test_domain_errors():
    with pytest.raises(ValueError):
        u(-0.1, 100, 0.01)
    with pytest.raises(ValueError):
        u(1.1, 100, 0.01)
    with pytest.raises(ValueError):
        u(0.1, 0, 0.01)


def test_sensitivity_matches_analytic():
    p, Ne, s = 0.01, 200, 0.01
    x = 4 * Ne * s
    A, B = math.expm1(-x * p), math.expm1(-x)
    dA, dB = -p * math.exp(-x * p), -math.exp(-x)
    analytic = x * (dA / A - dB / B)                      # d ln u / d ln x, x = 4 Ne s
    got = sensitivity(p, Ne, s)
    assert got["elasticity_s"] == pytest.approx(analytic, rel=1e-5)
    assert got["elasticity_Ne"] == pytest.approx(analytic, rel=1e-5)
    assert sensitivity(p, Ne, 0.0)["elasticity_s"] is None


# ---------------- independent exact reference chains ---------------------------------

def test_diploid_p_prime_matches_genotype_derivation():
    for p in (0.1, 0.5, 0.9):
        for s in (-0.1, 0.0, 0.05):
            q = 1 - p
            w = (1 + 2 * s, 1 + s, 1.0)                    # AA, Aa, aa
            wbar = p * p * w[0] + 2 * p * q * w[1] + q * q * w[2]
            pprime = (p * p * w[0] + p * q * w[1]) / wbar
            assert X.diploid_p_after_selection(p, s) == pytest.approx(pprime, rel=1e-12)


def test_neutral_chain_is_exactly_a_martingale():
    P, ab = X.diploid_wf_genic(15, 0.0)
    assert max(abs(ab[i] - i / 30) for i in range(31)) < 1e-11
    assert u(1 / 30, 15, 0.0) == pytest.approx(ab[1], abs=1e-11)


def test_float_solver_matches_exact_rational_solver():
    fr = X.diploid_exact_fraction(3, Fraction(1, 10))
    P, ab = X.diploid_wf_genic(3, 0.1)
    assert max(abs(float(a) - b) for a, b in zip(fr, ab)) < 1e-12


def test_linear_solve_matches_forward_iteration():
    P, ab = X.diploid_wf_genic(20, 0.02)
    it, _ = X.absorption_by_iteration(P, 1)
    assert it == pytest.approx(ab[1], abs=1e-10)


def test_moran_chain_matches_gamblers_ruin_closed_form():
    am = X.absorption_probabilities(X.moran_matrix(30, 1.05))
    assert max(abs(am[i] - X.moran_closed_form(30, 1.05, i)) for i in range(31)) < 1e-11


@pytest.mark.parametrize("N", [10, 25, 90])
def test_formula_vs_exact_diploid_chain_weak_selection(N):
    assert 2 * N + 1 < 200
    for s in (0.001, 0.01, -0.01):
        P, ab = X.diploid_wf_genic(N, s)
        assert u(1 / (2 * N), N, s) == pytest.approx(ab[1], rel=0.03)    # documented diffusion error band
        assert u(0.5, N, s) == pytest.approx(ab[N], rel=0.03)


def test_diffusion_error_grows_for_strong_selection_and_is_reported():
    P, ab = X.diploid_wf_genic(90, -0.05)
    rel = abs(u(1 / 180, 90, -0.05) - ab[1]) / ab[1]
    assert rel > 0.3         # honest limit: the diffusion approximation is poor here


def test_haploid_is_not_the_diploid_formula_with_Ne_equals_N():
    N, s = 50, 0.02
    P, ab = X.haploid_wf(N, s)
    naive = u(1 / N, N, s)
    assert abs(naive - ab[1]) / ab[1] > 0.5                              # conflation is badly wrong
    mapped = u(1 / N, N / 2, s)                                           # variance-effective mapping, NOT implemented in the adapter
    assert abs(mapped - ab[1]) / ab[1] < 0.02


def test_state_budget():
    P, _ = X.diploid_wf_genic(90, 0.01)
    assert len(P) == 181 < 200
