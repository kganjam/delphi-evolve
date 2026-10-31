"""Assembly checks on synthetic unit files (synthetic = test fixtures only, never reported as results)."""
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from gpu_batch import assemble as A, shard_runner as S  # noqa: E402
import trpb_ref as R  # noqa: E402


def fake_unit(k, rp=4, seed=0):
    perm = R.permuted_order()
    vi = perm[k * S.UNIT:(k + 1) * S.UNIT]
    rng = np.random.default_rng(seed + k)
    n = len(vi)
    return dict(variant_index=vi.astype(np.int32), partial=np.array(False), lp_un=rng.normal(size=(n, 4)).astype(np.float32),
                lp_mask=rng.normal(size=(n, 4)).astype(np.float32), lp_all=rng.normal(size=(n, 4)).astype(np.float32),
                site_rp=rng.normal(size=(n, 4, rp)).astype(np.float16), mean_rp=rng.normal(size=(n, rp)).astype(np.float16))


def write(d, model, ks, **kw):
    d.mkdir(parents=True, exist_ok=True)
    for k in ks:
        np.savez(d / f"unit_{model}_{k:03d}.npz", **fake_unit(k, **kw))


def test_assemble_places_rows_at_library_index_and_tracks_coverage(tmp_path):
    write(tmp_path / "a", "te3b", [0, 5])
    units = A.load_units("te3b", [tmp_path / "a"])
    lib, have = A.assemble(units)
    assert have.sum() == 2 * S.UNIT and lib["lp_mask"].shape == (160000, 4) and lib["site_rp"].shape == (160000, 4, 4)
    u0 = fake_unit(0)
    assert np.array_equal(lib["lp_mask"][u0["variant_index"]], u0["lp_mask"])
    assert np.isnan(lib["lp_mask"][~have]).all()


def test_identical_duplicate_units_merge_but_conflicting_duplicates_are_refused(tmp_path):
    write(tmp_path / "a", "te3b", [1])
    write(tmp_path / "b", "te3b", [1])
    assert len(A.load_units("te3b", [tmp_path / "a", tmp_path / "b"])) == 1
    write(tmp_path / "c", "te3b", [1], seed=99)
    with pytest.raises(ValueError):
        A.load_units("te3b", [tmp_path / "a", tmp_path / "c"])


def test_wrong_block_and_partial_outputs_are_refused(tmp_path):
    bad = fake_unit(2)
    bad["variant_index"] = fake_unit(3)["variant_index"]
    with pytest.raises(ValueError):
        A.assemble({2: {k: v for k, v in bad.items() if k != "partial"}})
    p = fake_unit(0)
    p["partial"] = np.array(True)
    (tmp_path / "x").mkdir()
    np.savez(tmp_path / "x/unit_te3b_000.npz", **p)
    with pytest.raises(ValueError):
        A.load_units("te3b", [tmp_path / "x"])


def test_scalar_priors_are_zscored_relative_to_parent_and_additive_wt_marginal_is_exact():
    units = {k: {f: v for f, v in fake_unit(k).items() if f != "partial"} for k in range(32)}
    lib, have = A.assemble(units)
    assert have.all()
    T = np.random.default_rng(5).normal(size=(4, 20)).astype(np.float32)
    wt = dict(wt_masked_table_20aa=T, wt_lp_mask=np.zeros(4, np.float32), wt_lp_un=np.zeros(4, np.float32), wt_lp_all=np.zeros(4, np.float32))
    raw, z = A.scalar_priors(lib, wt, have)
    aa = {a: i for i, a in enumerate(R.AA20)}
    g = R.all_genotypes()
    i = 12345
    want = sum(T[j, aa[g[i][j]]] - T[j, aa[R.PARENT[j]]] for j in range(4))
    assert abs(raw["mm_wt"][i] - want) < 1e-5
    for v in z.values():
        assert abs(np.nanmean(v)) < 1e-6 and abs(np.nanstd(v) - 1) < 1e-6
    # parent has zero raw score by construction of "relative to parent" only for mm_wt
    ip = g.index(R.PARENT)
    assert raw["mm_wt"][ip] == 0.0


def test_linear_index_matches_core_encode_order():
    core = Path("/data/worktrees/delphi-evolve/core/evolve")
    if not core.exists():
        pytest.skip("core checkout not available")
    src = (core / "data.py").read_text()
    assert 'AA = "ACDEFGHIKLMNPQRSTVWY"' in src and "AA[i // 8000]" in src     # same order as trpb_ref.all_genotypes
    g = R.all_genotypes()
    assert g[0] == "AAAA" and g[1] == "AAAC" and g[8000] == "CAAA" and g[-1] == "YYYY"
