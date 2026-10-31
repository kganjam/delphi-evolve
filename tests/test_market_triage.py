"""Scorecard tally built on the frozen claim file. Mini freeze fixtures with hand-worked counts; no claim is actually evaluated here."""
import hashlib
import json
from pathlib import Path

import pytest

from market import desk as D
from market import triage as T

VOCAB = ["PROVED", "REFUTED_AS_STATED", "NEEDS_SCOPE_CONDITION", "NOT_ATTEMPTED"]
# 10 claims: B0 x2, B1 x2, B2 x4, B3 x2
IDS = {"B0": ["x-empirical", "x-noformal"], "B1": ["b1a", "b1b"], "B2": ["b2a", "b2b", "b2c", "b2d"], "B3": ["b3a", "b3b"]}


def freeze_file(tmp_path, counts_override=None):
    claims = [{"claim_id": c, "bucket": b, "verdict": "NOT_ATTEMPTED"} for b, cs in IDS.items() for c in cs]
    counts = {"B0": 2, "B1": 2, "B2": 4, "B3": 2, "total": 10}
    counts.update(counts_override or {})
    p = tmp_path / "freeze.json"
    p.write_text(json.dumps({"version": "v1-freeze", "frozen_at_utc": "x", "verdict_vocabulary": VOCAB, "counts": counts, "claims": claims}))
    return p


def rec(cid, verdict, **kw):
    r = {"claim_id": cid, "verdict": verdict, "lean_artifact": "lean/a.lean#h", "axioms_clean": True, "statement_reviewed_by_other": True,
         "mutants_total": 3, "mutants_rejected": 3, "anti_triviality_mutant_rejected": True}
    if verdict == "NEEDS_SCOPE_CONDITION":
        r["scope_condition"] = "finite domain, Neumann"
    if verdict == "REFUTED_AS_STATED":
        r["counterexample"] = "J=..., Du=1, Dv=1.1"
    r.update(kw)
    return r


def run(tmp_path, rows):
    claims, _ = T.load_freeze(freeze_file(tmp_path))
    return T.triage(claims, rows)


def test_hand_counts_with_downgrades_and_missing_records(tmp_path):
    rows = [rec("b1a", "PROVED"), rec("b1b", "PROVED", anti_triviality_mutant_rejected=False),   # b1b downgraded: vacuous-proof guard
            rec("b2a", "NEEDS_SCOPE_CONDITION"), rec("b2b", "REFUTED_AS_STATED"),
            rec("b2c", "PROVED", mutants_rejected=2),                                              # a mutant survived -> downgraded
            {"claim_id": "b3a", "verdict": "NOT_ATTEMPTED", "attempted": True}]
    r = run(tmp_path, rows)                                                                         # b2d, b3b, both B0 have no record
    assert r["counts"] == {"PROVED": 1, "NEEDS_SCOPE_CONDITION": 1, "REFUTED_AS_STATED": 1, "NOT_ATTEMPTED": 3,
                           "CLAIMED_BUT_UNVERIFIED": 2, "EXCLUDED_BY_RECORD": 2}
    assert set(r["downgraded_to_claimed_but_unverified"]) == {"b1b", "b2c"}
    assert "anti-triviality" in r["downgraded_to_claimed_but_unverified"]["b1b"]["missing"][0]
    assert r["detail"] == {"b3a": "attempted-and-unreached"}                                        # never 'failed'
    assert r["verified_of_evaluable"]["k"] == 3 and r["verified_of_evaluable"]["n"] == 8
    assert sorted(r["no_record"]) == ["b2d", "b3b", "x-empirical", "x-noformal"]
    assert r["by_bucket"]["B1"]["PROVED"] == 1 and r["by_bucket"]["B0"]["EXCLUDED_BY_RECORD"] == 2
    assert "thin" in r["headline"] and "3 have a verified verdict" in r["headline"]                 # 3/8 < 0.5


