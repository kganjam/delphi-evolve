"""Resource states, bounded attention credits and contribution credit. Pure functions over plain dicts.

No storage, no atomicity, no identity, no transfer. Those belong to the Foundation worker's transactional layer;
this module only fixes WHAT must be true (invariants) so that layer can be tested against them:

  offered >= reserved >= consumed + released         (offered != reserved != consumed)
  attention credits: bounded per operator and per problem, never transferable, count verified operators only
  credit for work: only independently accepted work counts, and a result accepted by its own author does not
"""
from __future__ import annotations

import math

CREDIT_KINDS = ("accepted_result", "negative_result", "replication", "consolidation", "correction")


class ResourceError(ValueError):
    pass


class AllocationError(ValueError):
    pass


# ---------------------------- resource: offered -> availability_checked -> reserved -> consumed | released ---------
def new_offer(amount: float, unit: str) -> dict:
    if not (isinstance(amount, (int, float)) and math.isfinite(amount) and amount > 0) or not unit:
        raise ResourceError("an offer needs amount>0 and a unit")
    return {"unit": unit, "offered": float(amount), "checked": False, "reservations": {}}


def _tot(state: dict, k: str) -> float:
    return float(sum(r[k] for r in state["reservations"].values()))


def mark_checked(state: dict) -> dict:
    return {**state, "checked": True}


def reserve(state: dict, action_ref: str, amount: float) -> dict:
    if not state["checked"]:
        raise ResourceError("an unverified offer cannot be reserved: offered != availability_checked")
    if not (amount > 0) or not math.isfinite(amount):
        raise ResourceError("reserve amount must be > 0")
    if action_ref in state["reservations"]:
        raise ResourceError(f"{action_ref} already holds a reservation")
    if _tot(state, "reserved") + amount > state["offered"] + 1e-12:
        raise ResourceError(f"reserving {amount} would exceed the offer ({state['offered']}) given {_tot(state, 'reserved')} already reserved")
    return {**state, "reservations": {**state["reservations"], action_ref: {"reserved": float(amount), "consumed": 0.0, "released": 0.0}}}


def _update(state: dict, action_ref: str, **delta) -> dict:
    r = state["reservations"].get(action_ref)
    if r is None:
        raise ResourceError(f"no reservation for {action_ref}")
    new = {**r}
    for k, v in delta.items():
        new[k] = r[k] + v
    if new["consumed"] + new["released"] > new["reserved"] + 1e-12:
        raise ResourceError(f"{action_ref}: consumed+released ({new['consumed'] + new['released']}) would exceed reserved ({new['reserved']})")
    return {**state, "reservations": {**state["reservations"], action_ref: new}}


def consume(state: dict, action_ref: str, amount: float) -> dict:
    if not (amount >= 0) or not math.isfinite(amount):
        raise ResourceError("consumed amount must be >= 0")
    return _update(state, action_ref, consumed=float(amount))


def release(state: dict, action_ref: str) -> dict:
    """Release everything reserved and not consumed (unused capacity returns to the pool)."""
    r = state["reservations"][action_ref]
    return _update(state, action_ref, released=r["reserved"] - r["consumed"] - r["released"])


def available(state: dict) -> float:
    return state["offered"] - _tot(state, "reserved") + _tot(state, "released")


def reconcile(estimate: dict, reservation: dict, consumed_source: str) -> dict:
    """Estimate vs reservation vs consumption for one action. `consumed_source` ('ledger' | 'declared') is kept:
    a declared consumption is reported as unverified, never as a measured receipt."""
    if consumed_source not in ("ledger", "declared"):
        raise ResourceError("consumed_source must be 'ledger' or 'declared'")
    if estimate["unit"] != reservation.get("unit", estimate["unit"]):
        raise ResourceError("estimate and reservation use different units")
    est, res, con = estimate["amount"], reservation["reserved"], reservation["consumed"]
    return {"unit": estimate["unit"], "estimated": est, "reserved": res, "consumed": con,
            "overrun_vs_estimate": con - est, "overrun_vs_reservation": max(0.0, con - res),
            "consumption_status": "measured receipt" if consumed_source == "ledger" else "declared, unverified"}


