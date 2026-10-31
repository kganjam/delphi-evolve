"""Torch (CPU or CUDA) replay of solver A of the frozen sweep: Strang splitting, exact cosine diffusion, RK4 reaction, float64.
Same algorithm, same grid, same initial function and same metrics as `solvers.run_cell_a`; the DCT is applied as an orthonormal matrix
product so a whole group of cells (same model, same N) integrates as one batch. This is a REPLICATION and NUMERICAL-SENSITIVITY tool,
not a new preregistered finding.

  python3 -m scopedesk.oracles.nonlinear_sweep.gpu_replay run  OUT.jsonl [--device cpu|cuda] [--ids-mod M R] [--arm base|dt_half|grid_double]
  python3 -m scopedesk.oracles.nonlinear_sweep.gpu_replay compare OUT.jsonl REFERENCE_rows.jsonl
Cells come from `ensemble.build(10)` (frozen). --ids-mod 10 0 selects the preselected numerical-sensitivity subset (id % 10 == 0).
Arms: base (dt=0.02, N), dt_half (dt=0.01, N), grid_double (dt=0.02, 2N, same continuous initial function)."""
from __future__ import annotations

import json
import math
import sys
import time
from fractions import Fraction as F
from pathlib import Path

import numpy as np
import torch
from scipy.fft import dct

from .. import kinetics
from . import ensemble as E
from . import run as R
from . import solvers as S

DT = 0.02


def _react(model, pa, pb, u, v):
    w = u * u * v
    if model == "schnakenberg":
        return pa - u + w, pb - w
    return pa - (pb + 1) * u + w, pb * u - w


def integrate(cells, arm, device, log=None):
    """Return {cell id: metrics dict} for all cells (grouped by model and N internally)."""
    groups = {}
    for c in cells:
        L, NA, NB, K = R.grid_for(c)
        N = NA * (2 if arm == "grid_double" else 1)
        groups.setdefault((c["model"], N), []).append((c, L, K))
    out = {}
    dt = DT / 2 if arm == "dt_half" else DT
    for (model, N), items in groups.items():
        t0 = time.time()
        Sn = len(items)
        Dmat = torch.tensor(dct(np.eye(N), type=2, norm="ortho", axis=0), dtype=torch.float64, device=device)
        q = torch.tensor(np.stack([(np.arange(N) * math.pi / L) ** 2 for _, L, _ in items]), dtype=torch.float64, device=device)
        Dv = torch.tensor([float(F(c["Dv"])) for c, _, _ in items], dtype=torch.float64, device=device)[:, None]
        mu, mv = torch.exp(-q * dt / 2), torch.exp(-Dv * q * dt / 2)
        keys = ("a", "b") if model == "schnakenberg" else ("A", "B")
        pa = torch.tensor([float(F(c["params"][keys[0]])) for c, _, _ in items], dtype=torch.float64, device=device)[:, None]
        pb = torch.tensor([float(F(c["params"][keys[1]])) for c, _, _ in items], dtype=torch.float64, device=device)[:, None]
        u0, v0, ust = [], [], []
        for c, L, K in items:
            pp = kinetics.params(c["model"], c["params"])
            us, vs = (float(z) for z in kinetics.steady(c["model"], pp))
            pu, pv = S.ic_modal(c["seed"], K, L, N, c["eps"] * abs(us), c["eps"] * abs(vs))
            u0.append(us + pu); v0.append(vs + pv); ust.append(us)
        u = torch.tensor(np.stack(u0), dtype=torch.float64, device=device)
        v = torch.tensor(np.stack(v0), dtype=torch.float64, device=device)
        # per-cell horizon (same rule as run.run_cell) and snapshot steps
        steps, snap, final = [], {}, {}
        import scopedesk.oracles.linear as LIN
        for i, (c, _, _) in enumerate(items):
            lin = LIN.check(E.linear_structured(c))
            fast = (lin.get("witness") or {}).get("fastest_growing_mode")
            sig = (fast or {}).get("max_eigenvalue_float", 0.0) or 0.0
            T = min(1500.0, max(800.0, 40.0 / sig)) if sig > 0 else 800.0
            n = int(round(T / dt))
            steps.append(n)
            snap.setdefault(int(round(0.9 * n)), []).append(i)
            final.setdefault(n, []).append(i)
        snap_u = torch.zeros_like(u)
        fin_u = torch.zeros_like(u)
        fin_ok = torch.ones(Sn, dtype=torch.bool, device=device)

        def dif(x, m):
            return ((x @ Dmat.T) * m) @ Dmat

        h = dt
        for k in range(1, max(steps) + 1):
            u, v = dif(u, mu), dif(v, mv)
            k1u, k1v = _react(model, pa, pb, u, v)
            k2u, k2v = _react(model, pa, pb, u + .5 * h * k1u, v + .5 * h * k1v)
            k3u, k3v = _react(model, pa, pb, u + .5 * h * k2u, v + .5 * h * k2v)
            k4u, k4v = _react(model, pa, pb, u + h * k3u, v + h * k3v)
            u = u + h / 6 * (k1u + 2 * k2u + 2 * k3u + k4u)
            v = v + h / 6 * (k1v + 2 * k2v + 2 * k3v + k4v)
            u, v = dif(u, mu), dif(v, mv)
            if k in snap:
                snap_u[snap[k]] = u[snap[k]]
            if k in final:
                fin_u[final[k]] = u[final[k]]
        ok = torch.isfinite(fin_u).all(1) & (fin_u.abs().max(1).values < 1e3)
        fu, su = fin_u.cpu().numpy(), snap_u.cpu().numpy()
        for i, (c, _, _) in enumerate(items):
            if not bool(ok[i]):
                out[c["id"]] = {"diverged": True}
            else:
                m = S.metrics(fu[i], su[i], ust[i])
                m["diverged"] = False
                out[c["id"]] = m
        if log:
            log(f"{arm} {model} N={N} cells={Sn} steps<={max(steps)} {time.time()-t0:.1f}s")
    return out


