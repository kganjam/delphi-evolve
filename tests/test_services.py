"""Offline tests for scientific_services (no network, no credentials required except the leak scan, which
skips if the env files are absent). Run: python3 -m pytest tests/test_services.py -q"""
import hashlib
import json
import re
from pathlib import Path

import pytest

import scientific_services.common as C
import scientific_services.gemini_client as G
from scientific_services import nebius_mcp as M
from scientific_services.predict_structure import FASTA_SHA256, find_key, find_status, genotype_sequence, load_parent

ROOT = Path(__file__).resolve().parents[1]
NEB = ROOT / "artifacts" / "services" / "nebius"
SITES = (183, 184, 227, 228)


def test_redact_strips_secrets_and_signed_urls():
    C._secret_values.add("sentinel-secret-value-123")
    out = C.redact({"a": "x sentinel-secret-value-123 y", "b": ["Bearer abcdefghijklmnop1234", "https://h.example/p/q?X-Amz-Signature=abc&z=1"],
                    "c": "fs2-mit-hackathon-participant-05-deadbeef"})
    s = json.dumps(out)
    assert "sentinel-secret-value-123" not in s and "abcdefghijklmnop1234" not in s
    assert "X-Amz-Signature" not in s and "https://h.example/p/q?[QUERY-STRIPPED]" in s
    assert "participant-05" not in s


def test_strip_url():
    assert C.strip_url("https://a.b/c/d?sig=1#f") == "https://a.b/c/d"


def test_parent_fasta_pinned_and_sites():
    header, seq = load_parent(NEB / "parent_tm9d8s_AAs.fasta")
    assert hashlib.sha256((NEB / "parent_tm9d8s_AAs.fasta").read_bytes()).hexdigest() == FASTA_SHA256
    assert len(seq) == 397 and "".join(seq[p - 1] for p in SITES) == "VFVS"
    aikg = genotype_sequence(seq, "AIKG")
    assert len(aikg) == 397 and "".join(aikg[p - 1] for p in SITES) == "AIKG"
    assert sum(a != b for a, b in zip(seq, aikg)) == 4          # only the four sites change


def test_parent_fasta_tamper_detected(tmp_path):
    bad = tmp_path / "x.fasta"; bad.write_text(">Tm9D8*\nMKGY\n")
    with pytest.raises(ValueError):
        load_parent(bad)


def test_operation_id_both_response_shapes():
    """Regression: the AIKG submit returned {'operation': {'id': ...}}, VFVS returned an error payload with operation_id."""
    a = {"model_id": "openfold2", "operation": {"id": "op-c03164a04e76c310", "status": "RUNNING"}}
    b = {"error": {"admission": "accepted", "operation_id": "op-5e3d2111a651d8dd"}}
    assert (find_key(a, "operation_id") or (find_key(a, "operation") or {}).get("id")) == "op-c03164a04e76c310"
    assert find_key(b, "operation_id") == "op-5e3d2111a651d8dd"
    assert find_status(a) == "RUNNING"


def test_sse_parse():
    body = b'event: message\ndata: {"jsonrpc":"2.0","id":1,"result":{"ok":true}}\n\n'
    assert M._parse_body(body, "text/event-stream")["result"] == {"ok": True}
    assert M._parse_body(b'{"a":1}', "application/json") == {"a": 1}


def test_gemini_budget_enforced(tmp_path, monkeypatch):
    monkeypatch.setattr(G, "LEDGER", tmp_path / "ledger.json")
    monkeypatch.setattr(G, "load_env_value", lambda *a, **k: "dummy-not-a-key")
    g = G.Gemini()
    calls = []

    def fake_post(path, body):
        calls.append(path)
        if path.endswith(":countTokens"):
            return 200, {"totalTokens": 1000}
        return 200, {"modelVersion": "fake-1", "candidates": [{"content": {"parts": [{"text": "ok"}]}, "finishReason": "STOP"}],
                     "usageMetadata": {"promptTokenCount": 1000, "candidatesTokenCount": 10, "thoughtsTokenCount": 5}}

    g._post = fake_post
    for i in range(G.MAX_CALLS):
        r = g.generate("m", "p", max_output_tokens=100, label=f"c{i}", out_dir=tmp_path)
        assert r["response_text"] == "ok" and (tmp_path / f"c{i}.json").exists()
    with pytest.raises(G.BudgetExceeded):
        g.generate("m", "p", max_output_tokens=100, label="over", out_dir=tmp_path)
    led = json.loads((tmp_path / "ledger.json").read_text())
    assert led["calls"] == G.MAX_CALLS and led["output_tokens"] == G.MAX_CALLS * 15


