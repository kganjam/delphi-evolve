import os
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent))
import fixture  # noqa: E402
import validate as V  # noqa: E402

REPO = HERE.parents[1]
SRC = REPO if ((REPO / "site/data/landscape.js").exists() and (REPO / "artifacts/proof/receipt.json").exists() and (REPO / "artifacts/core/protocol.json").exists()) else None
DEMO = next((p for p in [REPO / "artifacts/demo.json", REPO / "site/data/demo.json", Path(os.environ.get("DELPHI_DEMO_JSON", "/nonexistent")),
                         Path("/data/worktrees/delphi-evolve/integration/artifacts/demo.json"), Path("/data/worktrees/delphi-evolve/core/artifacts/demo.json")] if p.exists()), None)
pytestmark = pytest.mark.skipif(SRC is None or DEMO is None, reason="needs an integrated checkout (landscape, proof receipt, protocol) and a core demo.json")
BUILD = HERE.parent / "build_deck.py"


def run(root, out, *flags):
    return subprocess.run([sys.executable, str(BUILD), "--root", str(root), "--out-dir", str(out), *flags], capture_output=True, text=True)


def mk(tmp_path, **kw):
    return fixture.make_root(SRC, tmp_path, demo_src=DEMO, **kw)


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
    root2 = fixture.make_root(SRC, tmp_path / "five", seeds=5, demo_src=DEMO) if (tmp_path / "five").mkdir() is None else None
    p2 = root2 / "artifacts/core/protocol.json"
    d = json.loads(p2.read_text()); d["seeds"] = 20; p2.write_text(json.dumps(d))
    e, _ = V.validate_replay(root2)
    assert any("seeds=5" in x for x in e) and any("25 episodes != 20 seeds x 5 = 100" in x for x in e)


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
    assert 'class="draft"' not in h and "false certificates among" in h and "POST HOC arms" in h
    assert h.count('class="slide"') == 6
    assert "spoken words:" in r.stdout and int(r.stdout.split("spoken words:")[1].split()[0]) <= 420


def test_eleven_arm_panel_accepted_only_when_complete_and_verified(tmp_path):
    root = mk(tmp_path / "r", with_followup=True, shards=False, queries=True) if (tmp_path / "r").mkdir() is None else None
    e, info = V.validate_replay(root)
    assert e == [] and info["panel_complete_11"] and info["shards"] == 0 and len(info["query_trace_verified_policies"]) == 11


def test_query_trace_tamper_rejected_when_shards_absent(tmp_path):
    root = mk(tmp_path / "r", with_followup=True, shards=False, queries=True, drop_query_row=True) if (tmp_path / "r").mkdir() is None else None
    e, _ = V.validate_replay(root)
    assert any("q2c" in x and "query trace disagrees" in x for x in e)


def test_no_shards_and_no_traces_is_rejected(tmp_path):
    root = mk(tmp_path / "r", shards=False, queries=False) if (tmp_path / "r").mkdir() is None else None
    e, _ = V.validate_replay(root)
    assert e and any("neither shards nor committed query trace" in x or "cannot be verified" in x for x in e)


def test_empty_shard_in_posthoc_arm_rejected(tmp_path):
    root = mk(tmp_path / "r", with_followup=True) if (tmp_path / "r").mkdir() is None else None
    (root / "artifacts/core/replay/shards/q2c_nomodel__seed03.json").write_text('{"rows": [], "qlogs": {}}')
    e, _ = V.validate_replay(root)
    assert any("zero rows" in x for x in e)


def test_incomplete_followup_arm_is_not_shown(tmp_path):
    root = mk(tmp_path / "r", with_followup=True, followup_partial=True) if (tmp_path / "r").mkdir() is None else None
    e, info = V.validate_replay(root)
    assert e == [] and any("post-hoc arm collective_shared_rr incomplete" in x for x in info["warnings"])
    assert "collective_shared_rr" not in info["followup_policies_complete"] and not info["panel_complete_11"]
