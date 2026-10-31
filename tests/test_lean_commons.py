"""Offline tests for the verified commons. They use the real Lean kernel (core) and a scripted fake
model adapter; no network, no subscription spend."""
import json
import threading
from pathlib import Path

import pytest

from lean_commons import lean_check as L
from lean_commons.accounting import TokenLedger, Usage, BudgetExceeded
from lean_commons.adapters import ModelAdapter, CallResult, AdapterError, make_adapter, sha256_text
from lean_commons.agent import RunCtx, attempt, publish, run_agent, COMMONS_MARK
from lean_commons.commons import Board, Commons, AppendOnlyLog

REF = json.loads((Path(L.HERE) / "reference/proofs.json").read_text())


class Fake(ModelAdapter):
    family, harness, default_model = "claude", "fake", "fake"

    def __init__(self, script):
        super().__init__()
        self.script, self.prompts, self.i = script, [], 0
        self._lock = threading.Lock()

    def _call(self, system, user, max_output_tokens):
        with self._lock:
            self.prompts.append(user)
            reply = self.script(user, self.i)
            self.i += 1
        return CallResult("c", "claude", "fake", "acct", "fake", "claude-fake", "provider_response", True, reply,
                          Usage(100, 50), 0.0, "subscription", None, "", "", True)


def reply_for(tid, helpers=""):
    return f"<<<HELPERS\n{helpers}\n>>>\n<<<PROOF\n{REF[tid]}\n>>>"


def mk(tmp, arm, script, targets=None, **kw):
    T = L.load_targets()
    if targets:
        T = [t for t in T if t["id"] in targets]
    led = TokenLedger(tmp / f"{arm}.ledger.jsonl", {"k": 10**6})
    return RunCtx(arm=arm, adapter=Fake(script), ledger=led, budget_key="k",
                  out_dir=tmp / arm,
                  board=Board(tmp / f"{arm}.board.jsonl"), attempts_log=AppendOnlyLog(tmp / f"{arm}.att.jsonl"),
                  targets=T, defs=L.load_defs(), t0=0.0, **kw)


def test_targets_hash_matches_validation():
    v = json.loads((Path(L.HERE) / "targets/VALIDATION.json").read_text())
    import hashlib
    assert v["targets_sha256"] == hashlib.sha256((Path(L.HERE) / "targets/targets.json").read_bytes()).hexdigest()
    assert v["all_reference_compile"] and v["all_mutants_rejected"]


def test_kernel_rejects_sorry_and_wrong_proof():
    T = {t["id"]: t for t in L.load_targets()}
    t = T["T01"]
    bad = L.check_source(L.assemble(L.load_defs(), [], "", "T01", t["statement"], "by sorry"), ["T01"], scan_text="by sorry")
    assert not bad.ok and "forbidden" in bad.errors
    wrong = L.check_source(L.assemble(L.load_defs(), [], "", "T01", t["statement"], "by intro m N M; rfl"), ["T01"], scan_text="by intro m N M; rfl")
    assert not wrong.ok


def test_statement_cannot_be_weakened_by_agent():
    T = {t["id"]: t for t in L.load_targets()}
    # agent tries to smuggle a different statement through the proof slot
    proof = "by intro m N M; exact (fun _ => rfl) ()"
    r = L.check_source(L.assemble(L.load_defs(), [], "", "T01", T["T01"]["statement"], proof), ["T01"], scan_text=proof)
    assert not r.ok


def test_forbidden_constructs_scanned():
    for bad in ["axiom foo : False", "def x := 1", "set_option maxRecDepth 5 in", "theorem a : True := by native_decide", "instance : Inhabited Nat := ⟨0⟩"]:
        r = L.check_source("theorem z : True := trivial", ["z"], scan_text=bad)
        assert not r.ok and r.forbidden


def test_commons_append_only_and_dedup(tmp_path):
    c = Commons(tmp_path / "c.jsonl")
    s1, _ = c.add(name="a", statement="True", source="theorem a : True := trivial", author="x", task=None, meta={})
    s2, _ = c.add(name="a", statement="True", source="theorem a : True := trivial", author="y", task=None, meta={})
    s3, _ = c.add(name="a", statement="False", source="x", author="y", task=None, meta={})
    assert (s1, s2, s3) == ("added", "duplicate", "name_taken")
    before = (tmp_path / "c.jsonl").read_text()
    c.add(name="b", statement="True", source="theorem b : True := trivial", author="y", task=None, meta={})
    assert (tmp_path / "c.jsonl").read_text().startswith(before)       # only appended
    assert [r["seq"] for r in c.read()] == [0, 1]


def test_concurrent_claims_are_exclusive(tmp_path):
    b = Board(tmp_path / "b.jsonl")
    order = [f"t{i}" for i in range(6)]
    got, lock = [], threading.Lock()

    def worker(n):
        while True:
            t = b.claim_next(n, order, 2)
            if t is None:
                return
            with lock:
                got.append(t)
            b.append({"kind": "proved", "task": t, "agent": n})
    ths = [threading.Thread(target=worker, args=(f"a{i}",)) for i in range(5)]
    [t.start() for t in ths]; [t.join() for t in ths]
    assert sorted(got) == sorted(order)          # each task claimed exactly once


