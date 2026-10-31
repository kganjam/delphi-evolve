"""Validate pde_oracle.solver against the independent solver in rethink-nca rd.py (path given on argv; not imported
from their worktree: pass a copy extracted with `git show e7838b3:experiments/rethink_nca/rd.py`)."""
import importlib.util, json, sys
import numpy as np, torch
from pde_oracle.solver import Solver

spec = importlib.util.spec_from_file_location("rd", sys.argv[1]); rd = importlib.util.module_from_spec(spec); spec.loader.exec_module(rd)
out = {"reference": "rethink-nca@e7838b3 rd.spectral_strang (DCT-II Neumann, Strang, RK4)", "cases": []}
for (g, d, r) in [(1.0, 1.0, 10), (1.0, 10.0, 10), (1.5, 20.0, 20), (0.7, 10.0, 30)]:
    N = rd.n_cells(r); S = 3; T = 20.0; dt = 0.02
    st = rd.initial_state(S, N, [11, 12, 13])
    ref, _ = rd.spectral_strang(st, [g] * S, [d] * S, r, T, dt=dt)
    # even periodic extension of length 2L reproduces the Neumann problem exactly
    u = np.concatenate([st[:, 0], st[:, 0][:, ::-1]], 1); v = np.concatenate([st[:, 1], st[:, 1][:, ::-1]], 1)
    P = {"a": torch.full((S,), rd.A, dtype=torch.float64), "b": torch.full((S,), rd.B, dtype=torch.float64), "Du": torch.full((S,), 1.0 / g, dtype=torch.float64), "Dv": torch.full((S,), d / g, dtype=torch.float64)}
    sv = Solver("schnakenberg", P, (2 * N,), (2 * r * np.pi,), "cpu", torch.float64)
    uu, vv = sv.run(torch.from_numpy(u.copy()), torch.from_numpy(v.copy()), T, dt)
    err = max(np.abs(uu.numpy()[:, :N] - ref[:, 0]).max(), np.abs(vv.numpy()[:, :N] - ref[:, 1]).max())
    out["cases"].append({"gamma": g, "d": d, "r": r, "N": N, "T_tau": T, "dt": dt, "max_abs_diff": float(err),
                         "state_scale": float(np.abs(ref).max())})
    print(out["cases"][-1])
out["max_abs_diff_all"] = max(c["max_abs_diff"] for c in out["cases"])
json.dump(out, open(sys.argv[2], "w"), indent=1)
