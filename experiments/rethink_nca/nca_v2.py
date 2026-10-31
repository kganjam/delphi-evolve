"""POST-HOC fair-chance NCA variant (added AFTER the v1 NCA arm failed; NOT part of the frozen decision rules).

Change from v1, nothing else: no hidden channels (HID=0, the NCA is then a learned local time-stepper on the two observed
fields) and 32-step training windows instead of 16. Stages: train (2 seeds), then design+evaluate arm "N2" with the frozen
selection rule and the frozen independent evaluator. Results are reported separately and labelled post hoc.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
import torch

from . import nca, rd
from . import run_probe as rp

OUT = Path("artifacts/rethink_nca")
MOD = OUT / "models_v2"
SEEDS = [0, 1]


def setup():
    nca.HID, nca.C = 0, 2
    torch.set_num_threads(2)


def train():
    setup()
    MOD.mkdir(parents=True, exist_ok=True)
    log = {}
    for sd in SEEDS:
        if (MOD / f"nca2_seed{sd}.pt").exists():
            continue
        t = time.time()
        model, hist = nca.train(seed=sd, iters=1000, K=32, batch=192, log=lambda s: print(f"nca2_seed{sd}", s, flush=True))
        torch.save(model.state_dict(), MOD / f"nca2_seed{sd}.pt")
        log[f"nca2_seed{sd}"] = {"first50": float(np.mean(hist[:50])), "last50": float(np.mean(hist[-50:])), "wall_s": time.time() - t}
        print(log, flush=True)
    (MOD / "train_log.json").write_text(json.dumps(log, indent=1))


def design_eval():
    setup()
    data = json.loads((OUT / "evaluated.json").read_text())
    reqs = {q["id"]: q for q in data["requests"] if not q["control"]}
    scan = rp.loggrid(*rp.GR, rp.NCA_SCAN)
    out = []
    for sd in SEEDS:
        m = nca.NCA(); m.load_state_dict(torch.load(MOD / f"nca2_seed{sd}.pt")); m.eval()
        tab = {}
        fid = {}
        for r in rp.RS:
            ks = [(float(g), float(d), r) for d in rp.DS for g in scan]
            st = rd.initial_state(len(ks), rd.n_cells(r), [0] * len(ks))
            fin = nca.fast_rollout(m, st, [k[0] for k in ks], [k[1] for k in ks], rp.T_DESIGN)
            ok = np.isfinite(fin).all(axis=(1, 2))
            u = np.where(ok[:, None], fin[:, 0], 0.0)
            pm = rd.pattern_metrics(u, r)
            # fidelity vs the training solver (Euler) on the same noise: dominant mode agreement and amplitude ratio
            eul = rd.euler_fd(st, np.array([k[0] for k in ks]), np.array([k[1] for k in ks]), rp.T_DESIGN, dt=nca.DT_NCA)
            pe = rd.pattern_metrics(eul[:, 0], r)
            fid[r] = {"finite_rows": int(ok.sum()), "rows": len(ks), "same_dominant_mode_as_euler": float(np.mean(pm["m"] == pe["m"])),
                      "amp_ratio_median": float(np.median(pm["amp"] / np.maximum(pe["amp"], 1e-12)))}
            for j, k in enumerate(ks):
                tab[k] = (int(pm["m"][j]), float(pm["amp"][j]), float(pm["lam"][j]), bool(pm["patterned"][j] and ok[j]))
        for i, q in reqs.items():
            t = {g: tab[(float(g), float(q["d"]), q["r"])] for g in scan}
            c = rp.pick(scan, q["lam"], t)
            rec = {"arm": "N2", "seed": sd, "req": i, "sims": 0}
            if c is None:
                rec["decision"] = "abstain_no_pattern"
            else:
                m_, amp, lam, pat = t[c]
                rec.update(decision="accept", gamma=c, design_world_ok=abs(lam - q["lam"]) / q["lam"] <= rp.TOL)
            out.append(rec)
        print("fidelity", sd, json.dumps(fid), flush=True)
        out.append({"arm": "fidelity", "seed": sd, "fid": fid})
    todo = [d for d in out if d.get("decision") == "accept"]
    items = [{"gamma": d["gamma"], "d": reqs[d["req"]]["d"], "r": reqs[d["req"]]["r"], "lam": reqs[d["req"]]["lam"]} for d in todo]
    ev = rp._eval_batch(items)
    for d, e in zip(todo, ev):
        d["eval"] = e
    res = {}
    for sd in SEEDS:
        recs = [d for d in out if d.get("arm") == "N2" and d["seed"] == sd]
        succ = {d["req"]: (float(np.mean([e["ok"] for e in d["eval"]])) if d.get("eval") else 0.0) for d in recs}
        held = [i for i in succ if reqs[i]["held_out"]]
        res[f"seed{sd}"] = {"success_treatment": float(np.mean(list(succ.values()))), "success_held_out": float(np.mean([succ[i] for i in held])),
                            "accepted": int(sum(d["decision"] == "accept" for d in recs)),
                            "design_world_ok_among_accepted": float(np.mean([bool(d.get("design_world_ok")) for d in recs if d["decision"] == "accept"])) if any(d["decision"] == "accept" for d in recs) else None}
    (OUT / "nca_v2_results.json").write_text(json.dumps({"label": "POST HOC fair-chance variant; not a frozen decision rule", "summary": res, "records": out}, indent=1, default=float))
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    {"train": train, "design_eval": design_eval}[sys.argv[1]]()
