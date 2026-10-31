"""POST-HOC control (added after the scored run): evaluate EVERY gamma of the 16-point log grid in [0.5,3] with the frozen
independent evaluator for each treatment request. Gives (a) the random-gamma baseline (fraction of grid gammas that
succeed) and (b) the feasibility ceiling (some grid gamma succeeds on >= 2 of 3 seeds). Not a frozen decision rule."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from . import run_probe as rp

OUT = Path("artifacts/rethink_nca")


def main():
    reqs = [q for q in rp.requests() if not q["control"]]
    grid = [float(g) for g in rp.loggrid(*rp.GR, 16)]
    items = [{"gamma": g, "d": q["d"], "r": q["r"], "lam": q["lam"], "req": q["id"]} for q in reqs for g in grid]
    ev = rp._eval_batch(items)
    per = {}
    for it, e in zip(items, ev):
        per.setdefault(it["req"], []).append(float(np.mean([x["ok"] for x in e])))
    rows = {i: {"mean_over_grid": float(np.mean(v)), "any_gamma_ge_2_of_3": bool(max(v) >= 2 / 3), "n_gamma_success_all3": int(sum(x == 1.0 for x in v))} for i, v in per.items()}
    held = {q["id"] for q in reqs if q["held_out"]}
    out = {"label": "POST HOC control", "random_gamma_success_treatment": float(np.mean([r["mean_over_grid"] for r in rows.values()])),
           "random_gamma_success_held_out": float(np.mean([rows[i]["mean_over_grid"] for i in held])),
           "feasible_requests": int(sum(r["any_gamma_ge_2_of_3"] for r in rows.values())), "of": len(rows), "per_request": rows}
    (OUT / "grid_oracle.json").write_text(json.dumps(out, indent=1))
    print(json.dumps({k: v for k, v in out.items() if k != "per_request"}, indent=1))


if __name__ == "__main__":
    main()
