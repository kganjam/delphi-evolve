"""Hand-worked tests for the Frontier attention/forecasting schema. Every numeric expectation below is computed by
hand in the comment beside it. Fixtures labelled ILLUSTRATIVE are invented to exercise the code; they are not data
about any real problem."""
import copy
import subprocess

import numpy as np
import pytest

from frontier_attention import card as cardmod
from frontier_attention import credit, evaluate as ev, forecasting, policies, schema, seeds, voi
from market.store import canon, sha256

H = "a" * 64
T0 = "2026-10-31T16:00:00Z"


def ref(i, v="v1"):
    return {"id": i, "version": v}


def good_action():
    return {"type": "proof", "input_hashes": [H], "resource_estimate": {"unit": "compiler_calls", "amount": 40, "basis": "estimate"},
            "stop_rule": "stop at 40 compiler calls", "acceptance_criterion": "compiled, axioms standard, mutants rejected", "reviewer": "reviewer-1"}


def good_profile():
    return {"problem_ref": ref("P1"), "known": [{"statement": "finite Price identity compiled", "evidence_kind": "formal", "source": "probe README"}],
            "open": {"question": "Which projection gives a faithful Fisher target?", "open_kind": "project_formalization_gap",
                     "novelty_status": "not_claimed", "acceptance_criterion": "independent fidelity review plus compiled correspondence"},
            "unlocks": [{"kind": "logical_necessity", "decision_ref": ref("D1"), "independent_group": "g1", "provenance": "curator"}],
            "working": [], "next_action": good_action()}


def codes(issues):
    return sorted(i["code"] for i in issues)


# ------------------------------------------------------------------ schema
def test_good_profile_is_valid():
    assert schema.validate_profile(good_profile()) == []


def test_each_missing_piece_is_reported_together():
    p = good_profile()
    del p["known"]; p["unlocks"][0]["kind"] = "similar_to"; p["next_action"]["stop_rule"] = " "
    got = {(i["path"], i["code"]) for i in schema.validate_profile(p)}
    assert ("known", "missing") in got and ("unlocks[0].kind", "untyped_edge") in got and ("next_action.stop_rule", "missing") in got


def test_estimate_must_be_labelled_estimate_and_inputs_pinned():
    a = good_action(); a["resource_estimate"]["basis"] = "measured"; a["input_hashes"] = ["not-a-hash"]
    assert {i["code"] for i in schema.validate_next_action(a)} == {"bad_estimate", "unpinned"}


def test_searched_novelty_needs_scope_and_date():
    p = good_profile(); p["open"]["novelty_status"] = "searched"
    assert ("open.search_scope", "missing") in {(i["path"], i["code"]) for i in schema.validate_profile(p)}
    p["open"].update(search_scope="arXiv+SSRN title/abstract, 2026-10-31", searched_at="2026-10-31T09:00:00-07:00")
    assert schema.validate_profile(p) == []


def sig(kind, payload, i="s1", op="opA", ver=True, **kw):
    return {"id": i, "version": "1", "kind": kind, "actor": {"operator": op, "identity_verified": ver}, "problem_ref": ref("P1"),
            "created_at": T0, "retracts": None, "payload": payload, **kw}


OFFER = {"resource_type": "gpu_hours", "amount": 10, "unit": "h", "window": {"start": "2026-10-31T17:00:00Z", "end": "2026-10-31T19:00:00Z"},
         "restrictions": [], "verification_status": "unverified"}


def test_signals_four_kinds_validate_and_blocked_needs_a_link():
    assert schema.validate_signal(sig("following", {})) == []
    assert schema.validate_signal(sig("resource_offer", OFFER)) == []
    assert schema.validate_signal(sig("blocked_by_this", {"downstream_ref": ref("F004"), "enablement": "faithful source claim"})) == []
    assert "bad_ref" in codes(schema.validate_signal(sig("blocked_by_this", {"enablement": "x"})))
    bad = dict(OFFER, window={"start": "2026-10-31T19:00:00Z", "end": "2026-10-31T17:00:00Z"})
    assert "bad_window" in codes(schema.validate_signal(sig("resource_offer", bad)))


