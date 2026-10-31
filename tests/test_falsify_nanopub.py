"""Tests for the Scope-verdict nanopublication preparation (never publishes). Needs node + `npm ci --ignore-scripts` in
falsify/np_sign for the signing tests (skipped otherwise). Run bounded like tests/test_falsify.py."""
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from falsify import nanopub as N  # noqa: E402
from falsify.engine import falsify_turing as run  # noqa: E402

COMMIT = "b" * 40
CREATED = "2026-10-31T14:00:00Z"
have_np = shutil.which("node") and (ROOT / "falsify/np_sign/node_modules").exists()
KEY = Path.home() / ".nanopub/collab-throwaway/rsa.pem"


def resp(r="2", **kw):
    q = {"jacobian": [[1, -2], [2, -3]], "diffusivities": [1, 10], "domain": {"dimension": 1, "boundary": "neumann", "length_over_pi": r}}
    q.update(kw)
    res = run(q)
    res["receipt_id"] = "deadbeef"
    return res


def trig(r="2", **kw):
    return N.build_trig(N.record_from_response(resp(r, **kw), COMMIT), CREATED)


def test_conforms_and_has_four_graphs():
    assert N.conform(trig()) == []
    assert N.conform(trig("1")) == []                       # refuted verdicts are published too (nulls are publishable)


def test_forbidden_iris_flagged_with_positive_controls():
    t = trig()
    assert N.conform(t.replace("schema:name", '<urn:sha256:abc> a schema:Thing ; schema:name', 1))        # urn:
    assert N.conform(t.replace("https://schema.org/", "https://example.org/", 1))                         # example.org
    assert N.conform(t.replace("schema:alternateName", "<ms:predicate/x> ; schema:alternateName", 1))     # ms:
    assert N.conform(t.replace("https://creativecommons.org/licenses/by/4.0/", "https://w3id.org/delphi/ontology/x", 1))   # unregistered ns
    assert N.conform(t.replace("sub:pubinfo {", "sub:pubinfoX {", 1))                                     # missing graph


def test_caller_text_and_labels_never_in_nanopub():
    t = trig(claim="this drug cures cancer", caller="teamX")
    assert "cancer" not in t and "teamX" not in t


def test_refuses_to_prepare_unpublishable_results(monkeypatch):
    from falsify import engine
    with pytest.raises(N.NotPublishable):
        N.record_from_response(run({"jacobian": [[1, 1], [1, 1]], "diffusivities": [1, 2], "domain": {"boundary": "neumann", "length_over_pi": 1}}), COMMIT)
    marg = run({"jacobian": [[1, 3], [-3, -8]], "diffusivities": [1, 16], "domain": {"dimension": 1, "boundary": "neumann", "length_over_pi": "2"}})
    with pytest.raises(N.NotPublishable):                   # unresolvable
        N.record_from_response(marg, COMMIT)
    with pytest.raises(N.NotPublishable, match="commit"):
        N.record_from_response(resp(), "main")
    monkeypatch.setattr(engine, "_delphi_basis", lambda: {"claim_iri": "turing-ddi", "source_pin_ok": False})
    with pytest.raises(N.NotPublishable, match="source pin"):
        N.record_from_response(resp(), COMMIT)


def test_created_must_be_pinned_and_build_is_deterministic(monkeypatch):
    rec = N.record_from_response(resp(), COMMIT)
    monkeypatch.delenv("FALSIFY_NP_CREATED", raising=False)
    with pytest.raises(N.NotPublishable):
        N.build_trig(rec, None)
    assert N.build_trig(rec, CREATED) == N.build_trig(rec, CREATED)


def test_regime_hash_ignores_caller_but_not_parameters():
    a, b, c = resp(caller="x", claim="a"), resp(caller="y", claim="b"), resp(r="3")
    assert N.regime_sha256(a) == N.regime_sha256(b) != N.regime_sha256(c)
    # equivalent spellings of the same regime normalize to one hash
    assert N.regime_sha256(resp(jacobian=[["1", "-2"], ["2", "-3"]], diffusivities=["1", "10.0"])) == N.regime_sha256(a)


def test_lean_witness_held_by_default():
    res = resp()
    res["lean"] = {"status": "checked", "source_sha256": "a" * 64, "axioms": ["propext"], "lean_version": "x"}
    assert "lean_source_sha256" not in N.build_trig(N.record_from_response(res, COMMIT), CREATED)
    assert "lean_source_sha256" in N.build_trig(N.record_from_response(res, COMMIT, include_lean=True), CREATED)


def test_supersedes_and_retraction_shapes():
    old = "https://w3id.org/np/RAvS6O5CBfWNEapZ9c0iPUyuGYWrOGBL5MJ9MT0i8VD3w"
    t = N.build_trig(N.record_from_response(resp(), COMMIT), CREATED, supersedes=old)
    assert f"npx:supersedes <{old}>" in t and N.conform(t) == []
    r = N.build_retraction(old, "engine bug in v0.1.0", CREATED)
    assert f"npx:retracts <{old}>" in r and N.conform(r.replace("sub:Head { this", "sub:Head {\n this", 1)) is not None


def test_sparql_builders_are_parameter_safe():
    with pytest.raises(AssertionError):
        N.q_by_regime('0" } UNION { ?s ?p ?o')
    assert "regime_sha256" in N.q_by_regime("0" * 64) and N.PROFILE_IRI in N.q_all_verdicts()


@pytest.mark.skipif(not (have_np and KEY.exists()), reason="needs node, falsify/np_sign/node_modules and the local throwaway key")
def test_local_sign_roundtrip_tamper_and_delphi_control(tmp_path):
    u = tmp_path / "u.trig"
    u.write_text(trig())
    s = N.sign_local(u, KEY, tmp_path / "s.trig")
    assert s["trusty_uri"].startswith("https://w3id.org/np/RA")
    assert N.verify_signed(tmp_path / "s.trig")["ok"] is True
    (tmp_path / "t.trig").write_text((tmp_path / "s.trig").read_text().replace("survived", "refuted", 1))
    assert N.verify_signed(tmp_path / "t.trig")["ok"] is False                     # tamper must fail
    d = ROOT / "artifacts/falsify_np/delphi-turing-ddi.network.trig"               # positive control: the cited Delphi nanopub
    assert N.verify_signed(d)["ok"] is True and N.verify_signed(d)["trusty_uri"] == N.CLASSICAL_RESULT["turing-ddi"]["np_uri"]


def test_key_inside_repo_is_refused(tmp_path):
    k = ROOT / "falsify" / "fake.pem"
    with pytest.raises(RuntimeError, match="outside the repository"):
        N.sign_local(tmp_path / "u", k, tmp_path / "o")


def test_no_publish_code_exists():
    src = (ROOT / "falsify/nanopub.py").read_text() + (ROOT / "falsify/np_sign/sign.mjs").read_text() + (ROOT / "falsify/np_sign/check.mjs").read_text()
    code = re.sub(r'"""(.|\n)*?"""|//[^\n]*|#[^\n]*', "", src)
    assert not re.search(r"\.publish\(|publish_intro|POST", code)
    assert not re.search(r"BEGIN (RSA )?PRIVATE KEY", "".join(p.read_text() for p in (ROOT / "falsify").rglob("*.py")))
