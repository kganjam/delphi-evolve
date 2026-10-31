"""Diagnostic figure from ACTUAL solver / NCA trajectories. Evidence kind: SIMULATED (declared Schnakenberg model; nothing observed).

A  control request (Dv/Du=1, L=20pi, target wavelength 11): independent solver with the formula design  -> no pattern.
B  the claim-licensed repair (Dv/Du raised to 9, the smallest integer the turing-ddi band check admits), independent solver.
C  max|u-u*| vs tau for the Euler training solver, the independent spectral solver, and the v1 NCA (seed 1), same noise
   for Euler/NCA, gamma=1, Dv/Du=20, L=10pi  -> NCA divergence is a measured trajectory, not an assertion.
D  independent-solver success by arm (treatment requests) with the post-hoc random-gamma baseline.
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import torch

from . import nca, rd

OUT = Path("artifacts/rethink_nca")


def spec_frames(gamma, d, r, T=400.0, n=80, seed=11):
    st = rd.initial_state(1, rd.n_cells(r), [seed])
    ts = np.linspace(0, T, n + 1)[1:]
    frames, cur, t0 = [], st, 0.0
    for t in ts:
        cur, _ = rd.spectral_strang(cur, np.array([gamma]), np.array([float(d)]), r, t - t0, dt=0.02)
        t0 = t
        frames.append(cur[0, 0].copy())
    return ts, np.array(frames)


def dev_curve_euler_spec_nca(gamma, d, r, T=60.0, every=2.0):
    N = rd.n_cells(r)
    st = rd.initial_state(1, N, [0])
    g, dd = np.array([gamma]), np.array([float(d)])
    _, ef = rd.euler_fd(st, g, dd, T, dt=nca.DT_NCA, record_every_tau=every)
    _, sv = rd.spectral_strang(st, g, dd, r, T, checkpoints=tuple(np.arange(every, T + 1e-9, every)))
    sp = np.array([np.abs(sv[k][0, 0] - rd.U0).max() for k in sorted(sv)])
    eu = np.abs(ef[0, :, 0] - rd.U0).max(-1)
    m = nca.NCA(); m.load_state_dict(torch.load(OUT / "models" / "nca_seed1.pt")); m.eval()
    nc = []
    x = nca.to_nca_state(st); c = nca.cond_of(g, dd)
    k_per = int(round(every / nca.DT_NCA))
    with torch.no_grad():
        for _ in range(int(T / every)):
            for _ in range(k_per):
                x = m(x, c)
            nc.append(float(x[0, 0].abs().max()))
    return np.arange(every, T + 1e-9, every), eu, sp, np.array(nc)


def main():
    torch.set_num_threads(2)
    fig, ax = plt.subplots(2, 2, figsize=(11, 8))
    # A, B
    from . import gate
    gA = gate.formula_gamma(1, 11)
    ts, fa = spec_frames(gA, 1, 20)
    im = ax[0][0].imshow(fa, aspect="auto", origin="lower", extent=[0, 20 * np.pi, 0, ts[-1]], cmap="viridis", vmin=0.5, vmax=2.0)
    ax[0][0].set_title(f"A: Dv/Du=1 (turing-ddi band absent), formula gamma={gA:.2f}\nindependent solver: no pattern", fontsize=8)
    rep = [m for m in json.loads((OUT / "repair.json").read_text())["repairs"] if m["knob"] == "diffusion_ratio" and m["found"] and m["found"]["r"] == 20 and abs(m["found"]["d"] - 9) < 1e-9 and m["req"] == 37][0]["found"]
    ts, fb = spec_frames(rep["gamma"], rep["d"], 20)
    ax[0][1].imshow(fb, aspect="auto", origin="lower", extent=[0, 20 * np.pi, 0, ts[-1]], cmap="viridis", vmin=0.5, vmax=2.0)
    ax[0][1].set_title(f"B: licensed repair Dv/Du=9, gamma={rep['gamma']:.3f}, mode {rep['mode']}\nindependent solver (seed 11): u(x,tau)", fontsize=8)
    for a in (ax[0][0], ax[0][1]):
        a.set_xlabel("x (length units, Du=1)"); a.set_ylabel("tau = gamma t")
    fig.colorbar(im, ax=ax[0].tolist(), shrink=0.8, label="u (dimensionless, simulated)")
    # C
    t, eu, sp, nc = dev_curve_euler_spec_nca(1.0, 20, 10)
    ax[1][0].semilogy(t, eu, label="Euler (training solver)")
    ax[1][0].semilogy(t, sp, "--", label="spectral (independent)")
    ax[1][0].semilogy(t, nc, label="NCA v1 seed 1")
    ax[1][0].set_xlabel("tau"); ax[1][0].set_ylabel("max |u-u*|"); ax[1][0].legend(fontsize=7)
    ax[1][0].set_title("C: gamma=1, Dv/Du=20, L=10pi, same noise (seed 0)", fontsize=8)
    # D
    s = json.loads((OUT / "summary.json").read_text())
    arms = ["C0", "D", "G", "Gmis", "N", "Nshuf"]
    ax[1][1].bar(arms, [s["arms"][a]["treatment"]["success_mean"] for a in arms])
    try:
        go = json.loads((OUT / "grid_oracle.json").read_text())
        ax[1][1].axhline(go["random_gamma_success_treatment"], color="k", ls=":", label="random-gamma baseline (post hoc)")
        ax[1][1].legend(fontsize=7)
    except Exception:
        pass
    ax[1][1].set_ylabel("independent-solver success (32 requests x 3 noise seeds)")
    ax[1][1].set_title("D: arms (C0 formula, D black-box, G claim-gated, Gmis continuum, N NCA, Nshuf control)", fontsize=8)
    fig.suptitle("SIMULATED Schnakenberg model; Euler/NCA/spectral are different solvers of the same declared equations; no biological measurement", fontsize=9)
    fig.tight_layout()
    fig.savefig(OUT / "diagnostic.png", dpi=130)
    (OUT / "diagnostic_meta.json").write_text(json.dumps({"evidence_kind": "simulated", "panels": "A,B independent spectral solver seed 11; C Euler/spectral/NCA seed 0; D summary.json (+ grid_oracle.json if present)"}, indent=1))


if __name__ == "__main__":
    main()
