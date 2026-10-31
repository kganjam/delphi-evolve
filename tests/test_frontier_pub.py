"""Tests for the Frontier publication layer. Fixtures in tests/fixtures/frontier_pub/bundles.json were produced by Frontier's REAL Store
(commit 42cd967, private throwaway PostgreSQL) via scripts/frontier_pub_make_fixtures.py; all reviews in them are workflow controls.
Run bounded: systemd-run --user --scope -p TasksMax=128 -p MemoryMax=4G -p MemorySwapMax=0 -p RuntimeMaxSec=600 python -m pytest tests/test_frontier_pub.py -q
No test contacts a real registry; the registry tests use a loopback fake and a stubbed URL opener.
"""
import copy
import http.server
import json
import os
import re
import shutil
import subprocess
import sys
import threading
from pathlib import Path

import pytest

from frontier_pub import binding, ledger as ledger_mod, registry
from frontier_pub.binding import build_trig, check_bundle, conform, count_triples, vet_iri
from frontier_pub.collect import HttpReader, collect
from frontier_pub.records import DIMENSIONS, NotPublishable, digest, ref, verify_record

ROOT = Path(__file__).resolve().parent.parent
FIX = json.loads((ROOT / "tests/fixtures/frontier_pub/bundles.json").read_text())
B = FIX["bundles"]
C = "a" * 40
T = "2026-10-31T20:00:00Z"
have_np = bool(shutil.which("node") and (ROOT / "falsify/np_sign/node_modules").exists() and shutil.which("openssl"))


def bundle(name="accepted_v1"):
    return copy.deepcopy(B[name])


def redigest(rec):
    rec["version"] = digest({k: v for k, v in rec.items() if k != "version"})
    return rec


def mutate_assessment(b, fn):
    """Change the Assessment payload and keep every digest/ref consistent, as a real node would have recorded it."""
    old = ref(b["assessment"])
    fn(b["assessment"]["payload"])
    redigest(b["assessment"])
    new = ref(b["assessment"])
    ev = b["review_event"]
    ev["payload"]["details"]["assessment"] = new
    redigest(ev)
    return b


def mutate_target(b, fn):
    fn(b["target"])
    redigest(b["target"])
    t = ref(b["target"])
    b["assessment"]["payload"]["target"] = t
    redigest(b["assessment"])
    for e in ("review_event", "proposal_event"):
        b[e]["payload"]["target"] = t
    b["review_event"]["payload"]["details"]["assessment"] = ref(b["assessment"])
    for e in ("review_event", "proposal_event"):
        redigest(b[e])
    return b


def dims_of(trig):
    return dict(re.findall(r'sub:dim_(\w+)_rating\s+a schema:Rating ;\s+schema:alternateName "(\w+)"', trig))


# ------------------------------------------------------------------ record identity
def test_every_fixture_record_verifies_under_our_independent_digest_rule():
    n = 0
    for name, b in B.items():
        if not isinstance(b, dict):
            continue
        for k in ("target", "assessment", "review_event", "proposal_event"):
            verify_record(b[k])
            n += 1
        for e in b["evidence"]:
            verify_record(e)
            n += 1
    assert n == 30      # 7 bundles x 4 records + 2 evidence records (accepted_v1 and its HTTP twin)


def test_tampered_record_is_refused_and_is_found_by_digest():
    b = bundle()
    b["target"]["payload"]["statement"] = "TAMPERED"
    with pytest.raises(NotPublishable, match="digest mismatch"):
        build_trig(b, code_commit=C, created=T)


@pytest.mark.skipif(not os.environ.get("FRONTIER_SRC"), reason="set FRONTIER_SRC to an extract of the pinned Frontier commit for the cross-check")
def test_digest_rule_agrees_with_frontiers_own_code():
    sys.path.insert(0, os.environ["FRONTIER_SRC"])
    from frontier.models import Record, digest as fdigest
    for name, b in B.items():
        if isinstance(b, dict):
            Record.model_validate(b["target"])                      # Frontier's validator also recomputes the digest
            assert fdigest({k: v for k, v in b["target"].items() if k != "version"}) == digest({k: v for k, v in b["target"].items() if k != "version"})


