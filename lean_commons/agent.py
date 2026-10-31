"""One prover agent: pull-claim a target from the frozen order, attempt with compiler feedback,
publish kernel-verified results. Identical code path for both arms; the ONLY difference is whether
verified lemma text is shared (`arm == "commons"`) or each attempt starts from the base library."""
from __future__ import annotations

import hashlib
import json
import re
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path

from . import lean_check as L
from .accounting import BudgetExceeded, TokenLedger
from .adapters import ModelAdapter, AdapterError, sha256_text
from .commons import Board, Commons, AppendOnlyLog

HERE = Path(__file__).parent
CONTRACT = (HERE / "CONTRACT.md").read_text()
COMMONS_MARK = "VERIFIED LIBRARY"
LEAN_SEM = threading.Semaphore(2)    # bound concurrent Lean checks (RAM)


@dataclass
class RunCtx:
    arm: str                       # "shared" | "private" | "none"  (sequential = private with 1 agent)
    adapter: ModelAdapter
    ledger: TokenLedger
    budget_key: str
    out_dir: Path
    board: Board
    attempts_log: AppendOnlyLog
    targets: list[dict]
    defs: str
    t0: float
    tries_per_claim: int = 3       # model calls per claim (initial + compiler-feedback repairs)
    max_claims_per_task: int = 2
    reserve_tokens: int = 7000
    max_output_tokens: int = 2500
    adapters: dict = field(default_factory=dict)   # agent id -> adapter (heterogeneous arms); falls back to `adapter`
    max_calls: int | None = None       # matched model-call (= compiler-call) budget for the whole arm
    stop: threading.Event = field(default_factory=threading.Event)
    _calls: int = 0
    _clock: threading.Lock = field(default_factory=threading.Lock)

    def adapter_for(self, agent: str) -> ModelAdapter:
        return self.adapters.get(agent, self.adapter)

    def take_call(self) -> bool:
        with self._clock:
            if self.max_calls is not None and self._calls >= self.max_calls:
                return False
            self._calls += 1
            return True

    @property
    def calls_used(self) -> int:
        return self._calls

    @property
    def order(self):
        return [t["id"] for t in self.targets]

    def store(self, agent: str) -> Commons | None:
        """shared: one library for the whole arm; private: one per agent (retention without sharing); none: nothing retained."""
        if self.arm == "shared":
            return Commons(self.out_dir / "commons_shared.jsonl")
        if self.arm == "private":
            return Commons(self.out_dir / f"commons_{agent}.jsonl")
        return None

    def target(self, tid):
        return next(t for t in self.targets if t["id"] == tid)


BLOCK = re.compile(r"<<<(HELPERS|PROOF)\s*\n(.*?)\n?>>>", re.S)


def parse_response(text: str) -> tuple[str, str, str]:
    blocks = {m.group(1): m.group(2).strip("\n") for m in BLOCK.finditer(text)}
    if "PROOF" not in blocks or not blocks["PROOF"].strip():
        return "", "", "response lacks a <<<PROOF ... >>> block"
    return blocks.get("HELPERS", ""), blocks["PROOF"], ""


def build_user(ctx: RunCtx, target: dict, library: list[dict], prev: tuple[str, str, str] | None) -> str:
    parts = ["BASE LIBRARY (frozen, in scope):", "```lean", ctx.defs.strip(), "```", ""]
    if ctx.arm in ("shared", "private"):
        who = "by agents in this team" if ctx.arm == "shared" else "by you earlier in this session"
        parts.append(f"{COMMONS_MARK} (kernel-checked theorems already proved {who}; they are in scope "
                     "and may be used by name. Names are taken: do not reuse them for helpers):")
        if library:
            parts += ["```lean"] + [L.render_signature(e["name"], e["statement"]) for e in library] + ["```"]
        else:
            parts.append("(empty so far)")
        parts.append("")
    parts += ["TARGET (frozen; do not alter):", f"theorem {target['id']} : {target['statement']}", ""]
    if prev:
        h, p, err = prev
        parts += ["YOUR PREVIOUS ATTEMPT FAILED.", "Helpers:", h or "(none)", "Proof:", p, "Compiler/auditor output:", err[:2500], ""]
    parts.append("Reply with the two blocks only.")
    return "\n".join(parts)


def _commons_library(ctx: RunCtx, agent: str) -> list[dict]:
    st = ctx.store(agent)
    return st.entries() if st else []


