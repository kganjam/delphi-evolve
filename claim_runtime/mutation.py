"""Mutation checks: break the guards/adapters on purpose and require the controls to notice.

(a) Guard mutants: disable one applicability guard; the matching NEGATIVE-CONTROL request
    (refused with the guard on) must then be accepted => mutant detected.
(b) Source mutants: apply a one-line edit to a copy of claim_runtime/ and run the unit tests
    against the copy; the tests must FAIL (non-zero exit) => mutant killed.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from . import demo as D
from .records import default_store
from .service import ClaimService, GuardConfig

ROOT = Path(__file__).resolve().parent.parent

GUARD_MUTANTS = [  # (guard, negative-control request that must be refused by the original)
    ("ploidy_diploid", D.KIMURA_HAPLOID_ECOLI),
    ("s_source_not_assay", {**D.KIMURA_TRPB_DEFAULT, "model": D.KIMURA_OK["model"]}),
    ("genic_selection", {**D.KIMURA_OK, "model": {**D.KIMURA_OK["model"], "selection": "dominant"}}),
    ("constant_ne", {**D.KIMURA_OK, "model": {**D.KIMURA_OK["model"], "ne": "fluctuating"}}),
    ("no_linkage", {**D.KIMURA_OK, "model": {**D.KIMURA_OK["model"], "linkage": "tight"}}),
    ("inference_partial_only", D.FISHER_STEPS),
    ("variance_additive", D.FISHER_CLONAL),
    ("conditions_hold", {**D.FISHER_OK, "conditions": {"average_effects_held_fixed": True, "environment_fixed": False, "frequency_independent": True}}),
    ("pin", None),   # handled specially: edited claim must be refused
]

SOURCE_MUTANTS = [  # (file, old, new, test file that must fail)
    ("kimura.py", "x = 4.0 * Ne * s", "x = 2.0 * Ne * s", "tests/test_claim_runtime_kimura.py"),
    ("kimura.py", "return p * (1.0 + x * (1.0 - p) / 2.0)", "return p * (1.0 - x * (1.0 - p) / 2.0)", "tests/test_claim_runtime_kimura.py"),
    ("kimura.py", "return math.exp(-y * (1.0 - p)) * (-math.expm1(-y * p)) / (-math.expm1(-y))", "return (-math.expm1(-y * p)) / (-math.expm1(-y))", "tests/test_claim_runtime_kimura.py"),
    ("fisher.py", "return V_A / _num(\"mean_fitness\", wbar, positive=True)", "return V_A", "tests/test_claim_runtime_service.py"),
    ("service.py", 'pin["content_sha256"] != rec.content_sha256()', 'False', "tests/test_claim_runtime_service.py"),
    ("evidence.py", 'c.get("assay_context_id") != req.assay_context_id', 'False', "tests/test_claim_runtime_evidence.py"),
    ("evidence.py", 'c.get("kind") != req.kind', 'False', "tests/test_claim_runtime_evidence.py"),
]


def guard_mutants() -> list:
    store = default_store()
    out = []
    for guard, req in GUARD_MUTANTS:
        if guard == "pin":
            iri = "https://w3id.org/delphi/resource/claim/kimura-fixation-probability"
            edited = store.with_field(iri, "delphi:context", "EDITED SYNTHETIC FIXTURE")
            orig = ClaimService(edited, require_verified=False).request(D.KIMURA_OK)
            mut = ClaimService(edited, guards=GuardConfig(frozenset(["pin"])), require_verified=False).request(D.KIMURA_OK)
        else:
            orig = ClaimService(store, require_verified=False).request(req)
            mut = ClaimService(store, guards=GuardConfig(frozenset([guard])), require_verified=False).request(req)
        out.append({"mutant": "disable guard " + guard, "original": orig["status"], "mutant_result": mut["status"],
                    "killed": orig["status"] == "refused" and mut["status"] == "computed"})
    return out


def source_mutants(timeout=180) -> list:
    out = []
    for fname, old, new, test in SOURCE_MUTANTS:
        with tempfile.TemporaryDirectory() as td:
            dst = Path(td) / "claim_runtime"
            shutil.copytree(ROOT / "claim_runtime", dst, ignore=shutil.ignore_patterns("__pycache__", "demo"))
            f = dst / fname
            text = f.read_text()
            assert old in text, (fname, old)
            f.write_text(text.replace(old, new, 1))
            (Path(td) / "tests").mkdir()
            for t in (ROOT / "tests").glob("test_claim_runtime*.py"):
                shutil.copy(t, Path(td) / "tests" / t.name)
            shutil.copytree(ROOT / "artifacts" / "claim_reuse", Path(td) / "artifacts" / "claim_reuse")
            env = dict(os.environ, PYTHONPATH=td, OMP_NUM_THREADS="2", CLAIM_RUNTIME_MUTANT_RUN="1")
            r = subprocess.run([sys.executable, "-m", "pytest", "-x", "-q", "-p", "no:cacheprovider", str(Path(td) / test)],
                               cwd=td, env=env, capture_output=True, text=True, timeout=timeout)
            out.append({"mutant": f"{fname}: {old!r} -> {new!r}", "test_file": test, "pytest_exit": r.returncode,
                        "killed": r.returncode != 0, "tail": r.stdout.strip().splitlines()[-1] if r.stdout.strip() else ""})
    return out


def main(out: Path):
    g, s = guard_mutants(), source_mutants()
    res = {"guard_mutants": g, "source_mutants": s,
           "all_killed": all(m["killed"] for m in g) and all(m["killed"] for m in s)}
    out.write_text(json.dumps(res, indent=1))
    return 0 if res["all_killed"] else 1


if __name__ == "__main__":
    sys.exit(main(Path(sys.argv[1])))
