"""Code-correctness tests for experiments/rethink_electric. Synthetic traces here test the DETECTORS only; they are
not data and no scientific result depends on them."""
import math

import numpy as np

from experiments.rethink_electric.glif_baseline import glif_short_threshold_pA
from experiments.rethink_electric.nwb_features import detect_spikes, stim_segments
from experiments.rethink_electric.run_strength_duration import lapicque, usable, wilson


def test_stim_segments_finds_pulses():
    st = np.zeros(1000); st[100:110] = 50e-12; st[500:503] = 300e-12
    segs = stim_segments(st)
    assert [(a, b) for a, b, _ in segs] == [(100, 110), (500, 503)]
    assert abs(segs[1][2] - 300) < 1e-6


def test_detect_spikes_respects_window_and_rate():
    for fs in (50_000.0, 200_000.0):
        n = int(fs * 0.2); v = np.full(n, -0.07)
        k = int(fs * 0.05); w = int(0.0015 * fs)      # 1.5 ms spike up to +30 mV
        v[k:k + w] = np.linspace(-0.05, 0.03, w)
        v[k + w:k + 2 * w] = np.linspace(0.03, -0.07, w)
        assert len(detect_spikes(v, 0, n, fs)) == 1
        assert detect_spikes(v, k + 3 * w, n, fs) == []            # window after the spike: none (rebound-window logic)
        assert detect_spikes(v, 0, k - 1, fs) == []                # window before the spike: none


def test_lapicque_limits():
    assert lapicque(100, 1000.0) > 1e4 * 0.9                        # very long tau: huge pulse threshold
    assert abs(lapicque(100, 0.01) - 100) < 1e-6                    # very short tau: rheobase


def test_glif_closed_form_matches_euler():
    m = {"R_input_ohm": 1e8, "C_F": 1e-10, "th_inf_V": 0.03, "coeffs": {"C": 1.0, "G": 1.0, "th_inf": 1.0}}
    I = glif_short_threshold_pA(m, 3e-3) * 1e-12
    G, C, dt = 1e-8, 1e-10, 5e-6
    def peak(I_):
        v = 0.0; pk = 0.0
        for _ in range(int(3e-3 / dt)):
            v += (I_ - G * v) * dt / C; pk = max(pk, v)
        return pk
    assert abs(peak(I) - 0.03) / 0.03 < 5e-3


def test_wilson_contains_point_and_is_ordered():
    lo, hi = wilson(45, 50); assert 0 < lo < 0.9 < hi < 1


def test_usable_flags_censoring_and_units():
    base = dict(unit_ok=True, short_pulse_ms=[3.0], short_right_censored=False, short_left_censored=False, short_thr_lo_pA=100.0,
                short_thr_hi_pA=110.0, rheobase_ls_pA=50.0, tau_ms=10.0, ri_MOhm=100.0, vth_ls_mV=-35.0, vrest_mV=-75.0, tau_fit_r2=0.99)
    assert usable(base) == []
    assert "short_left_censored" in usable({**base, "short_left_censored": True})
    assert "unit_conversion" in usable({**base, "unit_ok": False})


def test_pipeline_version_matches_sdk_rule(tmp_path):
    import h5py
    from experiments.rethink_electric.nwb_features import pipeline_version
    cases = {b"1.0": (1, 0), b"1.1": (1, 1), b"2.3": (2, 3), b"x": (0, 0)}
    for ver, want in cases.items():
        p = tmp_path / "f.h5"
        with h5py.File(p, "w") as f:
            f.create_group("general").create_dataset("generated_by", data=[b"pipeline", b"IVSCC", b"version", ver])
        with h5py.File(p, "r") as f:
            assert pipeline_version(f) == want
    with h5py.File(p, "w") as f:
        f.create_group("general")
    with h5py.File(p, "r") as f:
        assert pipeline_version(f) == (0, 0)
