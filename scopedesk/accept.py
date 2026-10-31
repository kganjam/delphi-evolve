#!/usr/bin/env python3
"""Scope Desk acceptance runner. One command, from a repository root (intended: a fresh clone of the integration branch):

    python3 scopedesk/accept.py [--out accept_receipt.json] [--bench scopedesk/bench/v1_2]

Steps (each recorded with its command, exit code, wall seconds and output tail in the receipt):
  a  bench hashes      every KEY.sha256 under scopedesk/bench recomputed against the files it lists
  b  oracle vs key     scopedesk.oracles.at5 on the bench (gate full/ablations/C0 vs key) + v1.1 audit; pass iff the full gate agrees with the key on every item
  c  tests             pytest for bench, oracles, probe (and the read-only service cross-check when the service ref exists)
  d  lean receipts     recorded receipts re-verified by hash/exit consistency (Lean/Mathlib is NOT rebuilt)
  e  receipt           accept_receipt.json with SHAs, commands, exits, overall verdict
Heavy subprocesses run under `systemd-run --user --scope -p TasksMax=128 -p MemoryMax=4G -p MemorySwapMax=0 -p RuntimeMaxSec=600`
when systemd-run is usable; otherwise they run under `timeout 600` and the receipt says caps=none. CPU threads are limited to 2.
Exit code 0 iff every required step passes. Nothing here installs software, reaches the network, or edits tracked files.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CAPS = ["systemd-run", "--user", "--scope", "-q", "-p", "TasksMax=128", "-p", "MemoryMax=4G", "-p", "MemorySwapMax=0", "-p", "RuntimeMaxSec=600"]
ENV = {**os.environ, "OMP_NUM_THREADS": "2", "OPENBLAS_NUM_THREADS": "2", "PYTHONPATH": str(ROOT), "PYTHONDONTWRITEBYTECODE": "1"}


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def git(*a):
    p = subprocess.run(["git", *a], cwd=ROOT, capture_output=True, text=True)
    return p.stdout.strip() if p.returncode == 0 else None


def caps_usable() -> bool:
    if not shutil.which("systemd-run"):
        return False
    p = subprocess.run(CAPS + ["true"], capture_output=True, text=True)
    return p.returncode == 0


USE_CAPS = caps_usable()


def run(cmd, steps, name, required=True, cwd=ROOT):
    full = (CAPS if USE_CAPS else ["timeout", "600"]) + cmd
    t = time.time()
    p = subprocess.run(full, cwd=cwd, capture_output=True, text=True, env=ENV)
    steps.append({"step": name, "command": " ".join(cmd), "capped_with": "systemd-run scope (TasksMax=128, MemoryMax=4G, MemorySwapMax=0, RuntimeMaxSec=600)" if USE_CAPS else "timeout 600 only (caps=none)",
                  "exit": p.returncode, "seconds": round(time.time() - t, 1), "output_tail": (p.stdout + p.stderr).strip().splitlines()[-12:], "required": required})
    return p


def step_a(steps):
    problems, checked = [], 0
    for ks in sorted((ROOT / "scopedesk" / "bench").rglob("KEY.sha256")):
        for line in ks.read_text().splitlines():
            if not line.strip():
                continue
            h, _, fn = line.partition("  ")
            f = ks.parent / fn.strip()
            checked += 1
            if not f.is_file():
                problems.append(f"{ks.relative_to(ROOT)}: missing {fn}")
            elif sha256(f) != h:
                problems.append(f"{ks.relative_to(ROOT)}: hash mismatch {fn}")
    steps.append({"step": "a_bench_hashes", "command": "internal sha256 re-computation of every scopedesk/bench/**/KEY.sha256", "exit": 0 if not problems else 1,
                  "files_checked": checked, "problems": problems[:20], "required": True})


def step_b(steps, bench, tmp):
    out = Path(tmp) / "at5.json"
    p = run([sys.executable, "-m", "scopedesk.oracles.at5", bench, str(out), "acceptance run"], steps, "b1_oracle_at5")
    if p.returncode == 0:
        res = json.loads(out.read_text())
        a = res["table"]["ALL"]
        ok = a["full"]["agree_with_key"] == a["n"]
        steps[-1]["summary"] = {"n": a["n"], "full_gate_agrees_with_key": a["full"]["agree_with_key"], "C0_agrees": a["C0"]["agree_with_key"],
                                "record_removed": a["record_removed"]["agree_with_key"], "continuum_only": a["continuum_only"]["agree_with_key"],
                                "record_hash_changed_refusals": a["record_hash_changed"]["refused"], "bench_files_sha256": res["bench_dir_files_sha256"]}
        if not ok:
            steps[-1]["exit"] = 1
            steps[-1]["failure"] = "full gate disagrees with the key on some item"
    v11 = ROOT / "scopedesk" / "bench" / "v1_1"
    if (v11 / "instances_full.jsonl").exists():
        run([sys.executable, "-m", "scopedesk.oracles.audit_v1_1", str(v11), str(Path(tmp) / "audit_v1_1.json")], steps, "b2_oracle_audit_v1_1")
        dis = json.loads((Path(tmp) / "audit_v1_1.json").read_text())["disagreements"] if (Path(tmp) / "audit_v1_1.json").exists() else ["no output"]
        steps[-1]["disagreements"] = len(dis)
        if dis:
            steps[-1]["exit"] = 1


def step_c(steps):
    tests = [t for t in ("tests/test_scopedesk_bench.py", "tests/test_scopedesk_bench_v1_1.py", "tests/test_scopedesk_bench_v1_2.py",
                         "tests/test_scopedesk_oracles.py", "tests/test_rethink_nca.py", "tests/test_scopedesk_service_crosscheck.py") if (ROOT / t).exists()]
    run([sys.executable, "-m", "pytest", "-q", "-W", "ignore::pytest.PytestUnknownMarkWarning", "-p", "no:cacheprovider", *tests], steps, "c_tests")
    steps[-1]["tests_run"] = tests


def step_d(steps):
    problems, notes = [], []
    r = ROOT / "artifacts/turing_scope/lean_receipt.json"
    if r.exists():
        d = json.loads(r.read_text())
        notes.append(f"turing_scope receipt ok={d.get('ok')} build_exit={d['build']['exit']} lean={d['lean_version'][:30]}")
        if not d.get("ok") or d["build"]["exit"] != 0 or d["axiom_audit"]["exit"] != 0 or d["axiom_audit"]["unexpected_axioms"]:
            problems.append("turing_scope receipt: ok/build/axiom audit not clean")
        for fn, h in d["sources"].items():
            f = ROOT / fn
            if not f.is_file() or sha256(f) != h:
                problems.append(f"turing_scope source hash mismatch or missing: {fn}")
        for m in d["mutants"]:
            f = ROOT / m["file"]
            if not f.is_file() or sha256(f) != m["sha256"]:
                problems.append(f"mutant file hash mismatch or missing: {m['file']}")
            if not m["as_expected"]:
                problems.append(f"mutant not as expected: {m['file']}")
        for m in d["generic_law_mutants"]:
            if not m.get("killed_in_model_file"):
                problems.append(f"generic law mutant not killed: {m['name']}")
    else:
        problems.append("artifacts/turing_scope/lean_receipt.json missing")
    r = ROOT / "artifacts/proof/receipt.json"
    if r.exists():
        d = json.loads(r.read_text())
        notes.append(f"proof receipt status={d.get('status')} compile_exit={d.get('compile_exit_code')}")
        if d.get("status") != "completed" or d.get("compile_exit_code") != 0:
            problems.append("proof receipt: not completed or compile exit != 0")
        for k in ("dominance_mutant_exit_code", "min_mutant_exit_code", "open_cut_edge_mutant_exit_code"):
            if d.get(k) in (0, None):
                problems.append(f"proof receipt: {k} should be nonzero (mutant rejected)")
        if not all(c.get("ok") for c in d.get("checks", [])):
            problems.append("proof receipt: a recorded check is not ok")
        if not all(m.get("rejected") for m in d.get("source_mutants", [])):
            problems.append("proof receipt: a source mutant was not rejected")
        if not all(m.get("as_expected") and m.get("mirror_agrees") for m in d.get("instance_mutants", [])):
            problems.append("proof receipt: an instance mutant disagreed with expectation or mirror")
        for c in d.get("certificates", []):
            cj = ROOT / "artifacts/proof" / (c["label"] + ".json")
            if cj.exists():
                notes.append(f"certificate json present: {c['label']}")
            else:
                problems.append(f"certificate json missing: {c['label']}")
    else:
        problems.append("artifacts/proof/receipt.json missing")
    steps.append({"step": "d_lean_receipts", "command": "internal consistency/hash verification of recorded receipts (Lean and Mathlib are NOT rebuilt)",
                  "exit": 0 if not problems else 1, "notes": notes, "problems": problems, "required": True})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="accept_receipt.json")
    ap.add_argument("--bench", default="scopedesk/bench/v1_2")
    a = ap.parse_args()
    steps = []
    t0 = time.time()
    with tempfile.TemporaryDirectory() as tmp:
        step_a(steps)
        step_b(steps, str(ROOT / a.bench), tmp)
        step_c(steps)
        step_d(steps)
    ok = all(s["exit"] == 0 for s in steps if s.get("required", True))
    receipt = {"accept_version": "1.0", "overall_pass": ok, "bench": a.bench, "head_sha": git("rev-parse", "HEAD"), "branch": git("rev-parse", "--abbrev-ref", "HEAD"),
               "tracked_tree_clean_at_start": git("status", "--porcelain", "--untracked-files=no") == "", "python": sys.version.split()[0],
               "caps_used": USE_CAPS, "started_wall_clock": time.strftime("%Y-%m-%d %H:%M:%S %Z"), "total_seconds": round(time.time() - t0, 1),
               "steps": steps, "not_checked": ["Lean/Mathlib not rebuilt (receipt hashes and exit codes only)", "agent arms are not run by this script",
                                                "oracle-vs-key agreement shares the bench convention document"]}
    Path(a.out).write_text(json.dumps(receipt, indent=1))
    for s in steps:
        print(f"{'PASS' if s['exit'] == 0 else 'FAIL'}  {s['step']}  (exit {s['exit']})")
    print("OVERALL", "PASS" if ok else "FAIL", "->", a.out)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
