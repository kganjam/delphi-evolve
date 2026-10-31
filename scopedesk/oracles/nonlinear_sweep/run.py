"""Run cells of the preregistered sweep. Usage:
  python3 -m scopedesk.oracles.nonlinear_sweep.run pilot OUT.json            (unscored pilot, separate ensemble seed)
  python3 -m scopedesk.oracles.nonlinear_sweep.run sweep OUTDIR [--workers 2] [--budget-seconds S] [--draws N]
The sweep visits cells in a fixed random permutation and appends one JSON line per finished cell (resumable); the stop rule is the
wall budget or completion, whichever is first; executed cells are an unbiased random subset of the grid."""
from __future__ import annotations

import json
import math
import sys
import time
from fractions import Fraction as F
from multiprocessing import Pool
from pathlib import Path

from .. import kinetics, linear
from . import ensemble as E
from . import solvers as S

TOL_AMP_SOLVERS = 0.15


def grid_for(c):
    L = float(F(c["r_over_pi"])) * math.pi
    dx = min(math.pi / 4, c["lambda_c"] / 20)
    NA = int(math.ceil(L / dx))
    return L, NA, int(math.ceil(1.5 * NA)), max(8, min(NA // 4, 40))


def run_cell(c):
    t0 = time.time()
    lin = linear.check(E.linear_structured(c))
    fast = (lin.get("witness") or {}).get("fastest_growing_mode")
    sig = (fast or {}).get("max_eigenvalue_float", 0.0) or 0.0
    T = min(1500.0, max(800.0, 40.0 / sig)) if sig > 0 else 800.0
    pp = kinetics.params(c["model"], c["params"])
    ust, vst = (float(z) for z in kinetics.steady(c["model"], pp))
    L, NA, NB, K = grid_for(c)
    Dv = F(c["Dv"])
    ta = time.time()
    A = S.run_cell_a(c["model"], pp, Dv, L, NA, T, c["eps"] * abs(ust), c["eps"] * abs(vst), c["seed"], K)
    tb = time.time()
    B = S.run_cell_b(c["model"], pp, Dv, L, NB, T, c["eps"] * abs(ust), c["eps"] * abs(vst), c["seed"], K)
    tc = time.time()
    if A.get("diverged") or B.get("diverged"):
        cat, why = "unresolved", "diverged"
    elif A["pattern"] != B["pattern"]:
        cat, why = "unresolved", "solver_disagree_flag"
    elif A["pattern"] and (A["mode"] != B["mode"] or abs(A["amp"] - B["amp"]) > TOL_AMP_SOLVERS * max(A["amp"], B["amp"])):
        cat, why = "unresolved", "solver_disagree_mode_or_amp"
    elif not (A["settled"] and B["settled"]):
        cat, why = "unresolved", "not_settled"
    else:
        cat, why = ("pattern" if A["pattern"] else "no_pattern"), None
    return {"id": c["id"], "model": c["model"], "draw": c["draw"], "rho": c["rho"], "x": c["x"], "eps": c["eps"], "seed": c["seed"],
            "linear": lin["scope_verdict"], "linear_wellmixed_or_refused": lin["verdict"] in ("wellmixed_unstable", "refused"),
            "linear_fastest_mode": fast["index"][0] if fast else None, "n_unstable_linear": lin.get("n_unstable_modes"), "sigma_fast": sig,
            "T": T, "NA": NA, "NB": NB, "category": cat, "why": why, "A": A, "B": B,
            "mode": A.get("mode") if cat == "pattern" else None, "seconds_A": round(tb - ta, 2), "seconds_B": round(tc - tb, 2),
            "seconds_total": round(time.time() - t0, 2)}


def pilot(out):
    import random
    cells = E.build(2, seed=777)                 # NOT the preregistered ensemble seed
    random.Random(5).shuffle(cells)
    rows = [run_cell(c) for c in cells[:24]]
    tot = sum(r["seconds_total"] for r in rows)
    res = {"n": len(rows), "seconds_total": tot, "seconds_per_cell_mean": tot / len(rows), "seconds_A_mean": sum(r["seconds_A"] for r in rows) / len(rows),
           "seconds_B_mean": sum(r["seconds_B"] for r in rows) / len(rows), "max_cell_seconds": max(r["seconds_total"] for r in rows),
           "categories": {k: sum(r["category"] == k for r in rows) for k in ("pattern", "no_pattern", "unresolved")},
           "why": {w: sum(r["why"] == w for r in rows) for w in {r["why"] for r in rows if r["why"]}}, "UNSCORED": True, "rows": rows}
    Path(out).write_text(json.dumps(res, indent=1))
    print(json.dumps({k: v for k, v in res.items() if k != "rows"}, indent=1))


def _work(c):
    try:
        return run_cell(c)
    except Exception as ex:   # a crashed cell is unresolved mass, never silently dropped
        return {"id": c["id"], "model": c["model"], "draw": c["draw"], "rho": c["rho"], "x": c["x"], "eps": c["eps"], "seed": c["seed"],
                "category": "unresolved", "why": "exception:" + repr(ex)[:120]}


def sweep(outdir, workers, budget, draws):
    out = Path(outdir)
    out.mkdir(parents=True, exist_ok=True)
    cells = E.build(draws)
    order = E.permutation(len(cells))
    order = [i for i in order if cells[i]["seed"] == E.PAIRED_SEEDS[0]] + [i for i in order if cells[i]["seed"] != E.PAIRED_SEEDS[0]]   # stage 1 = first seed, stage 2 = second
    rows_f = out / "rows.jsonl"
    done = {json.loads(l)["id"] for l in open(rows_f)} if rows_f.exists() else set()
    todo = [cells[i] for i in order if cells[i]["id"] not in done]
    t0 = time.time()
    with Pool(workers) as pool, open(rows_f, "a") as f:
        for r in pool.imap(_work, todo, chunksize=1):
            f.write(json.dumps(r) + "\n")
            f.flush()
            if time.time() - t0 > budget:
                pool.terminate()
                break
    n_done = sum(1 for _ in open(rows_f))
    import subprocess
    sha = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    (out / "run_status.json").write_text(json.dumps({"git_head": sha, "cells_total": len(cells), "cells_done": n_done, "wall_seconds_this_invocation": time.time() - t0,
                                                     "budget_seconds": budget, "stopped_by": "budget" if n_done < len(cells) else "completion"}, indent=1))
    print("done", n_done, "/", len(cells))


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[0] == "pilot":
        pilot(a[1])
    else:
        w = int(a[a.index("--workers") + 1]) if "--workers" in a else 2
        b = float(a[a.index("--budget-seconds") + 1]) if "--budget-seconds" in a else 10800
        d = int(a[a.index("--draws") + 1]) if "--draws" in a else 10
        sweep(a[1], w, b, d)
