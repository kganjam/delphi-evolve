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
NCA_SCAN = 16
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
            with_ctrl = name in ("nca_seed0", "nshuf_seed0")      # controls only for 2 models (throughput bound)
            ks = [(float(g), float(d), r) for d in (DS + [CTRL_D] if with_ctrl else DS) for g in scan]
            st = rd.initial_state(len(ks), N, [0] * len(ks))
            fin = nca.fast_rollout(mdl, st, [k[0] for k in ks], [k[1] for k in ks], T_DESIGN)
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
            if q["control"] and name not in ("nca_seed0", "nshuf_seed0"):
                continue
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


def _mid_gamma(iv_list, lam, r):
    L = r * math.pi
    m, lo, hi = min(iv_list, key=lambda iv: abs(2 * L / iv[0] - lam))
    return m, math.sqrt(lo * hi)


def _eval_batch(items, log=print):
    """items: list of dict(gamma,d,r,lam). Independent solver, 3 seeds; returns list of lists of eval dicts."""
    out = [None] * len(items)
    by_r = {}
    for k, it in enumerate(items):
        by_r.setdefault(it["r"], []).append(k)
    for r, ks in by_r.items():
        rows = [(k, s) for k in ks for s in EVAL_SEEDS]
        g = np.array([items[k]["gamma"] for k, _ in rows]); d = np.array([items[k]["d"] for k, _ in rows], float)
        st = rd.initial_state(len(rows), rd.n_cells(r), [s for _, s in rows])
        fin, saved = rd.spectral_strang(st, g, d, r, T_EVAL, dt=0.02, checkpoints=(T_CHK,))
        pm, pc = rd.pattern_metrics(fin[:, 0], r), rd.pattern_metrics(saved[T_CHK][:, 0], r)
        for j, (k, s) in enumerate(rows):
            lam = items[k]["lam"]
            ok = bool(pm["patterned"][j]) and abs(pm["lam"][j] - lam) / lam <= TOL and int(pm["m"][j]) == int(pc["m"][j])
            if out[k] is None:
                out[k] = []
            out[k].append({"seed": s, "ok": bool(ok), "m": int(pm["m"][j]), "lam": float(pm["lam"][j]), "amp": float(pm["amp"][j]),
                           "patterned": bool(pm["patterned"][j])})
        log(f"eval_batch r={r} samples={len(rows)}")
    return out


def stage_repair(log=print):
    data = json.loads((OUT / "evaluated.json").read_text())
    reqs = {q["id"]: q for q in data["requests"]}
    gdes = {d["req"]: d for d in data["designs"] if d["arm"] == "G"}
    c0 = {d["req"]: d for d in data["designs"] if d["arm"] == "C0"}
    targets = [i for i, q in reqs.items() if q["control"] or gdes[i]["decision"] != "accept"]
    items, meta = [], []
    for i in targets:
        q = reqs[i]
        # (1) domain-length repair: nearest integer r' admissible
        for knob in ("domain_length", "diffusion_ratio"):
            found = None
            cands = (sorted(range(5, 61), key=lambda x: (abs(x - q["r"]), x)) if knob == "domain_length"
                     else list(range(int(q["d"]) , 61)))
            for c in cands:
                r2, d2 = (c, q["d"]) if knob == "domain_length" else (q["r"], c)
                if knob == "domain_length" and c == q["r"]:
                    continue
                g = gate.gate_design(d2, r2, q["lam"])
                if g["verdict"] == "candidates":
                    m, gam = _mid_gamma(g["intervals"], q["lam"], r2)
                    chk = gate.check(gam, d2, r2)
                    if m in chk["unstable_modes"]:
                        found = {"knob": knob, "r": r2, "d": float(d2), "gamma": gam, "mode": m}
                        break
            meta.append({"req": i, "knob": knob, "found": found})
            if found:
                items.append({"gamma": found["gamma"], "d": found["d"], "r": found["r"], "lam": q["lam"], "meta": len(meta) - 1})
    ev = _eval_batch(items, log)
    for it, e in zip(items, ev):
        meta[it["meta"]]["eval"] = e
        meta[it["meta"]]["success"] = float(np.mean([x["ok"] for x in e]))
    # unrepaired baseline (C0 formula on the ORIGINAL request) already evaluated in evaluated.json
    base = {i: float(np.mean([x["ok"] for x in c0[i]["eval"]])) for i in targets}
    out = {"n_targets": len(targets), "repairs": meta, "unrepaired_C0_success": base,
           "summary": {}}
    for knob in ("domain_length", "diffusion_ratio"):
        rows = [m for m in meta if m["knob"] == knob]
        for cls, ids in (("treatment_refused", [i for i in targets if not reqs[i]["control"]]), ("control_d1", [i for i in targets if reqs[i]["control"]])):
            rr = [m for m in rows if m["req"] in ids]
            out["summary"][f"{knob}/{cls}"] = {"requests": len(ids), "repair_found": sum(m["found"] is not None for m in rr),
                                              "repaired_success_mean_over_found": (float(np.mean([m["success"] for m in rr if m["found"]])) if any(m["found"] for m in rr) else None),
                                              "unrepaired_C0_success_mean": float(np.mean([base[i] for i in ids])) if ids else None}
    (OUT / "repair.json").write_text(json.dumps(out, indent=1, default=float))
    log(json.dumps(out["summary"], indent=1))