# ------------------------------------------------------------------ the binding
def test_accepted_claim_builds_conforms_and_pins_everything():
    b = bundle()
    trig = build_trig(b, code_commit=C, created=T)
    assert conform(trig) == []
    assert count_triples(trig) < 400
    # exactly seven dimension reviews, each with its own status; none is the composite
    st = dims_of(trig)
    assert set(st) == set(DIMENSIONS) and st["independent_replication"] == "not_applicable" and st["source_fidelity"] == "passed"
    # issuer, operator, node namespace, exact version digests all survive
    t, a, rev, pr = b["target"], b["assessment"], b["review_event"], b["proposal_event"]
    for needle in (a["issuer"], rev["payload"]["operator"], pr["payload"]["operator"], t["issuer"], a["namespace"], t["version"], a["version"],
                   rev["version"], pr["version"], rev["payload"]["witnessed_at"], b["evidence"][0]["version"]):
        assert needle in trig, needle
    assert "prov:actedOnBehalfOf sub:reviewerOperator" in trig
    assert "NOT a truth rating" in trig and 'schema:value "none"' in trig


def test_no_composite_or_numeric_rating_anywhere():
    trig = build_trig(bundle(), code_commit=C, created=T)
    for term in ("ratingValue", "bestRating", "worstRating", "confidence", "probability", "score"):
        assert not re.search(rf"schema:{term}\b", trig)
    assert conform(trig.replace("schema:alternateName", "schema:ratingValue", 1))          # positive control: the check fires


def test_changing_one_dimension_changes_only_that_dimension():
    base = dims_of(build_trig(bundle(), code_commit=C, created=T))
    b = mutate_assessment(bundle(), lambda p: p["dimensions"]["statistical_adequacy"].update(status="not_applicable"))
    new = dims_of(build_trig(b, code_commit=C, created=T))
    assert {k for k in base if base[k] != new[k]} == {"statistical_adequacy"}
    assert new["statistical_adequacy"] == "not_applicable"


def test_statement_and_limits_are_quoted_not_interpreted_and_assumptions_stay_separate():
    trig = build_trig(bundle(), code_commit=C, created=T)
    assert 'schema:text "FIXTURE STATEMENT v1."' in trig
    assert 'schema:name "assumption[0]"' in trig and 'schema:name "limitation[1]"' in trig


def test_prior_review_labels_do_not_travel():
    b = mutate_target(bundle(), lambda t: t["payload"].update(prior_review={"finding": "SECRET-PRIOR-LABEL"}))
    assert "SECRET-PRIOR-LABEL" not in build_trig(b, code_commit=C, created=T)


def test_deterministic_and_created_must_be_pinned():
    assert build_trig(bundle(), code_commit=C, created=T) == build_trig(bundle(), code_commit=C, created=T)
    with pytest.raises(NotPublishable, match="pinned"):
        build_trig(bundle(), code_commit=C, created="now")
    with pytest.raises(NotPublishable, match="40-hex"):
        build_trig(bundle(), code_commit="main", created=T)


def test_imported_target_is_labelled_and_independence_uses_importing_operator():
    b = bundle("accepted_imported")
    trig = build_trig(b, code_commit=C, created=T)
    assert "IMPORTED from another node" in trig and "importing operator" in trig
    assert b["target"]["namespace"] != b["assessment"]["namespace"] and "node-b" in trig and "node-a" in trig


def test_unsourced_problem_is_labelled_a_curator_statement():
    trig = build_trig(bundle("accepted_problem_unsourced"), code_commit=C, created=T)
    assert 'schema:value "no source recorded"' in trig and "Curator statement" in trig and "schema:CreativeWork" in trig
    assert "schema:ClaimReview" not in trig and "npx:hasNanopubType schema:Review" in trig      # Problems are plain Reviews


