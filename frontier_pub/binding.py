"""Bind a Frontier record that has an ACCEPTED Assessment to a nanopublication DRAFT (profile `frontier-review-publication v0`).

What the nanopublication ASSERTS is the REVIEW, not the reviewed claim: "node N, reviewer R acting for operator O, under policy P,
recorded these seven separately named dimension outcomes for the exact record version V". The reviewed record's own text is quoted
as the thing reviewed (uninterpreted). Nothing is asserted about nature, and no composite truth/confidence number exists or is
computed: each dimension keeps its own status, reviewer and rationale (SPEC-087 rule 4.1, ASK pp.8).

Hard rules honoured (morphoswarm SPEC-007/031): http(s) IRIs only; no urn:/ms:/example.org; no IRI minted in an unregistered w3id
namespace (only the nanopub's own local IRIs and carried external references that already exist); dct:created is pinned by the
caller; corrections are NEW nanopubs with npx:supersedes (same key); there is no publish code here.
"""
from __future__ import annotations

import json
import re
from urllib.parse import urlsplit

from . import PROFILE_VERSION
from .records import DIMENSIONS, POLICY, NotPublishable, ref, ref_text, verify_record

REPO_URL = "https://github.com/kganjam/delphi-evolve"
PROFILE_IRI = REPO_URL + "/blob/main/docs/frontier-publication-layer.md"
TEMP = "http://purl.org/nanopub/temp/frontierpub/np"
LICENSE = "https://creativecommons.org/licenses/by/4.0/"        # prepared default; the owner decides (open decision)
PUBLISHABLE_KINDS = ("Claim", "Problem")
DECISION_MEANING = {
    "accepted": ("Outcome recorded by the reviewing node under its local policy frontier-independent-review-0.1: no dimension is unreviewed, "
                 "failed or insufficient (each is passed or not_applicable), and target_fidelity and applicability are passed. It is NOT a truth "
                 "rating, NOT a probability, NOT a combination of the dimensions, and NOT agreement of any other node."),
    "disputed": ("Outcome recorded by the reviewing node: the review is disputed. Published only as a superseding correction of an earlier "
                 "acceptance publication. It is not a finding that the reviewed record is false."),
    "rejected": ("Outcome recorded by the reviewing node: the review rejected the record. Published only as a superseding correction of an earlier "
                 "acceptance publication. It is not a finding about nature."),
}
SCOPE_LIMIT = ("Records a node-local, policy-bound review of one exact record version. Not a measurement. Not a truth, confidence or "
               "composite rating. No nonlinear, biological, wet-lab or clinical implication beyond the reviewed record's own stated scope.")
DIGEST_RECIPE = ("version = sha256 of canonical JSON (sort_keys, separators , and :, ensure_ascii false) of the record envelope without its "
                 "version field; schema frontier-record-0.1")
BAD_HOSTS = ("example.org", "example.com", "example.net", "localhost", "127.0.0.1", "::1")
UNREGISTERED_W3ID = ("/delphi", "/probknow", "/morphoswarm")
ALLOWED_NS = ("https://schema.org/", "http://www.w3.org/ns/prov#", "http://purl.org/dc/terms/", "http://www.w3.org/2000/01/rdf-schema#",
              "http://www.w3.org/1999/02/22-rdf-syntax-ns#", "http://www.w3.org/2001/XMLSchema#", "http://www.nanopub.org/nschema#",
              "http://purl.org/nanopub/x/", "http://purl.org/nanopub/temp/", "https://w3id.org/np/", LICENSE)


# ----------------------------------------------------------------- IRI policy
def vet_iri(u) -> bool:
    """May this EXISTING external reference travel as an IRI? (Otherwise it travels as a literal.)"""
    if not isinstance(u, str) or not u or len(u) > 500 or re.search(r'[\s<>"{}|\\^`]', u):
        return False
    p = urlsplit(u)
    if p.scheme not in ("http", "https") or not p.hostname:
        return False
    host = p.hostname.lower()
    if host in BAD_HOSTS or host.endswith(".example.org") or host.endswith(".localhost"):
        return False
    if host == "w3id.org" and not (p.path.startswith("/np/") and len(p.path) > 4):
        return False        # only existing nanopub IRIs under w3id; nothing else there is registered for us (SPEC-007 rule 5)
    return True


