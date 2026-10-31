"""Frozen feasibility probe: designs from six arms, independent evaluation, claim ablations. See protocol.json.

Stages (run in order, each resumable):  design  ->  evaluate  ->  summarize
All numbers are SIMULATED under the declared Schnakenberg model; none is observed.
"""
from __future__ import annotations

import copy
import itertools
import json
import math
import sys
import time
from pathlib import Path

import numpy as np
import torch

from turing_scope.source import load_pins

from . import gate, nca, rd

OUT = Path("artifacts/rethink_nca")
PROTO = json.loads((Path(__file__).parent / "protocol.json").read_text())
DS = PROTO["requests"]["d_values"]
RS = PROTO["requests"]["r_values"]
LAMS = PROTO["requests"]["lambda_targets"]
CTRL_D = PROTO["requests"]["control_d"]
TOL = gate.TOL
GR = tuple(PROTO["design_world"]["gamma_range"])
T_DESIGN = PROTO["design_world"]["horizon_tau"]
T_EVAL, T_CHK = 400.0, 360.0
EVAL_SEEDS = [11, 12, 13]
NCA_SCAN = 48
NCA_SEEDS = [0, 1, 2]
HELD_R = {30, 40}


def requests():
    reqs = []
    for d, r, l in itertools.product(DS, RS, LAMS):
        reqs.append({"d": d, "r": r, "lam": l, "control": False})
    for r, l in itertools.product(RS, LAMS):
        reqs.append({"d": CTRL_D, "r": r, "lam": l, "control": True})
    for i, q in enumerate(reqs):
        q["id"] = i
        gc = gate.formula_gamma(q["d"], q["lam"])
        q["held_out"] = bool(q["r"] in HELD_R or not (0.7 <= gc <= 2.0))
    return reqs


def loggrid(lo, hi, n):
    return list(np.exp(np.linspace(np.log(lo), np.log(hi), n)))


def success_from_final(u, r, lam_star, m_chk=None):
    pm = rd.pattern_metrics(u[None], r)
    ok = bool(pm["patterned"][0]) and abs(float(pm["lam"][0]) - lam_star) / lam_star <= TOL
    if m_chk is not None:
        ok = ok and int(pm["m"][0]) == m_chk
    return ok, pm


def run_design_sims(keys, log):
    """keys: list of (gamma, d, r). Returns {key: (m, amp, lam, patterned)} from the Euler design world, seed 0."""
    res = {}
    by_r = {}
    for k in keys:
        by_r.setdefault(k[2], []).append(k)
    for r, ks in by_r.items():
        N = rd.n_cells(r)
        t = time.time()
        g = np.array([k[0] for k in ks]); d = np.array([k[1] for k in ks], float)
        st = rd.initial_state(len(ks), N, [0] * len(ks))
        fin = rd.euler_fd(st, g, d, T_DESIGN, dt=nca.DT_NCA)
        pm = rd.pattern_metrics(fin[:, 0], r)
        for i, k in enumerate(ks):
            res[k] = (int(pm["m"][i]), float(pm["amp"][i]), float(pm["lam"][i]), bool(pm["patterned"][i]))
        log(f"design sims r={r} n={len(ks)} {time.time()-t:.1f}s")
    return res


def pick(cands, lam_star, table):
    """Selection rule shared by D, G, Gmis, N: among patterned candidates minimise |lam-lam*|."""
    best = None
    for g in cands:
        m, amp, lam, pat = table[g]
        if not pat:
            continue
        e = abs(lam - lam_star) / lam_star
        if best is None or e < best[0]:
            best = (e, g)
    return None if best is None else best[1]


