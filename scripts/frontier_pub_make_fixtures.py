"""Drive Frontier's REAL Store (pinned commit, private throwaway Postgres) through propose -> review -> supersede -> dispute -> import, and write the
records it produced as test fixtures. Everything is labelled a software protocol fixture: the reviews are workflow controls, NOT scientific reviews.

Run via scripts/frontier_pub_pg.sh (needs FRONTIER_SRC). Reads Frontier through Store.get / Store.events and through the loopback HTTP adapter
(read endpoints only); the writes below go to the THROWAWAY database this script created, never to a real node.
"""
import json
import os
import sys
import threading
import time
from pathlib import Path
from uuid import uuid4

from frontier.http import make_server
from frontier.models import DIMENSIONS, POLICY, ref as fref
from frontier.store import Store

from frontier_pub.collect import HttpReader, collect

OUT = Path(sys.argv[1])
FRONTIER_COMMIT = sys.argv[2]
DSN = os.environ["FRONTIER_TEST_DSN"]
SRC = "https://github.com/kganjam/delphi-evolve/blob/main/docs/frontier-publication-layer.md"
TOK = {x: "fixture-only-local-token-for-" + x for x in ("alice", "bob", "dana", "erin", "frank")}


def mk(ns):
    s = Store(DSN, ns, "pub_" + uuid4().hex)
    s.initialize()
    for actor, roles, op in [("alice", ["contributor", "coordinator"], "operator-a"), ("bob", ["reviewer", "contributor"], "operator-b"),
                             ("dana", ["reviewer", "contributor"], "operator-d"), ("erin", ["contributor", "coordinator"], "operator-e"),
                             ("frank", ["reviewer", "contributor"], "operator-f")]:
        s.provision(TOK[actor], actor, op, roles, [ns], 1000)
    return s


def source(uri=SRC):
    return {"uri": uri, "locator": "section: Fixtures", "source_version": "fixture-v1", "content_sha256": "a" * 64,
            "content_available": False, "access": "public reference; bytes not verified by Frontier", "license": "CC-BY-4.0"}


def claim(s, id, statement, issuer="alice", predecessor=None, visibility="public", src=None):
    return {"namespace": s.namespace, "kind": "Claim", "id": id, "issuer": issuer, "source_uri": SRC, "visibility": visibility,
            "predecessor": predecessor, "payload": {"title": "Protocol fixture, not scientific data", "statement": statement,
            "context": "Software protocol test of the Frontier publication layer; no empirical content.",
            "assumptions": ["The fixture is a stand-in for a real claim."], "limitations": ["Not measured evidence.", "Reviews on it are workflow controls."],
            "source": src or source()}}


def evid(s, target):
    return {"namespace": s.namespace, "kind": "Evidence", "id": "fixture-evidence-" + target["id"], "issuer": "alice", "source_uri": SRC,
            "payload": {"target": target, "evidence_kind": "source_assessment", "source": source(),
                        "created_time": {"value": None, "basis": "unknown"},
                        "retrieved_time": {"value": "2026-10-31T15:00:00+00:00", "basis": "declared"},
                        "method": "Software protocol fixture", "context": "No empirical claim", "assumptions": ["A fixture"],
                        "provenance": {"provider": "fixture"}, "source_dependence": {"group": "single-fixture-source", "independence": "unknown"},
                        "uncertainty": "Unknown", "limitations": ["Declared digest only."]}}


def review(target, reviewer, decision, statuses=None, links=None):
    st = {"independent_replication": "not_applicable", "empirical_relevance": "not_applicable"}
    st.update(statuses or {})
    dims = {d: {"status": st.get(d, "passed"), "reviewer": reviewer,
                "rationale": f"Workflow-control rationale for {d}; not a scientific review.", "evidence_links": (links or {}).get(d, [])}
            for d in DIMENSIONS}
    return {"target": target, "decision": decision, "dimensions": dims, "independence_rationale": "Separate configured operator in a throwaway fixture node.",
            "limitations": ["Exercises the publication workflow only."]}


def bundle(reader, target_ref, a_ref=None):
    return collect(reader, target_ref, a_ref)


out = {}
a = mk("node-a")
srv = make_server(a, 0)
threading.Thread(target=srv.serve_forever, daemon=True).start()
http = HttpReader(f"http://127.0.0.1:{srv.server_port}")