def esc(s) -> str:
    return json.dumps(str(s), ensure_ascii=False)


class Graph:
    """Insertion-ordered triple store for one named graph; renders Turtle blocks deterministically."""

    def __init__(self):
        self.s: dict[str, list[tuple[str, str]]] = {}
        self.n = 0

    def add(self, s: str, p: str, o: str):
        self.s.setdefault(s, []).append((p, o))
        self.n += 1

    def render(self) -> str:
        out = []
        for s, po in self.s.items():
            lines = []
            by_p: dict[str, list[str]] = {}
            for p, o in po:
                by_p.setdefault(p, []).append(o)
            for p, os in by_p.items():
                lines.append(f"    {p} " + " ,\n        ".join(os))
            out.append(f"  {s}\n" + " ;\n".join(lines) + " .\n")
        return "".join(out)


# ----------------------------------------------------------------- bundle gates
def check_bundle(b: dict, *, status_change: bool = False) -> dict:
    """Independently re-verify everything the publication relies on. Returns a normalised view or raises NotPublishable.

    Input `b` (all values are Frontier record envelopes as returned by Store.get / Store.events, plus two facts from Store.get):
      target, assessment, review_event, proposal_event, evidence[] (optional), target_is_head, local_review{status,policy_version}
    """
    for k in ("target", "assessment", "review_event", "proposal_event", "local_review", "target_is_head"):
        if k not in b:
            raise NotPublishable(f"bundle is missing {k!r}")
    t = verify_record(b["target"])
    a = verify_record(b["assessment"], "Assessment")
    re_ev = verify_record(b["review_event"], "Event")
    pr_ev = verify_record(b["proposal_event"], "Event")
    ev = [verify_record(e, "Evidence") for e in b.get("evidence", [])]
    if t["kind"] not in PUBLISHABLE_KINDS:
        raise NotPublishable(f"{t['kind']} records have no publication binding yet (implemented: {', '.join(PUBLISHABLE_KINDS)})")
    for r in (t, a, re_ev, pr_ev, *ev):
        if r["visibility"] != "public":
            raise NotPublishable(f"{r['kind']} {r['id']} is not public; private records never leave the node")
    ap = a["payload"]
    if ref(t) != ap.get("target"):
        raise NotPublishable("assessment does not pin exactly this target version (namespace, kind, id, version)")
    if ap.get("policy_version") != POLICY:
        raise NotPublishable(f"unsupported review policy {ap.get('policy_version')!r}")
    dec = ap.get("decision")
    if status_change:
        if dec not in ("disputed", "rejected"):
            raise NotPublishable("a status-change publication needs a disputed or rejected assessment")
    elif dec != "accepted":
        raise NotPublishable(f"decision {dec!r} is not published as a first publication (only 'accepted'; disputed/rejected only supersede an earlier acceptance)")
    dims = ap.get("dimensions")
    if not isinstance(dims, dict) or set(dims) != set(DIMENSIONS):
        raise NotPublishable("assessment must carry exactly the seven named dimensions")
    for name, d in dims.items():
        if d.get("reviewer") != a["issuer"]:
            raise NotPublishable(f"dimension {name} reviewer {d.get('reviewer')!r} is not the assessment issuer")
        if not d.get("rationale"):
            raise NotPublishable(f"dimension {name} has no rationale")
    if dec == "accepted":
        bad = [n for n, d in dims.items() if d["status"] not in ("passed", "not_applicable")]
        if bad:
            raise NotPublishable("accepted requires every dimension passed or not_applicable; offending: " + ", ".join(bad))
        if any(dims[k]["status"] != "passed" for k in ("target_fidelity", "applicability")):
            raise NotPublishable("accepted requires target_fidelity and applicability to be passed")
    if t["issuer"] == a["issuer"]:
        raise NotPublishable("target issuer and reviewer are the same actor")
    if re_ev["payload"].get("event_type") != "review_recorded":
        raise NotPublishable(f"review event has event_type {re_ev['payload'].get('event_type')!r}")
    if pr_ev["payload"].get("event_type") not in ("record_proposed", "record_imported"):
        raise NotPublishable(f"proposal event has event_type {pr_ev['payload'].get('event_type')!r}")
    for e in (re_ev, pr_ev):
        if e["payload"].get("target") != ref(t):
            raise NotPublishable("event does not pin this target version")
    if (re_ev["payload"].get("details") or {}).get("assessment") != ref(a):
        raise NotPublishable("review event does not name this assessment")
    if re_ev["payload"]["actor"] != a["issuer"]:
        raise NotPublishable("review event actor differs from the assessment issuer")
    origin = pr_ev["payload"]["event_type"]
    if origin == "record_proposed" and pr_ev["payload"]["actor"] != t["issuer"]:
        raise NotPublishable("proposal event actor differs from the target issuer")
    if pr_ev["payload"]["operator"] == re_ev["payload"]["operator"]:
        raise NotPublishable("submitting and reviewing operator are the same: not independent review")
    lr = b["local_review"]
    if lr.get("status") != dec or lr.get("policy_version") != POLICY:
        raise NotPublishable(f"node-local state is {lr.get('status')!r}, not {dec!r}: refusing to publish a stale or superseded review")
    if b["target_is_head"] is not True:
        raise NotPublishable("target version is not the node's current head: refusing to publish a stale version")
    declared = {json.dumps(x, sort_keys=True) for d in dims.values() for x in d.get("evidence_links", [])}
    have = {json.dumps(ref(e), sort_keys=True) for e in ev}
    if not have <= declared:
        raise NotPublishable("an evidence record was supplied that no dimension links to")
    return {"target": t, "assessment": a, "review_event": re_ev, "proposal_event": pr_ev, "evidence": ev, "decision": dec,
            "origin": origin, "unresolved_links": sorted(declared - have), "dims": dims}