def test_prediction_spec_rules():
    s = {"id": "e1", "problem_ref": ref("P1"), "event": "The nonlinear sweep finds a linear/nonlinear mismatch rate above 5% in stratum A",
         "resolution_criterion": "rate from committed rows", "resolution_source": "results/nonlinear_sweep/summary.json",
         "resolver": "reviewer-1", "forecasters": ["a", "b"], "horizon": "2026-10-31T23:00:00Z", "void_conditions": "sweep aborted before 50% of cells"}
    assert schema.validate_prediction_spec(s, now=T0) == []
    assert "not_independent" in codes(schema.validate_prediction_spec({**s, "resolver": "a"}, now=T0))
    assert "not_future" in codes(schema.validate_prediction_spec({**s, "horizon": "2026-10-31T15:00:00Z"}, now=T0))
    assert "vague" in codes(schema.validate_prediction_spec({**s, "event": "will it work"}, now=T0))


# ------------------------------------------------------------------ value of information (hand-worked)
PRIOR = {"H": 0.6, "notH": 0.4}
U = {"reuse": {"H": 10, "notH": -20}, "skip": {"H": 0, "notH": 0}}


def test_evpi_hand_example():
    # EU(reuse)=0.6*10+0.4*(-20)=-2 ; EU(skip)=0 ; best=skip (0). With perfect info: 0.6*10+0.4*0=6. EVPI=6
    assert voi.best_action(PRIOR, U) == ("skip", 0.0)
    assert voi.evpi(PRIOR, U) == pytest.approx(6.0)


def test_evpi_values_a_negative_answer():
    # p(H)=0.9: EU(reuse)=9-2=7 (best). Perfect info 0.9*10+0.1*0=9. EVPI=2 = P(notH)*[0-(-20)]=0.1*20: the value is entirely
    # in discovering the BAD state, i.e. the refusal/witness, not in confirming that reuse is fine.
    p = {"H": 0.9, "notH": 0.1}
    assert voi.best_action(p, U) == ("reuse", pytest.approx(7.0))
    assert voi.evpi(p, U) == pytest.approx(2.0)


def test_evsi_hand_example_and_bounds():
    # sens P(+|H)=.8, P(-|H)=.2 ; P(+|notH)=.1, P(-|notH)=.9
    # +: joint(H)=.48, joint(notH)=.04 -> reuse .48*10+.04*(-20)=4.0 ; skip 0 -> 4.0
    # -: joint(H)=.12, joint(notH)=.36 -> reuse 1.2-7.2=-6 ; skip 0 -> 0.  EVSI = 4.0+0-0 = 4.0 (< EVPI 6)
    L = {"pos": {"H": .8, "notH": .1}, "neg": {"H": .2, "notH": .9}}
    assert voi.evsi(PRIOR, U, L) == pytest.approx(4.0)
    assert voi.evsi(PRIOR, U, {"pos": {"H": 1.0, "notH": 0.0}, "neg": {"H": 0.0, "notH": 1.0}}) == pytest.approx(voi.evpi(PRIOR, U))
    assert voi.evsi(PRIOR, U, {"x": {"H": 1.0, "notH": 1.0}}) == pytest.approx(0.0)       # an uninformative test is worth nothing


def test_decision_model_errors():
    with pytest.raises(voi.DecisionModelError):
        voi.evpi({"H": 0.5, "notH": 0.4}, U)
    with pytest.raises(voi.DecisionModelError):
        voi.evpi(PRIOR, {"reuse": {"H": 1}})
    with pytest.raises(voi.DecisionModelError):
        voi.evsi(PRIOR, U, {"pos": {"H": .8, "notH": .1}, "neg": {"H": .1, "notH": .9}})   # H column sums to .9


def model(p_h, unit="eu"):
    return {"prior": {"H": p_h, "notH": 1 - p_h}, "utilities": U, "utility_unit": unit, "prior_source": "declared", "utility_source": "declared"}


