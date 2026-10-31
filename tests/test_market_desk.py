"""Scope Desk evaluation tests. Fixtures are literal, hand-worked examples (and clearly simulated power fixtures built
in the test only); none of it is data and none is reported as a result."""
import json
import math

import numpy as np
import pytest

from market import desk as D

V = ("applies", "out_of_scope", "underdetermined")


def P(a, o, u):
    return {"applies": a, "out_of_scope": o, "underdetermined": u}


KEY = [  # id, verdict, conds, family
    ("a1", "applies", [], "f1"), ("a2", "out_of_scope", ["BC_NEUMANN"], "f1"),
    ("b1", "applies", [], "f2"), ("b2", "out_of_scope", ["DOMAIN_ADMISSIBLE_MODE"], "f2"),
    ("c1", "applies", [], "f3"), ("c2", "underdetermined", ["BC_UNSTATED"], "f3"),
    ("d1", "applies", [], "f4"), ("d2", "out_of_scope", ["LARGE_DOMAIN"], "f4"),
]
# arm X answers: (verdict, p, diagnosis conds); d1 is unanswered
X = {
    "a1": ("applies", P(.7, .2, .1), []), "a2": ("out_of_scope", P(.1, .8, .1), ["BC_NEUMANN"]),
    "b1": ("out_of_scope", P(.2, .7, .1), ["BC_NEUMANN"]), "b2": ("applies", P(.6, .3, .1), []),
    "c1": ("underdetermined", P(.1, .2, .7), ["BC_UNSTATED"]), "c2": ("underdetermined", P(.1, .1, .8), ["BC_UNSTATED"]),
    "d2": ("out_of_scope", P(.2, .6, .2), ["NEAR_ONSET"]),
}


def write(tmp, name, rows):
    p = tmp / name
    p.write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    return p


def mk(tmp, arms: dict, ledger=None, key=KEY, strata=None, units=None, repairs=None):
    kp = write(tmp, "key.jsonl", [{"id": i, "verdict": v, "condition_ids": c} for i, v, c, _ in key])
    ip = write(tmp, "inst.jsonl", [{"id": i, "family": f, "stratum": (strata or {}).get(i, "formal"), "hidden": {"benign": v == "applies"}} for i, v, c, f in key])
    rows = []
    for arm, ans in arms.items():
        for i, (v, p, conds) in ans.items():
            rows.append({"id": i, "arm": arm, "verdict": v, "p": p, "diagnosis": {"condition_ids": conds}})
    rows += units or []
    ap = write(tmp, "answers.jsonl", rows)
    lp = write(tmp, "ledger.jsonl", ledger) if ledger else None
    rp = write(tmp, "repairs.jsonl", repairs) if repairs else None
    return dict(key_path=kp, answers_path=ap, instances_path=ip, ledger_path=lp, repairs_path=rp)


def test_hand_computed_metrics(tmp_path):
    rep, _ = D.run_desk(**mk(tmp_path, {"X": X}))
    h = rep["arms"]["X"]["headline"]
    assert h["accuracy"]["value"] == pytest.approx(4 / 8)            # a1,a2,c2,d2 correct; unanswered d1 wrong
    assert (h["false_alarm_rate"]["k"], h["false_alarm_rate"]["n"]) == (3, 4)  # b1, c1, and unanswered d1
    assert h["false_alarm_rate"]["value"] == pytest.approx(0.75)
    assert h["false_reassurance_rate"]["value"] == pytest.approx(1 / 3)  # b2 answered applies
    assert h["right_flag_rate"]["value"] == pytest.approx(2 / 3)
    assert h["brier3"]["value"] == pytest.approx(3.84 / 7)             # worked by hand: .14+.06+1.14+.86+1.34+.06+.24
    ll = [-math.log(x) for x in (.7, .8, .2, .3, .1, .8, .6)]
    assert h["log_loss3"]["value"] == pytest.approx(sum(ll) / 7)
    assert h["coverage_answered"] == pytest.approx(7 / 8) and h["n_valid_p"] == 7
    assert (h["diagnosis_exact"]["k"], h["diagnosis_exact"]["n"]) == (1, 2)  # a2 exact; d2 wrong condition
    assert h["repair_success"]["status"].startswith("NOT_SCORED")
    assert h["confusion_key_by_answer"]["applies"]["out_of_scope"] == 1 and h["confusion_key_by_answer"]["applies"][""] == 1
    # cry-wolf reference is visible: always out_of_scope false-alarms on every applies item
    assert h["trivial_policies"]["always_out_of_scope"]["false_alarm_rate"] == 1.0
    assert h["trivial_policies"]["always_out_of_scope"]["accuracy"] == pytest.approx(3 / 8)


