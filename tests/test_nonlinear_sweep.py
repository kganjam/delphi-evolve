import numpy as np

from scopedesk.oracles.nonlinear_sweep import ensemble as E
from scopedesk.oracles.nonlinear_sweep import solvers as S


def test_ensemble_deterministic_and_sized():
    a, b = E.build(10), E.build(10)
    assert a == b and len(a) == 2 * 10 * len(E.RHOS) * len(E.XS) * len(E.EPS) * len(E.PAIRED_SEEDS)
    assert E.permutation(len(a)) == E.permutation(len(a))


def test_ic_is_grid_independent_function():
    u1, _ = S.ic_modal(7, 12, 30.0, 64, 0.1, 0.1)
    u2, _ = S.ic_modal(7, 12, 30.0, 96, 0.1, 0.1)
    # same continuous function sampled on two grids: compare at shared cell-centre-free check via analytic std
    for u in (u1, u2):
        assert abs(u.std() - 0.1) < 0.03          # analytic std = amp (sampling error only)
    x1 = (np.arange(64) + .5) * 30 / 64
    x2 = (np.arange(96) + .5) * 30 / 96
    assert np.allclose(np.interp(x1, x2, u2), u1, atol=0.02)


def test_two_solvers_agree_on_clear_cases():
    from fractions import Fraction as F
    from scopedesk.oracles import kinetics
    pp = kinetics.params("schnakenberg")
    L, N = 40.0, 80
    A = S.run_cell_a("schnakenberg", pp, F(20), L, N, 300.0, 0.1, 0.09, 3, 16)
    B = S.run_cell_b("schnakenberg", pp, F(20), L, int(1.5 * N), 300.0, 0.1, 0.09, 3, 16)
    assert A["pattern"] and B["pattern"] and A["mode"] == B["mode"]
    assert abs(A["amp"] - B["amp"]) < 0.15 * max(A["amp"], B["amp"])