def edge(kind, d, g):
    return {"kind": kind, "decision_ref": ref(d), "independent_group": g, "provenance": "curator"}


def test_unlock_value_does_not_double_count_descendants():
    decisions = {"D1": model(0.6), "D2": model(0.9), "D3": model(0.9)}          # EVPI 6, 2, 2
    edges = [edge("logical_necessity", "D1", "g1"), edge("empirical_relevance", "D1", "g1"),   # two routes to ONE decision
             edge("logical_necessity", "D2", "g1"),                                              # descendant of the same result
             edge("empirical_relevance", "D3", "g2"),
             edge("proposed_connection", "D4", "g3")]                                            # an analogy never counts
    r = voi.unlock_value(edges, decisions)
    # groups: g1 -> max(6,2)=6 ; g2 -> 2.  total 8 (naive sum over edges would give 6+6+2+2=16, over decisions 10)
    assert r["value"] == pytest.approx(8.0) and r["unit"] == "eu"
    assert r["proposed_only_decisions"] == ["D4"] and r["n_decisions_estimated"] == 3


def test_unlock_value_lower_bound_and_units():
    r = voi.unlock_value([edge("logical_necessity", "D1", "g1"), edge("logical_necessity", "DX", "g2")], {"D1": model(0.6)})
    assert r["value"] == pytest.approx(6.0) and r["unestimated"] == ["DX"] and any("lower bound" in c for c in r["caveats"])
    r2 = voi.unlock_value([edge("logical_necessity", "D1", "g1"), edge("logical_necessity", "D2", "g2")], {"D1": model(0.6, "eu"), "D2": model(0.9, "hours")})
    assert r2["value"] is None
    assert voi.unlock_value([edge("logical_necessity", "Z", "g")], {})["value"] is None


# ------------------------------------------------------------------ cards and lenses
def make_card(profile=None, signals=(), states=None, decisions=None, problem=None, now="2026-10-31T16:00:00Z"):
    return cardmod.build_card(problem or {"id": "P1", "depends_on": [], "needs": []}, profile or good_profile(), decisions={"D1": model(0.6)} if decisions is None else decisions,
                              signals=list(signals), problem_states=states or {}, now=now)


def test_card_newly_actionable_and_blocking():
    c = make_card()
    assert c["bounded"] and c["ready"] and c["consequence"]["value"] == pytest.approx(6.0)
    assert set(c["lenses"]) >= {"newly_actionable", "blocking_downstream", "neglected_important"}
    assert "exploratory" not in c["lenses"]


def test_unresolved_dependency_blocks_readiness():
    c = make_card(problem={"id": "P1", "depends_on": ["P0"], "needs": []}, states={"P0": "open"})
    assert not c["ready"] and c["blocked_on"] == ["P0"] and "newly_actionable" not in c["lenses"]
    assert make_card(problem={"id": "P1", "depends_on": ["P0"], "needs": []}, states={"P0": "resolved"})["ready"]


def test_active_lease_removes_actionable_and_neglected_and_expired_lease_does_not_count():
    lease = {"operator": "w1", "status": "running", "leased_at": "2026-10-31T15:00:00Z", "expires_at": "2026-10-31T18:00:00Z", "last_progress_at": "2026-10-31T15:30:00Z"}
    p = good_profile(); p["working"] = [lease]
    c = make_card(p)
    assert c["active_leases"] == 1 and not {"newly_actionable", "neglected_important"} & set(c["lenses"])
    assert make_card(p, now="2026-10-31T19:00:00Z")["active_leases"] == 0
    p["working"] = [dict(lease, status="submitted")]
    assert "seeking_review" in make_card(p)["lenses"]