# 1. v1 accepted, with a linked Evidence record (one dimension cites it; one link will be left unresolved in a variant)
c1 = a.submit(TOK["alice"], "k1", claim(a, "pub-fixture-claim", "FIXTURE STATEMENT v1."))["record"]
e1 = a.submit(TOK["alice"], "k2", evid(a, fref(c1)))["record"]
r1 = a.review(TOK["bob"], "k3", review(fref(c1), "bob", "accepted", links={"source_fidelity": [fref(e1)]}))["assessment"]
out["accepted_v1"] = bundle(a, fref(c1), fref(r1))
out["accepted_v1_via_http"] = bundle(http, fref(c1), fref(r1))

# 2. v2 supersedes v1, accepted by a different reviewer/operator
c2 = a.submit(TOK["alice"], "k4", claim(a, "pub-fixture-claim", "FIXTURE STATEMENT v2.", predecessor=c1["version"]))["record"]
r2 = a.review(TOK["dana"], "k5", review(fref(c2), "dana", "accepted"))["assessment"]
out["accepted_v2"] = bundle(a, fref(c2), fref(r2))

# 3. a later review of v2 is disputed (status change; local state of v2 becomes 'disputed')
r3 = a.review(TOK["frank"], "k6", review(fref(c2), "frank", "disputed", statuses={"applicability": "insufficient"}))["assessment"]
out["disputed_v2"] = bundle(a, fref(c2), fref(r3))
out["accepted_v2_after_dispute_state"] = bundle(a, fref(c2), fref(r2))        # stale: node state is now 'disputed'

# 4. imported target: node-b proposes, node-a imports (coordinator) and reviews
b = mk("node-b")
cb = b.submit(TOK["erin"], "b1", claim(b, "imported-fixture-claim", "FIXTURE IMPORTED STATEMENT.", issuer="erin"))["record"]
exp = b.export_bundle([fref(cb)])
a.import_bundle(TOK["alice"], "i1", exp)
ri = a.review(TOK["bob"], "k7", review(fref(cb), "bob", "accepted"))["assessment"]
out["accepted_imported"] = bundle(a, fref(cb), fref(ri))

# 5. a Problem with NO source (curator statement), accepted
pr = {"namespace": "node-a", "kind": "Problem", "id": "pub-fixture-problem", "issuer": "alice", "source_uri": SRC, "payload": {
      "title": "Protocol fixture problem", "known_state": "Fixture state.", "question": "Fixture question?", "problem_kind": "project_gap",
      "novelty_status": "Fixture; no novelty claim.", "data_access": "None.", "completeness": "recorded", "acceptance_criteria": [], "falsifiers": [],
      "next_action": None, "required_capabilities": [], "cost_stop_bounds": None, "downstream_uses": [],
      "dependencies": [], "source": {"uri": None, "locator": None, "source_version": None, "content_sha256": None, "content_available": False,
                                      "access": "No source recorded: curator statement.", "license": None}}}
p1 = a.submit(TOK["alice"], "p1", pr)["record"]
rp = a.review(TOK["bob"], "p2", review(fref(p1), "bob", "accepted"))["assessment"]
out["accepted_problem_unsourced"] = bundle(a, fref(p1), fref(rp))

# 6. a PRIVATE claim, accepted: collection through the public reader cannot even see it
cp = a.submit(TOK["alice"], "q1", claim(a, "pub-fixture-private", "PRIVATE FIXTURE.", visibility="private"))["record"]
rq = a.review(TOK["bob"], "q2", review(fref(cp), "bob", "accepted"))["assessment"]
try:
    bundle(a, fref(cp), fref(rq))
    out["private_public_read"] = "UNEXPECTEDLY READABLE"
except Exception as e:      # noqa
    out["private_public_read"] = f"{type(e).__name__}: {e}"
private_with_token = {"target": a.get(fref(cp), TOK["alice"])["record"], "assessment": rq}

# the facts a reviewer of this run needs
meta = {"frontier_commit": FRONTIER_COMMIT, "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "note": "All reviews in these fixtures are software workflow controls on a throwaway database; none is a scientific review.",
        "refs": {"c1": fref(c1), "r1": fref(r1), "c2": fref(c2), "r2": fref(r2), "r3": fref(r3), "cb": fref(cb), "ri": fref(ri)}}
OUT.mkdir(parents=True, exist_ok=True)
(OUT / "bundles.json").write_text(json.dumps({"meta": meta, "bundles": out, "private_records": private_with_token}, sort_keys=True, indent=1, default=str))
print(json.dumps({"written": str(OUT / "bundles.json"), "keys": sorted(out), "private_public_read": out["private_public_read"]}))
srv.shutdown()