# ---------------------------- bounded, non-transferable attention credits -----------------------------------------
def allocate_attention(budget_per_operator: float, per_problem_cap: float, rows: list[dict]) -> dict:
    """rows: {operator, verified:bool, problem_id, credits>=0}. Credits express PREFERENCE for where attention
    should go. They are not evidence, not a probability of truth, and there is no transfer operation.
    Rows of one operator are merged first, so splitting an allocation across accounts of the same operator
    cannot raise the cap. Unverified operators are listed and not counted."""
    if not (budget_per_operator > 0 and per_problem_cap > 0):
        raise AllocationError("budget and per-problem cap must be > 0")
    merged: dict[tuple, float] = {}
    verified: dict[str, bool] = {}
    for r in rows:
        c = r["credits"]
        if not (isinstance(c, (int, float)) and not isinstance(c, bool) and math.isfinite(c) and c >= 0):
            raise AllocationError(f"credits must be a finite number >= 0, got {c!r}")
        key = (r["operator"], r["problem_id"])
        merged[key] = merged.get(key, 0.0) + float(c)
        verified[r["operator"]] = bool(verified.get(r["operator"], True) and r["verified"])
    spent: dict[str, float] = {}
    for (op, pid), c in merged.items():
        if c > per_problem_cap + 1e-12:
            raise AllocationError(f"{op} puts {c} on {pid}, over the per-problem cap {per_problem_cap}")
        spent[op] = spent.get(op, 0.0) + c
    for op, s in spent.items():
        if s > budget_per_operator + 1e-12:
            raise AllocationError(f"{op} allocates {s}, over the budget {budget_per_operator}")
    per: dict[str, dict] = {}
    for (op, pid), c in merged.items():
        if not verified[op] or c == 0:
            continue
        d = per.setdefault(pid, {"credits": 0.0, "operators": {}})
        d["credits"] += c
        d["operators"][op] = c
    for pid, d in per.items():
        d["n_operators"] = len(d["operators"])
        d["max_operator_share"] = max(d["operators"].values()) / d["credits"]
    return {"per_problem": per, "unverified_operators_not_counted": sorted(o for o, v in verified.items() if not v),
            "meaning": "stated preference of verified operators under a bound; not evidence and not a probability of truth"}


# ---------------------------- credit for work: only independently accepted work counts ----------------------------
def contribution_credit(events: list[dict], weights: dict | None = None) -> dict:
    """events: {operator, kind in CREDIT_KINDS, action_ref, reviewer_operator|None, accepted:bool}.
    Counts an event only when accepted AND reviewed by a different operator. Negative results, replications,
    consolidation and corrections are first-class kinds. `weights` is a POLICY the caller declares; with none,
    only counts are returned (no total is invented)."""
    counted: dict[str, dict] = {}
    rejected = []
    for e in events:
        if e["kind"] not in CREDIT_KINDS:
            raise AllocationError(f"unknown credit kind {e['kind']!r}")
        if not e.get("accepted"):
            rejected.append({"action_ref": e["action_ref"], "reason": "not accepted"}); continue
        if not e.get("reviewer_operator"):
            rejected.append({"action_ref": e["action_ref"], "reason": "no recorded reviewer"}); continue
        if e["reviewer_operator"] == e["operator"]:
            rejected.append({"action_ref": e["action_ref"], "reason": "accepted by its own operator"}); continue
        c = counted.setdefault(e["operator"], {k: 0 for k in CREDIT_KINDS})
        c[e["kind"]] += 1
    out = {"counts": counted, "not_counted": rejected, "weights": weights}
    if weights is not None:
        miss = [k for k in CREDIT_KINDS if k not in weights]
        if miss:
            raise AllocationError(f"weights missing for kinds {miss}")
        out["totals"] = {op: sum(weights[k] * n for k, n in c.items()) for op, c in counted.items()}
    else:
        out["totals"] = None
    return out
