"""Tests for the Claim/Evidence adapters and the nanopub draft exporter.

Run (bounded):  FRONTIER_PATH=<read-only delphi-frontier checkout> \
  systemd-run --user --scope -p MemoryMax=4G -p MemorySwapMax=0 -p TasksMax=128 -p RuntimeMaxSec=300 \
  python3 -I -m unittest frontier_adapters.tests.test_adapters -v

Tests that validate against the REAL Frontier models need $FRONTIER_PATH; they are reported as skipped WITH that
reason, never as passed. Every safety property has a must-fail control.
"""
import copy
import json
import os
import shutil
import subprocess
import tempfile
import unittest

from frontier_adapters import bundle, delphi_claim as dc, nanopub_draft as nd, orx_evidence as oe, orx_replay
from frontier_adapters.common import FrontierUnavailable, load_frontier, sha_bytes, validate_draft

HERE = os.path.dirname(os.path.abspath(__file__))
EX = os.path.join(HERE, "..", "examples")
RUN = os.path.join(EX, "orx_run_turing")
BUNDLE = os.path.join(EX, "turing_bundle")
RUN_ID = "330735e8-d32e-47cd-99ee-fb54845367d7"
RDF_PY = "/data/worktrees/morphoswarm/studio/.venv/bin/python"

try:
    load_frontier()
    HAVE_FRONTIER = True
except FrontierUnavailable:
    HAVE_FRONTIER = False
needs_frontier = unittest.skipUnless(HAVE_FRONTIER, "FRONTIER_PATH not set: real Frontier models unavailable, NOT validated")


def snap(cid):
    return json.load(open(os.path.join(EX, "delphi_snapshots", cid + ".json")))


def claim_draft(cid, verified=True):
    d = snap(cid)
    return dc.to_claim_draft(d["snapshot"], verification=d["verification"] if verified else None)


TARGET = {"namespace": "node-a", "kind": "Claim", "id": "turing-ddi", "version": "a" * 64}
AUTHOR = {"assumptions": ["declared instance"], "limitations": ["one instance"], "uncertainty": "exact arithmetic"}


def facts():
    return oe.read_run(run_id=RUN_ID, export_dir=RUN, result_file="results.json")


def tampered_export(mutate):
    tmp = tempfile.mkdtemp()
    dst = os.path.join(tmp, "run")
    shutil.copytree(RUN, dst)
    mutate(dst)
    return tmp, dst


