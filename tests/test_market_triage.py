"""Scorecard tally: literal fixtures with hand-worked counts. No claim is actually evaluated here."""
import json

import pytest

from market import desk as D
from market import triage as T


def hold(cid, dom, bucket="holds_as_stated", **kw):
    r = {"claim_id": cid, "domain": dom, "bucket": bucket, "lean_artifact": "lean/x.lean#abc", "axioms_clean": True,
         "mutants_total": 4, "mutants_rejected": 4, "statement_reviewed_by_other": True}
    if bucket == "holds_with_supplied_scope":
        r["scope_condition"] = "domain length L = pi, Neumann modes"
    r.update(kw)
    return r


def other(cid, dom, bucket, reason="no canonical formalization"):
    return {"claim_id": cid, "domain": dom, "bucket": bucket, "reason": reason}


def table():
    rows = [hold(f"pg{i}", "popgen") for i in range(6)]                                   # 6 as stated
    rows += [hold(f"pg{i}", "popgen", "holds_with_supplied_scope") for i in (6, 7, 8)]    # 3 with scope
    rows += [hold("pg9", "popgen", mutants_rejected=3)]                                   # a mutant survived -> downgrade
    rows += [hold("pg10", "popgen", statement_reviewed_by_other=False)]                   # unreviewed -> downgrade
    rows += [hold("pg11", "popgen", axioms_clean=False)]                                  # sorry -> downgrade
    rows += [hold("pg12", "popgen", "holds_with_supplied_scope", scope_condition="")]     # scope not written -> downgrade
    rows += [other(f"pg{i}", "popgen", "unresolved", "ran out of time") for i in (13, 14)]
    rows += [other(f"pg{i}", "popgen", "empirical_not_formalizable", "empirical") for i in (15, 16)]
    rows += [other("kimura-neutral-theory", "popgen", "empirical_not_formalizable", "calls itself empirical")]  # 18 popgen
    rows += [hold("turing-ddi", "turing", "holds_with_supplied_scope"), other("turing-wavelength", "turing", "unresolved", "no proof yet"),
             other("turing-morphogen-hypothesis", "turing", "empirical_not_formalizable")]
    return rows


def test_hand_counts_and_downgrades_are_visible():
    r = T.triage(table())
    assert r["n_claims"] == 21 and r["total_matches_expected"] and r["missing_traps"] == []
    assert r["counts"] == {"holds_as_stated": 6, "holds_with_supplied_scope": 4, "empirical_not_formalizable": 4, "unresolved": 7}   # empirical: pg15, pg16, kimura, turing-morphogen-hypothesis; 10+4+7 = 21
    assert set(r["downgraded_to_unresolved"]) == {"pg9", "pg10", "pg11", "pg12"} and r["counts"]["unresolved"] == 2 + 1 + 4  # pg13, pg14 + turing-wavelength + the 4 downgraded
    assert "mutation test" in r["downgraded_to_unresolved"]["pg9"]["missing"][0]
    assert "written scope condition" in r["downgraded_to_unresolved"]["pg12"]["missing"]
    assert r["holds_of_all_claims"]["k"] == 10 and r["holds_of_all_claims"]["n"] == 21
    assert r["by_domain"]["turing"] == {"holds_as_stated": 0, "holds_with_supplied_scope": 1, "empirical_not_formalizable": 1, "unresolved": 1}
    assert "10 of 21 claims hold with full evidence" in r["headline"] and "thin" in r["headline"]   # 10/21 < 0.5


def test_a_hold_with_no_evidence_at_all_is_unresolved():
    r = T.triage([{"claim_id": "x", "domain": "popgen", "bucket": "holds_as_stated"}], expected_total=1, traps=())
    assert r["counts"]["unresolved"] == 1 and len(r["downgraded_to_unresolved"]["x"]["missing"]) == 4


def test_trap_claims_cannot_be_holds():
    rows = table()
    rows[-1] = hold("turing-morphogen-hypothesis", "turing")
    with pytest.raises(D.DeskError, match="known trap"):
        T.triage(rows)


def test_reason_required_and_incomplete_tally_flagged():
    rows = table()
    rows[-1].pop("reason")
    with pytest.raises(D.DeskError, match="written reason"):
        T.triage(rows)
    short = T.triage(table()[:-1])
    assert short["n_claims"] == 20 and not short["total_matches_expected"] and short["missing_traps"] == ["turing-morphogen-hypothesis"]
    assert any("do not quote this as 'the 21 theorems'" in f for f in short["flags"])


def test_fail_closed_inputs():
    with pytest.raises(D.DeskError):
        T.triage([hold("a", "popgen"), hold("a", "popgen")])
    with pytest.raises(D.DeskError):
        T.triage([{"claim_id": "a", "bucket": "mostly_holds"}])


def test_run_writes_files(tmp_path):
    p = tmp_path / "c.jsonl"
    p.write_text("\n".join(json.dumps(r) for r in table()))
    r = T.run_triage(p, tmp_path / "o")
    assert (tmp_path / "o" / "scorecard.md").exists() and r["counts"]["holds_as_stated"] == 6