def test_unlinked_evidence_stays_a_digest_pin():
    b = bundle()
    b["evidence"] = []
    trig = build_trig(b, code_commit=C, created=T)
    assert "digest-pinned reference only" in trig and "schema:citation sub:evref0" in trig and conform(trig) == []


# ------------------------------------------------------------------ gates: every refusal is its own case
def refuses(b, match, **kw):
    with pytest.raises(NotPublishable, match=match):
        build_trig(b, code_commit=C, created=T, **kw)


def test_private_records_never_leave():
    for k in ("target", "assessment", "review_event", "proposal_event"):
        b = bundle()
        b[k]["visibility"] = "private"
        redigest(b[k])
        refuses(b, "not public|does not pin|digest")


def test_only_accepted_is_a_first_publication():
    refuses(bundle("disputed_v2"), "not published as a first publication")


def test_status_change_requires_a_disputed_or_rejected_assessment_and_a_supersedes():
    refuses(bundle("disputed_v2"), "must supersede", status_change=True)
    refuses(bundle("accepted_v1"), "disputed or rejected assessment", status_change=True, supersedes="https://w3id.org/np/RA" + "A" * 43)


def test_stale_review_and_non_head_are_refused():
    refuses(bundle("accepted_v2_after_dispute_state"), "stale or superseded")
    b = bundle()
    b["target_is_head"] = False
    refuses(b, "not the node's current head")


def test_accepted_with_a_failed_or_insufficient_dimension_is_refused_even_if_a_node_recorded_it():
    for status in ("failed", "insufficient", "unreviewed"):
        b = mutate_assessment(bundle(), lambda p, s=status: p["dimensions"]["statistical_adequacy"].update(status=s))
        refuses(b, "passed or not_applicable")


def test_target_fidelity_and_applicability_must_pass():
    for dname in ("target_fidelity", "applicability"):
        b = mutate_assessment(bundle(), lambda p, d=dname: p["dimensions"][d].update(status="not_applicable"))
        refuses(b, "target_fidelity and applicability")


def test_dimension_set_and_reviewer_identity_are_enforced():
    refuses(mutate_assessment(bundle(), lambda p: p["dimensions"].pop("applicability")), "seven named dimensions")
    refuses(mutate_assessment(bundle(), lambda p: p["dimensions"]["source_fidelity"].update(reviewer="mallory")), "not the assessment issuer")
    refuses(mutate_assessment(bundle(), lambda p: p["dimensions"]["source_fidelity"].update(rationale="")), "no rationale")


def test_independence_is_rechecked_not_trusted():
    b = bundle()
    b["proposal_event"]["payload"]["operator"] = b["review_event"]["payload"]["operator"]
    redigest(b["proposal_event"])
    refuses(b, "not independent review")
    b = bundle()
    b["target"]["issuer"] = b["assessment"]["issuer"]
    redigest(b["target"])
    refuses(b, "same actor|does not pin")


def test_assessment_must_pin_exactly_this_version_and_events_must_match():
    b = bundle()
    b["assessment"]["payload"]["target"] = dict(b["assessment"]["payload"]["target"], version="0" * 64)
    redigest(b["assessment"])
    refuses(b, "does not pin exactly")
    b = bundle()
    b["review_event"]["payload"]["details"]["assessment"] = dict(b["review_event"]["payload"]["details"]["assessment"], version="1" * 64)
    redigest(b["review_event"])
    refuses(b, "does not name this assessment")
    b = bundle()
    b["review_event"]["payload"]["event_type"] = "acceptance_changed"
    redigest(b["review_event"])
    refuses(b, "review event has event_type")


def test_unsupported_kinds_and_unreferenced_evidence_are_refused():
    b = bundle()
    b["target"]["kind"] = "Evidence"
    refuses(b, "no publication binding|expected|digest")
    b = bundle()
    b["evidence"].append(copy.deepcopy(B["accepted_v2"]["target"]))      # a Claim passed off as evidence
    refuses(b, "expected a Evidence")