class DelphiClaim(unittest.TestCase):
    @needs_frontier
    def test_all_snapshots_validate_under_real_models_and_licence_gate(self):
        for cid in ("turing-ddi", "darwin1859-ch02-04", "wolfram2002-ch02-08", "thompson1917-ch03-05", "fisher-ftns"):
            v = validate_draft(claim_draft(cid))
            self.assertEqual(v["licence_gate_offenders"], [], cid)

    def test_original_delphi_identifiers_and_versions_are_preserved(self):
        for cid in ("turing-ddi", "darwin1859-ch02-04", "wolfram2002-ch02-08"):
            d = claim_draft(cid)
            self.assertEqual(d["id"], cid)
            self.assertEqual(d["source_uri"], "https://w3id.org/delphi/resource/claim/" + cid)
            self.assertTrue(d["payload"]["source_record_version"].startswith("https://w3id.org/np/RA"), cid)
            o = d["payload"]["prior_review"]["delphi_original"]
            self.assertIn(o["registry"], ("production", "test"))
        self.assertEqual(claim_draft("wolfram2002-ch02-08")["payload"]["prior_review"]["delphi_original"]["registry"], "test")

    def test_content_never_available_and_no_licence_claimed(self):
        for cid in ("turing-ddi", "darwin1859-ch02-04", "wolfram2002-ch02-08", "fisher-ftns"):
            s = claim_draft(cid)["payload"]["source"]
            self.assertFalse(s["content_available"], cid)
            self.assertIsNone(s["license"], cid)

    def test_quote_text_is_never_stored_only_its_digest(self):
        for cid in ("darwin1859-ch02-04", "wolfram2002-ch02-08", "thompson1917-ch03-05"):
            q = claim_draft(cid)["payload"]["prior_review"]["delphi_original"]["quote"]
            self.assertFalse(q["text_stored"])
            self.assertEqual(len(q["sha256"]), 64)
            self.assertGreater(q["chars"], 0)
        self.assertNotIn("quote_text", json.dumps(snap("darwin1859-ch02-04")))

    def test_wolfram_rights_statement_is_carried_verbatim_and_record_licence_is_scoped(self):
        perm = claim_draft("wolfram2002-ch02-08")["payload"]["prior_review"]["delphi_original"]["permission"]
        self.assertIn("all rights reserved", perm["source_text_rights"])
        self.assertIn("NOT to the quoted source text", perm["delphi_record_license_applies_to"])
        self.assertFalse(perm["quote_text_included_in_output"])

    def test_recorded_hash_is_carried_only_after_verification(self):
        d = snap("darwin1859-ch02-04")
        recorded = d["snapshot"]["source"]["recorded_sha256"]
        self.assertEqual(dc.to_claim_draft(d["snapshot"], verification=d["verification"])["payload"]["source"]["content_sha256"], recorded)
        unverified = dc.to_claim_draft(d["snapshot"], verification=None)["payload"]
        self.assertIsNone(unverified["source"]["content_sha256"])                      # not verified -> not carried
        self.assertEqual(unverified["prior_review"]["delphi_original"]["recorded_sha256_unverified"], recorded)
        bad = dict(d["verification"], sha256_match=False)                              # MUST-FAIL control
        self.assertIsNone(dc.to_claim_draft(d["snapshot"], verification=bad)["payload"]["source"]["content_sha256"])

    def test_verify_source_detects_tampered_bytes_and_altered_quote(self):
        d = snap("darwin1859-ch02-04")["snapshot"]
        text = "\n".join(f"line {i}" for i in range(2000))
        quote = "an authentic sentence"
        lines = text.splitlines(); a, b = map(int, d["source"]["locator"][5:].split(","))
        lines[a] = quote
        raw = "\n".join(lines).encode()
        ver = dc.verify_source(d, {"quote": quote}, fetch=lambda u: raw)
        self.assertFalse(ver["sha256_match"])                                          # fetched bytes differ from the recorded hash
        self.assertEqual(ver["quote_at_locator"], "exact")
        self.assertEqual(dc.verify_source(d, {"quote": "a sentence that is not there"}, fetch=lambda u: raw)["quote_at_locator"], "not_found")

    def test_math_claims_state_what_is_absent_and_internal_iri_is_not_a_uri(self):
        t = claim_draft("turing-ddi")["payload"]
        self.assertIsNone(t["source"]["locator"]); self.assertIsNone(t["source"]["content_sha256"])
        self.assertTrue(t["source"]["uri"].startswith("https://doi.org/"))
        self.assertIn("locator", t["prior_review"]["delphi_original"]["absent_in_record"])
        f = claim_draft("fisher-ftns")["payload"]
        self.assertIsNone(f["source"]["uri"])                                          # Delphi-internal IRI does not resolve
        self.assertTrue(f["prior_review"]["delphi_original"]["source_detail"]["unresolved_internal_iri"].startswith("https://w3id.org/delphi/resource/paper/"))

    def test_incomplete_graph_read_fails_loudly(self):
        class Fake:
            def tool(self, name, args):
                return [{"g": "x/nanopubs/unsigned/c.trig#assertion", "s": "s", "p": "p", "o": "o"}]
        with self.assertRaises(LookupError):
            dc._triples(Fake(), "c")


