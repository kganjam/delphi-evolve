"""Forecast store + legacy binary-claim report. Fixtures are literal arithmetic examples, not data."""
import itertools
import json

import numpy as np
import pytest

from market import report as R
from market import store as S


def clock():
    c = itertools.count(1)
    return lambda: f"2026-10-31T00:00:{next(c):02d}.000000+00:00"


CLAIMS = [{"claim_id": f"c{i}", "text": "t", "tier": "formal", "oracle": "lean"} for i in range(1, 5)]


def setup(tmp_path):
    ck = clock()
    S.freeze_claims(tmp_path, CLAIMS, ck)
    res = S.ResolutionStore(tmp_path / "res" / "resolutions.jsonl")
    return S.ForecastStore(tmp_path, res, ck), res, ck


def sub(fs, claim, agent, p, arm="C", attempt=0, fam="m1", guild="g", tin=10, tout=5):
    return fs.submit(claim_id=claim, agent_id=agent, guild=guild, model_family=fam, arm=arm, probability=p, tokens_in=tin, tokens_out=tout, attempt=attempt)


def test_freeze_rejects_outcomes_and_overwrite(tmp_path):
    with pytest.raises(S.StoreError, match="outcome-like"):
        S.freeze_claims(tmp_path / "a", [dict(CLAIMS[0], outcome=1)])
    S.freeze_claims(tmp_path / "b", CLAIMS)
    with pytest.raises(S.StoreError, match="already frozen"):
        S.freeze_claims(tmp_path / "b", CLAIMS)


def test_submit_validation_and_immutability(tmp_path):
    fs, res, _ = setup(tmp_path)
    sub(fs, "c1", "a1", 0.7)
    with pytest.raises(S.DuplicateForecast):
        sub(fs, "c1", "a1", 0.2)
    for bad in (1.1, -0.1, float("nan"), True, "0.5"):
        with pytest.raises(S.StoreError):
            sub(fs, "c2", "a1", bad)
    with pytest.raises(S.StoreError, match="not in the frozen"):
        sub(fs, "zz", "a1", 0.5)
    with pytest.raises(S.StoreError):
        sub(fs, "c2", "a1", 0.5, tin=-1)
    sub(fs, "c1", "a1", 0.2, attempt=1)  # a new attempt is a new record, not an edit
    assert len(fs.forecasts()) == 2


def test_no_forecast_after_reveal_and_tamper_detection(tmp_path):
    fs, res, ck = setup(tmp_path)
    sub(fs, "c1", "a1", 0.7)
    res.reveal({"c1", "c2", "c3", "c4"}, "c1", 1, "lean", "lean/proof1.lean", ck)
    with pytest.raises(S.LateForecast):
        sub(fs, "c1", "a2", 0.5)
    with pytest.raises(S.StoreError, match="immutable"):
        res.reveal({"c1"}, "c1", 0, "lean", "x", ck)
    assert fs.verify()["n_forecasts"] == 1
    lines = fs.forecast_path.read_text().splitlines()
    rec = json.loads(lines[0]); rec["probability"] = 0.99
    fs.forecast_path.write_text(json.dumps(rec, sort_keys=True) + "\n")
    with pytest.raises(S.ChainError, match="edited"):
        fs.verify()


def full_store(tmp_path, tokens=(100, 100, 100)):
    """4 claims, outcomes 1,0,1,0; arm A: 1 agent x2 attempts; arm B: 3 samples; arm C: 3 guilds in 3 families."""
    fs, res, ck = setup(tmp_path)
    plan = {
        ("A", "a", 0): [0.6, 0.4, 0.6, 0.4], ("A", "a", 1): [0.7, 0.3, 0.7, 0.3],
        ("B", "b1", 0): [0.7, 0.3, 0.6, 0.4], ("B", "b2", 0): [0.7, 0.3, 0.6, 0.4], ("B", "b3", 0): [0.7, 0.3, 0.6, 0.4],
        ("C", "g1", 0): [0.9, 0.2, 0.4, 0.6], ("C", "g2", 0): [0.6, 0.1, 0.9, 0.3], ("C", "g3", 0): [0.5, 0.4, 0.7, 0.2],
    }
    for (arm, ag, att), ps in plan.items():
        for i, p in enumerate(ps):
            tok = tokens[{"A": 0, "B": 1, "C": 2}[arm]]
            sub(fs, f"c{i + 1}", ag, p, arm=arm, attempt=att, fam={"A": "m1", "B": "m1", "C": "m" + ag[-1]}[arm], guild=ag, tin=tok, tout=0)
    for i, o in enumerate([1, 0, 1, 0]):
        res.reveal({c["claim_id"] for c in CLAIMS}, f"c{i + 1}", o, "lean", f"ev{i}", ck)
    return fs, res


def test_report_end_to_end_matches_hand_numbers(tmp_path):
    fs, res = full_store(tmp_path, tokens=(100, 100, 100))
    # token totals: A 2 attempts x4 claims x100 = 800; B 3x4x100 = 1200; C 3x4x100 = 1200 -> A vs others refused, B vs C compared
    rep, extra, md = R.run_report(tmp_path, res.path, tmp_path / "out")
    c = rep["arms"]["C"]["diversity_decomposition_mean_aggregator"]
    P = np.array([[.9, .2, .4, .6], [.6, .1, .9, .3], [.5, .4, .7, .2]]); o = np.array([1, 0, 1, 0.0])
    crowd = P.mean(0)
    assert c["crowd_brier"] == pytest.approx(np.mean((crowd - o) ** 2))
    assert c["diversity"] == pytest.approx(np.mean((P - crowd) ** 2))
    assert c["crowd_brier"] == pytest.approx(c["mean_individual_brier"] - c["diversity"], abs=1e-12)
    assert rep["comparisons"]["C_vs_A"]["status"] == "REFUSED_BUDGET_MISMATCH"
    assert rep["comparisons"]["B_vs_A"]["status"] == "REFUSED_BUDGET_MISMATCH"
    assert rep["comparisons"]["C_vs_B"]["status"] == "COMPARED"
    assert "BEST" in rep["theorem_limit"] and "BEST" in md
    for f in ("report.json", "report.md", "slide.md", "per_claim.json", "reliability_arms.png"):
        assert (tmp_path / "out" / f).exists()
    json.loads((tmp_path / "out" / "report.json").read_text())


def test_report_refuses_late_forecast_in_ledger(tmp_path):
    fs, res = full_store(tmp_path)
    # forge a forecast timestamped after the reveal by rewriting the chain honestly (as a careless pipeline might)
    recs = fs.forecasts()
    last = recs[-1]
    body = {k: v for k, v in last.items() if k != "hash"}
    body["timestamp"] = "2026-10-31T23:59:59.000000+00:00"
    body["hash"] = S.sha256(S.canon(body))
    recs[-1] = body
    fs.forecast_path.write_text("\n".join(json.dumps(r, sort_keys=True) for r in recs) + "\n")
    with pytest.raises(S.LateForecast, match="at/after"):
        R.run_report(tmp_path, res.path)
