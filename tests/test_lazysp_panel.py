"""Panel-level tests: need the hashed source data (data/raw) and the committed LazySP artifacts."""
import gzip
import json
import shutil
from pathlib import Path

import pytest

from baselines.lazysp import analyze, audit, run as lrun
from baselines.lazysp.policy import LazySP
from evolve import data

ROOT = Path(__file__).resolve().parents[1]
have = (ROOT / "data" / "raw" / "summary_AA.csv").exists()
pytestmark = pytest.mark.skipif(not have, reason="run scripts/fetch_data.py")
SMOKE = ROOT / "artifacts" / "lazysp" / "smoke_seed0"
PANEL = ROOT / "artifacts" / "lazysp" / "panel"
RECOVERY = ROOT / "artifacts" / "recovery" / "episodes.csv"


@pytest.fixture(scope="module")
def land():
    return data.load()


def test_panel_hash_equals_frozen_original(land):
    assert lrun.panel_check(land) == "bb6c144e8f0eba1079d6353d9c7f612a02df30afa7770ce94a064a47ad9b9bcf"


def test_replanning_every_iteration_gives_identical_query_sequence(land):
    """Candidate-path caching is only an optimisation: force a full re-search every iteration on real panel episodes."""
    class Always(LazySP):
        def _path_valid(self, ledger):
            return False
    orig = lrun.LazySP
    try:
        for k in (0, 3):
            a, qa = lrun.run_task(land, "alternate", 0, k, None, 1000)
            lrun.LazySP = Always
            b, qb = lrun.run_task(land, "alternate", 0, k, None, 1000)
            lrun.LazySP = orig
            assert [x[2] for x in qa] == [x[2] for x in qb] and a["status"] == b["status"] == "open"
            assert b["lazysp"]["replans"] > a["lazysp"]["replans"]
    finally:
        lrun.LazySP = orig


def test_audit_accepts_real_shards_and_rejects_tampering(tmp_path, land):
    rep = audit.audit(SMOKE, ["alternate"])
    assert rep["alternate"]["shards_audited"] == 5 and rep["alternate"]["errors"] == []
    # tamper: change one logged interval, and separately truncate the log
    d = tmp_path / "t"; (d / "shards").mkdir(parents=True)
    src = sorted((SMOKE / "shards").glob("*ep0.json.gz"))[0]
    obj = json.load(gzip.open(src, "rt"))
    obj["qlog"][3][3][1] += 1
    with gzip.open(d / "shards" / src.name, "wt") as f:
        json.dump(obj, f)
    assert any("source data" in e[1] for e in audit.audit(d, ["alternate"])["alternate"]["errors"])
    obj = json.load(gzip.open(src, "rt")); obj["qlog"] = obj["qlog"][:-1]
    with gzip.open(d / "shards" / src.name, "wt") as f:
        json.dump(obj, f)
    assert audit.audit(d, ["alternate"])["alternate"]["errors"]      # truncated history: recorded status is not reproduced


def test_partial_panel_is_never_called_complete():
    res = analyze.analyze(SMOKE, ["alternate"], RECOVERY)
    s = res["variants"]["alternate"]["summary"]
    assert s["episodes_present"] == 5 and s["complete_panel"] is False and s["status"].startswith("PARTIAL_5_of_100")


def test_committed_full_panel_is_complete_audited_and_sound():
    rep = audit.audit(PANEL, ["alternate", "forward", "reverse"])
    for v in rep.values():
        assert v["shards_audited"] == 100 and v["errors"] == []
    res = analyze.analyze(PANEL, ["alternate", "forward", "reverse"], RECOVERY)
    for v in res["variants"].values():
        s = v["summary"]
        assert s["complete_panel"] and s["false_certificates"] == 0 and s["full_data_verification_failures"] == 0
        assert sum(s["status_counts"].values()) == 100 and len(s["baselines_sha256_values"]) == 1 and len(s["panel_sha256_values"]) == 1