def test_evidence_requirements_per_verdict(tmp_path):
    cases = [("b2a", "PROVED", {"axioms_clean": False}, "clean axiom audit"),
             ("b2a", "PROVED", {"lean_artifact": ""}, "compiled artifact"),
             ("b2a", "PROVED", {"statement_reviewed_by_other": False}, "non-author statement review"),
             ("b2a", "PROVED", {"mutants_total": 0, "mutants_rejected": 0}, "mutation test"),
             ("b2a", "NEEDS_SCOPE_CONDITION", {"scope_condition": " "}, "written scope condition"),
             ("b2a", "REFUTED_AS_STATED", {"counterexample": ""}, "written counterexample")]
    for cid, v, kw, needle in cases:
        r = run(tmp_path, [rec(cid, v, **kw)])
        assert r["counts"]["CLAIMED_BUT_UNVERIFIED"] == 1, (v, kw)
        assert any(needle in m for m in r["downgraded_to_claimed_but_unverified"][cid]["missing"]), (v, kw)
    # a refutation does not need mutants, a proof does
    ok = run(tmp_path, [rec("b2a", "REFUTED_AS_STATED", mutants_total=0, mutants_rejected=0)])
    assert ok["counts"]["REFUTED_AS_STATED"] == 1


def test_b0_claims_cannot_be_given_a_verdict_and_freeze_is_binding(tmp_path):
    with pytest.raises(D.DeskError, match="excluded by its own record"):
        run(tmp_path, [rec("x-empirical", "PROVED")])
    with pytest.raises(D.DeskError, match="not in the freeze"):
        run(tmp_path, [rec("invented-claim", "PROVED")])
    with pytest.raises(D.DeskError, match="buckets are fixed"):
        run(tmp_path, [rec("b2a", "PROVED", bucket="B1")])
    with pytest.raises(D.DeskError, match="two records"):
        run(tmp_path, [rec("b2a", "PROVED"), rec("b2a", "PROVED")])
    with pytest.raises(D.DeskError, match="not in"):
        run(tmp_path, [rec("b2a", "MOSTLY_PROVED")])


def test_freeze_integrity(tmp_path):
    p = freeze_file(tmp_path)
    good = hashlib.sha256(p.read_bytes()).hexdigest()
    T.load_freeze(p, good)
    with pytest.raises(D.DeskError, match="altered"):
        T.load_freeze(p, "0" * 64)
    with pytest.raises(D.DeskError, match="disagree with its claim list"):
        T.load_freeze(freeze_file(tmp_path, {"B2": 5}))
    d = json.loads(p.read_text()); d["verdict_vocabulary"] = ["PROVED"]
    p.write_text(json.dumps(d))
    with pytest.raises(D.DeskError, match="vocabulary"):
        T.load_freeze(p)


def test_run_writes_files(tmp_path):
    rp = tmp_path / "r.jsonl"
    rp.write_text(json.dumps(rec("b2a", "PROVED")) + "\n")
    r = T.run_triage(freeze_file(tmp_path), rp, tmp_path / "o")
    assert (tmp_path / "o" / "scorecard.md").exists() and r["counts"]["PROVED"] == 1 and r["freeze"]["counts"]["total"] == 10


REAL = Path("/data/worktrees/admissible-seed/bench/bench-v1-freeze.json")


@pytest.mark.skipif(not REAL.exists(), reason="real freeze file not present on this host")
def test_parses_the_real_freeze_schema():
    claims, info = T.load_freeze(REAL)
    assert info["counts"] == {"B0": 2, "B1": 4, "B2": 11, "B3": 4, "total": 21}
    assert {c for c, v in claims.items() if v["bucket"] == "B0"} == {"turing-morphogen-hypothesis", "kimura-neutral-theory"}
    r = T.triage(claims, [])
    assert r["counts"]["EXCLUDED_BY_RECORD"] == 2 and r["counts"]["NOT_ATTEMPTED"] == 19
