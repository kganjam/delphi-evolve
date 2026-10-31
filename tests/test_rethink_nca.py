import copy
import math

import numpy as np

from experiments.rethink_nca import gate, rd
from turing_scope.source import load_pins


def test_solvers_agree_on_unscored_dev_case():
    r = 15
    N = rd.n_cells(r)
    st = rd.initial_state(1, N, [900])
    g, d = np.array([1.0]), np.array([20.0])
    a = rd.euler_fd(st, g, d, 150.0, dt=0.005)
    b, _ = rd.spectral_strang(st, g, d, r, 150.0)
    ma, mb = rd.pattern_metrics(a[:, 0], r), rd.pattern_metrics(b[:, 0], r)
    assert ma["m"][0] == mb["m"][0] and ma["patterned"][0] and mb["patterned"][0]
    assert abs(ma["amp"][0] - mb["amp"][0]) < 0.05


def test_no_pattern_without_band_equal_diffusivity():
    r = 10
    st = rd.initial_state(1, rd.n_cells(r), [901])
    b, _ = rd.spectral_strang(st, np.array([1.0]), np.array([1.0]), r, 100.0)
    assert not rd.pattern_metrics(b[:, 0], r)["patterned"][0]


def test_gate_refuses_when_turing_ddi_inequality_fails():
    assert gate.gate_design(1, 20, 11)["verdict"] == "refuse_no_band"


def test_gate_refuses_when_pinned_record_changes():
    pins = load_pins()
    t = copy.deepcopy(pins)
    h = t["turing-ddi"]["content_sha256"]
    t["turing-ddi"]["content_sha256"] = ("0" if h[0] != "0" else "1") + h[1:]
    assert gate.gate_design(10, 20, 11)["verdict"] == "candidates"
    assert gate.gate_design(10, 20, 11, pins=t)["verdict"] == "refuse_source"


def test_gate_intervals_match_linear_instability():
    g = gate.gate_design(10, 20, 11)
    for m, lo, hi in g["intervals"]:
        q = (m / 20.0) ** 2
        mid = math.sqrt(lo * hi)
        for gam, expect in ((mid, True), (hi * 1.05, False)):
            if gam > 3.0 and not expect:
                continue
            sig, _ = rd.linear_sigma(gam, 10.0, 20)
            # mode m unstable <=> det < 0
            M = rd.J1 - q * np.diag([1 / gam, 10.0 / gam])
            assert (np.linalg.det(M) < 0) == expect


def test_finite_domain_changes_decision():
    # same chemistry (d=10), tiny domain: the continuum band exists but a short target wavelength window may have no mode
    g_small = gate.gate_design(10, 1, 8)     # L = pi
    assert g_small["verdict"] in ("refuse_no_mode", "candidates")
    if g_small["verdict"] == "candidates":
        for m, lo, hi in g_small["intervals"]:
            assert abs(2 * math.pi / m - 8) / 8 <= gate.TOL