def test_signals_count_operators_not_accounts_and_retraction_needs_same_operator():
    s1 = sig("following", {}, "f1", "opA"); s2 = sig("following", {}, "f2", "opA"); s3 = sig("following", {}, "f3", "opB")
    assert make_card(signals=[s1, s2, s3])["followers"] == ["opA", "opB"]                    # two accounts of opA = one voice
    retract_ok = sig("following", {}, "r1", "opA", retracts="f1")
    retract_other = sig("following", {}, "r2", "opB", retracts="f2")
    sigs = cardmod.active_signals([s1, s2, s3, retract_ok, retract_other])
    assert sorted(s["id"] for s in sigs) == ["f2", "f3"]
    assert "f1" not in {s["id"] for s in sigs} and "f2" in {s["id"] for s in sigs}           # opB cannot retract opA's signal


def test_no_decision_model_means_exploratory_and_no_invented_value():
    c = make_card(decisions={})
    assert c["consequence"]["value"] is None and "exploratory" in c["lenses"] and "newly_actionable" in c["lenses"]
    assert "not calibrated" in c["calibration_of_priors"]


def test_capability_match_is_exact_and_resolved_problem_has_no_lens():
    c = make_card(problem={"id": "P1", "depends_on": [], "needs": ["Lean/Mathlib expertise"]},
                  signals=[sig("can_contribute", {"capability": "lean/mathlib expertise", "availability": "10h", "proposed_task": "freeze target"})])
    assert c["staffed"] and c["contributors"] == ["opA"]
    assert make_card(problem={"id": "P1", "depends_on": [], "needs": ["Lean"]})["unmet_needs"] == ["Lean"]
    assert make_card(states={"P1": "resolved"})["lenses"] == {}


# ------------------------------------------------------------------ resources, attention, credit
def test_resource_states_hand_example():
    s = credit.new_offer(10, "h")
    with pytest.raises(credit.ResourceError):
        credit.reserve(s, "A", 5)                                   # offered != availability_checked
    s = credit.reserve(credit.mark_checked(s), "A", 6)
    with pytest.raises(credit.ResourceError):
        credit.reserve(s, "B", 5)                                   # 6+5 > 10
    s = credit.consume(s, "A", 4)
    with pytest.raises(credit.ResourceError):
        credit.consume(s, "A", 3)                                   # 4+3 > reserved 6
    s = credit.release(s, "A")                                      # releases reserved-consumed = 2
    assert s["reservations"]["A"] == {"reserved": 6.0, "consumed": 4.0, "released": 2.0}
    assert credit.available(s) == pytest.approx(10 - 6 + 2)         # 6 hours back in the pool
    r = credit.reconcile({"unit": "h", "amount": 5}, s["reservations"]["A"], "declared")
    assert r["overrun_vs_estimate"] == -1 and r["consumption_status"] == "declared, unverified"


def test_attention_credits_bounds_merge_and_verification():
    rows = [{"operator": "X", "verified": True, "problem_id": "P1", "credits": 4}, {"operator": "X", "verified": True, "problem_id": "P1", "credits": 4}]
    with pytest.raises(credit.AllocationError):
        credit.allocate_attention(10, 6, rows)                      # splitting 8 across two rows cannot dodge the cap of 6
    with pytest.raises(credit.AllocationError):
        credit.allocate_attention(10, 6, [{"operator": "X", "verified": True, "problem_id": p, "credits": 6} for p in ("P1", "P2")])   # 12 > budget 10
    ok = credit.allocate_attention(10, 6, [{"operator": "X", "verified": True, "problem_id": "P1", "credits": 3},
                                           {"operator": "Y", "verified": True, "problem_id": "P1", "credits": 1},
                                           {"operator": "Z", "verified": False, "problem_id": "P1", "credits": 5}])
    assert ok["per_problem"]["P1"]["credits"] == 4 and ok["per_problem"]["P1"]["n_operators"] == 2
    assert ok["per_problem"]["P1"]["max_operator_share"] == pytest.approx(0.75) and ok["unverified_operators_not_counted"] == ["Z"]