def test_gemini_input_cap(tmp_path, monkeypatch):
    monkeypatch.setattr(G, "LEDGER", tmp_path / "ledger.json")
    monkeypatch.setattr(G, "load_env_value", lambda *a, **k: "dummy-not-a-key")
    g = G.Gemini(); g._post = lambda p, b: (200, {"totalTokens": G.MAX_IN + 1})
    with pytest.raises(G.BudgetExceeded):
        g.generate("m", "p", out_dir=tmp_path)


def test_gemini_refuses_secret_in_prompt(monkeypatch):
    C._secret_values.add("another-sentinel-secret-9876")
    with pytest.raises(ValueError):
        G.assert_public_text("hello another-sentinel-secret-9876")


# ---------------- artifact consistency (real recorded outputs) ----------------
@pytest.mark.parametrize("g", ["VFVS", "AIKG"])
def test_structure_artifacts_consistent(g):
    m = json.loads((NEB / f"trpb_{g}_openfold2_metrics.json").read_text())
    pdb = (NEB / m["pdb_file"]).read_bytes()
    assert hashlib.sha256(pdb).hexdigest() == m["pdb_sha256"]
    _, parent = load_parent(NEB / "parent_tm9d8s_AAs.fasta")
    seq = genotype_sequence(parent, g)
    assert m["sequence"] == seq and m["sequence_sha256"] == hashlib.sha256(seq.encode()).hexdigest()
    three = {"ALA": "A", "ARG": "R", "ASN": "N", "ASP": "D", "CYS": "C", "GLN": "Q", "GLU": "E", "GLY": "G", "HIS": "H", "ILE": "I", "LEU": "L",
             "LYS": "K", "MET": "M", "PHE": "F", "PRO": "P", "SER": "S", "THR": "T", "TRP": "W", "TYR": "Y", "VAL": "V"}
    res = {}
    for l in pdb.decode().splitlines():
        if l.startswith("ATOM") and l[12:16].strip() == "CA":
            res[int(l[22:26])] = three[l[17:20]]
    assert "".join(res[i] for i in sorted(res)) == seq, "PDB residues/numbering must equal the submitted sequence"
    assert "".join(res[p] for p in SITES) == g
    assert m["epistemic_status"].startswith("PREDICTED")
    assert m["plddt"]["mean"] < 50, "recorded honestly: low confidence; if this changes the demo caveats must be revisited"
    assert any("not functional confidence" in x or "NOT functional confidence" in x for x in m["limits"])


def test_no_credentials_or_signed_urls_in_tracked_artifacts():
    if not (C.CONFIG_DIR / "nebius.env").exists():
        pytest.skip("env files absent")
    from scientific_services.leak_scan import scan
    assert scan([str(ROOT / "artifacts" / "services"), str(ROOT / "scientific_services"), str(ROOT / "docs"), str(ROOT / "tasks" / "results")]) == []


def test_structure_demo_labels():
    h = (ROOT / "scientific_services" / "demo" / "structure.html").read_text()
    assert "PREDICTED" in h and "OBSERVED" in h and "dummy" in h and "self-confidence" in h
    assert "http://" not in h and "https://" not in h.replace("https://data", "")   # no CDN / external script
    assert not re.search(r"<script[^>]+src=", h)


def test_gemini_calls_recorded_with_usage_and_model():
    led = json.loads((ROOT / "artifacts/services/gemini/usage_ledger.json").read_text())
    assert led["calls"] <= 6 and led["input_tokens"] <= 150_000 and led["output_tokens"] <= 30_000
    for name in ("review_flash_independent", "review_flash_independent_run2", "review_pro_serious_claim", "shortlist_result"):
        assert (ROOT / "artifacts/services/gemini" / f"{name}.json").exists()
    for name in ("review_flash_independent", "review_flash_independent_run2", "review_pro_serious_claim"):
        r = json.loads((ROOT / "artifacts/services/gemini" / f"{name}.json").read_text())
        assert r["epistemic_status"].startswith("model-opinion") and r["usage_metadata"] and r["model_version_returned"] and r["prompt_sha256"]
