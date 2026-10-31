"""Priority card: an explainable, multi-field view of one problem. No composite truth score, no hidden default.

Every field is either computed from declared inputs or None with a reason. The lenses are deterministic predicates
over the card, so a reader can see WHY an item appears, and choose the lens instead of trusting one ranking number.
"""
from __future__ import annotations

from .schema import parse_time, validate_profile, validate_next_action
from .voi import unlock_value

ACTIVE_LEASE = ("leased", "running", "submitted")
LENSES = ("newly_actionable", "blocking_downstream", "seeking_review", "neglected_important", "exploratory")


def active_signals(signals: list[dict]) -> list[dict]:
    """Signals not retracted. A retraction counts only if it comes from the same operator as the signal it retracts."""
    by_id = {s["id"]: s for s in signals}
    retracted = set()
    for s in signals:
        t = s.get("retracts")
        if t and t in by_id and by_id[t]["actor"]["operator"] == s["actor"]["operator"]:
            retracted.add(t)
    return [s for s in signals if s["id"] not in retracted and not s.get("retracts")]


def _operators(sigs: list[dict], kind: str) -> list[str]:
    # distinct OPERATORS, not accounts: one operator's many identities are one voice
    return sorted({s["actor"]["operator"] for s in sigs if s["kind"] == kind})


def build_card(problem: dict, profile: dict, *, decisions: dict, signals: list[dict], problem_states: dict,
               now: str, calibration: dict | None = None) -> dict:
    """problem: {id, depends_on:[ids], needs:[capability strings]}  (the seed map's own fields)
    profile: attention profile (schema.validate_profile). problem_states: {problem_id: 'open'|'resolved'}.
    signals: all signals for this problem (retractions applied here). now: ISO time for lease expiry."""
    issues = validate_profile(profile)
    bounded = not validate_next_action(profile.get("next_action"))
    sigs = active_signals([s for s in signals if s["problem_ref"]["id"] == problem["id"]])
    t_now = parse_time(now)
    leases = [l for l in profile.get("working", []) if l.get("status") in ACTIVE_LEASE and parse_time(l["expires_at"]) > t_now]
    deps = list(problem.get("depends_on", []))
    unresolved = [d for d in deps if problem_states.get(d) != "resolved"]
    offered = {s["payload"]["capability"].strip().casefold() for s in sigs if s["kind"] == "can_contribute"}
    unmet = [n for n in problem.get("needs", []) if n.strip().casefold() not in offered]
    uv = unlock_value(profile.get("unlocks", []), decisions)
    est = (profile.get("next_action") or {}).get("resource_estimate") if bounded else None
    card = {
        "id": problem["id"], "question": (profile.get("open") or {}).get("question"),
        "resolved": problem_states.get(problem["id"]) == "resolved",
        "profile_issues": issues, "bounded": bounded,
        "ready": bool(bounded and not unresolved), "blocked_on": unresolved,
        "staffed": not unmet, "unmet_needs": unmet,
        "active_leases": len(leases), "submitted_for_review": sum(l["status"] == "submitted" for l in leases),
        "consequence": uv, "cost": ({"amount": est["amount"], "unit": est["unit"], "basis": "estimate"} if est else None),
        "followers": _operators(sigs, "following"), "contributors": _operators(sigs, "can_contribute"),
        "blockers": _operators(sigs, "blocked_by_this"),
        "resource_offers": [s["payload"] | {"operator": s["actor"]["operator"]} for s in sigs if s["kind"] == "resource_offer"],
        "calibration_of_priors": calibration or "no resolved-forecast record supplied: priors are declared, not calibrated",
        "epistemic_note": "consequence = summed EVPI of DISTINCT unlocked decisions under declared utilities/priors; not a probability of truth",
    }
    card["lenses"] = lens_membership(card)
    return card


def lens_membership(card: dict) -> dict:
    """{lens: why} for each lens the card belongs to. Deterministic; every entry says which fields decided it."""
    out = {}
    if card["resolved"]:
        return out
    if card["ready"] and card["active_leases"] == 0:
        out["newly_actionable"] = "bounded next action, every dependency resolved, nobody holds an active lease"
    cv = card["consequence"]
    if any(v["evpi"] > 0 for v in cv["breakdown"].values()) or card["blockers"]:
        out["blocking_downstream"] = (f"{len(card['blockers'])} operator(s) report being blocked by it; "
                                       f"{cv['n_decisions_estimated']} unlocked decision(s) with a declared model")
    if card["submitted_for_review"]:
        out["seeking_review"] = f"{card['submitted_for_review']} submitted result(s) await independent review"
    value = cv["value"]
    if card["active_leases"] == 0 and not card["contributors"] and ((value or 0) > 0 or card["blockers"]):
        out["neglected_important"] = "declared consequence or a reported block, yet no lease and no contributor signal"
    if card["bounded"] and value is None:
        out["exploratory"] = "bounded action but no decision model: consequence unestimated, so only an exploration share can fund it"
    return out
