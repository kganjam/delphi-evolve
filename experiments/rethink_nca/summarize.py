"""Aggregate evaluated.json into summary.json following protocol.json decision rules. No new simulation."""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

import numpy as np

OUT = Path("artifacts/rethink_nca")


def req_success(rec):
    ev = rec.get("eval")
    return float(np.mean([e["ok"] for e in ev])) if ev else 0.0


def main():
    data = json.loads((OUT / "evaluated.json").read_text())
    proto = json.loads((Path(__file__).parent / "protocol.json").read_text())
    reqs = {q["id"]: q for q in data["requests"]}
    treat = [i for i, q in reqs.items() if not q["control"]]
    ctrl = [i for i, q in reqs.items() if q["control"]]
    held = [i for i in treat if reqs[i]["held_out"]]
    near = [i for i in treat if reqs[i]["d"] == 10]
    far = [i for i in treat if reqs[i]["d"] == 20]
    by = defaultdict(dict)       # (arm, seed) -> {req: rec}
    for rec in data["designs"]:
        by[(rec["arm"], rec["seed"])][rec["req"]] = rec

    def stat(key, ids):
        recs = [by[key][i] for i in ids]
        succ = [req_success(r) for r in recs]
        acc = [r for r in recs if r["decision"] == "accept"]
        return {"n_requests": len(ids), "success_mean": float(np.mean(succ)),
                "accepted": len(acc),
                "refused_or_abstained": len(recs) - len(acc),
                "success_among_accepted": float(np.mean([req_success(r) for r in acc])) if acc else None,
                "sims_total": int(sum(r.get("sims", 0) for r in recs)),
                "nca_queries_total": int(sum(r.get("nca_queries", 0) for r in recs)),
                "design_world_ok_among_accepted": (float(np.mean([bool(r.get("design_world_ok")) for r in acc if r.get("design_world_ok") is not None]))
                                                  if any(r.get("design_world_ok") is not None for r in acc) else None)}

    arms = {"C0": [("C0", None)], "D": [("D", None)], "G": [("G", None)], "Gmis": [("Gmis", None)],
            "N": [("N", s) for s in (0, 1, 2)], "Nshuf": [("Nshuf", 0)]}
    sets = {"treatment": treat, "near_onset_d10": near, "far_d20": far, "held_out": held, "control_d1": ctrl}
    out = {"strata_sizes": {k: len(v) for k, v in sets.items()}, "arms": {}}
    for arm, keys in arms.items():
        out["arms"][arm] = {}
        for sname, ids in sets.items():
            ks = [k for k in keys if ids and ids[0] in by[k]]      # controls exist only for NCA seed 0 / shuffled control
            per = [stat(k, ids) for k in ks]
            out["arms"][arm][sname] = {
                "success_mean": float(np.mean([p["success_mean"] for p in per])),
                "success_per_seed": [p["success_mean"] for p in per] if len(per) > 1 else None,
                "accepted_mean": float(np.mean([p["accepted"] for p in per])),
                "refused_or_abstained_mean": float(np.mean([p["refused_or_abstained"] for p in per])),
                "success_among_accepted_mean": (float(np.mean([p["success_among_accepted"] for p in per if p["success_among_accepted"] is not None]))
                                                if any(p["success_among_accepted"] is not None for p in per) else None),
                "sims_total_mean": float(np.mean([p["sims_total"] for p in per])),
                "nca_queries_total_mean": float(np.mean([p["nca_queries_total"] for p in per])),
                "design_world_ok_among_accepted_mean": (float(np.mean([p["design_world_ok_among_accepted"] for p in per if p["design_world_ok_among_accepted"] is not None]))
                                                         if any(p["design_world_ok_among_accepted"] is not None for p in per) else None)}
    # paired per-request comparison N(seed mean) vs D on treatment requests
    nmean = {i: float(np.mean([req_success(by[("N", s)][i]) for s in (0, 1, 2)])) for i in treat}
    dsucc = {i: req_success(by[("D", None)][i]) for i in treat}
    out["paired_N_minus_D_treatment"] = {"mean_diff": float(np.mean([nmean[i] - dsucc[i] for i in treat])),
                                         "requests_N_better": int(sum(nmean[i] > dsucc[i] + 1e-9 for i in treat)),
                                         "requests_N_worse": int(sum(nmean[i] < dsucc[i] - 1e-9 for i in treat)),
                                         "requests_tied": int(sum(abs(nmean[i] - dsucc[i]) <= 1e-9 for i in treat))}
    # union solvability (lower bound on feasibility: some arm succeeded on >=2 of 3 seeds)
    solved = {i: any(req_success(by[k][i]) >= 2 / 3 for k in by) for i in treat}
    out["treatment_requests_solved_by_at_least_one_arm"] = int(sum(solved.values()))
    out["G_refusals_on_treatment"] = [{"req": i, "d": reqs[i]["d"], "r": reqs[i]["r"], "lam": reqs[i]["lam"],
                                       "decision": by[("G", None)][i]["decision"], "solved_by_other_arm": solved[i]}
                                      for i in treat if by[("G", None)][i]["decision"] != "accept"]
    # G vs D on the requests G accepted
    gacc = [i for i in treat if by[("G", None)][i]["decision"] == "accept"]
    out["G_vs_D_on_G_accepted"] = {"n": len(gacc), "G_success": float(np.mean([req_success(by[("G", None)][i]) for i in gacc])) if gacc else None,
                                   "D_success": float(np.mean([req_success(by[("D", None)][i]) for i in gacc])) if gacc else None,
                                   "G_sims": int(sum(by[("G", None)][i]["sims"] for i in gacc)),
                                   "D_sims": int(sum(by[("D", None)][i]["sims"] for i in gacc)),
                                   "G_analytic_route": int(sum(by[("G", None)][i].get("route") == "analytic_licensed" for i in gacc))}
    out["claim_record_changed_refusals"] = {"refused": data["tampered_record_refusals"], "of": data["n_requests"]}
    out["controls_C0_hallucinated_success_requests"] = int(sum(req_success(by[("C0", None)][i]) > 0 for i in ctrl))
    out["controls_pattern_count_by_arm_seeds"] = {
        f"{a}{'' if s is None else s}": int(sum(1 for i in ctrl if i in by[(a, s)] and by[(a, s)][i]["decision"] == "accept"
                                                 and any(e["patterned"] for e in by[(a, s)][i].get("eval", []))))
        for (a, s) in by}
    # decision rules from protocol
    A = out["arms"]
    n_t, d_t = A["N"]["treatment"]["success_mean"], A["D"]["treatment"]["success_mean"]
    n_h, d_h = A["N"]["held_out"]["success_mean"], A["D"]["held_out"]["success_mean"]
    n_dw = A["N"]["treatment"]["design_world_ok_among_accepted_mean"]
    n_acc = A["N"]["treatment"]["success_among_accepted_mean"]
    rules = {
        "N_ge_D_minus_0.05_treatment": {"N": n_t, "D": d_t, "pass": n_t >= d_t - 0.05},
        "N_ge_D_minus_0.05_held_out": {"N": n_h, "D": d_h, "pass": n_h >= d_h - 0.05},
        "self_consistent_minus_independent_le_0.10": {"self_consistent_among_accepted": n_dw, "independent_among_accepted": n_acc,
                                                      "pass": (n_dw is not None and n_acc is not None and n_dw - n_acc <= 0.10)},
        "Nshuf_le_N_minus_0.20": {"Nshuf": A["Nshuf"]["treatment"]["success_mean"], "N": n_t,
                                  "pass": A["Nshuf"]["treatment"]["success_mean"] <= n_t - 0.20},
    }
    rules["NCA_GO_overall"] = all(v["pass"] for v in rules.values())
    gacc_ok = out["G_vs_D_on_G_accepted"]
    gacc_ids = gacc
    grules = {
        "controls_G_refuses_all_C0_accepts_all_C0_no_success": {
            "G_refused": A["G"]["control_d1"]["refused_or_abstained_mean"], "of": len(ctrl),
            "C0_accepted": A["C0"]["control_d1"]["accepted_mean"], "C0_success": A["C0"]["control_d1"]["success_mean"],
            "pass": A["G"]["control_d1"]["refused_or_abstained_mean"] == len(ctrl) and A["C0"]["control_d1"]["accepted_mean"] == len(ctrl) and A["C0"]["control_d1"]["success_mean"] == 0.0},
        "G_coverage_ge_50pct_of_treatment": {"accepted": len(gacc_ids), "of": len(treat), "pass": len(gacc_ids) >= 0.5 * len(treat)},
        "G_ge_D_minus_0.05_on_accepted_with_le_half_sims": {
            "G": gacc_ok["G_success"], "D": gacc_ok["D_success"], "G_sims": gacc_ok["G_sims"], "D_sims": gacc_ok["D_sims"],
            "pass": gacc_ok["n"] > 0 and gacc_ok["G_success"] >= gacc_ok["D_success"] - 0.05 and gacc_ok["G_sims"] <= 0.5 * gacc_ok["D_sims"]},
        "record_changed_refuses_all": {"refused": data["tampered_record_refusals"], "of": data["n_requests"],
                                       "pass": data["tampered_record_refusals"] == data["n_requests"]},
    }
    grules["GATED_CLAIM_GO_overall"] = all(v["pass"] for v in grules.values())
    out["decision_rules_NCA"] = rules
    out["decision_rules_gated_claim"] = grules
    (OUT / "summary.json").write_text(json.dumps(out, indent=1))
    print(json.dumps({"arms_treatment": {a: round(A[a]["treatment"]["success_mean"], 3) for a in A},
                      "arms_held_out": {a: round(A[a]["held_out"]["success_mean"], 3) for a in A},
                      "NCA_GO": rules["NCA_GO_overall"], "GATED_GO": grules["GATED_CLAIM_GO_overall"]}, indent=1))


if __name__ == "__main__":
    main()
