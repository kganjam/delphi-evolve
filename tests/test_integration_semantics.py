"""Integrator tests: two different 'no route' statements must never be conflated (planning/INTEGRATION-FINDINGS.md F1,
tasks/semantics-review.md)."""
import itertools
import json
import os
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
ELAN = Path.home() / ".elan" / "bin"


def conservative_edge(lo, hi, u, v):          # what core/browser admit: lower(v) >= upper(u)
    return lo[v] >= hi[u]


def strong_exit(lo, hi, u, v):                # what Lean blocked_cut_sound needs: upper(v) < lower(u)
    return hi[v] < lo[u]


def test_conservative_cut_does_not_rule_out_an_ascending_assignment():
    lo, hi = {"A": 0, "B": 1}, {"A": 2, "B": 3}   # A=[0,2], B=[1,3]
    assert not conservative_edge(lo, hi, "A", "B")        # closed set {A} under the conservative rule
    assert not strong_exit(lo, hi, "A", "B")              # but the exit is NOT certified lower
    ascending = [(fa, fb) for fa, fb in itertools.product(range(lo["A"], hi["A"] + 1), range(lo["B"], hi["B"] + 1)) if fb >= fa]
    assert ascending, "an assignment inside both intervals must allow A -> B to ascend"
    assert (1, 2) in ascending                            # the Lean witness f(A)=1, f(B)=2


def test_strong_exit_requires_strictly_lower_interval():
    lo, hi = {"A": 5, "B": 0}, {"A": 6, "B": 4}
    assert strong_exit(lo, hi, "A", "B")                  # every value of B is below every value of A
    assert all(fb < fa for fa in range(5, 7) for fb in range(0, 5))


def test_lean_distinction_theorems_compile():
    lake = ELAN / "lake"
    if not lake.exists():
        pytest.skip("lake not installed")
    src = (ROOT / "lean/DarwinBridge/Distinction.lean").read_text()
    for name in ("adm_accepts", "blocked_rejects", "true_route_exists_despite_adm_cut"):
        assert f"theorem {name}" in src
    for banned in ("sorry", "native_decide", "admit"):
        assert banned not in src.replace("-- ", "")
    env = dict(os.environ, PATH=f"{ELAN}:{os.environ['PATH']}")
    r = subprocess.run([str(lake), "build", "DarwinBridge.Distinction"], cwd=ROOT / "lean", env=env, capture_output=True, text=True, timeout=600)
    assert r.returncode == 0, r.stdout[-800:] + r.stderr[-800:]


def test_site_labels_the_weak_verdict_precisely():
    app = (ROOT / "site/app.js").read_text()
    assert "Blocked · in this declared graph" not in app
    assert "No route certifiable" in app and "An actual ascending route may still exist" in app
    assert "Two different “no route” statements" in app
    html = (ROOT / "site/index.html").read_text()
    assert "no route certifiable" in html


def test_demo_json_blocked_route_is_labelled_not_strong():
    p = ROOT / "site/data/demo.json"
    if not p.exists():
        pytest.skip("demo.json not assembled")
    d = json.loads(p.read_text())
    weak = [r for r in d["routes"] if r.get("verdict") == "no_route_certifiable"]
    assert weak, "the core blocked example must carry verdict no_route_certifiable"
    for r in weak:
        assert "ascending route may still exist" in r["status"]
        assert "blocked_cut_sound" in r["semantics"]
        if r.get("lean_checked"):
            assert "admCert_sound" in r["lean_theorem"] and "weaker" in r["lean_theorem"]
