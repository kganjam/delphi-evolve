"""Read-only cross-check of the reviewed falsification service against the oracle layer on bench v1.2 Turing items.
Needs a service snapshot (git archive of SERVICE_REF, default origin/work/collab) and a bench dir (BENCH_V12_DIR with
instances_full.jsonl + key.jsonl). Skipped when either is unavailable (fresh clones without the remote refs)."""
import json
import os
import subprocess
import tarfile
import tempfile
from pathlib import Path

import pytest

from scopedesk.oracles import crosscheck_service

REF = os.environ.get("SERVICE_REF", "origin/work/collab")
BENCH = os.environ.get("BENCH_V12_DIR", "scopedesk/bench/v1_2")


def _snapshot(tmp):
    p = subprocess.run(["git", "archive", REF, "falsify", "turing_scope"], capture_output=True)
    if p.returncode != 0:
        pytest.skip(f"service ref {REF} not available")
    tar = Path(tmp) / "svc.tar"
    tar.write_bytes(p.stdout)
    with tarfile.open(tar) as t:
        t.extractall(Path(tmp) / "snap", filter="data")
    return Path(tmp) / "snap"


def test_service_vs_oracle_no_unexplained_disagreement():
    if not (Path(BENCH) / "instances_full.jsonl").exists():
        pytest.skip("bench v1.2 not present")
    with tempfile.TemporaryDirectory() as tmp:
        snap = _snapshot(tmp)
        out = Path(tmp) / "out.json"
        crosscheck_service.main(snap, BENCH, out)
        res = json.loads(out.read_text())
    s = res["summary"]
    assert s["n"] >= 30
    assert s["unexplained_disagreements"] == 0
    assert s["unstable_count_equal"] == s["unstable_count_compared"]