def main(argv):
    cmd = argv[0]
    if cmd == "run":
        out = Path(argv[1])
        device = argv[argv.index("--device") + 1] if "--device" in argv else "cpu"
        arm = argv[argv.index("--arm") + 1] if "--arm" in argv else "base"
        cells = E.build(10)
        if "--ids-mod" in argv:
            i = argv.index("--ids-mod")
            M, Rr = int(argv[i + 1]), int(argv[i + 2])
            cells = [c for c in cells if c["id"] % M == Rr]
        t0 = time.time()
        res = integrate(cells, arm, torch.device(device), log=lambda s: print(s, flush=True))
        with open(out, "w") as f:
            for cid, m in sorted(res.items()):
                f.write(json.dumps({"id": cid, "arm": arm, "A_replay": m}) + "\n")
        print(json.dumps({"cells": len(res), "arm": arm, "device": device, "seconds": time.time() - t0,
                          "torch": torch.__version__, "cuda": torch.cuda.get_device_name(0) if device == "cuda" else None}))
    elif cmd == "compare":
        rep = {json.loads(l)["id"]: json.loads(l) for l in open(argv[1])}
        ref = {json.loads(l)["id"]: json.loads(l) for l in open(argv[2])}
        n = same_flag = same_mode = amp_ok = div = 0
        worst = 0.0
        for cid, r in rep.items():
            a, b = r["A_replay"], ref[cid]["A"]
            if a.get("diverged") or b.get("diverged"):
                div += 1
                continue
            n += 1
            same_flag += a["pattern"] == b["pattern"]
            same_mode += (a["mode"] == b["mode"]) or not b["pattern"]
            rel = abs(a["amp"] - b["amp"]) / max(b["amp"], 1e-12) if b["pattern"] else abs(a["amp"] - b["amp"])
            amp_ok += rel <= 0.01 if b["pattern"] else rel <= 1e-6
            worst = max(worst, rel)
        print(json.dumps({"compared": n, "diverged_either": div, "pattern_flag_equal": same_flag, "dominant_mode_equal_or_no_pattern": same_mode,
                          "amp_within_tolerance": amp_ok, "worst_relative_amp_difference": worst}))


if __name__ == "__main__":
    main(sys.argv[1:])