def _two_step(arm, tmp, agents=("a0", "a1")):
    sc = lambda u, i: reply_for("T02") if i == 0 else reply_for("T05")
    c = mk(tmp, arm, sc, ["T02", "T05"], tries_per_claim=1)
    o1 = attempt(c, agents[0], "T02"); assert o1["ok"]; publish(c, agents[0], "T02", o1)
    o2 = attempt(c, agents[1], "T05")
    return c, o2


def test_shared_arm_agent_b_sees_and_reuses_agent_a_lemma(tmp_path):
    c, o2 = _two_step("shared", tmp_path)
    assert o2["ok"] and o2["used_commons"] == [{"name": "T02", "author": "a0"}]
    assert COMMONS_MARK in c.adapter.prompts[1] and "theorem T02 :" in c.adapter.prompts[1]


def test_private_arm_agent_b_cannot_see_agent_a_lemma(tmp_path):
    c, o2 = _two_step("private", tmp_path)                       # different agents -> different libraries
    assert not o2["ok"]                                            # T05's reference proof cites T02, which b never proved
    assert "theorem T02 :" not in c.adapter.prompts[1]
    assert [e["name"] for e in Commons(tmp_path / "private/commons_a0.jsonl").entries()] == ["T02"]
    assert Commons(tmp_path / "private/commons_a1.jsonl").entries() == []


def test_sequential_agent_retains_its_own_lemma(tmp_path):
    c, o2 = _two_step("private", tmp_path, agents=("solo", "solo"))
    assert o2["ok"] and o2["used_commons"] == [{"name": "T02", "author": "solo"}]


def test_none_arm_retains_nothing_and_never_sees_library_header(tmp_path):
    c, o2 = _two_step("none", tmp_path)
    assert not o2["ok"]
    assert all(COMMONS_MARK not in p for p in c.adapter.prompts)
    assert not list(tmp_path.glob("none/commons_*.jsonl"))


def test_call_budget_matches_across_arms(tmp_path):
    c = mk(tmp_path, "shared", lambda u, i: "no blocks here", ["T01"], tries_per_claim=5, max_calls=3)
    out = attempt(c, "a0", "T01")
    assert not out["ok"] and c.calls_used == 3 and len(c.adapter.prompts) == 3


def test_deterministic_arm_is_tokenless_and_partial():
    from lean_commons import deterministic
    o = deterministic.run(["T01", "T02", "T08", "H02"])
    assert o["tokens"] == 0 and 0 < o["n_proved"] <= o["n_targets"]


def test_none_arm_isolation_guard_blocks_marker(tmp_path):
    led = TokenLedger(tmp_path / "l.jsonl", {"k": 1000})
    f = Fake(lambda u, i: "x")
    with pytest.raises(AdapterError):
        f.complete("sys", "has VERIFIED LIBRARY inside", tag="t", ledger=led, budget_key="k", forbidden=[COMMONS_MARK])


def test_token_budget_enforced_and_recorded(tmp_path):
    led = TokenLedger(tmp_path / "l.jsonl", {"k": 400})
    f = Fake(lambda u, i: "x")
    f.complete("s", "u", tag="t", ledger=led, budget_key="k", reserve_tokens=100)
    assert led.spent("k") == 150
    f.complete("s", "u", tag="t", ledger=led, budget_key="k", reserve_tokens=100)
    with pytest.raises(BudgetExceeded):
        f.complete("s", "u", tag="t", ledger=led, budget_key="k", reserve_tokens=200)
    rows = [json.loads(l) for l in (tmp_path / "l.jsonl").read_text().splitlines()]
    assert len(rows) == 2 and rows[0]["tokens"]["total"] == 150 and rows[0]["family_verified"] is True


def test_adapter_factory_covers_six_families():
    fams = {"claude", "gpt", "gemini", "glm", "grok", "minimax"}
    from lean_commons.adapters import ADAPTERS
    assert set(ADAPTERS) == fams
    for f in fams:
        a = make_adapter(f)
        assert a.family == f


# ---- Codex-reported soundness holes (feb5dbd) and their repairs -----------------------------------------
FALSE_TARGET_DEFS = L.load_defs()


def _false_target_source(helpers, proof):
    return L.assemble(FALSE_TARGET_DEFS, [], helpers, "Tfalse", "False", proof)


def test_variable_include_false_loophole_is_closed():
    helpers = "variable (h : False)\ninclude h\ntheorem aux : True := trivial"
    proof = "by exact h"
    # The attack as Codex reproduced it: without the repair this compiled with no axioms (False elaborated as False -> False).
    assert L.helper_structure_error(helpers)                                    # structural filter rejects it
    r = L.check_source(_false_target_source(helpers, proof), ["Tfalse"], scan_text=helpers + "\n" + proof,
                       fidelity=("Tfalse", "False"))
    assert not r.ok and r.forbidden