def key_of(b: dict) -> str:
    """Logical identity of the reviewed thing across versions (the supersession chain key)."""
    return ref_text(b["target"])


# ----------------------------------------------------------------- the profile
def _pv(g: Graph, owner: str, idx: list, name: str, value, why: str | None = None):
    n = f"sub:pv{idx[0]}"
    idx[0] += 1
    g.add(owner, "schema:additionalProperty", n)
    g.add(n, "a", "schema:PropertyValue")
    g.add(n, "schema:name", esc(name))
    g.add(n, "schema:value", esc(value))
    if why:
        g.add(n, "schema:description", esc(why))


def _list_props(g, owner, idx, name, items):
    for i, x in enumerate(items or []):
        _pv(g, owner, idx, f"{name}[{i}]", x)


def build_trig(b: dict, *, code_commit: str, created: str, supersedes: str | None = None, status_change: bool = False) -> str:
    v = check_bundle(b, status_change=status_change)
    if not re.fullmatch(r"[0-9a-f]{40}", code_commit or ""):
        raise NotPublishable("code_commit must be a full 40-hex pushed git commit of the publication layer")
    if not re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ", created or ""):
        raise NotPublishable("created must be pinned explicitly as YYYY-MM-DDTHH:MM:SSZ (SPEC-007 rule 14)")
    if status_change and not supersedes:
        raise NotPublishable("a disputed/rejected publication must supersede the earlier acceptance nanopublication")
    if supersedes and not re.fullmatch(r"https://w3id\.org/np/RA[A-Za-z0-9_-]{43}", supersedes):
        raise NotPublishable("supersedes must be a trusty nanopub URI of the earlier publication")
    t, a, rev, prop = v["target"], v["assessment"], v["review_event"], v["proposal_event"]
    kind, dec = t["kind"], v["decision"]
    tp = t["payload"]
    A, P = Graph(), Graph()
    idx = [0]
    top = "schema:ClaimReview" if kind == "Claim" else "schema:Review"
    label = f"Frontier review: {kind} {t['id']} @{t['version'][:12]}: {dec}"[:200]

    # ---- assertion: the review, dimension by dimension
    A.add("sub:review", "a", top)
    A.add("sub:review", "schema:name", esc(label))
    A.add("sub:review", "schema:itemReviewed", "sub:item")
    A.add("sub:review", "schema:author", "sub:reviewer")
    if kind == "Claim":
        A.add("sub:review", "schema:claimReviewed", esc(tp["statement"]))
    for d in DIMENSIONS:
        A.add("sub:review", "schema:hasPart", f"sub:dim_{d}")
    _pv(A, "sub:review", idx, "frontier_node_decision", dec, DECISION_MEANING[dec])
    _pv(A, "sub:review", idx, "review_policy_version", a["payload"]["policy_version"])
    _pv(A, "sub:review", idx, "aggregation", "none", "Seven separately reported dimensions. No combined score or confidence is defined or published.")
    _pv(A, "sub:review", idx, "independence_rationale", a["payload"]["independence_rationale"])
    _list_props(A, "sub:review", idx, "review_limitation", a["payload"]["limitations"])
    _pv(A, "sub:review", idx, "scope_limit", SCOPE_LIMIT)
    # reviewed item: quoted, uninterpreted
    A.add("sub:item", "a", "schema:Claim" if kind == "Claim" else "schema:CreativeWork")
    A.add("sub:item", "schema:name", esc(tp["title"]))
    A.add("sub:item", "schema:identifier", esc(ref_text(t)))
    A.add("sub:item", "schema:version", esc(t["version"]))
    if kind == "Claim":
        A.add("sub:item", "schema:text", esc(tp["statement"]))
        A.add("sub:item", "schema:description", esc(tp["context"]))
        _list_props(A, "sub:item", idx, "assumption", tp.get("assumptions"))
        _list_props(A, "sub:item", idx, "limitation", tp.get("limitations"))
    else:
        A.add("sub:item", "schema:description", esc(tp["known_state"]))
        _pv(A, "sub:item", idx, "question", tp["question"])
        _pv(A, "sub:item", idx, "problem_kind", tp["problem_kind"])
        _pv(A, "sub:item", idx, "completeness", tp.get("completeness", "not_stated_by_this_record_version"))
        for f in ("acceptance_criteria", "falsifiers"):
            _list_props(A, "sub:item", idx, f, tp.get(f))
        for f in ("next_action", "cost_stop_bounds"):
            if tp.get(f):
                _pv(A, "sub:item", idx, f, tp[f])
    src = tp.get("source") or {}
    has_source = bool(src.get("uri") or src.get("locator") or src.get("content_sha256"))
    if not has_source:
        _pv(A, "sub:item", idx, "source_status", "no source recorded",
            "Curator statement. It must not be read as a sourced field-level claim or open problem.")
    else:
        for k in ("uri", "locator", "source_version", "content_sha256", "access", "license"):
            if src.get(k):
                _pv(A, "sub:item", idx, k if k.startswith("source_") else "source_" + k, src[k])
        _pv(A, "sub:item", idx, "source_bytes_available_to_frontier", str(bool(src.get("content_available"))).lower(),
            "Frontier did not verify source bytes at submission; any content_sha256 is a declared pin.")
    if kind == "Claim" and tp.get("source_record_version"):
        _pv(A, "sub:item", idx, "source_record_version", tp["source_record_version"])
    # the seven dimensions
    ev_ids = {json.dumps(ref(e), sort_keys=True): f"sub:ev{i}" for i, e in enumerate(v["evidence"])}
    unres = {x: f"sub:evref{i}" for i, x in enumerate(v["unresolved_links"])}
    for d in DIMENSIONS:
        dd, n = v["dims"][d], f"sub:dim_{d}"
        A.add(n, "a", "schema:Review")
        A.add(n, "schema:reviewAspect", esc(d))
        A.add(n, "schema:itemReviewed", "sub:item")
        A.add(n, "schema:author", "sub:reviewer")
        A.add(n, "schema:reviewRating", f"sub:dim_{d}_rating")
        A.add(f"sub:dim_{d}_rating", "a", "schema:Rating")
        A.add(f"sub:dim_{d}_rating", "schema:alternateName", esc(dd["status"]))
        A.add(n, "schema:reviewBody", esc(dd["rationale"]))
        for link in dd.get("evidence_links", []):
            k = json.dumps(link, sort_keys=True)
            A.add(n, "schema:citation", ev_ids.get(k) or unres[k])
    for k, n in ev_ids.items():
        e = next(x for x in v["evidence"] if json.dumps(ref(x), sort_keys=True) == k)
        A.add(n, "a", "schema:CreativeWork")
        A.add(n, "schema:identifier", esc(ref_text(e)))
        A.add(n, "schema:version", esc(e["version"]))
        A.add(n, "schema:additionalType", esc("frontier Evidence: " + e["payload"]["evidence_kind"]))
        _pv(A, n, idx, "evidence_method", e["payload"]["method"])
    for k, n in unres.items():
        r = json.loads(k)
        A.add(n, "a", "schema:CreativeWork")
        A.add(n, "schema:identifier", esc(ref_text(r)))
        A.add(n, "schema:version", esc(r["version"]))
        _pv(A, n, idx, "resolution", "digest-pinned reference only; the linked record was not supplied to this publication")

    # ---- provenance: issuer, operator, exact version digests, node namespace
    q = a["namespace"]
    P.add("sub:assertion", "prov:wasAttributedTo", "sub:reviewer")
    P.add("sub:assertion", "prov:wasGeneratedBy", "sub:reviewActivity")
    for n in ("sub:assessmentRecord", "sub:targetRecord", "sub:reviewEventRecord", "sub:proposalEventRecord", *ev_ids.values()):
        P.add("sub:assertion", "prov:wasDerivedFrom", n)
    P.add("sub:assertion", "prov:wasDerivedFrom", f"<{REPO_URL}/tree/{code_commit}/frontier_pub>")
    for n, label_, ident in (("sub:reviewer", "reviewer (Frontier actor id)", a["issuer"]),
                             ("sub:reviewerOperator", "reviewing operator", rev["payload"]["operator"]),
                             ("sub:submitter", "target issuer (Frontier actor id)", t["issuer"]),
                             ("sub:submitterOperator", "submitting operator" if v["origin"] == "record_proposed" else "importing operator",
                              prop["payload"]["operator"])):
        P.add(n, "a", "prov:Agent")
        P.add(n, "rdfs:label", esc(label_))
        P.add(n, "schema:identifier", esc(ident))
    P.add("sub:reviewer", "prov:actedOnBehalfOf", "sub:reviewerOperator")
    P.add("sub:submitter", "prov:actedOnBehalfOf", "sub:submitterOperator")
    P.add("sub:reviewerOperator", "rdfs:comment", esc("Identity as configured on the reviewing Frontier node. This publication does not verify it."))
    P.add("sub:reviewNode", "a", "prov:Agent")
    P.add("sub:reviewNode", "rdfs:label", esc("reviewing Frontier node namespace"))
    P.add("sub:reviewNode", "schema:identifier", esc(q))
    P.add("sub:reviewNode", "rdfs:comment", esc("A Frontier node namespace string. It is not a registered IRI namespace and not a verified organisation."))
    P.add("sub:reviewActivity", "a", "prov:Activity")
    P.add("sub:reviewActivity", "prov:wasAssociatedWith", "sub:reviewer")
    P.add("sub:reviewActivity", "prov:wasAssociatedWith", "sub:reviewNode")
    P.add("sub:reviewActivity", "prov:used", "sub:targetRecord")
    P.add("sub:reviewActivity", "prov:endedAtTime", f'{esc(rev["payload"]["witnessed_at"])}^^xsd:dateTime')
    P.add("sub:reviewActivity", "rdfs:comment", esc("End time is the reviewing node's own clock (Event witnessed_at): declared by the node, not a third-party timestamp."))
    P.add("sub:proposalActivity", "a", "prov:Activity")
    P.add("sub:proposalActivity", "prov:wasAssociatedWith", "sub:submitter")
    P.add("sub:proposalActivity", "prov:generated", "sub:targetRecord")
    P.add("sub:proposalActivity", "prov:endedAtTime", f'{esc(prop["payload"]["witnessed_at"])}^^xsd:dateTime')
    if v["origin"] == "record_imported":
        P.add("sub:proposalActivity", "rdfs:comment", esc("Target was IMPORTED from another node; its issuer was not authenticated by the importing node."))
    recs = [("sub:assessmentRecord", a, "sub:reviewer", "sub:reviewActivity"), ("sub:targetRecord", t, "sub:submitter", "sub:proposalActivity"),
            ("sub:reviewEventRecord", rev, "sub:reviewer", None), ("sub:proposalEventRecord", prop, "sub:submitter", None)]
    for n, r, who, act in recs:
        P.add(n, "a", "prov:Entity")
        P.add(n, "schema:identifier", esc(ref_text(r)))
        P.add(n, "schema:version", esc(r["version"]))
        P.add(n, "rdfs:label", esc(f"Frontier {r['kind']} record version (digest above)"))
        P.add(n, "dct:created", f'{esc(r["created_at"])}^^xsd:dateTime')
        P.add(n, "prov:wasAttributedTo", who)
        if act:
            P.add(n, "prov:wasGeneratedBy", act)
    P.add("sub:targetRecord", "schema:provider", "sub:originNode")
    P.add("sub:assessmentRecord", "schema:provider", "sub:reviewNode")
    P.add("sub:originNode", "a", "prov:Agent")
    P.add("sub:originNode", "rdfs:label", esc("origin namespace of the reviewed record"))
    P.add("sub:originNode", "schema:identifier", esc(t["namespace"]))
    if vet_iri(src.get("uri")):
        P.add("sub:targetRecord", "prov:wasDerivedFrom", f"<{src['uri']}>")
    for e in v["evidence"]:
        n = ev_ids[json.dumps(ref(e), sort_keys=True)]
        P.add(n, "a", "prov:Entity")
        P.add(n, "rdfs:comment", esc("Frontier Evidence record; issuer actor id: " + e["issuer"]))
        if vet_iri((e["payload"].get("source") or {}).get("uri")):
            P.add(n, "prov:wasDerivedFrom", f"<{e['payload']['source']['uri']}>")

    # ---- pubinfo
    I = Graph()
    I.add("this:", "dct:created", f'"{created}"^^xsd:dateTime')
    I.add("this:", "dct:creator", f"<{REPO_URL}>")
    I.add("this:", "dct:license", f"<{LICENSE}>")
    I.add("this:", "dct:conformsTo", f"<{PROFILE_IRI}>")
    I.add("this:", "npx:hasNanopubType", top)
    I.add("this:", "npx:introduces", "sub:review")
    if supersedes:
        I.add("this:", "npx:supersedes", f"<{supersedes}>")
    I.add("this:", "rdfs:label", esc(label))
    I.add("this:", "rdfs:comment", esc(
        f"Publication-layer rendering ({PROFILE_VERSION}) of Frontier records. Frontier remains the system of record. This nanopublication is "
        "immutable; later Frontier changes (new versions, disputes, new evidence) are published only as superseding nanopublications and are NOT "
        "reflected here. Record digest recipe: " + DIGEST_RECIPE + "."))
    n_triples = A.n + P.n + I.n + 4
    if n_triples > 1100:
        raise NotPublishable(f"{n_triples} triples exceeds the registry limit of 1200 (SPEC-007 rule 12) with margin")
    head = ("sub:Head {\n  this: a np:Nanopublication ;\n    np:hasAssertion sub:assertion ;\n    np:hasProvenance sub:provenance ;\n"
            "    np:hasPublicationInfo sub:pubinfo .\n}\n\n")
    prefixes = (f"@prefix this: <{TEMP}> .\n@prefix sub: <{TEMP}#> .\n@prefix np: <http://www.nanopub.org/nschema#> .\n"
                "@prefix npx: <http://purl.org/nanopub/x/> .\n@prefix prov: <http://www.w3.org/ns/prov#> .\n"
                "@prefix dct: <http://purl.org/dc/terms/> .\n@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .\n"
                "@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .\n@prefix schema: <https://schema.org/> .\n\n")
    return (prefixes + head + "sub:assertion {\n" + A.render() + "}\n\nsub:provenance {\n" + P.render() + "}\n\nsub:pubinfo {\n" + I.render() + "}\n")


