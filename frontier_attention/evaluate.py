"""Does coordinated allocation resolve more decision-relevant uncertainty than simple policies at the same budget?

This is the evaluation the proposal names as decisive. It is a HARNESS: it runs only on a ledger of what arms
actually did, with value estimates frozen (and hashed) BEFORE the run. Nothing in it generates outcomes.
  * budgets must match (reuses market.arms.check_budgets); otherwise the comparison is refused;
  * value is the pre-registered, frozen EVPI of the problem an accepted result resolved - never a post-hoc value;
  * incorrect acceptance (accepted, then overturned by independent review), duplicate effort and failed handoffs are
    reported beside it, and a policy cannot 'win' by resolving more while accepting more wrong results;
  * the problem set is small (the seed map has seven). Under `min_problems` no verdict is issued.
Generated questions, messages or leases are not outcomes and never enter a metric.
"""
from __future__ import annotations

import json
from pathlib import Path

from market.arms import check_budgets
from market.stats import mcnemar_exact
from market.store import canon, sha256

PREREG = json.loads((Path(__file__).parent / "prereg_eval.json").read_text())


class EvalError(Exception):
    pass


def frozen_hash(frozen: dict) -> str:
    return sha256(canon({"unit": frozen["unit"], "values": frozen["values"]}))


def evaluate(rows: list[dict], frozen: dict, arms: list[str], prereg: dict | None = None) -> dict:
    """rows: {arm, problem_id, action_id, cost, accepted, overturned, duplicate_of|None, handoff_failed}
    frozen: {unit, values:{problem_id: value}, sha256}"""
    prereg = prereg or PREREG
    if frozen_hash(frozen) != frozen.get("sha256"):
        raise EvalError("frozen value table does not match its recorded sha256: values were changed after freezing")
    unknown = sorted({r["problem_id"] for r in rows} - set(frozen["values"]))
    if unknown:
        raise EvalError(f"rows reference problems with no frozen value: {unknown}")
    budgets = {a: {"cost": sum(r["cost"] for r in rows if r["arm"] == a)} for a in arms}
    bc = check_budgets(budgets, arms, prereg["budget_tolerance"], unit_key="cost")
    if not bc["ok"]:
        return {"verdict": "REFUSED", "reason": bc["reason"], "budget_check": bc}
    problems = sorted(frozen["values"])
    resolved: dict[str, dict[str, bool]] = {}
    per_arm = {}
    for a in arms:
        ar = [r for r in rows if r["arm"] == a]
        good = {r["problem_id"] for r in ar if r["accepted"] and not r["overturned"]}
        resolved[a] = {p: p in good for p in problems}
        n_acc = sum(1 for r in ar if r["accepted"])
        per_arm[a] = {
            "cost": budgets[a]["cost"], "actions": len(ar), "accepted": n_acc,
            "incorrect_acceptance": sum(1 for r in ar if r["accepted"] and r["overturned"]),
            "incorrect_acceptance_rate": (sum(1 for r in ar if r["accepted"] and r["overturned"]) / n_acc) if n_acc else None,
            "duplicate_effort_cost": sum(r["cost"] for r in ar if r.get("duplicate_of")),
            "failed_handoffs": sum(1 for r in ar if r.get("handoff_failed")),
            "problems_resolved": sum(resolved[a].values()), "problems_total": len(problems),
            "registered_value_resolved": sum(frozen["values"][p] for p in good),
            "cost_per_accepted_correct": (budgets[a]["cost"] / len(good)) if good else None,
        }
    out = {"verdict": "COMPARED", "budget_check": bc, "frozen_sha256": frozen["sha256"], "value_unit": frozen["unit"],
           "per_arm": per_arm, "n_problems": len(problems), "comparisons": {}}
    px, py = prereg["primary_comparison"]
    for x in arms:
        for y in arms:
            if x >= y:
                continue
            m = mcnemar_exact([resolved[x][p] for p in problems], [resolved[y][p] for p in problems])
            ax, ay = per_arm[x], per_arm[y]
            if len(problems) < prereg["min_problems"]:
                v = f"INSUFFICIENT PROBLEMS ({len(problems)} < {prereg['min_problems']}): descriptive only"
            elif m["p_two_sided_exact"] >= prereg["alpha"]:
                v = "no detectable difference in problems resolved"
            else:
                better = x if ax["problems_resolved"] > ay["problems_resolved"] else y
                worse_acc = (per_arm[better]["incorrect_acceptance"] > per_arm[y if better == x else x]["incorrect_acceptance"])
                v = f"{better} resolved more problems" + ("; BUT it also accepted more results that were later overturned, so it is not a clean win" if worse_acc else "")
            out["comparisons"][f"{x} vs {y}"] = {**m, "verdict": v,
                                                  "value_resolved": [ax["registered_value_resolved"], ay["registered_value_resolved"]],
                                                  "incorrect_acceptance": [ax["incorrect_acceptance"], ay["incorrect_acceptance"]],
                                                  "primary": sorted([x, y]) == sorted([px, py])}
    out["note"] = ("per-problem exact McNemar is item-level over a small, curated problem set; it is descriptive. "
                   "Value comes from frozen declared utilities, so a 'win' means more declared-value resolved, not more truth.")
    return out
