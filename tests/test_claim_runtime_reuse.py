"""Reuse accounting: deterministic fault injection, identical-context equality of cache and claim reuse,
fail-closed behaviour, and consistency of the committed benchmark artifact. Synthetic traces are
SOFTWARE FIXTURES; the committed benchmark used the real recorded queries."""
import json
import os
from pathlib import Path

import numpy as np
import pytest

from claim_runtime import evidence as E
from claim_runtime import reuse_benchmark as R
from claim_runtime.common import sha_file

ROOT = Path(__file__).resolve().parent.parent
ART = ROOT / "artifacts" / "claim_reuse"


class StubLand:
    def __init__(self):
        n = 160000
        self.measured = np.ones(n, bool); self.measured[5] = False
        self.s = np.arange(n, dtype=np.int64); self.s1 = self.s - 3; self.s2 = self.s + 3
        self.count_min = np.full(n, 100, np.int32)


def mk_ff():
    return R.FactFactory(StubLand(), "e" * 64)


def trace(codes):
    return [(i + 1, "x", c, None) for i, c in enumerate(codes)]


TR = {(0, "B:A", "p1"): trace([10, 11, 12]), (0, "B:A", "p2"): trace([11, 12, 13]), (1, "B:A", "p1"): trace([12, 13, 14, 5])}
ORDER = list(TR)


def test_attack_selection_is_deterministic_and_has_declared_rate():
    sel = [R.attack_selected("withdrawn", f"id{i}", 50) for i in range(20000)]
    assert sel == [R.attack_selected("withdrawn", f"id{i}", 50) for i in range(20000)]
    assert 0.04 < sum(sel) / len(sel) < 0.06
    assert not any(R.attack_selected("withdrawn", f"id{i}", 0) for i in range(2000))


def test_identical_context_cache_and_claim_reuse_save_the_same():
    r = R.run(TR, ORDER, mk_ff(), "pooled")
    t = r["totals"]
    assert t["requests"] == 10
    assert t["cache_hits"] == t["claim_hits"] == 4          # p2 reuses 11,12; seed-1 p1 reuses 12,13
    assert t.get("claim_invalid_reused", 0) == 0


def test_hand_count_of_pooled_and_per_policy_hits():
    # pooled order: p1:[10,11,12] p2:[11,12,13] p1(seed1):[12,13,14,5]
    # hits: p2 -> 11,12 ; seed1 -> 12,13 ; none for 14,5  => 4
    r = R.run(TR, ORDER, mk_ff(), "pooled")
    assert r["totals"]["claim_hits"] == 4
    pp = R.run(TR, ORDER, mk_ff(), "per_policy")["totals"]
    # per policy: p1 stores [10,11,12], then seed1 p1 reuses 12 only; p2 reuses nothing
    assert pp["claim_hits"] == 1 == pp["cache_hits"]


def test_unmeasured_genotype_result_is_typed_and_reused():
    ff = mk_ff()
    f = ff.fact(5)
    assert f["value"] == {"outcome": "absent_from_measured_table"}


def test_faults_hurt_the_cache_but_not_typed_reuse():
    ff = mk_ff()
    big = {(0, "B:A", "p1"): trace(range(2000)), (0, "B:A", "p2"): trace(range(2000)), (1, "B:A", "p1"): trace(range(2000))}
    rates = {a: 100 for a in R.ATTACKS}
    r = R.run(big, list(big), ff, "pooled", fault_per_mille=rates)
    t = r["totals"]
    assert t["cache_invalid_reused"] > 0
    assert t.get("claim_invalid_reused", 0) == 0
    assert t["claim_reassays_forced"] > 0 and t["claim_hits"] < t["cache_hits"]
    assert t["claim_hits"] + t["claim_reassays_forced"] == t["cache_hits"]       # every cache 'hit' is either valid reuse or a forced reassay