def count_triples(trig: str) -> int:
    s = re.sub(r'"(?:[^"\\]|\\.)*"', '""', trig)
    s = re.sub(r"<[^>]*>", "<>", s)
    return len(re.findall(r"[;,.](?=\s|$)", s))


def conform(trig: str, carried_iris: set[str] | None = None) -> list[str]:
    """Textual well-formedness/IRI-policy check (SPEC-031 R1-R9 subset, SPEC-007 rules 5 and 7). nanopub-rs parses for real on signing."""
    bad = []
    code = re.sub(r'"(?:[^"\\]|\\.)*"', '""', trig)
    for g in ("Head", "assertion", "provenance", "pubinfo"):
        if len(re.findall(rf"^sub:{g}\s*\{{", trig, flags=re.M)) != 1:
            bad.append(f"graph sub:{g} must appear exactly once")
    for m in re.findall(r"<([^>\s]*)>", code):
        if not m.startswith(("http://", "https://")):
            bad.append(f"non-http(s) IRI: {m}")
            continue
        if m.startswith(ALLOWED_NS) or m == REPO_URL or m.startswith(REPO_URL + "/") or (carried_iris and m in carried_iris):
            if m.startswith("https://w3id.org/") and not m.startswith("https://w3id.org/np/"):
                bad.append(f"IRI under an unregistered/unknown w3id namespace: {m}")
            continue
        if vet_iri(m):
            continue          # an existing external reference carried from a record (source uri)
        bad.append(f"IRI refused by policy: {m}")
    if re.search(r"example\.org|<urn:|<ms:", code):
        bad.append("forbidden example.org / urn: / ms: IRI")
    for pfx, ns in re.findall(r"@prefix\s+(\w*):\s*<([^>]+)>", code):
        if not ns.startswith(ALLOWED_NS):
            bad.append(f"prefix {pfx}: outside allowed namespaces: {ns}")
    for name in ("ratingValue", "bestRating", "worstRating", "confidence", "probability", "score"):
        if re.search(rf"\b{name}\b", code):
            bad.append(f"composite/numeric rating term present: {name}")
    if count_triples(trig) > 1200:
        bad.append("more than 1200 triples")
    if len(trig.encode()) > 1_000_000:
        bad.append("larger than 1,000,000 bytes")
    return bad