def test_contribution_credit_counts_only_independently_accepted_work():
    ev_ = [{"operator": "a", "kind": "negative_result", "action_ref": "1", "reviewer_operator": "b", "accepted": True},
           {"operator": "a", "kind": "accepted_result", "action_ref": "2", "reviewer_operator": "a", "accepted": True},     # self-accepted
           {"operator": "a", "kind": "replication", "action_ref": "3", "reviewer_operator": "b", "accepted": False},
           {"operator": "c", "kind": "consolidation", "action_ref": "4", "reviewer_operator": None, "accepted": True}]
    r = credit.contribution_credit(ev_)
    assert r["counts"] == {"a": {**{k: 0 for k in credit.CREDIT_KINDS}, "negative_result": 1}} and r["totals"] is None
    assert [x["reason"] for x in r["not_counted"]] == ["accepted by its own operator", "not accepted", "no recorded reviewer"]
    w = {k: 1 for k in credit.CREDIT_KINDS}
    assert credit.contribution_credit(ev_, w)["totals"] == {"a": 1}
    with pytest.raises(credit.AllocationError):
        credit.contribution_credit(ev_, {"accepted_result": 1})


# ------------------------------------------------------------------ forecasting
NOW = "2026-10-31T20:00:00Z"


def spec(i, horizon="2026-10-31T19:00:00Z"):
    return {"id": i, "horizon": horizon}


def fc(sid, who, fam, p, at="2026-10-31T10:00:00Z"):
    return {"spec_id": sid, "forecaster": who, "family": fam, "probability": p, "submitted_at": at}


def rs(sid, o, at="2026-10-31T15:00:00Z", resolver="rev"):
    return {"spec_id": sid, "outcome": o, "resolved_at": at, "resolver": resolver}


def test_score_events_hand_example_and_selection_accounting():
    specs = [spec("e1"), spec("e2"), spec("e3"), spec("e4"), spec("e5", "2026-10-31T23:00:00Z"), spec("e6")]
    res = [rs("e1", 1), rs("e2", 0), rs("e3", 1), rs("e4", "void")]          # e5 pending, e6 expired unresolved
    A = [fc("e1", "A", "x", .8), fc("e2", "A", "x", .3), fc("e3", "A", "x", .6)]
    B = [fc(s, "B", "y", .5) for s in ("e1", "e2", "e3")]
    r = forecasting.score_events(specs, A + B, res, NOW)
    assert r["event_status"] == {"resolved": 3, "void": 1, "expired_unresolved": 1, "pending": 1}
    # Brier A = ((.8-1)^2 + (.3-0)^2 + (.6-1)^2)/3 = (.04+.09+.16)/3 ; B = .25
    assert r["per_forecaster"]["A"]["brier"] == pytest.approx(0.29 / 3) and r["per_forecaster"]["B"]["brier"] == pytest.approx(0.25)
    assert "1 void and 1 expired-unresolved" in r["selection_note"]
    assert r["reference"]["brier_p0.5"] == pytest.approx(0.25)
    assert r["calibration_summary_for_cards"]["calibrated_claim_allowed"] is False
    assert r["aggregates"]["mean"]["brier"] == pytest.approx(np.mean([(.65 - 1) ** 2, (.4 - 0) ** 2, (.55 - 1) ** 2]))


def test_late_forecast_and_resolver_conflict_are_excluded_not_scored():
    specs = [spec("e1"), spec("e2")]
    res = [rs("e1", 1, at="2026-10-31T12:00:00Z"), rs("e2", 1, resolver="A")]
    f = [fc("e1", "A", "x", .9, at="2026-10-31T13:00:00Z"), fc("e1", "B", "y", .6, at="2026-10-31T09:00:00Z"), fc("e2", "A", "x", .9), fc("e2", "B", "y", .1)]
    r = forecasting.score_events(specs, f, res, NOW)
    assert r["excluded"]["late_forecast"] == [("e1", "A")] and r["excluded"]["resolver_conflict"] == ["e2"]
    assert set(r["per_forecaster"]) == {"B"} and r["per_forecaster"]["B"]["brier"] == pytest.approx(0.16)    # only e1: (.6-1)^2