class OrxEvidence(unittest.TestCase):
    def test_export_reads_back_and_verifies_digests(self):
        f = facts()
        self.assertEqual(f["status"], "done"); self.assertEqual(f["exit_code_file"], 0); self.assertIsNone(f["db_exit_code"])
        self.assertEqual(f["result_sha256"], "b4698e56aed6496cfae6cb32dc3ef50c8b3fdd21d051f000a5de25abc74e2c45")
        self.assertEqual(f["source_tar_sha256"], sha_bytes(open(os.path.join(RUN, "source.tar"), "rb").read()))

    def test_export_contains_no_local_absolute_paths(self):
        for n in ("run.json", "health.json"):
            self.assertNotIn("/tmp/", open(os.path.join(RUN, n)).read())

    def test_refuses_failed_nonzero_tampered_or_missing(self):
        def not_done(d):
            j = json.load(open(d + "/run.json")); j["run"]["status"] = "failed"; json.dump(j, open(d + "/run.json", "w"))
        def nonzero(d): open(d + "/exit_code", "w").write("1\n")
        def no_exit(d): os.remove(d + "/exit_code")
        def tamper_tar(d):
            b = bytearray(open(d + "/source.tar", "rb").read()); b[600] ^= 0xFF; open(d + "/source.tar", "wb").write(bytes(b))
        def no_result(d): os.remove(d + "/outputs/results.json")
        for name, m in (("status", not_done), ("exit", nonzero), ("exit-missing", no_exit), ("tar", tamper_tar), ("result", no_result)):
            tmp, dst = tampered_export(m)
            with self.subTest(name), self.assertRaises(oe.Refused):
                oe.read_run(run_id=RUN_ID, export_dir=dst, result_file="results.json")
            shutil.rmtree(tmp)

    def test_refuses_observed_formal_and_assessment_kinds(self):
        for k in ("observed", "formal", "source_assessment", "anything"):
            with self.subTest(k), self.assertRaises(oe.Refused):
                oe.to_evidence_draft(facts(), target=TARGET, author=AUTHOR, kind=k)

    def test_refuses_inexact_target(self):
        for bad in ({**TARGET, "version": "abc"}, {k: v for k, v in TARGET.items() if k != "id"}):
            with self.assertRaises(oe.Refused):
                oe.to_evidence_draft(facts(), target=bad, author=AUTHOR)

    def test_draft_shape_origin_map_and_absent_fields(self):
        d = oe.to_evidence_draft(facts(), target=TARGET, author=AUTHOR)
        p = d["payload"]
        self.assertFalse(p["source"]["content_available"]); self.assertIsNone(p["source"]["license"]); self.assertIsNone(p["source"]["uri"])
        self.assertEqual(p["evidence_kind"], "simulated")
        fo = p["provenance"]["field_origin"]
        self.assertEqual(fo["provider_assessment"], "absent")
        self.assertEqual(fo["assumptions"], "author")
        self.assertGreaterEqual(len(p["limitations"]), len(oe.MECHANICAL_LIMITATIONS))
        undeclared = oe.to_evidence_draft(facts(), target=TARGET, author={})["payload"]
        self.assertEqual(undeclared["assumptions"], []); self.assertEqual(undeclared["provenance"]["field_origin"]["assumptions"], "absent")
        self.assertEqual(undeclared["source_dependence"], {"declared": False})

    @needs_frontier
    def test_evidence_validates_under_real_models_and_licence_gate(self):
        v = validate_draft(oe.to_evidence_draft(facts(), target=TARGET, author=AUTHOR))
        self.assertEqual(v["licence_gate_offenders"], [])

    @needs_frontier
    def test_store_licence_gate_would_refuse_if_content_were_marked_available(self):          # MUST-FAIL control
        d = oe.to_evidence_draft(facts(), target=TARGET, author=AUTHOR)
        d["payload"]["source"]["content_available"] = True
        self.assertTrue(validate_draft(d)["licence_gate_offenders"])

    def test_replay_requires_trust_flag_and_rejects_vacuous_mutation(self):
        with self.assertRaises(PermissionError):
            orx_replay.replay(RUN, command="python3 run_modes.py", result_file="results.json", recorded_sha256="0" * 64,
                              interpreters={"x": "/usr/bin/python3"})
        with self.assertRaises(ValueError):
            orx_replay.replay(RUN, command="python3 run_modes.py", result_file="results.json", recorded_sha256="0" * 64,
                              interpreters={"x": "/usr/bin/python3"}, trust_code=True, mutation=("run_modes.py", "NOT PRESENT", "x"))

    def test_committed_replay_report_matches_and_control_discriminated(self):
        r = json.load(open(os.path.join(BUNDLE, "replay_report.json")))
        self.assertTrue(all(v["matches_recorded"] for v in r["results"].values()))
        self.assertTrue(r["mutation_control"])
        self.assertFalse(any(v["matches_recorded"] for v in r["control_results"].values()))


