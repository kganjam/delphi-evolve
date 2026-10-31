import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from gpu_batch import prior_replay as PR  # noqa: E402


def test_calibration_uses_only_the_given_free_nodes_and_recovers_an_affine_map():
    rng = np.random.default_rng(0)
    z = rng.normal(size=1000)
    nodes = np.arange(100)
    y = 0.3 + 0.2 * z[nodes]
    a, b = PR.calibrate(z, nodes, y)
    assert abs(a - 0.3) < 1e-9 and abs(b - 0.2) < 1e-9
    # changing z OUTSIDE the calibration nodes cannot change (a, b): no unseen-label or unseen-row leakage into the fit
    z2 = z.copy()
    z2[500:] = 99
    assert PR.calibrate(z2, nodes, y) == (a, b)
    assert PR.calibrate(np.ones(1000), nodes, y)[1] == 0.0              # degenerate prior => zero slope, no crash


def test_episode_prior_never_reads_scores_beyond_start_target_init():
    z = np.random.default_rng(1).normal(size=160000)
    scores = np.random.default_rng(2).integers(0, 10**6, 160000)
    ep = {"start": 5, "target": 9, "init": list(range(100, 196))}
    p1, a1, b1, n1 = PR.episode_prior(z, scores, ep, 1e6)
    scores2 = scores.copy()
    scores2[200:] = 0                                                        # every non-free label destroyed
    p2, a2, b2, n2 = PR.episode_prior(z, scores2, ep, 1e6)
    assert n1 == 98 and (a1, b1) == (a2, b2) and np.array_equal(p1, p2)


def test_shuffled_control_is_a_fixed_permutation_with_same_values():
    z = np.arange(1000, dtype=float)
    s1, s2 = PR.shuffled(z), PR.shuffled(z)
    assert np.array_equal(s1, s2) and not np.array_equal(s1, z) and np.array_equal(np.sort(s1), z)


def test_parse_seeds():
    assert PR.parse_seeds("0-2,5") == [0, 1, 2, 5]
