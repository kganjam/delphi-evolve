"""Analysis exactly as preregistered (PREREG.md). Usage: python3 -m scopedesk.oracles.nonlinear_sweep.analyze OUTDIR"""
from __future__ import annotations

import hashlib
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

from scipy.stats import beta


def cp(k, n, a=0.05):
    if n == 0:
        return None
    lo = 0.0 if k == 0 else float(beta.ppf(a / 2, k, n - k + 1))
    hi = 1.0 if k == n else float(beta.ppf(1 - a / 2, k + 1, n - k))
    return [round(lo, 4), round(hi, 4)]


def rate(num, den):
    return {"k": num, "n": den, "rate": (num / den if den else None), "ci95_exact_cells_treated_independent": cp(num, den)}


def quantities(rows):
    lin_stable = [r for r in rows if r["linear"] == "out_of_scope"]
    lin_unst = [r for r in rows if r["linear"] == "applies"]
    r1 = sum(r["category"] == "pattern" for r in lin_stable)
    r2 = sum(r["category"] == "no_pattern" for r in lin_unst)
    pat_u = [r for r in lin_unst if r["category"] == "pattern"]
    mism = [r for r in pat_u if r["mode"] != r["linear_fastest_mode"]]
    unres = lambda rs: sum(r["category"] == "unresolved" for r in rs)
    return {"cells": len(rows), "linear_stable_cells": len(lin_stable), "linear_unstable_cells": len(lin_unst),
            "R1_linear_stable_but_nonlinear_pattern": rate(r1, len(lin_stable)),
            "R2_linear_unstable_but_no_pattern": rate(r2, len(lin_unst)),
            "R3_linear_unstable_pattern_with_different_dominant_mode": rate(len(mism), len(lin_unst)),
            "R3_among_resolved_patterned_linear_unstable": rate(len(mism), len(pat_u)),
            "mode_offset_nonlinear_minus_linear": dict(Counter(r["mode"] - r["linear_fastest_mode"] for r in mism)),
            "unresolved_mass": rate(unres(rows), len(rows)),
            "unresolved_reasons": dict(Counter(r["why"] for r in rows if r["category"] == "unresolved")),
            "draw_level": {"draws_with_R1_event": len({(r["model"], r["draw"]) for r in lin_stable if r["category"] == "pattern"}),
                           "draws_with_R2_event": len({(r["model"], r["draw"]) for r in lin_unst if r["category"] == "no_pattern"}),
                           "draws_with_R3_event": len({(r["model"], r["draw"]) for r in mism}),
                           "draws_total": len({(r["model"], r["draw"]) for r in rows})}}


def main(outdir):
    out = Path(outdir)
    raw = (out / "rows.jsonl").read_bytes()
    rows = [json.loads(l) for l in raw.decode().splitlines() if l.strip()]
    status = json.loads((out / "run_status.json").read_text()) if (out / "run_status.json").exists() else {}
    rep = {"rows_sha256": hashlib.sha256(raw).hexdigest(), "run_status": status, "overall": quantities(rows), "strata": {}, "rho_by_eps": {}}
    for name, key in (("model", "model"), ("rho", "rho"), ("x_L_over_lambda_c", "x"), ("eps", "eps"), ("seed", "seed")):
        g = defaultdict(list)
        for r in rows:
            g[str(r[key])].append(r)
        rep["strata"][name] = {k: quantities(v) for k, v in sorted(g.items())}
    g = defaultdict(list)
    for r in rows:
        g[f"rho={r['rho']}|eps={r['eps']}"].append(r)
    rep["rho_by_eps"] = {k: {kk: vv for kk, vv in quantities(v).items() if kk in ("cells", "linear_stable_cells", "R1_linear_stable_but_nonlinear_pattern", "R2_linear_unstable_but_no_pattern", "unresolved_mass")} for k, v in sorted(g.items())}
    # preregistered predictions
    s = rep["strata"]
    p1 = all(s["rho"][k]["R1_linear_stable_but_nonlinear_pattern"]["k"] == 0 for k in s["rho"] if False) and True
    r1_eps001 = sum(1 for r in rows if r["eps"] == 0.01 and r["linear"] == "out_of_scope" and r["category"] == "pattern")
    r1_events = [r for r in rows if r["linear"] == "out_of_scope" and r["category"] == "pattern"]
    r2_events = [r for r in rows if r["linear"] == "applies" and r["category"] == "no_pattern"]
    ov = rep["overall"]
    rep["predictions"] = {
        "P1_R1_zero_at_eps_0.01": {"R1_events_at_eps_0.01": r1_eps001, "holds": r1_eps001 == 0},
        "P2_R1_only_rho_ge_0.9_and_eps_ge_0.1": {"events_total": len(r1_events), "events_violating": sum(1 for r in r1_events if r["rho"] < 0.9 or r["eps"] < 0.1),
                                                  "holds": all(r["rho"] >= 0.9 and r["eps"] >= 0.1 for r in r1_events)},
        "P3_R2_concentrated_at_rho_1.03_or_x_2": {"events_total": len(r2_events), "events_at_rho1.03_or_x2": sum(1 for r in r2_events if r["rho"] == 1.03 or r["x"] == 2),
                                                   "events_at_rho_ge_1.5": sum(1 for r in r2_events if r["rho"] >= 1.5),
                                                   "holds": bool(r2_events) and sum(1 for r in r2_events if r["rho"] == 1.03 or r["x"] == 2) > 0.5 * len(r2_events) and not any(r["rho"] >= 1.5 for r in r2_events)},
        "P4_R3_ge_0.2_and_mostly_lower": {"R3": ov["R3_linear_unstable_pattern_with_different_dominant_mode"]["rate"],
                                           "lower_share_of_mismatches": (sum(v for k, v in ov["mode_offset_nonlinear_minus_linear"].items() if int(k) < 0) / max(1, sum(ov["mode_offset_nonlinear_minus_linear"].values()))),
                                           "holds": (ov["R3_linear_unstable_pattern_with_different_dominant_mode"]["rate"] or 0) >= 0.2 and
                                                    sum(v for k, v in ov["mode_offset_nonlinear_minus_linear"].items() if int(k) < 0) > 0.5 * max(1, sum(ov["mode_offset_nonlinear_minus_linear"].values()))},
        "P5_unresolved_below_5pct": {"unresolved": ov["unresolved_mass"], "holds": (ov["unresolved_mass"]["rate"] or 0) < 0.05}}
    rep["notes"] = ["intervals treat cells as independent and are too narrow (cells share parameter draws and paired seeds); draw-level counts are given",
                    "both solvers are by the same author and share the equations", "R1 is a finite-amplitude outcome of the declared model, not proof of subcriticality",
                    "evidence kind: simulated (nonlinear) + formal (linear verdicts)"]
    (out / "report.json").write_text(json.dumps(rep, indent=1))
    print(json.dumps({"cells": ov["cells"], "R1": ov["R1_linear_stable_but_nonlinear_pattern"], "R2": ov["R2_linear_unstable_but_no_pattern"],
                      "R3": ov["R3_linear_unstable_pattern_with_different_dominant_mode"], "unresolved": ov["unresolved_mass"],
                      "predictions": {k: v["holds"] for k, v in rep["predictions"].items()}}, indent=1))


if __name__ == "__main__":
    main(sys.argv[1])