def test_binary_applies_forecast(tmp_path):
    rep, _ = D.run_desk(**mk(tmp_path, {"X": X}))
    b = rep["arms"]["X"]["headline"]["binary_applies"]
    pa = np.array([.7, .1, .2, .6, .1, .1, .2])
    ev = np.array([1, 0, 1, 0, 1, 0, 0.0])
    assert b["brier"] == pytest.approx(np.mean((pa - ev) ** 2))
    assert b["auc_p_applies_ranks_applies_above_not"] == pytest.approx(ST_auc(pa[ev == 1], pa[ev == 0]))


def ST_auc(pos, neg):
    return np.mean([(p > n) + 0.5 * (p == n) for p in pos for n in neg])


def test_invalid_probabilities_excluded_not_invented(tmp_path):
    bad = dict(X)
    bad["a1"] = ("applies", {"applies": .9, "out_of_scope": .3, "underdetermined": .1}, [])  # sums to 1.3
    rep, _ = D.run_desk(**mk(tmp_path, {"X": bad}))
    h = rep["arms"]["X"]["headline"]
    assert h["n_valid_p"] == 6 and h["accuracy"]["value"] == pytest.approx(4 / 8)
    assert h["brier3"]["value"] == pytest.approx((3.84 - .14) / 6)


def test_arm_comparison_budget_gate_and_identical_arms_are_null(tmp_path):
    ledger_ok = [{"arm": "X", "total_tokens": 1000}, {"arm": "Y", "tokens_in": 600, "tokens_out": 400, "tool_tokens": 30}]
    rep, _ = D.run_desk(**mk(tmp_path, {"X": X, "Y": X}, ledger=ledger_ok))
    # primary comparison arms C/C0 absent => explicitly not run, no claim
    assert rep["comparisons"]["C_vs_C0"]["status"] == "NOT_RUN_ARM_MISSING"
    assert "NOT establish" not in rep["headline"]["slide_markdown"] and "not available" in rep["headline"]["slide_markdown"]


def test_matched_vs_refused_and_null_headline(tmp_path):
    ans = {"C": X, "C0": X}
    t1 = tmp_path / "ok"; t1.mkdir()
    rep, _ = D.run_desk(**mk(t1, ans, ledger=[{"arm": "C", "total_tokens": 1000}, {"arm": "C0", "total_tokens": 1030}]))
    e = rep["comparisons"]["C_vs_C0"]
    assert e["status"] == "COMPARED_MATCHED_BUDGET"
    assert e["accuracy"]["x_minus_y"] == 0.0 and e["accuracy"]["verdict"].startswith("INSUFFICIENT FAMILIES")  # only 4 families in this hand fixture
    assert "does NOT establish" in rep["headline"]["slide_markdown"]  # an identical pair yields a legible null
    t2 = tmp_path / "bad"; t2.mkdir()
    rep2, _ = D.run_desk(**mk(t2, ans, ledger=[{"arm": "C", "total_tokens": 1000}, {"arm": "C0", "total_tokens": 1100}]))
    assert rep2["comparisons"]["C_vs_C0"]["status"] == "REFUSED_BUDGET_MISMATCH"
    assert "accuracy" not in rep2["comparisons"]["C_vs_C0"]
    t3 = tmp_path / "noledger"; t3.mkdir()
    rep3, _ = D.run_desk(**mk(t3, ans))
    assert rep3["comparisons"]["C_vs_C0"]["status"] == "REFUSED_NO_LEDGER"


def test_exempt_deterministic_arm_compared_but_labelled(tmp_path):
    rep, _ = D.run_desk(**mk(tmp_path, {"C": X, "B0": X}))
    assert rep["comparisons"]["C_vs_B0"]["status"] == "COMPARED_UNMATCHED_BASELINE_EXEMPT_ARM"


def _sim_items(n_fam=12, per=10):
    key = []
    for f in range(n_fam):
        for k in range(per):
            v = "applies" if k % 3 == 0 else ("out_of_scope" if k % 3 == 1 else "underdetermined")
            key.append((f"i{f}-{k}", v, ["BC_NEUMANN"] if v != "applies" else [], f"fam{f}"))
    return key


