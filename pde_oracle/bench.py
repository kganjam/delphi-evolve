"""Throughput pilot for the PDE settlement oracle: CPU (1..k threads) vs CUDA, 4 canonical models, 2-D periodic.

Reports cell-steps/s = batch * N^2 * steps / wall. Canonical illustrative parameters (NOT preregistered claims;
no pattern verdict is produced). Writes $COPS_OUT/pde_bench.json (or ./pde_bench.json).
"""
import json, os, sys, time
import torch
from pde_oracle.solver import Solver, initial_state

CANON = {  # model: (params, dt, dx)
    "schnakenberg": ({"a": .1, "b": .9, "Du": 1.0, "Dv": 10.0}, 0.05, 0.785),
    "gierer_meinhardt": ({"a": .40, "b": 1.0, "Du": 1.0, "Dv": 30.0}, 0.05, 0.785),
    "gray_scott": ({"F": .035, "k": .065, "Du": .16, "Dv": .08}, 1.0, 1.0),
    "brusselator": ({"A": 2.0, "B": 4.5, "Du": 1.0, "Dv": 8.0}, 0.05, 0.5),
}
CONFIGS = [(128, 16, "f64"), (256, 16, "f64"), (128, 128, "f64"), (128, 128, "f32")]


def sync(dev):
    if dev == "cuda": torch.cuda.synchronize()


def one(model, N, B, prec, dev):
    P0, dt, dx = CANON[model]
    dtype = torch.float64 if prec == "f64" else torch.float32
    P = {k: torch.full((B,), v, dtype=torch.float64) for k, v in P0.items()}
    u, v = initial_state(model, P, (N, N), list(range(B)), device=dev, dtype=dtype)
    s = Solver(model, P, (N, N), (N * dx, N * dx), dev, dtype)
    u, v = s.run(u, v, 3 * dt, dt); sync(dev)                       # warm-up
    n = 8; tot = 0.0
    while True:
        sync(dev); t = time.perf_counter(); u, v = s.run(u, v, n * dt, dt); sync(dev); w = time.perf_counter() - t
        if w >= 1.5 or n >= 640: break
        n = min(640, max(n * 2, int(n * 1.8 / max(w, 1e-3))))
    return {"model": model, "N": N, "B": B, "prec": prec, "steps": n, "wall_s": round(w, 3),
            "cell_steps_per_s": float(f"{B * N * N * n / w:.4g}"), "finite": bool(torch.isfinite(u).all() and torch.isfinite(v).all()),
            "dt": dt, "steps_for_T1000": int(round(1000 / dt))}


def main():
    out = {"torch": torch.__version__, "nproc": os.cpu_count(), "runs": []}
    devs = []
    if torch.cuda.is_available():
        out["gpu"] = torch.cuda.get_device_name(0); devs.append(("cuda", 1))
    if not os.environ.get("PDE_NO_CPU"):
        for th in [int(x) for x in os.environ.get("PDE_THREADS", "1,2").split(",")]:
            devs.append(("cpu", th))
    models = os.environ.get("PDE_MODELS", ",".join(CANON)).split(",")
    configs = [(int(a), int(b), c) for a, b, c in (x.split(":") for x in os.environ["PDE_CONFIGS"].split(","))] if os.environ.get("PDE_CONFIGS") else CONFIGS
    for dev, th in devs:
        torch.set_num_threads(th)
        for model in models:
            for N, B, prec in configs:
                if dev == "cpu" and th == 1 and (N, B) == (256, 16):  # keep 1-thread pilot short
                    pass
                r = one(model, N, B, prec, dev); r.update(device=dev, threads=th if dev == "cpu" else None)
                if dev == "cuda": r["peak_mem_gb"] = round(torch.cuda.max_memory_allocated() / 2**30, 2)
                out["runs"].append(r); print(json.dumps(r), flush=True)
    json.dump(out, open(os.path.join(os.environ.get("COPS_OUT", "."), os.environ.get("PDE_OUTNAME", "pde_bench.json")), "w"), indent=1)


main()