def test_family_first_mean_hand_example():
    P = np.array([[.8], [.6], [.2]])
    # family x = mean(.8,.6)=.7 ; family y = .2 ; family-first = .45 ; plain mean = (.8+.6+.2)/3 = .5333
    assert forecasting.family_first_mean(P, ["x", "x", "y"])[0] == pytest.approx(0.45)
    assert P.mean() == pytest.approx(0.5333, abs=1e-4)


def test_no_resolved_events_returns_reason_not_zero():
    r = forecasting.score_events([spec("e1")], [fc("e1", "A", "x", .5)], [], NOW)
    assert r["per_forecaster"] is None and r["event_status"]["expired_unresolved"] == 1


# ------------------------------------------------------------------ policies
def pcard(i, value, cost, ready=True, leases=0, resolved=False):
    return {"id": i, "ready": ready, "active_leases": leases, "resolved": resolved,
            "consequence": {"value": value}, "cost": ({"amount": cost, "unit": "u", "basis": "estimate"} if cost else None)}


def test_value_per_cost_and_budgeted_selection():
    cards = [pcard("A", 6, 2), pcard("B", 8, 4), pcard("C", None, 1), pcard("D", 5, None)]
    order = policies.value_per_cost_order(cards, ["D", "C", "B", "A"])
    assert order == ["A", "B", "D", "C"]            # A=3.0/unit, B=2.0/unit ; D (no cost) and C (no value) unranked in curator order D,C
    sel = policies.select_within_budget(order, cards, 5)
    # A(2) fits -> 2 ; B(4) 2+4>5 skipped ; D no cost ; C(1) fits -> 3
    assert sel["selected"] == ["A", "C"] and sel["spent"] == 3 and ("D", "no cost estimate") in sel["skipped"]


def test_coordinated_excludes_leased_and_unready_and_reserves_exploration():
    cards = [pcard("A", 6, 2), pcard("B", 8, 4, leases=1), pcard("C", None, 1), pcard("E", 9, 1, ready=False), pcard("R", 3, 1, resolved=True)]
    r = policies.coordinated(cards, ["A", "B", "C", "E"], budget=4, exploration_share=0.25)
    # pool = A, C (B leased, E not ready, R resolved) ; main share 3 -> A (2) ; exploration share 1 + leftover 1 = 2 -> C (1)
    assert r["selected"] == ["A", "C"] and r["excluded_not_ready_or_leased"] == ["B", "E"]
    with pytest.raises(policies.PolicyError):
        policies.value_per_cost_order([pcard("A", 1, 1), {**pcard("B", 1, 1), "cost": {"amount": 1, "unit": "other", "basis": "estimate"}}], [])


# ------------------------------------------------------------------ allocation evaluation
def frozen(values, unit="eu"):
    f = {"unit": unit, "values": values}
    f["sha256"] = ev.frozen_hash(f)
    return f


def row(arm, p, cost, accepted=True, overturned=False, dup=None, hand=False):
    return {"arm": arm, "problem_id": p, "action_id": f"{arm}-{p}", "cost": cost, "accepted": accepted, "overturned": overturned, "duplicate_of": dup, "handoff_failed": hand}


def test_evaluate_hand_example_exact_p_and_clean_win():
    probs = [f"p{i}" for i in range(1, 7)]
    f = frozen({p: 1.0 for p in probs})
    rows = [row("X", p, 2) for p in probs] + [row("Y", p, 4, accepted=False) for p in probs[:3]]        # X cost 12, Y cost 12
    r = ev.evaluate(rows, f, ["X", "Y"])
    c = r["comparisons"]["X vs Y"]
    # discordant: X-only right on 6 problems, Y-only 0 -> exact two-sided p = 2*(1/2)^6 = 0.03125
    assert c["x_only_right"] == 6 and c["p_two_sided_exact"] == pytest.approx(0.03125) and c["verdict"] == "X resolved more problems"
    assert r["per_arm"]["X"]["registered_value_resolved"] == 6.0 and r["per_arm"]["Y"]["registered_value_resolved"] == 0


