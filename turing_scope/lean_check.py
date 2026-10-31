"""Build the standalone Lean project and the mutants; record exit codes and output hashes.
Run under systemd-run limits (see docs/turing-scope.md)."""
from __future__ import annotations

import datetime
import json
import re
import subprocess
from pathlib import Path
from zoneinfo import ZoneInfo

from .source import PKG, sha_file

LEAN = PKG / "lean"
MUTANTS = [("Control_unmutated", 0, "unmutated claim (L=2π, original law): must compile"),
           ("M1_law_reaction_d", 1, "source-law mutation: g_v -3 -> -2"),
           ("M2_law_diffusion_ratio", 1, "source-law mutation: Dv 10 -> 1 (equal diffusivities)"),
           ("M3_domain_short", 1, "domain mutation: L=π, claim mode 1 unstable")]


def _run(cmd, timeout=500):
    p = subprocess.run(cmd, cwd=LEAN, capture_output=True, text=True, timeout=timeout)
    return p.returncode, (p.stdout + p.stderr)


def seattle_now() -> str:
    return datetime.datetime.now(ZoneInfo("America/Los_Angeles")).strftime("%Y-%m-%d %H:%M:%S %Z")


def run() -> dict:
    ver = _run(["lean", "--version"])[1].strip()
    code, out = _run(["lake", "build"])
    src = sorted((LEAN / "TuringScope").glob("*.lean")) + [LEAN / "TuringScope.lean"]
    text = "\n".join(p.read_text() for p in src)
    forbidden = sorted(set(re.findall(r"\b(sorry|admit|native_decide)\b", re.sub(r"/-.*?-/", "", text, flags=re.S))))
    acode, aout = _run(["lake", "env", "lean", "Audit.lean"])
    axioms = sorted(set(re.findall(r"\[(.*?)\]", aout)))
    rec = {"timestamp_seattle": seattle_now(), "lean_version": ver,
           "build": {"command": "lake build", "exit": code, "output_tail": out.strip().splitlines()[-4:]},
           "forbidden_tokens_in_source": forbidden,
           "axiom_audit": {"command": "lake env lean Audit.lean", "exit": acode, "distinct_axiom_sets": axioms},
           "sources": {str(p.relative_to(PKG.parent)): sha_file(p) for p in src},
           "mutants": []}
    for name, want, desc in MUTANTS:
        f = LEAN / "mutants" / f"{name}.lean"
        c, o = _run(["lake", "env", "lean", str(f)])
        first = next((ln for ln in o.splitlines() if "error" in ln), "")
        rec["mutants"].append({"file": f"turing_scope/lean/mutants/{name}.lean", "sha256": sha_file(f), "description": desc,
                               "expected_exit_nonzero": want == 1, "exit": c,
                               "as_expected": (c != 0) == (want == 1), "first_error": first[:200],
                               "proved_false_by_decide": "is false" in o})
    rec["ok"] = (code == 0 and acode == 0 and not forbidden and all(m["as_expected"] for m in rec["mutants"]))
    return rec
