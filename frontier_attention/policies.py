"""Allocation policies over priority cards: simple baselines and one explicit 'coordinated' heuristic.

A policy returns an ORDER; `select_within_budget` turns an order into a funded set against a declared cost
estimate. The coordinated policy is a disclosed heuristic, not an optimum, and it is compared to the baselines by
evaluate.py rather than assumed better. Items with no declared consequence are never given an invented one: they
are unranked, and only an explicit exploration share can fund them.
"""
from __future__ import annotations


class PolicyError(ValueError):
    pass


def _cost(card):
    return card["cost"]["amount"] if card.get("cost") else None


def _units(cards):
    u = {c["cost"]["unit"] for c in cards if c.get("cost")}
    if len(u) > 1:
        raise PolicyError(f"cost estimates use several units {sorted(u)}; convert before ranking")
    return u


def curator_order(cards: list[dict], curator_ids: list[str]) -> list[str]:
    known = {c["id"] for c in cards}
    return [i for i in curator_ids if i in known] + sorted(known - set(curator_ids))


def round_robin_first_cycle(cards: list[dict]) -> list[str]:
    return sorted(c["id"] for c in cards)


def value_per_cost_order(cards: list[dict], curator_ids: list[str]) -> list[str]:
    """Descending declared consequence / estimated cost. Cards missing either number come AFTER, in curator order."""
    _units(cards)
    ranked, unranked = [], []
    for c in cards:
        v, k = c["consequence"]["value"], _cost(c)
        (ranked if (v is not None and k) else unranked).append(c)
    ranked.sort(key=lambda c: (-c["consequence"]["value"] / _cost(c), c["id"]))
    rest = {c["id"] for c in unranked}
    return [c["id"] for c in ranked] + [i for i in curator_order(cards, curator_ids) if i in rest]


def select_within_budget(order: list[str], cards: list[dict], budget: float) -> dict:
    """Greedy in the given order; an item that does not fit is skipped, not truncated. Items with no cost
    estimate cannot be budgeted and are listed as unfunded for that reason."""
    by_id = {c["id"]: c for c in cards}
    spent, picked, skipped = 0.0, [], []
    for i in order:
        k = _cost(by_id[i])
        if k is None:
            skipped.append((i, "no cost estimate")); continue
        if spent + k <= budget + 1e-12:
            spent += k; picked.append(i)
        else:
            skipped.append((i, "does not fit remaining budget"))
    return {"selected": picked, "spent": spent, "budget": budget, "skipped": skipped}


def coordinated(cards: list[dict], curator_ids: list[str], budget: float, exploration_share: float) -> dict:
    """Explicit heuristic: (1) only READY items nobody currently holds a lease on (avoids duplicate effort);
    (2) fund by declared value/cost; (3) reserve `exploration_share` of the budget for items that have a bounded
    action but no decision model (replication, consolidation and exploration are not optimised away)."""
    if not 0 <= exploration_share < 1:
        raise PolicyError("exploration_share must be in [0,1)")
    pool = [c for c in cards if c["ready"] and c["active_leases"] == 0 and not c["resolved"]]
    main = value_per_cost_order([c for c in pool if c["consequence"]["value"] is not None], curator_ids)
    a = select_within_budget(main, pool, budget * (1 - exploration_share))
    expl_pool = [c for c in pool if c["consequence"]["value"] is None]
    b = select_within_budget(curator_order(expl_pool, curator_ids), expl_pool, budget * exploration_share + (budget * (1 - exploration_share) - a["spent"]))
    why = {i: "value/cost within the main share" for i in a["selected"]} | {i: "exploration share (no decision model)" for i in b["selected"]}
    return {"selected": a["selected"] + b["selected"], "why": why, "spent": a["spent"] + b["spent"], "budget": budget,
            "excluded_not_ready_or_leased": sorted(c["id"] for c in cards if c not in pool and not c["resolved"])}