def stage_convergence(log=print):
    data = json.loads((OUT / "evaluated.json").read_text())
    reqs = {q["id"]: q for q in data["requests"]}
    acc = [d for d in data["designs"] if d["arm"] in ("D", "G") and d["decision"] == "accept"]
    sub = acc[::6]
    rows = []
    for variant in ("dt_half", "res_double"):
        by_r = {}
        for k, dsg in enumerate(sub):
            by_r.setdefault(reqs[dsg["req"]]["r"], []).append(k)
        for r, ks in by_r.items():
            N = rd.n_cells(r) * (2 if variant == "res_double" else 1)
            rr = [(k, s) for k in ks for s in EVAL_SEEDS]
            g = np.array([sub[k]["gamma"] for k, _ in rr]); d = np.array([reqs[sub[k]["req"]]["d"] for k, _ in rr], float)
            st = rd.initial_state(len(rr), N, [s for _, s in rr])
            fin, saved = rd.spectral_strang(st, g, d, r, T_EVAL, dt=0.01 if variant == "dt_half" else 0.02, checkpoints=(T_CHK,))
            pm, pc = rd.pattern_metrics(fin[:, 0], r), rd.pattern_metrics(saved[T_CHK][:, 0], r)
            for j, (k, s) in enumerate(rr):
                lam = reqs[sub[k]["req"]]["lam"]
                ok = bool(pm["patterned"][j]) and abs(pm["lam"][j] - lam) / lam <= TOL and int(pm["m"][j]) == int(pc["m"][j])
                base = [e for e in sub[k]["eval"] if e["seed"] == s][0]
                rows.append({"variant": variant, "arm": sub[k]["arm"], "req": sub[k]["req"], "seed": s, "ok": bool(ok), "base_ok": base["ok"],
                             "m": int(pm["m"][j]), "base_m": base["m"], "same_flag": bool(ok == base["ok"]),
                             "same_m": int(pm["m"][j]) == base["m"]})
            log(f"convergence {variant} r={r} {len(rr)}")
    summ = {}
    for v in ("dt_half", "res_double"):
        rv = [x for x in rows if x["variant"] == v]
        summ[v] = {"n": len(rv), "success_flag_agreement": float(np.mean([x["same_flag"] for x in rv])),
                   "dominant_mode_agreement": float(np.mean([x["same_m"] for x in rv])),
                   "base_success": float(np.mean([x["base_ok"] for x in rv])), "variant_success": float(np.mean([x["ok"] for x in rv]))}
    (OUT / "convergence.json").write_text(json.dumps({"subset_size_designs": len(sub), "summary": summ, "rows": rows}, indent=1))
    log(json.dumps(summ, indent=1))


def main(argv=None):
    stage = (argv or sys.argv)[1]
    {"design": stage_design, "evaluate": stage_evaluate, "repair": stage_repair, "convergence": stage_convergence}[stage]()


if __name__ == "__main__":
    main()