def _answers(key, rng, acc):
    out = {}
    for i, v, c, _ in key:
        right = rng.uniform() < acc
        ans = v if right else rng.choice([x for x in V if x != v])
        p = [0.05, 0.05, 0.05]; p[V.index(ans)] = 0.9
        out[i] = (ans, dict(zip(V, p)), c)
    return out


def test_engine_detects_a_real_difference_and_not_a_null(tmp_path):
    """SIMULATED power fixture: confirms the verdict rule can say 'better' and can say 'no difference'."""
    rng = np.random.default_rng(3)
    key = _sim_items()
    strong, weak, twin = _answers(key, rng, 0.97), _answers(key, rng, 0.30), _answers(key, rng, 0.97)
    ledger = [{"arm": a, "total_tokens": 1000} for a in ("C", "C0", "PL")]
    rep, _ = D.run_desk(**mk(tmp_path, {"C": strong, "C0": weak, "PL": twin}, ledger=ledger, key=key))
    assert rep["comparisons"]["C_vs_C0"]["accuracy"]["verdict"] == "arm C BETTER than arm C0"
    assert rep["comparisons"]["C_vs_C0"]["false_alarm_rate"]["verdict"] == "arm C BETTER than arm C0"
    assert "SUPPORTS a commons benefit" in rep["headline"]["slide_markdown"]
    # two equally good arms that differ by a few random errors: no detectable difference
    assert rep["comparisons"]["C_vs_PL"]["accuracy"]["verdict"].startswith("NO DETECTABLE DIFFERENCE")
    assert rep["comparisons"]["C_vs_PL"]["accuracy"]["mcnemar"]["p_two_sided_exact"] >= 0.0


def test_reversed_direction_says_the_commons_hurt(tmp_path):
    rng = np.random.default_rng(4)
    key = _sim_items()
    strong, weak = _answers(key, rng, 0.97), _answers(key, rng, 0.30)
    ledger = [{"arm": a, "total_tokens": 1000} for a in ("C", "C0")]
    rep, _ = D.run_desk(**mk(tmp_path, {"C": weak, "C0": strong}, ledger=ledger, key=key))
    assert rep["comparisons"]["C_vs_C0"]["accuracy"]["verdict"] == "arm C0 BETTER than arm C"
    assert "does NOT establish" in rep["headline"]["slide_markdown"]


def test_descriptive_stratum_not_in_headline(tmp_path):
    strata = {"a1": "descriptive", "a2": "descriptive"}
    rep, _ = D.run_desk(**mk(tmp_path, {"X": X}, strata=strata))
    assert rep["items"]["n_headline_items"] == 6 and rep["items"]["by_stratum"]["descriptive"] == 2
    assert "descriptive" in rep["arms"]["X"]["by_stratum"]


def test_repair_success_uses_oracle_verdicts_only(tmp_path):
    repairs = [{"arm": "X", "id": "a2", "repair_ok": True}, {"arm": "X", "id": "d2", "repair_ok": False}]
    rep, _ = D.run_desk(**mk(tmp_path, {"X": X}, repairs=repairs))
    r = rep["arms"]["X"]["headline"]["repair_success"]
    assert (r["k"], r["n"]) == (1, 3)  # denominator is all 3 KEY out_of_scope items


def test_fail_closed_inputs(tmp_path):
    args = mk(tmp_path, {"X": X})
    sha = tmp_path / "KEY.sha256"
    sha.write_text("0" * 64 + "  key.jsonl\n")
    with pytest.raises(D.DeskError, match="altered key"):
        D.run_desk(**args, sha_path=sha)
    import hashlib
    sha.write_text(hashlib.sha256(args["key_path"].read_bytes()).hexdigest() + "  key.jsonl\n")
    rep, _ = D.run_desk(**args, sha_path=sha)
    assert rep["key"]["sha256_verified_against_file"] is True
    rows = [json.loads(l) for l in args["answers_path"].read_text().splitlines()]
    rows.append({"id": "zz", "arm": "X", "verdict": "applies"})
    args["answers_path"].write_text("\n".join(json.dumps(r) for r in rows))
    with pytest.raises(D.DeskError, match="unknown instance"):
        D.run_desk(**args)
    rows[-1] = rows[0]
    args["answers_path"].write_text("\n".join(json.dumps(r) for r in rows))
    with pytest.raises(D.DeskError, match="duplicate"):
        D.run_desk(**args)
    with pytest.raises(D.DeskError, match="token field"):
        D.desk_budgets([{"arm": "X", "note": "no tokens"}])