def stage_design(log=print):
    OUT.mkdir(parents=True, exist_ok=True)
    reqs = requests()
    designs = []          # one record per (arm, request[, nca seed])
    need = set()
    # ---- gate (exact, adapter) for every request ; plus record-changed ablation
    pins = load_pins()
    tampered = copy.deepcopy(pins)
    h = tampered["turing-ddi"]["content_sha256"]
    tampered["turing-ddi"]["content_sha256"] = ("0" if h[0] != "0" else "1") + h[1:]
    gate_res = {}
    t = time.time()
    for q in reqs:
        gate_res[q["id"]] = gate.gate_design(q["d"], q["r"], q["lam"])
    tam_ref = [gate.gate_design(q["d"], q["r"], q["lam"], pins=tampered)["verdict"] for q in reqs]
    log(f"gate calls {time.time()-t:.1f}s; tampered refusals {sum(v=='refuse_source' for v in tam_ref)}/{len(reqs)}")
    # analytic G route: licensed formula at the admissible mode nearest lam*
    plans = {}
    for q in reqs:
        g = gate_res[q["id"]]
        base = {"req": q["id"]}
        if g["verdict"] != "candidates":
            plans[("G", q["id"])] = {"decision": g["verdict"]}
            plans[("Gmis", q["id"])] = {"decision": g["verdict"]}   # turing-ddi still applies (no band) -- see report
            continue
        # nearest admissible mode in the window that has an instability interval
        ivs = g["intervals"]
        L = q["r"] * math.pi
        m_best = min(ivs, key=lambda iv: abs(2 * L / iv[0] - q["lam"]))[0]
        gam_an = gate.formula_gamma(q["d"], 2 * L / m_best)
        lic = False
        if GR[0] <= gam_an <= GR[1]:
            chk = gate.check(gam_an, q["d"], q["r"])
            lic = chk["wavelength"]["status"] == "licensed" and (m_best in chk["unstable_modes"])
        if lic:
            plans[("G", q["id"])] = {"decision": "analytic", "gamma": gam_an, "mode": m_best, "sims": 0}
        else:
            # candidates: 12 points log-spaced over union of intervals (proportional to log length)
            tot = sum(math.log(hi / lo) for _, lo, hi in ivs)
            cands = []
            for _, lo, hi in ivs:
                n = max(1, round(12 * math.log(hi / lo) / tot))
                cands += loggrid(lo, hi, n) if n > 1 else [math.sqrt(lo * hi)]
            cands = [float(c) for c in cands][:12] if len(cands) > 12 else [float(c) for c in cands]
            plans[("G", q["id"])] = {"decision": "simulate", "cands": cands, "sims": len(cands)}
            for c in cands:
                need.add((c, float(q["d"]), q["r"]))
        # Gmis: continuum band only, no admissible-mode check
        ql, qu = (float(gate_res[q["id"]]["band_q"][0]), float(gate_res[q["id"]]["band_q"][1]))
        qt = (2 * math.pi / q["lam"]) ** 2
        lo, hi = max(qt / qu, GR[0]), min(qt / ql, GR[1])
        if lo < hi:
            cands = [float(c) for c in loggrid(lo, hi, 12)]
            plans[("Gmis", q["id"])] = {"decision": "simulate", "cands": cands, "sims": 12}
            for c in cands:
                need.add((c, float(q["d"]), q["r"]))
        else:
            plans[("Gmis", q["id"])] = {"decision": "refuse_empty_continuum_interval"}
    dgrid = [float(c) for c in loggrid(*GR, 12)]
    for q in reqs:
        for c in dgrid:
            need.add((c, float(q["d"]), q["r"]))
    sims = run_design_sims(sorted(need), log)
    # ---- assemble arms C0, D, G, Gmis
    for q in reqs:
        i = q["id"]
        # C0: formula, never refuses, no design-world simulation
        designs.append({"arm": "C0", "seed": None, "req": i, "decision": "accept", "gamma": gate.formula_gamma(q["d"], q["lam"]),
                        "sims": 0, "design_world_ok": None})
        c = pick(dgrid, q["lam"], {g: sims[(g, float(q["d"]), q["r"])] for g in dgrid})
        rec = {"arm": "D", "seed": None, "req": i, "sims": 12}
        if c is None:
            rec.update(decision="abstain_no_pattern")
        else:
            m, amp, lam, pat = sims[(c, float(q["d"]), q["r"])]
            ok = abs(lam - q["lam"]) / q["lam"] <= TOL
            rec.update(decision="accept", gamma=c, design_world_ok=bool(ok), design_world_lam=lam)
        designs.append(rec)
        for arm in ("G", "Gmis"):
            p = plans[(arm, i)]
            rec = {"arm": arm, "seed": None, "req": i, "sims": p.get("sims", 0)}
            if p["decision"] == "analytic":
                rec.update(decision="accept", gamma=p["gamma"], mode=p["mode"], design_world_ok=None, route="analytic_licensed")
            elif p["decision"] == "simulate":
                tab = {g: sims[(g, float(q["d"]), q["r"])] for g in p["cands"]}
                c = pick(p["cands"], q["lam"], tab)
                if c is None:
                    rec.update(decision="abstain_no_pattern", route="simulate")
                else:
                    m, amp, lam, pat = tab[c]
                    rec.update(decision="accept", gamma=c, route="simulate", design_world_ok=abs(lam - q["lam"]) / q["lam"] <= TOL,
                               design_world_lam=lam)
            else:
                rec.update(decision=p["decision"])
            designs.append(rec)
    # ---- NCA arms
    scan = loggrid(*GR, NCA_SCAN)
    models = {}
    for name in [f"nca_seed{s}" for s in NCA_SEEDS] + ["nshuf_seed0"]:
        mdl = nca.NCA()
        mdl.load_state_dict(torch.load(OUT / "models" / f"{name}.pt"))
        mdl.eval()
        models[name] = mdl
    torch.set_num_threads(2)
    nca_tables = {}
    for name, mdl in models.items():
        for r in RS:
            N = rd.n_cells(r)
            t = time.time()
            ks = [(float(g), float(d), r) for d in DS + [CTRL_D] for g in scan]
            st = rd.initial_state(len(ks), N, [0] * len(ks))
            fin, _ = nca.rollout(mdl, st, [k[0] for k in ks], [k[1] for k in ks], T_DESIGN)
            fin_ok = np.isfinite(fin).all(axis=(1, 2))
            u = np.where(fin_ok[:, None], fin[:, 0], U_NAN)
            pm = rd.pattern_metrics(u, r)
            for j, k in enumerate(ks):
                nca_tables[(name, k)] = (int(pm["m"][j]), float(pm["amp"][j]), float(pm["lam"][j]), bool(pm["patterned"][j] and fin_ok[j]))
            log(f"nca {name} r={r} {time.time()-t:.1f}s finite={int(fin_ok.sum())}/{len(ks)}")
    for name in models:
        arm = "Nshuf" if name.startswith("nshuf") else "N"
        sd = int(name.split("seed")[1])
        for q in reqs:
            tab = {g: nca_tables[(name, (float(g), float(q["d"]), q["r"]))] for g in scan}
            c = pick(scan, q["lam"], tab)
            rec = {"arm": arm, "seed": sd, "req": q["id"], "sims": 0, "nca_queries": NCA_SCAN}
            if c is None:
                rec.update(decision="abstain_no_pattern")
            else:
                m, amp, lam, pat = tab[c]
                rec.update(decision="accept", gamma=c, design_world_ok=abs(lam - q["lam"]) / q["lam"] <= TOL, design_world_lam=lam)
            designs.append(rec)
    (OUT / "designs.json").write_text(json.dumps({"requests": reqs, "designs": designs,
                                                  "tampered_record_refusals": int(sum(v == "refuse_source" for v in tam_ref)),
                                                  "n_requests": len(reqs),
                                                  "gate_verdicts": {str(k): v["verdict"] for k, v in gate_res.items()},
                                                  "gate_source_checks": gate_res[0]["source_checks"]}, indent=1, default=float))
    log("designs written")