def test_wrong_policy_is_refused():
    refuses(mutate_assessment(bundle(), lambda p: p.update(policy_version="other-policy")), "unsupported review policy")


# ------------------------------------------------------------------ IRI policy
@pytest.mark.parametrize("u,ok", [("https://doi.org/10.1/x", True), ("https://github.com/a/b", True), ("https://example.org/x", False),
                                  ("urn:frontier:local-review", False), ("https://w3id.org/delphi/resource/claim/turing-ddi", False),
                                  ("https://w3id.org/probknow/ontology", False), ("https://w3id.org/morphoswarm", False),
                                  ("https://w3id.org/np/RAaQ-9SCjYC7GBJ0ZtrPcVNxZBB7z-VNAdWa8ImGAi610", True), ("http://localhost/x", False),
                                  ("https://a.org/x y", False), ("ftp://a.org/x", False), (None, False), ("https://a.org/" + "x" * 600, False)])
def test_iri_policy(u, ok):
    assert vet_iri(u) is ok


def test_unvettable_source_uri_travels_as_literal_not_iri():
    for bad in ("https://example.org/data", "https://w3id.org/delphi/resource/claim/x", "urn:frontier:thing"):
        b = mutate_target(bundle(), lambda t, bad=bad: t["payload"]["source"].update(uri=bad))
        trig = build_trig(b, code_commit=C, created=T)
        assert f"<{bad}>" not in trig and conform(trig) == []
        assert f'schema:value {json.dumps(bad)}' in trig
    trig = build_trig(bundle(), code_commit=C, created=T)
    assert "prov:wasDerivedFrom <https://github.com/kganjam/delphi-evolve/blob/main/docs/frontier-publication-layer.md>" in trig


def test_signed_conformance_checks_iris_and_has_a_positive_control():
    assert binding.conform_signed(build_trig(bundle(), code_commit=C, created=T)) == []
    good = build_trig(bundle(), code_commit=C, created=T)
    assert binding.conform_signed(good + "\n<urn:sha256:abc> a <https://w3id.org/delphi/x> .")
    assert binding.conform_signed(good.replace("schema:alternateName", "schema:ratingValue", 1))


def test_conformance_positive_controls():
    good = build_trig(bundle(), code_commit=C, created=T)
    assert conform(good) == []
    for broken, why in ((good.replace("sub:Head", "sub:Hxad", 1), "graph"), (good.replace("schema:name", "<urn:x:y> schema:name", 1), "IRI"),
                        (good + "\n<https://example.org/z> a <https://example.org/y> .", "IRI"),
                        (good.replace("https://schema.org/", "https://w3id.org/delphi/"), "w3id|namespaces|prefix")):
        assert conform(broken), why


# ------------------------------------------------------------------ collection is read-only and equals the HTTP path
def test_http_reader_is_loopback_only_and_http_and_store_paths_agree():
    with pytest.raises(ValueError):
        HttpReader("http://10.0.0.5:8000")
    assert B["accepted_v1"] == B["accepted_v1_via_http"]


class ReadOnlyStub:
    """Has only the two read methods; any write attempt raises AttributeError."""

    def __init__(self, b):
        self.b = b

    def get(self, r):
        for k in ("target", "assessment"):
            if ref(self.b[k]) == r:
                return {"record": self.b[k], "local_review": self.b["local_review"], "is_head": True, "action": None}
        for e in self.b["evidence"]:
            if ref(e) == r:
                return {"record": e, "local_review": {}, "is_head": True, "action": None}
        raise KeyError

    def events(self, after=0, limit=50):
        rows = [{"sequence": i + 1, "envelope": e} for i, e in enumerate((self.b["proposal_event"], self.b["review_event"]))]
        return {"events": rows[after:after + limit], "next_cursor": None}