def test_unit_appendix_zero_diversity_when_units_identical(tmp_path):
    units = []
    for u in ("u1", "u2"):
        for i, (v, p, c) in X.items():
            units.append({"id": i, "arm": "P", "role": "unit", "agent_id": u, "model_family": "m", "verdict": v, "p": p})
    # complete coverage needed: add d1
    for u in ("u1", "u2"):
        units.append({"id": "d1", "arm": "P", "role": "unit", "agent_id": u, "model_family": "m", "verdict": "applies", "p": P(.5, .3, .2)})
    rep, _ = D.run_desk(**mk(tmp_path, {"X": X}, units=units))
    app = rep["unit_appendix_diversity_and_family_error_correlation"]["P"]
    assert app["decomposition_on_p_applies"]["diversity"] == pytest.approx(0.0, abs=1e-20)
    assert "BEST" in app["note"]
    # derived output for arm P from units (mean-probability pooling), flagged as derived
    assert "P" in rep["output_derivations"] and "P" in rep["arms"]


def test_outputs_written_and_json_strict(tmp_path):
    out = tmp_path / "out"
    D.run_desk(**mk(tmp_path, {"X": X}), out_dir=out)
    for f in ("desk_report.json", "desk_report.md", "slide.md", "reliability_p_applies.png"):
        assert (out / f).exists()
    json.loads((out / "desk_report.json").read_text())  # strict JSON, no NaN


def test_excluded_source_claims_abort_scoring(tmp_path):
    args = mk(tmp_path, {"X": X})
    rows = [json.loads(l) for l in args["key_path"].read_text().splitlines()]
    rows[0]["source_claim_id"] = "kimura-neutral-theory"
    args["key_path"].write_text("\n".join(json.dumps(r) for r in rows))
    with pytest.raises(D.DeskError, match="excluded source claim"):
        D.run_desk(**args)
    rows[0]["source_claim_id"] = "turing-ddi"  # an allowed source is fine
    args["key_path"].write_text("\n".join(json.dumps(r) for r in rows))
    D.run_desk(**args)


def test_headline_keeps_evidence_columns_separate_and_flags_few_families(tmp_path):
    strata = {"a1": "simulated", "a2": "simulated", "b1": "simulated", "b2": "simulated"}
    rep, _ = D.run_desk(**mk(tmp_path, {"X": X}, strata=strata))
    md = rep["headline"]["slide_markdown"]
    assert "X / formal" in md and "X / simulated" in md and "X / pooled" in md
    assert "PROVED" in md and "SIMULATED" in md
    assert "Prove2Me" in md and "Not claimed as ours" in md
    assert "Only 4 independent families" in rep["limitations"][0]
    sim = rep["arms"]["X"]["by_stratum"]["simulated"]
    assert sim["n_items"] == 4 and sim["false_alarm_rate"]["k"] == 1 and sim["false_alarm_rate"]["n"] == 2  # b1 only; a1 correct


def test_textbook_arm_error_rate_is_reported(tmp_path):
    txt = {i: (("applies" if v == "applies" else "applies"), P(.9, .05, .05), []) for i, v, c, f in KEY}  # naive: always applies
    rep, _ = D.run_desk(**mk(tmp_path, {"TXT": txt}))
    t = rep["arms"]["TXT"]["headline"]
    assert t["accuracy"]["value"] == pytest.approx(4 / 8) and t["false_reassurance_rate"]["value"] == 1.0
    assert "How often does the textbook criterion mispredict" in rep["headline"]["slide_markdown"]


def test_cry_nothing_is_wrong_desk_cannot_win_on_false_alarms_alone(tmp_path):
    """C answers 'applies' everywhere (zero false alarms, total false reassurance); C0 is a competent desk."""
    rng = np.random.default_rng(5)
    key = _sim_items()
    good = _answers(key, rng, 0.9)
    lazy = {i: ("applies", {"applies": .9, "out_of_scope": .05, "underdetermined": .05}, []) for i, *_ in key}
    ledger = [{"arm": a, "total_tokens": 1000} for a in ("C", "C0")]
    rep, _ = D.run_desk(**mk(tmp_path, {"C": lazy, "C0": good}, ledger=ledger, key=key))
    e = rep["comparisons"]["C_vs_C0"]
    assert e["false_alarm_rate"]["verdict"] == "arm C BETTER than arm C0"      # looks great on its own...
    assert e["false_reassurance_rate"]["verdict"] == "arm C0 BETTER than arm C"  # ...and is exposed here
    assert e["accuracy"]["verdict"] == "arm C0 BETTER than arm C"
    assert "does NOT establish" in rep["headline"]["slide_markdown"]
