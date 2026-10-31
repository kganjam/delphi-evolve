"""Arms at matched TOTAL TOKEN budget (not wall clock).

  A  one agent run sequentially for N attempts (each attempt may read the previous ones). Units = attempts.
     Primary output = the FINAL attempt (what a sequential agent actually hands over). The mean/median/etc. of
     attempts are also reported.
  B  N independent samples from ONE model family. Units = samples. Primary output = preregistered aggregator.
  C  N heterogeneous guilds bound to different model families and evidence modalities. Units = guild agents.
     Primary output = preregistered aggregator.

Budget of an arm = sum(tokens_in + tokens_out over its forecasts) + sum(overhead tokens booked to the arm).
Arms are only compared when max/min - 1 <= tolerance (preregistered, default 5%). Otherwise the comparison is
REFUSED and the report says so; per-arm scores are still printed but flagged not comparable.
Arms must also cover the identical set of resolved claims.
"""
from __future__ import annotations

import numpy as np


class BudgetMismatch(Exception):
    pass


def arm_budgets(forecasts: list[dict], overhead: list[dict]) -> dict:
    out: dict[str, dict] = {}
    for r in forecasts:
        a = out.setdefault(r["arm"], {"forecast_tokens": 0, "overhead_tokens": 0, "n_forecasts": 0})
        a["forecast_tokens"] += r["tokens_in"] + r["tokens_out"]
        a["n_forecasts"] += 1
    for r in overhead:
        a = out.setdefault(r["arm"], {"forecast_tokens": 0, "overhead_tokens": 0, "n_forecasts": 0})
        a["overhead_tokens"] += r["tokens"]
    for a in out.values():
        a["total_tokens"] = a["forecast_tokens"] + a["overhead_tokens"]
    return out


def check_budgets(budgets: dict, arms: list[str], tolerance: float, unit_key: str = "total_tokens") -> dict:
    """unit_key names the matched resource: total_tokens (default) or e.g. compiler_calls."""
    missing = [a for a in arms if a not in budgets or budgets[a].get(unit_key, 0) <= 0]
    if missing:
        return {"ok": False, "unit": unit_key, "reason": f"arms with no recorded {unit_key}: {missing}", "tolerance": tolerance}
    tot = {a: budgets[a][unit_key] for a in arms}
    lo, hi = min(tot.values()), max(tot.values())
    spread = hi / lo - 1.0
    return {"ok": bool(spread <= tolerance + 1e-12), "unit": unit_key, "totals": tot, "max_over_min_minus_1": float(spread), "tolerance": tolerance,
            "reason": None if spread <= tolerance + 1e-12 else f"budgets differ by {spread:.1%} > tolerance {tolerance:.1%}"}


def require_matched(budgets: dict, arms: list[str], tolerance: float):
    c = check_budgets(budgets, arms, tolerance)
    if not c["ok"]:
        raise BudgetMismatch(c["reason"])
    return c


def arm_matrix(forecasts: list[dict], arm: str, claim_ids: list[str]):
    """Return (unit_keys, meta, P) with P[(unit), claim]; units with incomplete coverage are dropped and listed."""
    rows = [r for r in forecasts if r["arm"] == arm]
    by_unit: dict[tuple, dict] = {}
    meta: dict[tuple, dict] = {}
    for r in rows:
        k = (r["agent_id"], r["attempt"])
        by_unit.setdefault(k, {})[r["claim_id"]] = r["probability"]
        meta[k] = {"agent_id": r["agent_id"], "attempt": r["attempt"], "guild": r["guild"], "model_family": r["model_family"]}
    keep, dropped = [], []
    for k in sorted(by_unit):
        (keep if all(c in by_unit[k] for c in claim_ids) else dropped).append(k)
    P = np.array([[by_unit[k][c] for c in claim_ids] for k in keep]) if keep else np.zeros((0, len(claim_ids)))
    return keep, {k: meta[k] for k in keep}, P, [{"unit": f"{a}#{t}", "n_claims_covered": len(by_unit[(a, t)])} for a, t in dropped]


def primary_output(arm: str, spec: dict, keys, P, aggregates: dict):
    """The arm's preregistered single output vector over claims."""
    if spec["output"] == "final_attempt":
        # last attempt of the (single) agent; if several agent ids exist in arm A the report flags it
        order = sorted(range(len(keys)), key=lambda i: (keys[i][1], keys[i][0]))
        return P[order[-1]], keys[order[-1]]
    name = spec["aggregator"]
    return aggregates[name], name