def attempt(ctx: RunCtx, agent: str, tid: str) -> dict:
    target = ctx.target(tid)
    prev = None
    tries = 0
    for k in range(ctx.tries_per_claim):
        if ctx.stop.is_set():
            return {"ok": False, "why": "stopped", "tries": tries}
        library = _commons_library(ctx, agent)          # re-read EVERY attempt: this is the sharing channel
        user = build_user(ctx, target, library, prev)
        forbidden = [COMMONS_MARK] if ctx.arm == "none" else []
        try:
            ctx.ledger.check(ctx.budget_key, ctx.reserve_tokens)
        except BudgetExceeded:
            ctx.stop.set()
            return {"ok": False, "why": "budget", "tries": tries}
        res = None
        for retry in range(3):
            if retry == 0 and not ctx.take_call():       # only the first send counts as a budgeted call
                ctx.stop.set()
                return {"ok": False, "why": "call_budget", "tries": tries}
            res = ctx.adapter_for(agent).complete(CONTRACT, user, tag=f"{agent}:{tid}:{k}", ledger=ctx.ledger, budget_key=ctx.budget_key,
                                       max_output_tokens=ctx.max_output_tokens, forbidden=forbidden)
            if res.ok:
                break
            time.sleep(4 * (retry + 1))
        tries += 1
        row = {"kind": "attempt", "agent": agent, "task": tid, "k": k, "arm": ctx.arm, "call_id": res.call_id,
               "account": res.account, "served_model": res.served_model, "family_verified": res.family_verified, "family": res.family,
               "tokens": res.usage.total, "tokens_arm_cum": ctx.ledger.spent(ctx.budget_key),
               "library_size": len(library), "prompt_sha256": sha256_text(user), "response": res.text,
               "t_since_start_s": round(time.time() - ctx.t0, 1)}
        if not res.ok:
            row.update(ok=False, error=res.error)
            ctx.attempts_log.append(row)
            prev = ("", "", f"model call failed: {res.error}")
            continue
        helpers, proof, perr = parse_response(res.text)
        err = perr
        if not err:
            names = L.theorem_names(helpers)
            taken = set(ctx.order) | {e["name"] for e in library}
            clash = [n for n in names if n in taken]
            if clash:
                err = f"helper name(s) already taken: {clash}"
        cres = None
        if not err:
            src = L.assemble(ctx.defs, library, helpers, tid, target["statement"], proof)
            with LEAN_SEM:
                cres = L.check_source(src, L.theorem_names(helpers) + [tid], scan_text=helpers + "\n" + proof)
            if not cres.ok:
                err = cres.errors or "check failed"
        row.update(ok=(not err), error=err[:1500], lean_seconds=(cres.seconds if cres else None),
                   check_sha256=(cres.sha256 if cres else None))
        ctx.attempts_log.append(row)
        if not err:
            used = []
            if ctx.arm in ("shared", "private"):
                text = helpers + "\n" + proof
                for e in library:
                    if re.search(r"(?<![A-Za-z0-9_'.])" + re.escape(e["name"]) + r"(?![A-Za-z0-9_'])", text):
                        used.append({"name": e["name"], "author": e["author"]})
            return {"ok": True, "tries": tries, "helpers": helpers, "proof": proof, "used_commons": used,
                    "axioms": cres.axioms, "check_sha256": cres.sha256, "library_size": len(library)}
        prev = (helpers, proof, err)
    return {"ok": False, "why": "attempts_exhausted", "tries": tries}


def publish(ctx: RunCtx, agent: str, tid: str, out: dict) -> None:
    target = ctx.target(tid)
    meta_base = {"arm": ctx.arm, "model": ctx.adapter_for(agent).model, "family": ctx.adapter_for(agent).family,
                 "tokens_arm_cum": ctx.ledger.spent(ctx.budget_key)}
    commit = []
    store = ctx.store(agent)
    if store is not None:
        # helpers first (target may depend on them), then the target theorem itself
        decls = re.split(r"(?m)^(?=theorem\s)", out["helpers"].strip()) if out["helpers"].strip() else []
        for d in decls:
            if not d.strip():
                continue
            nm = L.theorem_names(d)[0]
            stmt_m = re.match(r"\s*theorem\s+\S+\s*:\s*(.*?)\s*:=", d, re.S)
            stmt = stmt_m.group(1).strip() if stmt_m else d
            status, _ = store.add(name=nm, statement=stmt, source=d.strip(), author=agent, task=None,
                                        meta={**meta_base, "role": "helper", "for_task": tid})
            commit.append((nm, status))
        src = f"theorem {tid} : {target['statement']} := {out['proof'].strip()}"
        status, _ = store.add(name=tid, statement=target["statement"], source=src, author=agent, task=tid,
                                    meta={**meta_base, "role": "target", "check_sha256": out["check_sha256"],
                                          "axioms": out["axioms"].get(tid), "used_commons": out["used_commons"]})
        commit.append((tid, status))
    ctx.board.append({"kind": "proved", "task": tid, "agent": agent, "tries": out["tries"],
                      "t_since_start_s": round(time.time() - ctx.t0, 1), "tokens_arm_cum": ctx.ledger.spent(ctx.budget_key),
                      "used_commons": out["used_commons"], "library_size_seen": out["library_size"],
                      "axioms": out["axioms"].get(tid), "commit": commit, "arm": ctx.arm})


def run_agent(ctx: RunCtx, agent: str) -> None:
    idle = 0
    while not ctx.stop.is_set():
        try:
            ctx.ledger.check(ctx.budget_key, ctx.reserve_tokens)
        except BudgetExceeded:
            break
        tid = ctx.board.claim_next(agent, ctx.order, ctx.max_claims_per_task)
        if tid is None:
            st = ctx.board.state()
            open_left = [t for t in ctx.order if not st.get(t, {}).get("proved") and st.get(t, {}).get("tries", 0) < ctx.max_claims_per_task]
            if not open_left or idle > 30:
                break
            idle += 1
            time.sleep(4)
            continue
        idle = 0
        out = attempt(ctx, agent, tid)
        if out["ok"]:
            publish(ctx, agent, tid, out)
        else:
            ctx.board.append({"kind": "failed", "task": tid, "agent": agent, "why": out.get("why"), "tries": out.get("tries"),
                              "t_since_start_s": round(time.time() - ctx.t0, 1), "tokens_arm_cum": ctx.ledger.spent(ctx.budget_key), "arm": ctx.arm})
