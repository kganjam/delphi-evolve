"""CPU tests for the gpu/ tools. No GPU, no network, no outcome data.

The tiny-model smoke test needs Hugging Face network access to fetch ESM2-8M and is
skipped when GPU_SMOKE_NETWORK != 1.  It exercises the real masked-marginal code path
on CPU with the *plain* 8M model (never labelled BioNeMo).
"""
import base64
import hashlib
import json
import os
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "gpu"))
import trpb_ref as R  # noqa: E402
import recover_from_logs as RL  # noqa: E402


def test_reference_hash_length_sites():
    hdr, seq = R.load_reference()
    assert len(seq) == 397 and hdr == "Tm9D8*"
    assert "".join(seq[p - 1] for p in R.SITES) == "VFVS"
    assert seq.endswith("LEHHHHHH")


def test_reference_rejects_tampering(tmp_path):
    hdr, seq = R.load_reference()
    bad = tmp_path / "bad.fasta"
    mut = seq[:227] + "A" + seq[228:]            # S228A
    bad.write_text(">x\n" + mut + "\n")
    with pytest.raises(ValueError):
        R.load_reference(bad)                      # hash mismatch
    with pytest.raises(ValueError):
        R.load_reference(bad, check_hash=False)    # wrong site residue (S228->A) caught structurally


def test_genotype_substitution_and_order():
    _, seq = R.load_reference()
    g = R.all_genotypes()
    assert len(g) == 160000 == len(set(g))
    assert g[0] == "AAAA" and g[-1] == "YYYY"
    assert R.genotype_sequence(seq, "VFVS") == seq
    v = R.genotype_sequence(seq, "AIKG")
    assert [i for i in range(len(seq)) if v[i] != seq[i]] == [182, 183, 226, 227]
    assert (v[182], v[183], v[226], v[227]) == tuple("AIKG")


def test_linear_index_digits_match_enumeration():
    import importlib
    E = importlib.import_module("embed_trpb")
    g = R.all_genotypes()
    idx = np.array([0, 1, 19, 20, 399, 400, 7999, 8000, 159999, 54321])
    d = E.lin_to_digits(idx)
    for i, row in zip(idx, d):
        assert "".join(R.AA20[x] for x in row) == g[i]


def test_permutation_is_seeded_and_complete():
    p1, p2 = R.permuted_order(), R.permuted_order()
    assert (p1 == p2).all() and sorted(p1.tolist()) == list(range(160000))
    assert p1[:5].tolist() == R.permuted_order()[:5].tolist()


def _emit(name, raw, chunk=50):
    b64 = base64.b64encode(raw).decode()
    n = (len(b64) + chunk - 1) // chunk
    lines = ["RESULT_FILE " + json.dumps({"name": name, "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest(), "chunks": n})]
    for i in range(n):
        part = b64[i * chunk:(i + 1) * chunk]
        lines.append(f"2026-10-31T07:00:00Z RESULT_CHUNK {name} {i} {n} {hashlib.sha256(part.encode()).hexdigest()[:12]} {part}")
    return lines


def test_log_recovery_roundtrip_and_rejects_corruption(tmp_path):
    raw = np.random.default_rng(1).integers(0, 256, 1000, dtype=np.uint8).tobytes()
    lines = _emit("a.bin", raw) + ["noise line", 'RESULT_JSON j {"x": 1}']
    # shuffle chunk order and duplicate one: still recoverable
    lines2 = lines[:1] + lines[1:][::-1] + [lines[3]]
    written, js = RL.recover("\n".join(lines2), tmp_path)
    assert (tmp_path / "a.bin").read_bytes() == raw and js == ["j"] and written["a.bin"]["bytes"] == 1000
    # missing chunk
    with pytest.raises(ValueError):
        RL.recover("\n".join(lines[:3] + lines[4:]), tmp_path / "m")
    # corrupted chunk payload
    bad = list(lines)
    bad[2] = bad[2][:-3] + ("AAA" if not bad[2].endswith("AAA") else "BBB")
    with pytest.raises(ValueError):
        RL.recover("\n".join(bad), tmp_path / "c")


@pytest.mark.skipif(os.environ.get("GPU_SMOKE_NETWORK") != "1", reason="needs HF network for ESM2-8M")
def test_cpu_smoke_plain_8m_masked_marginals():
    import importlib
    import torch
    E = importlib.import_module("embed_trpb")
    E.DEVICE = "cpu"
    E.PLAIN_REPO, E.PLAIN_REV = "facebook/esm2_t6_8M_UR50D", None
    from transformers import AutoModelForMaskedLM
    tk = E.Tok()
    m = AutoModelForMaskedLM.from_pretrained("facebook/esm2_t6_8M_UR50D").eval()
    lin = np.array([R.all_genotypes().index("VFVS"), R.all_genotypes().index("AIKG"), 5])
    with torch.inference_mode():
        out = E.score_batch(m, tk, E.lin_to_digits(lin))
        tab = E.wt_masked_table(m, tk)
    assert out["meanpool"].shape == (3, 320) and out["site_emb"].shape == (3, 4, 320)
    assert out["lp_un"].shape == out["lp_mask"].shape == (3, 4)
    assert (out["lp_mask"] <= 0).all() and np.isfinite(out["lp_mask"]).all()
    # WT row of the batch must equal the standalone WT table for the observed residues (same pass, same context)
    aa = {a: i for i, a in enumerate(R.AA20)}
    expect = np.array([tab[j, aa[c]] for j, c in enumerate("VFVS")])
    assert np.allclose(out["lp_mask"][0], expect, atol=1e-4)
    # masked table rows are proper distributions over the 20 aa plus <=1 remaining mass on specials
    assert (np.exp(tab).sum(1) <= 1 + 1e-4).all()


def test_recovered_prior_artifacts_consistent():
    """Checks the committed recovered arrays against the job-side manifest and basic invariants."""
    base = ROOT / "artifacts" / "gpu" / "main"
    if not (base / "zeroshot_prior.npz").exists():
        pytest.skip("recovered artifacts absent")
    summ = json.loads((base / "main_summary.json").read_text())
    for name, meta in summ["compact_artifacts"].items():
        assert R.sha256_file(base / name) == meta["sha256"], name
    z = np.load(base / "zeroshot_prior.npz")
    assert summ["complete_library"] and len(set(z["variant_index"].tolist())) == R.N_VARIANTS
    assert np.isfinite(z["lp_masked_obs"]).all() and (z["lp_masked_obs"] <= 0).all()
    assert np.allclose(np.exp(z["wt_masked_table_20aa"]).sum(1), 1, atol=0.05)
    from load_prior import load_prior
    P = load_prior(base)
    assert len(P) == R.N_VARIANTS and abs(P["VFVS"]["pll4_delta"]) < 0.1   # parent vs itself ~0 up to bf16 batch noise
    assert P["VFVS"]["evidence_kind"] == "predicted"


def test_reference_receipt_present_and_passes():
    rec = json.loads((ROOT / "artifacts" / "gpu" / "reference_verification.json").read_text())
    assert rec["checks"]["pooled_culture_118_184"]["rows_inconsistent_with_reference_numbering"] == 0
    assert rec["checks"]["target_fa_identical"]["identical"] is True
    assert rec["checks"]["fasta"]["site_residues"] == {"183": "V", "184": "F", "227": "V", "228": "S"}
