#!/usr/bin/env python3
"""Offline review controls for a pinned commons runner. No adapters or model calls.

Run inside the repository's bounded systemd scope. The reviewed modules are loaded
from git objects, never from a worker's changing checkout. Only the Lean executable
is replaced by a wrapper fixing the version and limiting compiler threads to two.
"""
from __future__ import annotations

import dataclasses
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import types

REVISION = "feb5dbd3b6b5613f47c73bbed6ff1a95ecc76e87"
LEAN = Path("/home/ubuntu/.elan/toolchains/leanprover--lean4---v4.35.0/bin/lean")
OUT = Path("artifacts/integration/codex-api/lean-commons-review")


def blob(path: str) -> bytes:
    return subprocess.check_output(["git", "show", f"{REVISION}:{path}"])


def load_module(name: str, path: str) -> types.ModuleType:
    module = types.ModuleType(name)
    module.__file__ = str(OUT / Path(path).name)
    sys.modules[name] = module
    exec(compile(blob(path), path, "exec"), module.__dict__)
    return module


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    files = ["lean_check.py", "accounting.py", "agent.py", "commons.py",
             "experiment.py", "PREREG.md", "CONTRACT.md", "FREEZE.sha256",
             "targets/targets.json", "targets/Defs.lean", "run_registered.py"]
    hashes = {f: hashlib.sha256(blob("lean_commons/" + f)).hexdigest() for f in files}
    checker = load_module("review_lean_checker", "lean_commons/lean_check.py")
    ledger_module = load_module("review_lean_accounting", "lean_commons/accounting.py")
    with tempfile.TemporaryDirectory(prefix="commons-review-") as temp:
        temp = Path(temp)
        wrapper = temp / "lean-bounded"
        wrapper.write_text(f'#!/bin/sh\nexec "{LEAN}" -j2 "$@"\n')
        wrapper.chmod(0o700)
        checker.LEAN_BIN = str(wrapper)
        cases = [
            ("true_control", "", "True", "by trivial"),
            ("false_control", "", "False", "by trivial"),
            ("extra_assumption", "theorem review_helper : True := by trivial\n"
             "variable (h : False)\ninclude h", "False", "by exact h"),
        ]
        results = []
        for label, helpers, target, proof in cases:
            source = checker.assemble("", [], helpers, "review_target", target, proof)
            audit_names = checker.theorem_names(helpers) + ["review_target"]
            result = checker.check_source(source, audit_names, scan_text=helpers + "\n" + proof)
            raw_source = source + "\n#check @review_target\n" + "\n".join(
                f"#print axioms {n}" for n in audit_names) + "\n"
            source_path = OUT / f"{label}.lean"
            source_path.write_text(raw_source)
            raw = subprocess.run([str(LEAN), "-j2", str(source_path.resolve())],
                                 capture_output=True, text=True, timeout=30)
            (OUT / f"{label}.log").write_text(raw.stdout + raw.stderr)
            results.append({"case": label, "frozen_statement": target,
                            "checker": dataclasses.asdict(result), "compiler_exit": raw.returncode,
                            "source": str(source_path), "output": raw.stdout + raw.stderr})
        ledger = ledger_module.TokenLedger(temp / "ledger.jsonl", {"arm": 100})
        ledger.check("arm", 60)  # first in-flight call is not reserved
        ledger.check("arm", 60)  # second in-flight call also passes
        for name in ["first", "second"]:
            ledger.record("arm", {"review_call": name}, ledger_module.Usage(input_tokens=60))
        budget_result = {"cap": 100, "in_flight_upper_bounds": [60, 60],
                         "both_prechecks_passed": True, "spent": ledger.spent("arm"),
                         "remaining": ledger.remaining("arm"), "model_calls": 0}
        freeze_checks = []
        for line in blob("lean_commons/FREEZE.sha256").decode().splitlines():
            expected, path = line.split(maxsplit=1)
            actual = hashlib.sha256(blob("lean_commons/" + path)).hexdigest()
            freeze_checks.append({"path": path, "expected": expected, "actual": actual,
                                  "matches": expected == actual})
        receipt = {"reviewed_revision": REVISION, "source_hashes": hashes,
                   "purpose": "offline verifier and budget review; not a prover arm",
                   "model_calls": 0, "compiler": str(LEAN), "compiler_threads": 2,
                   "checker_change": "only LEAN_BIN replaced by version/thread-pinned wrapper",
                   "cases": results, "budget_control": budget_result,
                   "freeze_checks": freeze_checks}
        (OUT / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
        print(json.dumps({"checker_accepts": {r["case"]: r["checker"]["ok"] for r in results},
                          "budget_control": budget_result,
                          "freeze_mismatches": [r["path"] for r in freeze_checks if not r["matches"]]}, indent=2))
        assert results[0]["checker"]["ok"]
        assert not results[1]["checker"]["ok"]
        assert results[2]["checker"]["ok"], "reassess the extra-assumption finding"
        assert "False → False" in results[2]["output"]
        assert ledger.spent("arm") == 120


if __name__ == "__main__":
    main()
