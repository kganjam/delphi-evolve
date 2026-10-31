import os
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent))
import fixture  # noqa: E402
import validate as V  # noqa: E402

CAND = [Path(os.environ.get("DELPHI_INTEGRATED_ROOT", "/nonexistent")), HERE.parents[1], Path("/data/worktrees/delphi-evolve/integration")]
SRC = next((c for c in CAND if (c / "site/data/landscape.js").exists() and (c / "artifacts/proof/receipt.json").exists()
            and ((c / "artifacts/demo.json").exists() or (c / "site/data/demo.json").exists())), None)
pytestmark = pytest.mark.skipif(SRC is None, reason="no integrated checkout with demo/proof/landscape artifacts")
BUILD = HERE.parent / "build_deck.py"


def run(root, out, *flags):
    return subprocess.run([sys.executable, str(BUILD), "--root", str(root), "--out-dir", str(out), *flags], capture_output=True, text=True)


def mk(tmp_path, **kw):
    return fixture.make_root(SRC, tmp_path, **kw)


def test_complete_synthetic_replay_validates(tmp_path):
    e, info = V.validate_replay(mk(tmp_path))
    assert e == [] and info["empty_shards"] == 0


def test_empty_shards_rejected(tmp_path):
    e, _ = V.validate_replay(mk(tmp_path, empty_shards=5))
    assert any("zero rows" in x for x in e)


def test_cardinality_mismatch_rejected(tmp_path):
    e, _ = V.validate_replay(mk(tmp_path, drop_episode=True))
    assert any("q2c" in x and "!=" in x for x in e)


def test_five_seed_run_rejected_against_twenty_seed_protocol(tmp_path):
    root = mk(tmp_path)
    import json
    p = root / "artifacts/core/protocol.json"
    d = json.loads(p.read_text()); d["seeds"] = 20; p.write_text(json.dumps(d))
    root2 = fixture.make_root(SRC, tmp_path / "five", seeds=5) if (tmp_path / "five").mkdir() is None else None
    p2 = root2 / "artifacts/core/protocol.json"
    d = json.loads(p2.read_text()); d["seeds"] = 20; p2.write_text(json.dumps(d))
    e, _ = V.validate_replay(root2)
    assert any("seeds=5" in x for x in e) and any("!= 0..19" in x for x in e)


def test_final_mode_refuses_bad_data_and_draft_mode_has_no_replay_numbers(tmp_path):
    root = mk(tmp_path / "r", empty_shards=3) if (tmp_path / "r").mkdir() is None else None
    out = tmp_path / "o"; out.mkdir()
    r = run(root, out)
    assert r.returncode == 2 and "REJECTED" in r.stderr and not (out / "deck.html").exists()
    r = run(root, out, "--allow-draft")
    assert r.returncode == 0 and (out / "deck.DRAFT.html").exists() and not (out / "deck.html").exists()
    h = (out / "deck.DRAFT.html").read_text()
    assert 'class="draft"' in h and "REPLAY RESULT NOT FINAL" in h and "false certificates among" not in h


def test_final_render_from_complete_fixture(tmp_path):
    root = mk(tmp_path / "r", with_followup=True) if (tmp_path / "r").mkdir() is None else None
    out = tmp_path / "o"; out.mkdir()
    r = run(root, out)
    assert r.returncode == 0, r.stderr
    h = (out / "deck.html").read_text()
    assert 'class="draft"' not in h and "false certificates among" in h and "EXPLORATORY FOLLOW-UP" in h
    assert h.count('class="slide"') == 6


def test_incomplete_followup_arm_is_not_shown(tmp_path):
    root = mk(tmp_path / "r", with_followup=True, followup_partial=True) if (tmp_path / "r").mkdir() is None else None
    e, info = V.validate_replay(root)
    assert e == [] and any("follow-up arm" in x for x in info["warnings"]) and info["followup_policies_complete"] == []
