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