SIGNER_PREFIXES = ("http://www.w3.org/2004/02/skos/core#", "http://www.w3.org/2002/07/owl#", "https://orcid.org/")


def conform_signed(trig: str) -> list[str]:
    """After signing, nanopub-rs rewrites prefixes and graph names, so the structural text check does not apply (the signer's own parser and
    the independent verifier cover structure). The IRI policy and the no-composite-rating rule still must hold on the exact signed bytes."""
    bad = []
    code = re.sub(r'"(?:[^"\\]|\\.)*"', '""', trig)
    for m in re.findall(r"<([^>\s]*)>", code):
        ok = m.startswith(ALLOWED_NS) or m == REPO_URL or m.startswith(REPO_URL + "/") or m.startswith(SIGNER_PREFIXES) or vet_iri(m)
        if not ok or (m.startswith("https://w3id.org/") and not m.startswith("https://w3id.org/np/")):
            bad.append(f"IRI refused by policy: {m}")
    if re.search(r"example\.org|<urn:|<ms:", code):
        bad.append("forbidden example.org / urn: / ms: IRI")
    for name in ("ratingValue", "bestRating", "worstRating", "confidence", "probability", "score"):
        if re.search(rf"schema:{name}\b", code):
            bad.append(f"composite/numeric rating term present: {name}")
    if len(trig.encode()) > 1_000_000:
        bad.append("larger than 1,000,000 bytes")
    return bad