def test_evaluate_not_a_clean_win_when_it_accepts_more_wrong_results():
    probs = [f"p{i}" for i in range(1, 8)]
    f = frozen({p: 1.0 for p in probs})
    rows = [row("X", p, 2, overturned=(p == "p7")) for p in probs] + [row("Y", p, 2, accepted=False) for p in probs]
    r = ev.evaluate(rows, f, ["X", "Y"])
    # X resolves 6 (p7 accepted then overturned -> unresolved), Y 0 ; p = 2*(1/2)^6 = .03125 ; X incorrect acceptance 1 > Y 0
    assert r["per_arm"]["X"]["problems_resolved"] == 6 and r["per_arm"]["X"]["incorrect_acceptance"] == 1
    assert "not a clean win" in r["comparisons"]["X vs Y"]["verdict"]


def test_evaluate_refusals_and_small_n():
    probs = [f"p{i}" for i in range(1, 7)]
    f = frozen({p: 1.0 for p in probs})
    mism = [row("X", p, 2) for p in probs] + [row("Y", p, 3, accepted=False) for p in probs]            # 12 vs 18 -> 50% spread
    r = ev.evaluate(mism, f, ["X", "Y"])
    assert r["verdict"] == "REFUSED" and "differ by 50.0%" in r["reason"]
    tampered = dict(f, values={**f["values"], "p1": 99.0})
    with pytest.raises(ev.EvalError):
        ev.evaluate([row("X", "p1", 1), row("Y", "p1", 1)], tampered, ["X", "Y"])
    small = frozen({"p1": 1.0, "p2": 1.0})
    r = ev.evaluate([row("X", "p1", 2), row("X", "p2", 2), row("Y", "p1", 4, accepted=False)], small, ["X", "Y"])
    assert "INSUFFICIENT PROBLEMS" in r["comparisons"]["X vs Y"]["verdict"]
    with pytest.raises(ev.EvalError):
        ev.evaluate([row("X", "nope", 1), row("Y", "p1", 1)], small, ["X", "Y"])


def test_evaluate_counts_duplicate_effort_and_failed_handoffs():
    f = frozen({f"p{i}": 1.0 for i in range(1, 7)})
    rows = [row("X", "p1", 3), row("X", "p1", 2, accepted=False, dup="X-p1", hand=True), row("Y", "p1", 5, accepted=False)]
    r = ev.evaluate(rows, f, ["X", "Y"])
    assert r["per_arm"]["X"]["duplicate_effort_cost"] == 2 and r["per_arm"]["X"]["failed_handoffs"] == 1


# ------------------------------------------------------------------ read-only seed pilot against the real map
def _real_seed_map():
    try:
        return subprocess.run(["git", "-C", "/data/worktrees/delphi-evolve/frontier-curation", "show",
                               "5165177:site/review/frontier-problems.json"], capture_output=True, text=True, check=True).stdout
    except Exception:
        return None


@pytest.mark.skipif(_real_seed_map() is None, reason="Frontier seed map commit not present in this checkout")
def test_real_seed_map_is_honestly_not_yet_rankable():
    d = seeds.load_seed_map(_real_seed_map())
    ids = [s["id"] for s in d["problems"]]
    assert ids == ["F001", "F002", "F003", "F004", "F005", "F006", "F007"]
    states = seeds.seed_states(d["problems"])
    assert states["F007"] == "resolved" and states["F001"] == "open"
    cards = [cardmod.build_card(seeds.problem_row(s), seeds.to_partial_profile(s), decisions={}, signals=[], problem_states=states, now=T0) for s in d["problems"]]
    assert not any(c["bounded"] for c in cards) and not any(c["ready"] for c in cards)      # prose next_action is not a bounded action
    assert all(c["consequence"]["value"] is None for c in cards)                            # no value is invented
    by = {c["id"]: c for c in cards}
    assert by["F001"]["blocked_on"] == ["F004"] and by["F006"]["blocked_on"] == ["F005"]
    assert len(seeds.seed_version(d["problems"][0])) == 64