U_NAN = np.zeros(1)   # placeholder replaced below


def stage_evaluate(log=print):
    data = json.loads((OUT / "designs.json").read_text())
    reqs = {q["id"]: q for q in data["requests"]}
    todo = [dsg for dsg in data["designs"] if dsg["decision"] == "accept"]
    by_r = {}
    for k, dsg in enumerate(todo):
        by_r.setdefault(reqs[dsg["req"]]["r"], []).append(k)
    for r, ks in by_r.items():
        N = rd.n_cells(r)
        t = time.time()
        rows = [(k, s) for k in ks for s in EVAL_SEEDS]
        g = np.array([todo[k]["gamma"] for k, _ in rows])
        d = np.array([reqs[todo[k]["req"]]["d"] for k, _ in rows], float)
        st = rd.initial_state(len(rows), N, [s for _, s in rows])
        fin, saved = rd.spectral_strang(st, g, d, r, T_EVAL, dt=0.02, checkpoints=(T_CHK,))
        pm = rd.pattern_metrics(fin[:, 0], r)
        pc = rd.pattern_metrics(saved[T_CHK][:, 0], r)
        for j, (k, s) in enumerate(rows):
            q = reqs[todo[k]["req"]]
            ok = bool(pm["patterned"][j]) and abs(pm["lam"][j] - q["lam"]) / q["lam"] <= TOL and int(pm["m"][j]) == int(pc["m"][j])
            todo[k].setdefault("eval", []).append({"seed": s, "ok": bool(ok), "m": int(pm["m"][j]), "lam": float(pm["lam"][j]),
                                                   "amp": float(pm["amp"][j]), "patterned": bool(pm["patterned"][j]),
                                                   "stable_mode": bool(int(pm["m"][j]) == int(pc["m"][j]))})
        log(f"evaluate r={r} samples={len(rows)} {time.time()-t:.1f}s")
    (OUT / "evaluated.json").write_text(json.dumps(data, indent=1, default=float))


def main(argv=None):
    stage = (argv or sys.argv)[1]
    {"design": stage_design, "evaluate": stage_evaluate}[stage]()


if __name__ == "__main__":
    main()