@pytest.mark.parametrize("attack", R.ATTACKS)
def test_each_attack_is_caught_by_exactly_its_guard_and_mutant_passes_it(attack):
    ff = mk_ff()
    big = {(0, "B:A", "p1"): trace(range(1500)), (0, "B:A", "p2"): trace(range(1500))}
    rates = {attack: 200}
    guard = R.CATCHING_GUARD[attack]
    on = R.run(big, list(big), ff, "pooled", fault_per_mille=rates)
    off = R.run(big, list(big), ff, "pooled", fault_per_mille=rates, disabled_guards=frozenset([guard]))
    assert on["totals"].get("claim_invalid_reused", 0) == 0
    assert off["totals"]["claim_invalid_reused"] > 0
    other = [g for g in E.GUARDS if g != guard and g != "id_integrity"]
    off2 = R.run(big, list(big), ff, "pooled", fault_per_mille=rates, disabled_guards=frozenset(other))
    assert off2["totals"].get("claim_invalid_reused", 0) == 0                    # the single matching guard is sufficient


def test_corrupted_copies_keep_consistent_ids_except_withdrawn():
    f = mk_ff().fact(7)
    for a in ("context_drift", "coordinate_shift", "prediction_as_observation"):
        c = R.corrupt(f, a)
        assert c["id"] == E.claim_id(c) and c["id"] != f["id"] and c["provenance"]["synthetic_fault"] == a
    w = R.corrupt(f, "withdrawn")
    assert w["status"] == "withdrawn" and w["id"] == f["id"]


# ---------------------------- committed benchmark artifact ----------------------------------

@pytest.mark.skipif(os.environ.get("CLAIM_RUNTIME_MUTANT_RUN") == "1", reason="artifact check not needed in mutant runs")
def test_committed_reuse_benchmark_invariants():
    b = json.loads((ART / "reuse_benchmark.json").read_text())
    assert b["protocol_sha256"] == sha_file(ART / "protocol.json")
    assert b["inputs"]["episodes"] == 700 and b["inputs"]["paid_requests"] == 488601
    assert b["source_verification"]["mismatches"] == 0
    for scope in ("pooled", "per_policy"):
        base = b["baseline"][scope]
        assert base["cache_equals_claim"] and base["claim_gain_over_cache"] == 0
        assert base["fresh_assays"] == 488601 and 0 < base["claim_avoided"] < 488601
        f = b["fault_injection"][scope]
        assert f["typed_claim_reuse"]["invalid_reuse_events"] == 0
        assert f["cache"]["invalid_reuse_events"] > 0
        assert f["cache"]["invalid_reuse_events"] == sum(f["cache"]["events_by_attack"].values())
        assert f["typed_claim_reuse"]["avoided"] + f["typed_claim_reuse"]["forced_reassays"] == f["cache"]["avoided"]
    assert b["negative_controls_all_passed"] is True
    assert all(v["claim_invalid_reuse_events"] > 0 and v["with_guard_enabled_invalid_reuse_events"] == 0 for v in b["negative_controls"].values())


@pytest.mark.skipif(not os.environ.get("CLAIM_REUSE_SHARDS"), reason="set CLAIM_REUSE_SHARDS to the extracted original shards directory")
def test_recompute_pooled_baseline_from_real_traces():
    from claim_runtime import trpb_data
    land, dsha = trpb_data.load_landscape()
    tr = R.load_traces(Path(os.environ["CLAIM_REUSE_SHARDS"]))
    assert len(tr) == 700 and sum(map(len, tr.values())) == 488601
    assert R.verify_against_source(tr, land)["mismatches"] == 0
    order = R.campaign_order(tr, json.loads((ART / "protocol.json").read_text()))
    r = R.run(tr, order, R.FactFactory(land, dsha), "pooled")
    b = json.loads((ART / "reuse_benchmark.json").read_text())["baseline"]["pooled"]
    assert r["totals"]["claim_hits"] == b["claim_avoided"] == r["totals"]["cache_hits"]