def test_collect_uses_only_read_methods_and_pins_the_node_answer():
    b = bundle()
    got = collect(ReadOnlyStub(b), ref(b["target"]), ref(b["assessment"]))
    assert got["assessment"] == b["assessment"] and got["evidence"] == b["evidence"] and got["proposal_event"] == b["proposal_event"]
    bad = ReadOnlyStub(b)
    bad.get = lambda r: {"record": B["accepted_v2"]["target"], "local_review": {}, "is_head": True}
    with pytest.raises(NotPublishable, match="different record"):
        collect(bad, ref(b["target"]))


# ------------------------------------------------------------------ signing, chain, ledger, test-registry mechanics
@pytest.fixture
def key(tmp_path_factory):
    d = tmp_path_factory.mktemp("keys")
    k = d / "rsa.pem"
    subprocess.run(["openssl", "genpkey", "-algorithm", "RSA", "-pkeyopt", "rsa_keygen_bits:2048", "-out", str(k)], check=True, capture_output=True)
    assert not str(k).startswith(str(ROOT))
    return k


class FakeRegistry:
    """Loopback stand-in for a TEST registry; records every request method so HEAD can be shown never to be used."""

    def __init__(self, is_test=True, flag_key="isTestInstance", drop_get=False, wrong_bytes=None, throttle_first=False):
        self.store, self.methods, self.is_test, self.flag_key = {}, [], is_test, flag_key
        self.drop_get, self.wrong_bytes, self.throttle = drop_get, wrong_bytes, throttle_first
        outer = self

        class H(http.server.BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def _send(self, code, body=b"", headers=None):
                self.send_response(code)
                for k, v in (headers or {}).items():
                    self.send_header(k, v)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def do_GET(self):
                outer.methods.append("GET " + self.path)
                if self.path == "/.json":
                    doc = {"status": "ready"}
                    if outer.flag_key:
                        doc[outer.flag_key] = outer.is_test
                    return self._send(200, json.dumps(doc).encode(), {"Content-Type": "application/json"})
                code = self.path.rsplit("/", 1)[-1]
                if outer.drop_get or code not in outer.store:
                    return self._send(404)
                return self._send(200, outer.wrong_bytes or outer.store[code])

            def do_HEAD(self):
                outer.methods.append("HEAD " + self.path)
                self._send(200)                       # the real registry answers 200 for codes that do not exist (SPEC-007 rule 1b)

            def do_POST(self):
                outer.methods.append("POST " + self.path)
                if outer.throttle:
                    outer.throttle = False
                    return self._send(429, b"", {"Retry-After": "1"})
                body = self.rfile.read(int(self.headers["Content-Length"]))
                outer.store[re.search(rb"https://w3id\.org/np/(RA[A-Za-z0-9_-]{43})", body).group(1).decode()] = body
                self._send(201)

        self.srv = http.server.HTTPServer(("127.0.0.1", 0), H)
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()
        self.url = f"http://127.0.0.1:{self.srv.server_port}"

    def close(self):
        self.srv.shutdown()


@pytest.fixture
def fake():
    r = FakeRegistry()
    yield r
    r.close()


needs_np = pytest.mark.skipif(not have_np, reason="needs node, falsify/np_sign/node_modules and openssl")


def auth_for(path, text="USER-AUTHORIZED-TEST-FIXTURE: publish these test files to the test registry"):
    sha = ledger_mod.hashlib.sha256(Path(path).read_bytes()).hexdigest()
    return registry.Authorization(instruction=text, given_by="user", given_at="2026-10-31T12:00:00-07:00", files_sha256=(sha,))


@needs_np
def test_full_local_pipeline_then_chain_supersession_and_correction(tmp_path, key, fake):
    from frontier_pub.pipeline import prepare
    L = ledger_mod.Ledger(tmp_path / "ledger.json")
    out = tmp_path / "out"
    r1 = prepare(bundle("accepted_v1"), L, out_dir=out, key_pem=key, code_commit=C, created=T)
    uri1 = r1["entry"]["np_uri"]
    assert r1["verified"]["exit"] == 0 and r1["entry"]["supersedes"] is None and r1["entry"]["stage"] is None
    # unsigned/signed identical content except the signature block: signing is deterministic for fixed inputs
    assert f"<{uri1}/>" in Path(r1["signed"]).read_text() and "npx:supersedes" not in Path(r1["signed"]).read_text()
    # tamper negative control: one character changed in the signed file fails independent verification
    t = tmp_path / "tampered.trig"
    t.write_text(Path(r1["signed"]).read_text().replace("FIXTURE STATEMENT v1.", "FIXTURE STATEMENT v9.", 1))
    from falsify.nanopub import verify_signed
    assert verify_signed(t)["exit"] != 0
    # a v2 draft made while v1 is still unpublished carries no supersedes; that is fine locally
    early_v2 = prepare(bundle("accepted_v2"), L, out_dir=out, key_pem=key, code_commit=C, created=T)
    assert early_v2["entry"]["supersedes"] is None
    # publish v1 to the loopback TEST registry (real mechanics, fake registry), then v2 supersedes it
    a1 = auth_for(r1["signed"])
    res = registry.post_test(Path(r1["signed"]), uri1, fake.url, a1, dry_run=False, _loopback_ok=True, sleep=lambda s: None)
    assert res["sent"] and res["fetch_back"]["verified"] and "HEAD" not in " ".join(fake.methods)
    L.mark_test_published(uri1, registry=fake.url, observed_is_test=True, fetched_back=True, authorization_sha256=a1.sha256())
    L.save()
    # ...but once v1 is published, that early draft can no longer be published (it would fork the chain) and must be rebuilt
    with pytest.raises(NotPublishable, match="would fork the chain"):
        L.mark_test_published(early_v2["entry"]["np_uri"], registry=fake.url, observed_is_test=True, fetched_back=True, authorization_sha256="x")
    r2 = prepare(bundle("accepted_v2"), L, out_dir=out, key_pem=key, code_commit=C, created=T)
    assert r2["entry"]["supersedes"] == uri1 and f"npx:supersedes <{uri1}>" in Path(r2["signed"]).read_text()
    a2 = auth_for(r2["signed"])
    registry.post_test(Path(r2["signed"]), r2["entry"]["np_uri"], fake.url, a2, dry_run=False, _loopback_ok=True, sleep=lambda s: None)
    L.mark_test_published(r2["entry"]["np_uri"], registry=fake.url, observed_is_test=True, fetched_back=True, authorization_sha256=a2.sha256())
    # the same exact version cannot be published twice
    with pytest.raises(NotPublishable, match="already published"):
        prepare(bundle("accepted_v2"), L, out_dir=out, key_pem=key, code_commit=C, created=T)
    # the later dispute is published only as a correction of v2's acceptance
    r3 = prepare(bundle("disputed_v2"), L, out_dir=out, key_pem=key, code_commit=C, created=T, status_change=True)
    assert r3["entry"]["supersedes"] == r2["entry"]["np_uri"] and r3["entry"]["decision"] == "disputed"
    s3 = Path(r3["unsigned"]).read_text()
    assert '"insufficient"' in Path(r3["signed"]).read_text()
    assert dims_of(s3)["applicability"] == "insufficient" and 'schema:value "disputed"' in s3 and "not a finding that the reviewed record is false" in s3
    # a dispute with no published acceptance in the ledger is refused
    with pytest.raises(NotPublishable, match="none is in the ledger"):
        prepare(bundle("disputed_v2"), ledger_mod.Ledger(tmp_path / "other.json"), out_dir=out, key_pem=key, code_commit=C, created=T, status_change=True)


@needs_np
def test_signing_key_inside_the_repo_is_refused(tmp_path):
    from falsify.nanopub import sign_local
    u = tmp_path / "u.trig"
    u.write_text(build_trig(bundle(), code_commit=C, created=T))
    with pytest.raises(RuntimeError, match="outside the repository"):
        sign_local(u, ROOT / "pyproject.toml", tmp_path / "o.trig")


def test_ledger_rejects_forks_and_unpublished_supersession(tmp_path):
    L = ledger_mod.Ledger(tmp_path / "l.json")
    u1, u2 = "https://w3id.org/np/RA" + "A" * 43, "https://w3id.org/np/RA" + "B" * 43
    L.add_signed(key="n/Claim/x", target_version="1" * 64, assessment_version="2" * 64, decision="accepted", file="f", signed_bytes=b"x", np_uri=u1)
    with pytest.raises(NotPublishable, match="not a published entry"):
        L.add_signed(key="n/Claim/x", target_version="3" * 64, assessment_version="4" * 64, decision="accepted", file="g", signed_bytes=b"y", np_uri=u2, supersedes=u1)
    with pytest.raises(NotPublishable, match="did not say it is a test instance"):
        L.mark_test_published(u1, registry="r", observed_is_test=None, fetched_back=True, authorization_sha256="z")
    with pytest.raises(NotPublishable, match="already in the ledger"):
        L.add_signed(key="n/Claim/x", target_version="1" * 64, assessment_version="2" * 64, decision="accepted", file="f", signed_bytes=b"x", np_uri=u1)


# ------------------------------------------------------------------ the test-registry gate
def test_dry_run_sends_nothing(tmp_path, monkeypatch):
    f = tmp_path / "x.trig"
    f.write_text("x")
    monkeypatch.setattr(registry, "_opener", lambda: (_ for _ in ()).throw(AssertionError("network used in dry run")))
    plan = registry.post_test(f, "https://w3id.org/np/RA" + "A" * 43, "https://test.registry.knowledgepixels.com", None)
    assert plan["dry_run"] is True and plan["sent"] is False and plan["method"] == "POST"


@pytest.mark.parametrize("url", ["https://registry.knowledgepixels.com", "https://registry.petapico.org", "https://np.knowledgepixels.com",
                                 "https://registry.nanodash.net", "https://evil.test.registry.knowledgepixels.com.attacker.net",
                                 "http://test.registry.knowledgepixels.com", "http://10.0.0.5"])
def test_production_and_unknown_hosts_are_refused_before_any_request(url, monkeypatch):
    monkeypatch.setattr(registry, "_opener", lambda: (_ for _ in ()).throw(AssertionError("network used")))
    with pytest.raises(NotPublishable, match="not a known test-registry host"):
        registry.registry_role(url)


def test_loopback_is_not_allowed_unless_tests_ask(fake):
    with pytest.raises(NotPublishable, match="not a known test-registry host"):
        registry.registry_role(fake.url)
    assert registry.registry_role(fake.url, _loopback_ok=True)["observed"] == {"isTestInstance": True}


def test_registry_must_say_it_is_a_test_instance():
    for kw in ({"is_test": False}, {"flag_key": None}, {"is_test": False, "flag_key": "testInstance"}):
        r = FakeRegistry(**kw)
        try:
            with pytest.raises(NotPublishable, match="treated as production and refused"):
                registry.registry_role(r.url, _loopback_ok=True)
        finally:
            r.close()
    r = FakeRegistry(flag_key="testInstance")
    try:
        assert registry.registry_role(r.url, _loopback_ok=True)["observed"] == {"testInstance": True}
    finally:
        r.close()


@needs_np
def test_publication_needs_the_users_own_authorization_for_these_exact_bytes(tmp_path, key, fake):
    from frontier_pub.pipeline import prepare
    r1 = prepare(bundle(), ledger_mod.Ledger(tmp_path / "l.json"), out_dir=tmp_path, key_pem=key, code_commit=C, created=T)
    p, uri = Path(r1["signed"]), r1["entry"]["np_uri"]
    def go(a):
        return registry.post_test(p, uri, fake.url, a, dry_run=False, _loopback_ok=True, sleep=lambda s: None)
    with pytest.raises(NotPublishable, match="no authorization"):
        go(None)
    good = auth_for(p)
    for bad in (registry.Authorization("short", "user", "t", good.files_sha256), registry.Authorization(good.instruction, "host", "t", good.files_sha256),
                registry.Authorization(good.instruction, "user", "t", ("0" * 64,))):
        with pytest.raises(NotPublishable):
            go(bad)
    assert not any(m.startswith("POST") for m in fake.methods)             # nothing was posted by any refused attempt
    assert go(good)["sent"]


@needs_np
def test_fetch_back_is_a_verifying_get_and_has_a_negative_control(tmp_path, key):
    from frontier_pub.pipeline import prepare
    r1 = prepare(bundle(), ledger_mod.Ledger(tmp_path / "l.json"), out_dir=tmp_path, key_pem=key, code_commit=C, created=T)
    p, uri = Path(r1["signed"]), r1["entry"]["np_uri"]
    other = prepare(bundle("accepted_v2"), ledger_mod.Ledger(tmp_path / "l2.json"), out_dir=tmp_path / "o2", key_pem=key, code_commit=C, created=T)
    for kw, why in (({"drop_get": True}, "404"), ({"wrong_bytes": Path(other["signed"]).read_bytes()}, "do not verify as"),
                    ({"wrong_bytes": p.read_bytes().replace(b"FIXTURE STATEMENT v1.", b"FIXTURE STATEMENT v9.")}, "do not verify as")):
        r = FakeRegistry(**kw)
        try:
            with pytest.raises(NotPublishable, match="fetch-back failed|do not verify as"):
                registry.post_test(p, uri, r.url, auth_for(p), dry_run=False, _loopback_ok=True, sleep=lambda s: None)
            assert not any(m.startswith("HEAD") for m in r.methods)
        finally:
            r.close()


@needs_np
def test_throttling_429_is_waited_out_not_treated_as_failure(tmp_path, key):
    from frontier_pub.pipeline import prepare
    r1 = prepare(bundle(), ledger_mod.Ledger(tmp_path / "l.json"), out_dir=tmp_path, key_pem=key, code_commit=C, created=T)
    p = Path(r1["signed"])
    r = FakeRegistry(throttle_first=True)
    slept = []
    try:
        res = registry.post_test(p, r1["entry"]["np_uri"], r.url, auth_for(p), dry_run=False, _loopback_ok=True, sleep=slept.append)
        assert res["sent"] and slept and slept[0] == 1
        assert [m for m in r.methods if m.startswith("POST")] == ["POST /", "POST /"]
    finally:
        r.close()


def test_no_production_publish_path_exists_in_the_package():
    src = "".join(p.read_text() for p in (ROOT / "frontier_pub").glob("*.py"))
    for host in ("registry.knowledgepixels.com/", "registry.petapico.org", "np.knowledgepixels.com", "registry.nanodash.net", "registry.np.trustyuri.net"):
        assert not re.search(r"(?<!test\.)" + re.escape(host), src.replace("test.registry.knowledgepixels.com", "").replace("test.registry.petapico.org", "")), host
    assert not re.search(r"def\s+\w*prod", src) and "--prod" not in src and 'stage="prod"' not in src
    # no Frontier write operation is called anywhere
    for w in (".submit(", ".review(", ".transition(", ".lease(", ".import_bundle(", ".provision(", ".initialize("):
        assert w not in src, w


def test_cli_plan_is_dry_run_and_refuses_production(tmp_path, capsys):
    from frontier_pub.__main__ import main
    f = tmp_path / "x.trig"
    f.write_text("x")
    assert main(["plan-test-publish", str(f), "--uri", "https://w3id.org/np/RA" + "A" * 43, "--registry", "https://test.registry.knowledgepixels.com"]) == 0
    assert '"sent": false' in capsys.readouterr().out
