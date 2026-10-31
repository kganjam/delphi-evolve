"""The number-trace check must pass on the real deck and FAIL on tampered decks / artifacts."""
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
TRACE = REPO / "presentation" / "trace_numbers.py"


def run(root, deck, out):
    r = subprocess.run([sys.executable, str(TRACE), "--root", str(root), "--deck", str(deck), "--out", str(out)],
                       capture_output=True, text=True)
    return r.returncode, r.stdout


def test_committed_deck_traces_cleanly(tmp_path):
    code, out = run(REPO, "presentation/deck.html", tmp_path / "t.json")
    assert code == 0, out
    res = json.loads((tmp_path / "t.json").read_text())
    assert res["ok"] and res["claims_checked"] >= 60


def _mutated_deck(tmp_path, old, new, count=1):
    root = tmp_path / "root"
    shutil.copytree(REPO / "presentation", root / "presentation", ignore=shutil.ignore_patterns("screenshots", "video", "__pycache__", "tests"))
    for d in ("artifacts", "docs", "site"):
        shutil.copytree(REPO / d, root / d, ignore=shutil.ignore_patterns("*.mp4", "*.zip", "*.npz", "*.gz"))
    p = root / "presentation" / "deck.html"
    t = p.read_text(encoding="utf-8")
    assert t.count(old) >= 1, old
    p.write_text(t.replace(old, new, count), encoding="utf-8")
    return root


def test_changed_headline_number_fails(tmp_path):
    root = _mutated_deck(tmp_path, "159,129 of 160,000 variants", "159,130 of 160,000 variants")
    code, out = run(root, "presentation/deck.html", tmp_path / "t.json")
    assert code == 1 and "159,129 of 160,000 variants" in out


def test_unclaimed_extra_number_fails(tmp_path):
    root = _mutated_deck(tmp_path, "No collective uplift.", "No collective uplift (p = 0.04).")
    code, out = run(root, "presentation/deck.html", tmp_path / "t.json")
    assert code == 1 and "not traced" in out


def test_stale_artifact_fails(tmp_path):
    """Deck says 96/100; if the underlying summary changes, the trace must notice."""
    root = _mutated_deck(tmp_path, "certifies 96/100", "certifies 96/100")
    p = root / "artifacts/lazysp/results/summary.json"
    d = json.loads(p.read_text())
    d["variants"]["alternate"]["resolved_at"]["1000"] = 0.95
    p.write_text(json.dumps(d))
    code, out = run(root, "presentation/deck.html", tmp_path / "t.json")
    assert code == 1


def test_input_changed_since_build_is_stale(tmp_path):
    """Changing any hashed input (even one the slide text does not show) must be reported as STALE."""
    root = _mutated_deck(tmp_path, "certifies 96/100", "certifies 96/100")
    p = root / "artifacts/core/protocol.json"
    p.write_text(p.read_text() + "\n")
    code, out = run(root, "presentation/deck.html", tmp_path / "t.json")
    assert code == 1 and "STALE" in out and "artifacts/core/protocol.json" in out
