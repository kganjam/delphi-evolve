"""Value of information: what would an answer unlock, as a change in a NAMED DECISION.

EVPI = E_s[ max_a U(a,s) ] - max_a E_s[ U(a,s) ]          (expected value of perfect information)
EVSI = sum_o max_a sum_s p(s) L(o|s) U(a,s) - max_a E_s[U(a,s)]   (a real experiment with likelihood L)

Both are exact and computed from a decision model that a human declares: states, actions, utilities, prior.
The library invents none of them. A negative answer is valued exactly like a positive one, because VOI is the
expected improvement of the decision, averaged over what the answer might be.

Assumptions that are stated, not hidden:
  * utilities and the prior are DECLARED (with a source); a prior taken from an aggregate forecast is only as good
    as that forecast's calibration record, which the card prints next to it;
  * decisions are treated as additive across independent groups. Decisions that share an `independent_group`
    are NOT additive (they are descendants of one result): the group contributes its maximum, not its sum.
  * `proposed_connection` edges (a suggested analogy) never enter the headline value.
"""
from __future__ import annotations

import math

TOL = 1e-9


class DecisionModelError(ValueError):
    pass


def _check(prior: dict, utilities: dict):
    if not prior or not utilities:
        raise DecisionModelError("a decision needs states with a prior and at least one action with utilities")
    for s, p in prior.items():
        if not isinstance(p, (int, float)) or isinstance(p, bool) or not math.isfinite(p) or p < 0:
            raise DecisionModelError(f"prior[{s!r}] must be a finite probability >= 0")
    if abs(sum(prior.values()) - 1.0) > TOL:
        raise DecisionModelError(f"prior sums to {sum(prior.values())}, not 1")
    for a, row in utilities.items():
        if set(row) != set(prior):
            raise DecisionModelError(f"action {a!r} must give a utility for exactly the states {sorted(prior)}")
        for s, u in row.items():
            if not isinstance(u, (int, float)) or isinstance(u, bool) or not math.isfinite(u):
                raise DecisionModelError(f"utility[{a!r}][{s!r}] must be a finite number")


def best_action(prior: dict, utilities: dict):
    """(action, expected utility) under the prior. Ties broken by action name so the result is deterministic."""
    _check(prior, utilities)
    scored = sorted(((-sum(prior[s] * u for s, u in row.items()), a) for a, row in utilities.items()))
    neg, a = scored[0]
    return a, -neg


def evpi(prior: dict, utilities: dict) -> float:
    _check(prior, utilities)
    with_info = sum(p * max(row[s] for row in utilities.values()) for s, p in prior.items())
    return float(with_info - best_action(prior, utilities)[1])


def evsi(prior: dict, utilities: dict, likelihood: dict) -> float:
    """likelihood[outcome][state] = P(outcome | state); for every state the outcomes must sum to 1."""
    _check(prior, utilities)
    for s in prior:
        tot = sum(likelihood[o][s] for o in likelihood)
        if abs(tot - 1.0) > TOL:
            raise DecisionModelError(f"likelihood for state {s!r} sums to {tot}, not 1")
    value = 0.0
    for o, col in likelihood.items():
        joint = {s: prior[s] * col[s] for s in prior}
        value += max(sum(joint[s] * u for s, u in row.items()) for row in utilities.values())
    return float(value - best_action(prior, utilities)[1])


def unlock_value(edges: list[dict], decisions: dict) -> dict:
    """Consequence of resolving a problem: summed EVPI over the DISTINCT decisions it unlocks.

    edges: validated unlock edges {kind, decision_ref{id}, independent_group, ...}
    decisions: {decision_id: {prior, utilities, utility_unit, prior_source, utility_source}}
    Returns {value, unit, n_edges, n_decisions_estimated, unestimated, proposed_only, breakdown, caveats}.
    `value` is None when nothing is estimable or the estimable decisions use different units."""
    counted_edges = [e for e in edges if e.get("kind") in ("logical_necessity", "empirical_relevance")]
    proposed_ids = sorted({e["decision_ref"]["id"] for e in edges if e.get("kind") == "proposed_connection"})
    # 1. one decision reached by several edges (several routes, several descendants) is ONE decision
    by_decision: dict[str, dict] = {}
    for e in counted_edges:
        d = e["decision_ref"]["id"]
        by_decision.setdefault(d, {"group": e["independent_group"], "edges": 0})
        by_decision[d]["edges"] += 1
    estimated, unestimated = {}, []
    for d, info in sorted(by_decision.items()):
        m = decisions.get(d)
        if m is None:
            unestimated.append(d)
            continue
        estimated[d] = {"evpi": evpi(m["prior"], m["utilities"]), "unit": m.get("utility_unit"), "group": info["group"],
                        "n_edges": info["edges"], "prior_source": m.get("prior_source"), "utility_source": m.get("utility_source")}
    units = sorted({v["unit"] for v in estimated.values()})
    out = {"n_edges": len(edges), "n_decisions_estimated": len(estimated), "unestimated": unestimated,
           "proposed_only_decisions": [d for d in proposed_ids if d not in by_decision], "breakdown": estimated, "caveats": []}
    if not estimated:
        return {**out, "value": None, "unit": None}
    if len(units) != 1 or units[0] is None:
        out["caveats"].append(f"decision utilities use units {units}; not summed")
        return {**out, "value": None, "unit": None}
    # 2. decisions inside one independent_group are not additive: the group counts its largest member once
    groups: dict[str, float] = {}
    for d, v in estimated.items():
        groups[v["group"]] = max(groups.get(v["group"], 0.0), v["evpi"])
    out["groups"] = groups
    if unestimated:
        out["caveats"].append(f"{len(unestimated)} unlocked decision(s) have no decision model; value is a lower bound over the estimated ones")
    return {**out, "value": float(sum(groups.values())), "unit": units[0]}
