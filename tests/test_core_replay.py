import json
from pathlib import Path

import numpy as np
import pytest

from evolve import data, replay

ROOT = Path(__file__).resolve().parents[1]
have = (ROOT / "data" / "raw" / "summary_AA.csv").exists()
pytestmark = pytest.mark.skipif(not have, reason="run scripts/fetch_data.py")


@pytest.fixture(scope="module")
def land():
    return data.load()


def test_panel_deterministic_and_label_free_start_rule(land):
    a, b = replay.make_episodes(land, 3), replay.make_episodes(land, 3)
    assert a == b and len(a) == 15
    for e in a:
        assert land.measured[e["start"]] and land.measured[e["target"]] and len(e["init"]) == 96
        if e["family"] == "A":      # target is the best of the seed's own initial observations only
            assert e["target"] == max(e["init"], key=lambda v: land.s[v]) and e["start"] in e["init"]


def test_frozen_protocol_matches_code(land):
    prot = json.loads((ROOT / "artifacts" / "core" / "protocol.json").read_text())
    assert prot["panel_sha256"] == replay.protocol(land)["panel_sha256"]


@pytest.mark.parametrize("pol", list(replay.POLICIES))
def test_policy_is_sound_matched_and_deterministic(land, pol):
    ep = replay.make_episodes(land, 1)[1]            # B: VFVS -> AIKG, a hard censored case at low budget
    o1, q1, _, log = replay.run_episode(land, ep, pol, bmax=40)
    o2, q2, _, _ = replay.run_episode(land, ep, pol, bmax=40)
    assert o1["assays"] <= 40 and o1["assays"] == len(q1)
    assert q1 == q2 and o1["status"] == o2["status"]                 # reproducible
    assert o1["certificate"] is None or (o1["correct"] and o1["verified_by_full_data"])
    assert log.verify()
    # all policies start from the same admissible initial observations (free reveals)
    free = [e["node"] for e in log.events if e["type"] == "reveal" and e["cost"] == 0]
    assert free[0] == ep["start"] and free[1] == ep["target"] and len(free) == 98 - (1 if ep["start"] in ep["init"] else 0) - (1 if ep["target"] in ep["init"] else 0)


def test_blocked_pair_gets_sound_cut_certificate(land):
    eps = replay.make_episodes(land, 20)
    blocked = [e for e in eps if e["family"] == "A" and not replay.truth(land, e["start"], e["target"])[0]]
    assert blocked, "panel should contain blocked pairs"
    smallest = min(blocked, key=lambda e: replay.truth(land, e["start"], e["target"])[1])
    out, *_ = replay.run_episode(land, smallest, "directed", bmax=300)
    assert out["status"] == "blocked" and out["correct"] and out["verified_by_full_data"]


def test_censored_failures_are_retained_not_dropped(land):
    ep = replay.make_episodes(land, 1)[1]
    out, *_ = replay.run_episode(land, ep, "random", bmax=10)
    assert out["status"] == "unresolved" and out["censored"] and out["certificate"] is None and out["correct"] is None


def test_demo_json_contract(tmp_path):
    from evolve import demo
    originals = {p: p.read_bytes() for p in (ROOT / "artifacts/core/certificates").glob("*.json")}
    d = demo.build(tmp_path / "demo.json", replay_dir=tmp_path / "none")
    assert list((tmp_path / "core/certificates").glob("*.json")), "certificates travel with the output bundle"
    assert all(p.read_bytes() == value for p, value in originals.items()), "test build changed audited certificates"
    for k in ("schema_version", "generated_at", "source", "nodes", "edges", "routes", "claims", "benchmark", "proof", "compute", "limitations"):
        assert k in d
    assert d["proof"]["status"] == "unavailable" and d["proof"]["exit_code"] is None and d["compute"]["status"] == "unavailable"
    assert d["benchmark"]["status"] == "unavailable"     # no replay dir => never fabricated
    assert {"url", "doi", "sha256", "license", "assay", "counts"} <= set(d["source"])
    for n in d["nodes"]:
        assert {"id", "genotype", "observed_score", "replicate_1", "replicate_2", "lower", "upper", "evidence_kind"} <= set(n)
        if n["evidence_kind"] == "unknown":
            assert n["observed_score"] is None
    assert all({"source", "target", "status"} <= set(e) for e in d["edges"])
    assert all({"id", "nodes", "status", "assumptions", "certificate_path"} <= set(r) for r in d["routes"])


def test_run_shard_writes_all_five_episodes(tmp_path, land):
    """Regression: a shard must contain one family-A and four family-B episodes (an earlier edit silently emptied shards)."""
    path, cached = replay.run_shard((str(tmp_path), "random", 2, 2.0, 30))
    j = json.loads(Path(path).read_text())
    assert len(j["rows"]) == 5 and {r["family"] for r in j["rows"]} == {"A", "B"} and all(r["seed"] == 2 for r in j["rows"])
    assert len(j["qlogs"]) == 5