class NanopubDraft(unittest.TestCase):
    def records(self):
        return json.load(open(os.path.join(BUNDLE, "records.json")))

    def test_deterministic_and_matches_committed_drafts(self):
        c, e = self.records()
        self.assertEqual(nd.record_to_trig(c), nd.record_to_trig(copy.deepcopy(c)))
        self.assertEqual(nd.record_to_trig(c), open(os.path.join(BUNDLE, "claim.draft.trig")).read())
        self.assertEqual(nd.record_to_trig(e, target_claim=c), open(os.path.join(BUNDLE, "evidence.draft.trig")).read())

    def test_evidence_pinned_to_exact_claim_version_and_original_delphi_ids_present(self):
        c, e = self.records()
        self.assertEqual(e["payload"]["target"]["version"], c["version"])
        trig = open(os.path.join(BUNDLE, "evidence.draft.trig")).read()
        self.assertIn("<https://w3id.org/delphi/resource/claim/turing-ddi>", trig)
        self.assertIn(c["payload"]["source_record_version"], trig)
        with self.assertRaises(nd.ExportRefused):                                       # wrong target claim -> refuse
            nd.record_to_trig(e, target_claim={**c, "version": "b" * 64})

    def test_structure_check_counts_four_graphs_and_catches_a_missing_one(self):
        good = open(os.path.join(BUNDLE, "evidence.draft.trig")).read()
        self.assertTrue(nd.validate_trig(good)["four_graphs"])
        i, j = good.index("sub:provenance {"), good.index("sub:pubinfo {")
        self.assertFalse(nd.validate_trig(good[:i] + good[j:])["four_graphs"])           # MUST-FAIL control

    def test_refusals(self):
        c, e = self.records()
        private = {**c, "visibility": "private"}
        with self.assertRaises(nd.ExportRefused): nd.record_to_trig(private)
        leaky = copy.deepcopy(c); leaky["payload"]["source"].update(content_available=True, license=None)
        with self.assertRaises(nd.ExportRefused): nd.record_to_trig(leaky)
        stored = copy.deepcopy(c); stored["payload"]["prior_review"]["delphi_original"]["quote"]["text_stored"] = True
        with self.assertRaises(nd.ExportRefused): nd.record_to_trig(stored)
        badiri = copy.deepcopy(c); badiri["source_uri"] = "https://x.org/a b>"
        with self.assertRaises(nd.ExportRefused): nd.record_to_trig(badiri)
        with self.assertRaises(nd.ExportRefused): nd.refuse_publication()

    def test_licensed_content_is_exportable_only_with_a_licence(self):
        c, _ = self.records()
        ok = copy.deepcopy(c); ok["payload"]["source"].update(content_available=True, license="CC-BY-4.0")
        self.assertIn("YES under licence CC-BY-4.0", nd.record_to_trig(ok))

    def test_drafts_carry_the_limits_and_no_signature(self):
        trig = open(os.path.join(BUNDLE, "claim.draft.trig")).read()
        for needle in ("UNSIGNED DRAFT", "single-reader, not Codex-reviewed", "NO. Only a digest and locator", "Delphi record licence"):
            self.assertIn(needle, trig)
        self.assertNotRegex(trig, r"https://w3id\.org/np/RA\S*>\s*a\s+np:Nanopublication")  # we never mint a trusty URI

    @unittest.skipUnless(os.path.exists(RDF_PY), "MorphoSwarm venv with rdflib not present: independent parse NOT run")
    def test_independent_rdflib_parse_finds_exactly_four_named_graphs(self):
        code = ("import sys\nfrom rdflib import Dataset\nfor p in sys.argv[1:]:\n ds=Dataset(); ds.parse(p,format='trig')\n"
                " print(sorted(str(g.identifier).rsplit('/',1)[-1] for g in ds.graphs() if len(g)))")
        out = subprocess.run([RDF_PY, "-I", "-c", code, os.path.join(BUNDLE, "claim.draft.trig"), os.path.join(BUNDLE, "evidence.draft.trig")],
                             capture_output=True, text=True, timeout=120)
        self.assertEqual(out.returncode, 0, out.stderr)
        for line in out.stdout.strip().splitlines():
            self.assertEqual(eval(line), ["Head", "assertion", "provenance", "pubinfo"])


if __name__ == "__main__":
    unittest.main()
