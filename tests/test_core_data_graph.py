"""Core data/graph/oracle tests. Fixtures that are synthetic are labelled as unit-test logic fixtures,
never as measurements; data-dependent tests use the real hashed source files and skip if absent."""
import json
from pathlib import Path

import numpy as np
import pytest

from evolve import data
from evolve.graph import Ledger, truth_bfs, verify_cut, verify_route, path_to
from evolve.oracle import EventLog, Oracle

ROOT = Path(__file__).resolve().parents[1]
have_data = all((ROOT / "data" / "raw" / n).exists() for n in ("summary_AA.csv", "KNN_imputed_TrpB.csv", "simplified_AA.csv"))
needs_data = pytest.mark.skipif(not have_data, reason="run scripts/fetch_data.py")


@pytest.fixture(scope="module")
def land():
    return data.load()


def test_encode_decode_roundtrip_and_neighbours():
    for g in ("AAAA", "YYYY", "VFVS", "AIKG"):
        assert data.decode(data.encode(g)) == g
    nb = data.neighbors(data.encode("VFVS"))
    assert nb.shape == (76,) and len(set(nb.tolist())) == 76
    assert (data.hamming(nb, data.encode("VFVS")) == 1).all()


@needs_data
def test_counts_and_separation_of_imputed(land):
    c = land.counts
    assert c["source_rows_summary_AA"] == 193170 and c["measured_nonstop_genotypes"] == 159129
    assert c["knn_imputed_rows_separate_file"] == 871 and c["knn_imputed_overlap_with_measured"] == 0
    assert c["imputed_rows_used_as_observations"] == 0
    assert not land.measured[[data.encode(g) for g in ("AIKG", "VFVS")]].__invert__().any()


@needs_data
def test_manifest_hashes_match_files(land):
    man = json.loads((ROOT / "data" / "manifest.json").read_text())
    for n, m in man["files"].items():
        assert land.sha[n] == m["sha256"]
    assert "CC0" in man["license"]


@needs_data
def test_score_is_raw_not_max_normalised(land):
    i = data.encode("AIKG")
    # raw mu minus stop mean, NOT divided by the library max (the source's /max column would give 1.0 for AIKG)
    expect = round(((land.raw_mu1[i] - land.bg[0]) + (land.raw_mu2[i] - land.bg[1])) / 2 * 1e6)
    assert abs(land.s[i] - expect) <= 1
    assert land.s[i] > 300_000 and land.s[i] != 1_000_000


@needs_data
def test_intervals_integer_and_ordered(land):
    Lo, Hi = land.intervals()
    m = land.measured
    assert Lo.dtype == np.int64 and (Lo[m] < Hi[m]).all() and (Lo[m] <= land.s[m]).all() and (land.s[m] <= Hi[m]).all()
    # monotone in kappa
    Lo0, Hi0 = land.intervals(0.0)
    assert (Lo[m] <= Lo0[m]).all() and (Hi0[m] <= Hi[m]).all()


@needs_data
def test_noise_model_matches_recomputation(tmp_path):
    from evolve import audit
    assert audit.run(tmp_path / "a.json")["noise_model_check"]["ok"]


def test_ledger_logic_fixture_open_and_blocked():
    a, c = data.encode("AAAA"), data.encode("AAAD")
    L = Ledger(a, c)
    L.reveal(a, (0, 10, 5))
    L.reveal(c, (100, 120, 110))
    # c is a neighbour of a with lo>=hi(a): but c was revealed before the closure learned its frontier
    assert L.status() == "open" and L.route() == [a, c]
    # blocked: every neighbour revealed and inadmissible
    s = data.encode("AAAA"); t = data.encode("CCCC")
    B = Ledger(s, t); B.reveal(s, (0, 10, 5)); B.reveal(t, (500, 510, 505))
    assert B.status() == "unresolved"
    for w in data.neighbors(np.int64(s)).tolist():
        B.reveal(w, (-5, 9, 2))
    assert B.status() == "blocked" and B.cut()[0] == {s}


def test_ledger_nan_or_missing_never_certifies():
    s, t = data.encode("AAAA"), data.encode("AAAC")
    L = Ledger(s, t); L.reveal(s, (0, 10, 5))
    assert L.status() == "unresolved"      # target unrevealed => no certificate either way
    L.reveal(t, None)                      # target outside scope: never open
    assert L.status() != "open"


@needs_data
def test_truth_bfs_matches_ledger_on_full_reveal(land):
    Lo, Hi = land.intervals()
    start = data.encode("HTGR")           # real panel start with a closed set of 1 genotype
    r, p, d = truth_bfs(land.measured, Lo, Hi, start)
    assert r.sum() == 1
    tgt = data.encode("GTVN")
    o = Oracle(land, land.kappa); L = Ledger(start, tgt)
    for v in (start, tgt):
        L.reveal(v, o.reveal_free(v))
    for w in data.neighbors(np.int64(start)).tolist():
        if w not in o.queried:
            L.reveal(w, o.query(w, "test"))
    assert L.status() == "blocked" and o.n_queries == 76   # one assay per neighbour
    S, bnd = L.cut()
    assert verify_cut(land.measured, Lo, Hi, S, start, tgt)
    # opening a cut edge must break verification: pretend start is lower than a neighbour's lower bound
    Hi2 = Hi.copy(); w = data.neighbors(np.int64(start))[0]; Hi2[start] = Lo[w] - 1
    assert not verify_cut(land.measured, Lo, Hi2, S, start, tgt)


@needs_data
def test_route_verification_and_mutation(land):
    Lo, Hi = land.intervals()
    s, t = data.encode("VFVS"), data.encode("AIKG")
    r, p, d = truth_bfs(land.measured, Lo, Hi, s)
    route = path_to(p, s, t)
    assert route and verify_route(land.measured, Lo, Hi, route)
    Lo2 = Lo.copy(); Lo2[route[3]] = Hi[route[2]] - 1       # mutate dominance inequality on one edge
    assert not verify_route(land.measured, Lo2, Hi, route)
    bad = list(route); bad[2] = data.encode("YYYY")          # non single-substitution step
    assert not verify_route(land.measured, Lo, Hi, bad)


@needs_data
def test_oracle_discloses_only_queried_and_charges(land):
    o = Oracle(land, land.kappa)
    i = data.encode("AIKG")
    rec = o.query(i, "t")
    assert rec[2] == land.s[i] and o.n_queries == 1
    with pytest.raises(ValueError):
        o.query(i, "t")
    unmeasured = int(np.flatnonzero(~land.measured)[0])
    assert o.query(unmeasured, "t") is None and o.n_queries == 2    # costs an assay, reveals only absence


def test_event_log_tamper_detected():
    log = EventLog()
    log.emit("a", "x", v=1); log.emit("b", "y", v=2)
    assert log.verify()
    log.events[0]["v"] = 9
    assert not log.verify()
