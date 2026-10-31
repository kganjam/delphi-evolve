"""Extract subthreshold and spike-threshold features from Allen Institute Cell Types NWB files.

Everything here is MEASURED-DATA processing (observed): no model is fitted in this module except the single
exponential used for the membrane time constant. Conventions are documented so a reader can re-derive them; they are
NOT claimed to equal the Allen Institute's own feature pipeline (that agreement is checked, not assumed, in
``run_strength_duration.py`` against the Allen API ``ef__*`` fields).

Stimulus layout verified by inspection of cell 565871768 (NWB 659446233): every sweep starts with a 10 ms,
50 pA test pulse at 5 ms (older 200 kHz cells: 40 ms in index units of 50 kHz => same 10 ms); Long Square is a 1 s step starting at 1.02 s; Short Square is a 3 ms pulse at 1.02 s;
50 kHz (newer cells) or 200 kHz (older cells) sampling, read per sweep; voltage in V, stimulus in A.
"""
from __future__ import annotations

import math

import h5py
import numpy as np
from scipy.optimize import curve_fit

DVDT_THRESH = 20.0          # V/s (20 mV/ms), the usual spike-onset criterion
SPIKE_PEAK_MIN_V = -0.020   # a candidate needs a peak above -20 mV ...
SPIKE_MIN_AMPL_V = 0.020    # ... and at least 20 mV above its onset


def _str(x):
    return x.decode() if isinstance(x, bytes) else str(x)


def stim_segments(st: np.ndarray):
    """Contiguous non-zero segments of a stimulus trace: (start_idx, end_idx_exclusive, mean_amp_pA)."""
    nz = (st != 0).astype(np.int8)
    d = np.diff(np.r_[0, nz, 0])
    s, e = np.nonzero(d == 1)[0], np.nonzero(d == -1)[0]
    return [(int(a), int(b), float(st[a:b].mean()) * 1e12) for a, b in zip(s, e)]


def detect_spikes(v: np.ndarray, i0: int, i1: int, FS: float):
    """Spikes with onset in [i0, i1). Returns list of (onset_idx, threshold_V, peak_V)."""
    seg = v[i0:i1]
    dv = np.diff(seg) * FS
    above = dv >= DVDT_THRESH
    onsets = np.nonzero(above & ~np.r_[False, above[:-1]])[0]
    out, last = [], -10**9
    for o in onsets:
        if o - last < int(0.002 * FS):
            continue
        w = seg[o:o + int(0.003 * FS)]
        if w.size == 0:
            continue
        pk = float(w.max())
        if pk >= SPIKE_PEAK_MIN_V and pk - float(seg[o]) >= SPIKE_MIN_AMPL_V:
            out.append((i0 + int(o), float(seg[o]), pk))
            last = o
    return out


def _exp_rise(t, A, tau):
    return A * (1.0 - np.exp(-t / tau))


def pipeline_version(f) -> tuple:
    """Replicates AllenSDK NwbDataSet.get_pipeline_version(): 'version' entry of general/generated_by (alternating
    key/value array); missing or unparsable -> (0, 0). This is the Allen pipeline version, NOT the NWB schema version."""
    major = minor = 0
    try:
        if "generated_by" in f["general"]:
            info = f["general/generated_by"]
            version = None
            for i in range(len(info)):
                if _str(info[i]) == "version":
                    version = _str(info[i + 1]); break
            toks = version.split(".")
            if len(toks) >= 2:
                major, minor = int(toks[0]), int(toks[1])
    except Exception:  # noqa: BLE001 - same fallback as the SDK
        major = minor = 0
    return major, minor