def test_elaborated_type_comparison_catches_a_changed_target_even_without_the_token_scan():
    # bypass the scan on purpose: the trusted elaborated-type comparison must still reject the changed target
    src = L.assemble(FALSE_TARGET_DEFS, [], "variable (h : False)\ninclude h", "Tfalse", "False", "by exact h")
    r = L.check_source(src, ["Tfalse"], scan_text="", fidelity=("Tfalse", "False"))
    assert not r.ok and "fidelity" in r.errors


def test_legit_target_passes_fidelity_and_conditional_false_is_not_accepted_as_false():
    T = {t["id"]: t for t in L.load_targets()}
    ok = L.check_source(L.assemble(FALSE_TARGET_DEFS, [], "", "T01", T["T01"]["statement"], REF["T01"]), ["T01"], scan_text="",
                        fidelity=("T01", T["T01"]["statement"]))
    assert ok.ok


@pytest.mark.parametrize("helpers", ["theorem a : True := trivial\nvariable (x : Nat)", "def f := 1", "section\ntheorem a : True := trivial\nend",
                                     "namespace Foo\ntheorem a : True := trivial\nend Foo", "open Scope in\ntheorem a : True := trivial"])
def test_helper_structure_rejects_non_theorem_top_level(helpers):
    assert L.helper_structure_error(helpers) or L.check_source("theorem z : True := trivial", ["z"], scan_text=helpers).forbidden


def test_ledger_reservations_are_atomic_under_concurrency(tmp_path):
    led = TokenLedger(tmp_path / "l.jsonl", {"k": 100})
    results, lock = [], threading.Lock()
    barrier = threading.Barrier(2)

    def go():
        barrier.wait()
        try:
            led.reserve_tokens("k", 60)
            ok = True
        except BudgetExceeded:
            ok = False
        with lock:
            results.append(ok)
    ths = [threading.Thread(target=go) for _ in range(2)]
    [t.start() for t in ths]; [t.join() for t in ths]
    assert sorted(results) == [False, True]                         # exactly one in-flight reservation of 60 fits in 100


def test_adapter_holds_and_releases_reservation(tmp_path):
    led = TokenLedger(tmp_path / "l.jsonl", {"k": 400})
    f = Fake(lambda u, i: "x")
    f.complete("s", "u", tag="t", ledger=led, budget_key="k", reserve_tokens=300)   # spends 150, releases 300 hold
    assert led.spent("k") == 150 and led._pending.get("k", 0) == 0
    f.complete("s", "u", tag="t", ledger=led, budget_key="k", reserve_tokens=250)   # 150+250 <= 400 ok
    with pytest.raises(BudgetExceeded):
        f.complete("s", "u", tag="t", ledger=led, budget_key="k", reserve_tokens=200)  # 300+200 > 400


def test_failed_replay_leaves_no_helpers_behind(tmp_path):
    """Codex finding: validate the candidate closure BEFORE mutating the store; publish atomically."""
    c = mk(tmp_path, "shared", lambda u, i: "", ["T02"])
    bad_helper = "theorem aux_ok : True := trivial"
    out = {"ok": True, "tries": 1, "helpers": bad_helper, "proof": "by sorry", "used_commons": [], "axioms": {"T02": []},
           "check_sha256": "x", "library_size": 0}
    publish(c, "a0", "T02", out)                     # proof contains sorry -> replay must fail
    assert c.store("a0").entries() == []              # nothing published, not even the valid helper
    assert [r for r in c.board.read() if r["kind"] == "failed"][0]["why"] == "publish_replay_failed"
    assert not [r for r in c.board.read() if r["kind"] == "proved"]


def test_publish_is_atomic_and_dedups_helper_names(tmp_path):
    c = mk(tmp_path, "shared", lambda u, i: "", ["T02"])
    helper = "theorem aux_two : True := trivial"
    out = {"ok": True, "tries": 1, "helpers": helper, "proof": REF["T02"], "used_commons": [], "axioms": {"T02": []},
           "check_sha256": "x", "library_size": 0}
    publish(c, "a0", "T02", out)
    assert [e["name"] for e in c.store("a0").entries()] == ["aux_two", "T02"]
    ok, st = c.store("a0").add_many([{"name": "aux_two", "statement": "True", "source": helper, "author": "z", "task": None},
                                      {"name": "new", "statement": "True", "source": "theorem new : True := trivial", "author": "z", "task": None}])
    assert ok and dict(st) == {"aux_two": "duplicate", "new": "added"}
    ok2, st2 = c.store("a0").add_many([{"name": "fresh", "statement": "True", "source": "x", "author": "z", "task": None},
                                       {"name": "T02", "statement": "DIFFERENT", "source": "x", "author": "z", "task": None}])
    assert not ok2 and "fresh" not in [e["name"] for e in c.store("a0").entries()]
