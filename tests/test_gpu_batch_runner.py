"""Pure-helper tests for the job-side runner and its log transport (no model download, no GPU)."""
import hashlib
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "gpu_batch/vendor"))
from gpu_batch import shard_runner as S  # noqa: E402
import recover_from_logs as RL  # noqa: E402
import trpb_ref as R  # noqa: E402


def test_units_partition_the_whole_library_exactly_once():
    perm = R.permuted_order()
    allv = np.concatenate([S.unit_indices(perm, k) for k in range(32)])
    assert len(allv) == R.N_VARIANTS == 160000 and len(np.unique(allv)) == 160000


def test_parse_units():
    assert S.parse_units("0-3,7,9-10") == [0, 1, 2, 3, 7, 9, 10] and S.parse_units("5") == [5]


def test_projection_is_deterministic_and_shard_independent():
    a, b = S.projection_matrix(1280, 32, "site"), S.projection_matrix(1280, 32, "site")
    assert np.array_equal(a, b) and a.shape == (1280, 32) and a.dtype == np.float32
    assert not np.array_equal(a, S.projection_matrix(1280, 32, "mean"))
    # JL sanity: distances preserved to within sampling error
    x = np.random.default_rng(0).standard_normal((50, 1280)).astype(np.float32)
    P = S.projection_matrix(1280, 256, "site")
    d0 = np.linalg.norm(x[:25] - x[25:], axis=1)
    d1 = np.linalg.norm((x @ P)[:25] - (x @ P)[25:], axis=1)
    assert np.all(np.abs(d1 / d0 - 1) < 0.3)


def test_throttled_emission_roundtrips_through_the_gpu_workers_recovery_script(tmp_path):
    lines = []
    raw = S.npz_bytes(a=np.arange(10000, dtype=np.float32), b=np.random.default_rng(1).standard_normal((300, 40)).astype(np.float16))
    S.emit_blob_throttled("unit_x_000.npz", raw, chunk_chars=500, sleep_s=0, out=lines.append)
    lines.insert(2, "GPULOG {\"noise\": 1}")                                      # interleaved log noise
    lines.append(lines[3])                                                         # a duplicated chunk is tolerated
    written, _ = RL.recover("\n".join("[2026-10-31T00:00:00-07:00] " + x for x in lines), tmp_path)
    assert (tmp_path / "unit_x_000.npz").read_bytes() == raw
    assert written["unit_x_000.npz"]["sha256"] == hashlib.sha256(raw).hexdigest()


def test_corrupted_chunk_is_rejected(tmp_path):
    lines = []
    S.emit_blob_throttled("u.npz", b"x" * 5000, chunk_chars=500, sleep_s=0, out=lines.append)
    lines[3] = lines[3][:-3] + "AAA"
    try:
        RL.recover("\n".join(lines), tmp_path)
    except ValueError:
        return
    raise AssertionError("corruption not detected")


def test_vendor_files_match_recorded_hashes_and_reference_is_checked():
    v = json.loads((ROOT / "gpu_batch/vendor/VENDOR.json").read_text())
    for rel, rec in v["files"].items():
        assert hashlib.sha256((ROOT / "gpu_batch/vendor" / rel).read_bytes()).hexdigest() == rec["sha256"], rel
    hdr, ref = R.load_reference()
    assert len(ref) == 397 and "".join(ref[p - 1] for p in R.SITES) == "VFVS"


def test_registry_revisions_are_full_commit_shas():
    for k, (repo, rev, kind) in S.REGISTRY.items():
        assert len(rev) == 40 and set(rev) <= set("0123456789abcdef"), k
        assert kind in ("te", "plain")