def extract(nwb_path: str) -> dict:
    f = h5py.File(nwb_path, "r")
    major, minor = pipeline_version(f)
    # SDK rule (nwb_data_set.py get_sweep, read 2026-10-31): (major == 1 and minor > 0) or major > 1 -> apply conversion attrs
    apply_conv = (major == 1 and minor > 0) or major > 1
    acq = f["acquisition/timeseries"]
    sweeps = {"Long Square": [], "Short Square": []}
    units_seen, unit_bad = set(), []
    for name in acq:
        s = acq[name]
        nm = _str(s["aibs_stimulus_name"][()])
        if nm not in sweeps:
            continue
        v_ds, st_ds = s["data"], f["stimulus/presentation/" + name]["data"]
        vraw, straw = v_ds[:].astype(np.float64), st_ds[:].astype(np.float64)
        uv, us = _str(v_ds.attrs.get("unit", "?")), _str(st_ds.attrs.get("unit", "?"))
        cv, cs = float(v_ds.attrs.get("conversion", float("nan"))), float(st_ds.attrs.get("conversion", float("nan")))
        units_seen.add(("v", uv, cv)); units_seen.add(("stim", us, cs))
        if apply_conv:      # AllenSDK nwb_data_set.get_sweep(): files >=1.1 -> multiply by conversion attr
            if not (math.isfinite(cv) and math.isfinite(cs)):
                unit_bad.append(name); continue
            v, st = vraw * cv, straw * cs
        else:               # earlier files: attrs are wrong, stored values are already SI
            v, st = vraw, straw
        fs = float(s["starting_time"].attrs["rate"])               # 50 kHz for newer cells, 200 kHz for older ones
        segs = stim_segments(st)
        main = [g for g in segs if g[0] > int(0.5 * fs)]          # drop the test pulse at the start of each sweep
        if len(main) != 1:
            continue
        a, b, amp = main[0]
        sweeps[nm].append({"sweep": name, "v": v, "i0": a, "i1": b, "amp_pA": amp, "fs": fs})

    out = {"pipeline_version": [major, minor], "conversion_applied": apply_conv,
           "unit_conversion_seen": sorted(units_seen), "unit_ok": False,  # set below after plausibility check
           "sweep_qc_flags": "NOT USED: per-sweep QC fields (ephys_sweeps.json) were not applied; omission is a limitation",
           "nwb": nwb_path, "sampling_hz": sorted({r["fs"] for k in sweeps for r in sweeps[k]}), "n_long": len(sweeps["Long Square"]), "n_short": len(sweeps["Short Square"])}

    # ---- long square: rheobase, spike threshold voltage, resting potential, input resistance, tau
    ls = sorted(sweeps["Long Square"], key=lambda r: r["amp_pA"])
    base, nonspiking_dv, nonspiking_I, rheo, vth = [], [], [], None, None
    hyper = []
    for r in ls:
        v, a, b, FS = r["v"], r["i0"], r["i1"], r["fs"]
        pre = v[a - int(0.20 * FS):a - int(0.01 * FS)]
        base.append(float(pre.mean()))
        sp = detect_spikes(v, a, b, FS)                          # spikes with onset DURING the step only
        reb = detect_spikes(v, b, b + int(0.05 * FS), FS)        # stimulus-off window, reported separately
        r["n_spikes"] = len(sp)
        r["n_rebound"] = len(reb)
        if sp and r["amp_pA"] > 0:                               # rheobase = lowest POSITIVE step with an on-step spike
            if rheo is None:
                rheo, vth = r["amp_pA"], sp[0][1]
                r["first_spike"] = sp[0]
        elif not sp:
            late = v[b - int(0.10 * FS):b - int(0.005 * FS)].mean()
            nonspiking_dv.append(float(late - pre.mean()))
            nonspiking_I.append(r["amp_pA"])
            if r["amp_pA"] < 0:
                hyper.append((r, pre.mean()))
    out["long_square_rebound_sweeps"] = [(round(r["amp_pA"], 1), r["n_rebound"]) for r in ls if r["n_rebound"]]
    out["long_square_negative_onstep_spikes"] = [(round(r["amp_pA"], 1), r["n_spikes"]) for r in ls if r["amp_pA"] <= 0 and r["n_spikes"]]
    out["vrest_mV"] = 1e3 * float(np.median(base)) if base else None
    out["rheobase_ls_pA"] = rheo
    out["vth_ls_mV"] = None if vth is None else 1e3 * vth
    out["long_square_amps_pA"] = [round(r["amp_pA"], 1) for r in ls]
    # input resistance: free-intercept regression of steady-state dV on I over non-spiking sweeps
    if len(nonspiking_I) >= 3:
        I = np.array(nonspiking_I) * 1e-12
        dv = np.array(nonspiking_dv)
        slope, icpt = np.polyfit(I, dv, 1)
        out["ri_MOhm"] = float(slope) / 1e6
        out["ri_n_sweeps"] = len(I)
        # also the hyperpolarising-only slope through the origin (closer to a pure passive estimate)
        hm = I < 0
        out["ri_hyper_MOhm"] = float((I[hm] @ dv[hm]) / (I[hm] @ I[hm])) / 1e6 if hm.sum() >= 2 else None
    # tau: average normalised hyperpolarising onset, single exponential over 0..100 ms
    if hyper:
        FS = hyper[0][0]["fs"]
        t = np.arange(int(0.100 * FS)) / FS
        traces = []
        for r, pre in hyper:
            assert r["fs"] == FS
            a = r["i0"]
            seg = r["v"][a:a + t.size] - pre
            traces.append(seg / (r["amp_pA"] * 1e-12))      # V/A, signed so the response is positive
        m = np.mean(traces, axis=0)
        try:
            (A, tau), _ = curve_fit(_exp_rise, t, m, p0=(m[-1], 0.02), bounds=([-1e12, 1e-4], [1e12, 1.0]))
            resid = m - _exp_rise(t, A, tau)
            ss_res, ss_tot = float((resid ** 2).sum()), float(((m - m.mean()) ** 2).sum())
            out["tau_ms"] = tau * 1e3
            out["tau_fit_r2"] = 1 - ss_res / ss_tot
            out["tau_n_sweeps"] = len(hyper)
        except Exception as e:  # noqa: BLE001 - record failure, never invent a value
            out["tau_ms"], out["tau_fit_error"] = None, repr(e)

    # ---- short square: threshold bracket (highest non-spiking amp, lowest spiking amp)
    ss = sorted(sweeps["Short Square"], key=lambda r: r["amp_pA"])
    durs = {round((r["i1"] - r["i0"]) / r["fs"] * 1e3, 2) for r in ss}
    out["short_pulse_ms"] = sorted(durs)
    by_amp = {}
    for r in ss:
        sp = detect_spikes(r["v"], r["i0"], r["i1"] + int(0.02 * r["fs"]), r["fs"])   # 20 ms after pulse end at most
        by_amp.setdefault(round(r["amp_pA"], 1), []).append(len(sp) > 0)
    amps = sorted(by_amp)
    rows = [(a, sum(by_amp[a]), len(by_amp[a])) for a in amps]               # (amp, sweeps with spike, sweeps)
    any_spike = [a for a in amps if any(by_amp[a])]
    all_spike = [a for a in amps if all(by_amp[a])]
    hi_any = min(any_spike) if any_spike else None
    lo = [a for a in amps if hi_any is not None and a < hi_any and not any(by_amp[a])]
    out["short_square_by_amp"] = rows
    out["short_thr_hi_pA"] = hi_any                                          # lowest amplitude with >=1 spiking repeat
    out["short_thr_lo_pA"] = max(lo) if lo else None                         # highest amplitude below it with no spike
    out["short_thr_all_repeat_pA"] = min(all_spike) if all_spike else None   # lowest amplitude where ALL repeats spiked
    out["short_mixed_amps"] = [a for a in amps if 0 < sum(by_amp[a]) < len(by_amp[a])]
    out["short_nonmonotone"] = bool(hi_any is not None and any(not any(by_amp[a]) for a in amps if a > hi_any))
    out["short_left_censored"] = bool(hi_any is not None and not lo)         # lowest tested amp already spiked
    out["short_right_censored"] = hi_any is None                              # nothing spiked up to the max amp
    # plausibility is a FLAG only (never selects units): rest in [-120,-30] mV, stimulus below 5 nA, units recognised
    amps_all = [r["amp_pA"] for k in sweeps for r in sweeps[k]]
    out["unit_bad_sweeps"] = unit_bad
    out["unit_ok"] = bool(not unit_bad and amps_all and max(abs(a) for a in amps_all) < 5000
                          and out.get("vrest_mV") is not None and -120 < out["vrest_mV"] < -30)
    f.close()
    return out
